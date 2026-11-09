import threading
import unittest
from unittest.mock import MagicMock

from robot.configuration import load_config
from robot.contact import clear_contacts, encode_contacts, setup_contact_sensors
from robot.contracts import CONTACT_DEVICE_NAMES, CONTACT_INPUTS, AIR_INPUTS, LEGS
from robot.live_inputs import LiveInputs


class ContactTests(unittest.TestCase):
    def test_pad_measurements_encode_independently_without_phase_selection(self):
        values = dict(FL=1.0, FR=0.0, RL=0.0, RR=1.0)
        self.assertEqual(encode_contacts(values), {
            **{name: [int(values[leg])] * 4 for leg, name in CONTACT_INPUTS.items()},
            **{name: [1-int(values[leg])] * 4 for leg, name in AIR_INPUTS.items()},
        })
        self.assertTrue(all(v == [0] * 4 for v in encode_contacts(values, suspended=True).values()))
        for bad in (float("nan"), float("inf"), -1, 0.2, 2, True, None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                encode_contacts(dict(values, FL=bad))
        with self.assertRaises(ValueError):
            encode_contacts(dict(FL=1))

    def test_each_real_bumper_is_required_and_enabled(self):
        sensors = {name: MagicMock(BUMPER=0) for name in CONTACT_DEVICE_NAMES.values()}
        for sensor in sensors.values():
            sensor.getType.return_value = 0
        body = MagicMock()
        body.getDevice.side_effect = sensors.get
        actual = setup_contact_sensors(body, 32)
        self.assertEqual(actual, {leg: sensors[name] for leg, name in CONTACT_DEVICE_NAMES.items()})
        for sensor in actual.values():
            sensor.enable.assert_called_once_with(32)
        sensors[CONTACT_DEVICE_NAMES["FR"]] = None
        with self.assertRaisesRegex(RuntimeError, "Missing foot TouchSensor.*front right"):
            setup_contact_sensors(body, 32)

    def test_wrong_sensor_type_is_not_silently_read_as_contact(self):
        body = MagicMock()
        body.getDevice.return_value = MagicMock(BUMPER=0)
        body.getDevice.return_value.getType.return_value = 2
        with self.assertRaisesRegex(RuntimeError, "must be a bumper"):
            setup_contact_sensors(body, 32)

    def test_contact_is_published_even_with_tilt_reflex_disabled(self):
        sent = threading.Event()
        logs = []
        publish = MagicMock(return_value=dict(ok=True, queued_for_hardware=True, atomic_frame=True))
        settings = dict(load_config()["reflex"], enabled=False)
        def record(event):
            logs.append(event)
            sent.set()
        with LiveInputs(publish, lambda: 10, settings, contact_record=record) as live:
            with self.assertRaisesRegex(ValueError, "measured foot contacts"):
                live.feedback([0, 0, 0], dict(value=0))
            live.feedback([0, 0, 0], dict(value=0), contacts=dict.fromkeys(LEGS, 1), native_step=7)
            self.assertTrue(sent.wait(1))
            self.assertEqual(logs[-1]["native_step"], 7)
            self.assertTrue(all(logs[-1]["inputs"][n] == [1] * 4 for n in CONTACT_INPUTS.values()) and all(logs[-1]["inputs"][n] == [0] * 4 for n in AIR_INPUTS.values()))
            sent.clear()
            live.feedback([0.2, 0, 0], dict(value=0), contacts=dict.fromkeys(LEGS, 1), tilt_suspended=True)
            self.assertTrue(sent.wait(1))
            self.assertTrue(all(logs[-1]["inputs"][n] == [1] * 4 for n in CONTACT_INPUTS.values()) and all(logs[-1]["inputs"][n] == [0] * 4 for n in AIR_INPUTS.values()))
            sent.clear()
            live.feedback([0, 0, 0], dict(value=0), contacts=dict.fromkeys(LEGS, 1), suspended=True)
            self.assertTrue(sent.wait(1))
            self.assertTrue(all(v == [0] * 4 for v in logs[-1]["inputs"].values()))
        self.assertEqual(publish.call_count, 3)

    def test_shutdown_clears_contact_and_rejects_unaccepted_frame(self):
        publish = MagicMock(return_value=dict(ok=True, queued_for_hardware=True, atomic_frame=True))
        clear_contacts(publish)
        self.assertEqual(publish.call_args.args[0], encode_contacts(dict.fromkeys(LEGS, 0), suspended=True))
        publish.return_value = dict(ok=True)
        with self.assertRaisesRegex(RuntimeError, "atomic queue acceptance"):
            clear_contacts(publish)

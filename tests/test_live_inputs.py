import threading
import time
import unittest
from unittest.mock import MagicMock

from robot.configuration import load_config
from robot.contracts import REWARD_INPUT, TILT_INPUTS, TILT_NEURONS
from robot.live_inputs import LiveInputs
from robot.transport import EventBuffer
from test_runtime import frame


ACCEPTED = dict(ok=True, queued_for_hardware=True, atomic_frame=True)


class LiveInputTests(unittest.TestCase):
    def make_sender(self, publish, **kwargs):
        return LiveInputs(publish, lambda: 50, load_config()["reflex"], **kwargs)

    def test_blocked_http_keeps_motor_delivery_running_and_only_latest_feedback(self):
        entered, release, last_sent = (threading.Event() for _ in range(3))
        sent, logs = [], []
        def publish(payload, **kwargs):
            sent.append(payload)
            if len(sent) == 1:
                entered.set()
                if not release.wait(3):
                    raise TimeoutError("test did not release HTTP")
            return dict(ACCEPTED)
        def record(event):
            logs.append(event)
            if event["native_step"] == 30:
                last_sent.set()
        inputs = self.make_sender(publish, tilt_record=record)
        events = EventBuffer()
        with inputs:
            try:
                inputs.feedback([-0.2, 0, 0], dict(value=0), native_step=0)
                self.assertTrue(entered.wait(1))
                delivered = []
                for step in range(1, 31):
                    events.on_output(frame(step, FL_HIP_POS=step % 2))
                    delivered.append(events.wait_one(time.monotonic() + 1)["step"])
                    inputs.feedback([0.2, 0, 0], dict(value=1), native_step=step)
                self.assertEqual(delivered, list(range(1, 31)))
                self.assertEqual(events.stats()["queued_frames"], 0)
                self.assertEqual(inputs.stats()["pending_feedback"], 1)
                self.assertEqual(inputs.stats()["replaced_unsent_feedback"], 29)
                self.assertEqual(len(sent), 1)
            finally:
                release.set()
            self.assertTrue(last_sent.wait(1))
        self.assertEqual([e["native_step"] for e in logs], [0, 30])
        self.assertEqual(len(sent), 2)
        self.assertEqual(sent[-1][REWARD_INPUT]["signal"], 1.0)

    def test_command_has_priority_and_discards_precommand_unsent_feedback(self):
        entered, release = threading.Event(), threading.Event()
        sent = []
        def publish(payload, **kw):
            sent.append(payload)
            if len(sent) == 1:
                entered.set()
                if not release.wait(3):
                    raise TimeoutError("test did not release HTTP")
            return dict(ACCEPTED)
        with self.make_sender(publish) as inputs:
            try:
                inputs.feedback([0.2, 0, 0], dict(value=1))
                self.assertTrue(entered.wait(1))
                inputs.feedback([-0.2, 0, 0], dict(value=1))
                receipt = inputs.command(dict(WALK_START=[0.0], WALK_STOP=[1.0]))
                self.assertFalse(receipt.ready.is_set())
                self.assertEqual(inputs.stats()["pending_feedback"], 0)
            finally:
                release.set()
            self.assertTrue(receipt.ready.wait(1))
            self.assertEqual(receipt.after_step, 50)
            self.assertIsNone(receipt.error)
        self.assertEqual(len(sent), 2)
        self.assertEqual(set(sent[-1]), {"WALK_START", "WALK_STOP"})

    def test_rejected_command_reports_failure_without_retry(self):
        publish = MagicMock(return_value=dict(ok=False))
        with self.assertRaisesRegex(RuntimeError, "queue acceptance"):
            with self.make_sender(publish) as inputs:
                receipt = inputs.command(dict(WALK_STOP=[1.0]))
                self.assertTrue(receipt.ready.wait(1))
                self.assertIn("queue acceptance", receipt.error)
        # Failure is still visible if it arrives during shutdown.
        with self.assertRaisesRegex(RuntimeError, "queue acceptance"):
            inputs.check_health()
        publish.assert_called_once()

    def test_shutdown_joins_inflight_request_and_discards_unsent_feedback(self):
        entered, release, finished = (threading.Event() for _ in range(3))
        sent = []
        def publish(payload, **kw):
            sent.append(payload)
            entered.set()
            if not release.wait(3):
                raise TimeoutError("test did not release HTTP")
            return dict(ACCEPTED)
        inputs = self.make_sender(publish).__enter__()
        inputs.feedback([0.2, 0, 0], dict(value=1))
        self.assertTrue(entered.wait(1))
        inputs.feedback([-0.2, 0, 0], dict(value=1))
        def close():
            inputs.close()
            finished.set()
        closer = threading.Thread(target=close)
        closer.start()
        try:
            self.assertFalse(finished.wait(0.02))
        finally:
            release.set()
            closer.join(2)
        self.assertTrue(finished.is_set())
        self.assertEqual(len(sent), 1)
        with self.assertRaisesRegex(RuntimeError, "closed"):
            inputs.command(dict(WALK_STOP=[1.0]))

    def test_public_sdk_encodes_tilt_and_ten_reward_neurons_in_one_atomic_frame(self):
        from ab_sdk.encoder import SpikeEncoder
        from ab_sdk.maps import InputSensorMap
        from ab_sdk.session import RealtimeSession
        session = RealtimeSession.__new__(RealtimeSession)
        session.compile_id = "test-install"
        session.encoder = SpikeEncoder(InputSensorMap([
            *[dict(inputId=name, sensor=name, n=TILT_NEURONS) for name in TILT_INPUTS],
            dict(inputId=REWARD_INPUT, sensor=REWARD_INPUT, n=10),
        ]))
        session.input_client = MagicMock()
        session.input_client.send_frame.return_value = dict(ACCEPTED)
        published = threading.Event()
        with self.make_sender(session.publish_sensor_frame,
                              reward_record=lambda e: published.set()) as inputs:
            inputs.feedback([-0.2, 0.2, 0], dict(value=1), native_step=7)
            self.assertTrue(published.wait(1))
            inputs.check_health()
        session.input_client.send_frame.assert_called_once()
        events = session.input_client.send_frame.call_args.kwargs["events"]
        payload = {event["target"]: event["payload"] for event in events}
        self.assertEqual(payload, {
            **{name: [int(name in ("TILT_ROLL_NEG", "TILT_PITCH_POS"))] * 12
               for name in TILT_INPUTS},
            REWARD_INPUT: [1] * 10,
        })
        self.assertTrue(all("step" not in event for event in events))


if __name__ == "__main__":
    unittest.main()

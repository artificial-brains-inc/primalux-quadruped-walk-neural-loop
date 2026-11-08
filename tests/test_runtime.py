import unittest
from collections import deque
from unittest.mock import patch

from robot.configuration import load_config
from robot.contracts import COMMAND_INPUT_SIZES, INPUT_SIZES, OUTPUT_SIZES, REWARD_INPUT
from robot.decoder import joint_targets
from robot.exchange import CommandExchange
from robot.transport import EventBuffer


def frame(step, **changes):
    channels = {k: 0 for k in OUTPUT_SIZES}
    channels.update(changes)
    return dict(step=step, actuation=dict(channels=channels))


class Frames:
    def __init__(self, items):
        self.items = deque(items)
        self.cursor = 0

    def wait_one(self, deadline):
        if not self.items:
            raise TimeoutError("No neural output")
        result = self.items.popleft()
        self.cursor = result["step"]
        return result

    def stats(self):
        return dict(last_received_step=self.cursor, queued_frames=0)


class RuntimeTests(unittest.TestCase):
    def test_ack_does_not_clear_start_while_rest_is_still_active(self):
        events = Frames(
            [
                frame(1),
                frame(2, TRANSPORT_ACK_OUT=1, REST_ACTIVE=1),
                frame(3, REST_ACTIVE=1),
                frame(4, WALK_ENABLED=1, REST_ACTIVE=1),
                frame(5, WALK_ENABLED=1),
                frame(6, PHASE_A_OUT=1),
            ]
        )
        sends, records = [], []

        def publish(payload, **kw):
            sends.append(payload)
            self.assertEqual(kw, dict(mode="vector_f32"))
            return dict(ok=True, queued_for_hardware=True, atomic_frame=True)

        exchange = CommandExchange(publish, events, 1, record=records.append)
        exchange.initialize_inputs()
        ack = exchange.command("start")
        self.assertEqual(ack["step"], 2)
        self.assertEqual(
            sends[1], dict(WALK_START=[1.0], WALK_STOP=[0.0], TRANSPORT_ACK=[1.0])
        )
        self.assertEqual(sends[2], {"TRANSPORT_ACK": [0.0]})
        self.assertIsNone(exchange.observe(ack))
        self.assertIsNone(exchange.observe(events.wait_one(99)))
        self.assertIsNone(exchange.observe(events.wait_one(99)))
        self.assertEqual(len(sends), 3)  # No refreshes or premature goal clearing.
        self.assertEqual(exchange.pending_action, "start")
        self.assertEqual(exchange.observe(events.wait_one(99)), "start")
        self.assertTrue(all(v == [0.0] for v in sends[3].values()))
        self.assertIsNone(exchange.pending_action)
        self.assertIsNone(exchange.observe(events.wait_one(99)))
        self.assertEqual(len(sends), 4)
        self.assertTrue(all(REWARD_INPUT not in payload for payload in sends))
        self.assertEqual(
            [r["step"] for r in records if r["kind"] == "command_confirmed"], [5]
        )

    def test_stop_waits_for_walk_to_clear_before_releasing_its_request(self):
        sends = []

        def publish(payload, **kw):
            sends.append(payload)
            return dict(ok=True, queued_for_hardware=True, atomic_frame=True)

        events = Frames([frame(1), frame(2, TRANSPORT_ACK_OUT=1, WALK_ENABLED=1)])
        exchange = CommandExchange(publish, events, 1)
        exchange.command("stop")
        self.assertIsNone(exchange.observe(frame(3, WALK_ENABLED=1, REST_ACTIVE=1)))
        self.assertEqual(len(sends), 2)
        self.assertEqual(exchange.observe(frame(4, REST_ACTIVE=1)), "stop")
        self.assertEqual(len(sends), 3)

    def test_old_readout_cannot_confirm_a_fresh_command(self):
        exchange = CommandExchange(
            lambda *a, **k: dict(ok=True, queued_for_hardware=True, atomic_frame=True),
            Frames([frame(10), frame(11, TRANSPORT_ACK_OUT=1)]),
            1,
        )
        exchange.command("start")
        self.assertIsNone(exchange.observe(frame(9, WALK_ENABLED=1)))
        self.assertEqual(exchange.pending_action, "start")

    def test_goal_timeout_reports_rest_lock_and_fails_without_retrying(self):
        sends, records = [], []

        def publish(payload, **kw):
            sends.append(payload)
            return dict(ok=True, queued_for_hardware=True, atomic_frame=True)

        exchange = CommandExchange(
            publish,
            Frames([frame(1), frame(2, TRANSPORT_ACK_OUT=1)]),
            30,
            record=records.append,
        )
        with patch("robot.exchange.time.monotonic", return_value=100):
            exchange.command("start")
        with patch("robot.exchange.time.monotonic", return_value=130):
            with self.assertRaisesRegex(TimeoutError, "WALK_ENABLED=0, REST_ACTIVE=1"):
                exchange.observe(frame(3, REST_ACTIVE=1))
        self.assertEqual(len(sends), 2)
        self.assertEqual(records[-1]["kind"], "command_timeout")
        with self.assertRaises(RuntimeError):
            exchange.command("start")

    def test_stop_can_replace_a_start_that_has_not_confirmed(self):
        sends, records = [], []

        def publish(payload, **kw):
            sends.append(payload)
            return dict(ok=True, queued_for_hardware=True, atomic_frame=True)

        events = Frames(
            [
                frame(1),
                frame(2, TRANSPORT_ACK_OUT=1, REST_ACTIVE=1),
                frame(3, REST_ACTIVE=1),
                frame(4, TRANSPORT_ACK_OUT=1, REST_ACTIVE=1),
            ]
        )
        exchange = CommandExchange(publish, events, 1, record=records.append)
        exchange.command("start")
        ack = exchange.command("stop")
        self.assertEqual(
            sends[2], dict(WALK_START=[0.0], WALK_STOP=[1.0], TRANSPORT_ACK=[1.0])
        )
        self.assertEqual(exchange.observe(ack), "stop")
        self.assertEqual(
            [r["replacement"] for r in records if r["kind"] == "command_superseded"],
            ["stop"],
        )

    def test_ack_failure_cannot_release_a_command_or_retry_it(self):
        sent = []

        def publish(payload, **kw):
            sent.append(payload)
            return dict(ok=True, queued_for_hardware=True, atomic_frame=True)

        exchange = CommandExchange(
            publish, Frames([frame(1), frame(2, FL_HIP_POS=1)]), 1
        )
        with self.assertRaises(TimeoutError):
            exchange.command("start")
        with self.assertRaises(RuntimeError):
            exchange.command("start")
        self.assertEqual(len(sent), 1)

    def test_queue_acceptance_is_not_neural_ack(self):
        exchange = CommandExchange(lambda *a, **k: dict(ok=True), Frames([frame(1)]), 1)
        with self.assertRaisesRegex(RuntimeError, "acceptance"):
            exchange.command("stop")

    def test_decoder_never_uses_phase_or_enable_as_a_gait_selector(self):
        config = load_config()
        baseline = joint_targets(frame(1), config)
        changed = joint_targets(
            frame(
                2,
                PHASE_A_OUT=1,
                PHASE_B_OUT=1,
                WALK_ENABLED=1,
                REST_ACTIVE=1,
                START_A_BIAS=1,
                PHASE_A_INHIBITOR_OUT=1,
                PHASE_B_INHIBITOR_OUT=1,
                PHASE_A_RELEASE_OUT=1,
                PHASE_B_RELEASE_OUT=1,
            ),
            config,
        )
        self.assertEqual(baseline, changed)
        driven = joint_targets(frame(3, FL_HIP_POS=1), config)
        self.assertGreater(driven[("FL", "HIP")], baseline[("FL", "HIP")])
        self.assertEqual(
            [k for k in baseline if baseline[k] != driven[k]], [("FL", "HIP")]
        )
        cancelled = joint_targets(frame(4, FL_KNEE_POS=1, FL_KNEE_NEG=1), config)
        self.assertEqual(cancelled, baseline)
        self.assertEqual(
            joint_targets(frame(5, FL_HIP_POS=1), config, rhythm_only=True), baseline
        )

    def test_missing_native_frame_fails_instead_of_inventing_motion(self):
        events = EventBuffer()
        events.on_output(frame(1))
        events.on_output(frame(3))
        with self.assertRaisesRegex(RuntimeError, "Missing Prima-Lux"):
            events.check_health()

    def test_only_one_outcome_neuron_is_added_to_the_command_inputs(self):
        self.assertEqual(
            COMMAND_INPUT_SIZES, dict(WALK_START=1, WALK_STOP=1, TRANSPORT_ACK=1)
        )
        self.assertEqual(INPUT_SIZES, {**COMMAND_INPUT_SIZES, REWARD_INPUT: 1})


if __name__ == "__main__":
    unittest.main()

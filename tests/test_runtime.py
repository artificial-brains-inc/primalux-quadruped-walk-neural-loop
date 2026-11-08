import unittest
from collections import deque
from unittest.mock import patch

from robot.configuration import load_config
from robot.contracts import (
    COMMAND_INPUT_SIZES,
    INPUT_SIZES,
    OUTPUT_SIZES,
    REWARD_INPUT,
    REWARD_INPUT_NEURONS,
    TILT_INPUTS,
    TILT_NEURONS,
)
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
    def sender(self, cursor=10):
        from robot.live_inputs import Receipt
        import time
        self.sent = []
        def submit(payload):
            self.sent.append(payload)
            receipt = Receipt()
            receipt.after_step = cursor
            receipt.accepted_at = time.monotonic()
            receipt.ready.set()
            return receipt
        return submit

    def test_command_is_one_event_with_no_ack_or_confirmation_resend(self):
        exchange = CommandExchange(self.sender(), 30)
        exchange.initialize_inputs()
        exchange.command("start")
        self.assertEqual(self.sent, [dict.fromkeys(COMMAND_INPUT_SIZES, [0.0]),
                                     dict(WALK_START=[1.0], WALK_STOP=[0.0])])
        self.assertIsNone(exchange.observe(frame(11, REST_ACTIVE=1)))
        self.assertIsNone(exchange.observe(frame(12, WALK_ENABLED=1, REST_ACTIVE=1)))
        self.assertEqual(exchange.observe(frame(13, WALK_ENABLED=1)), "start")
        self.assertIsNone(exchange.observe(frame(14, WALK_ENABLED=1)))
        self.assertEqual(len(self.sent), 2)

    def test_ack_output_is_irrelevant_and_old_goals_do_not_confirm(self):
        exchange = CommandExchange(self.sender(), 30)
        exchange.command("start")
        self.assertIsNone(exchange.observe(frame(10, WALK_ENABLED=1, TRANSPORT_ACK_OUT=1)))
        self.assertIsNone(exchange.observe(frame(11, REST_ACTIVE=1, TRANSPORT_ACK_OUT=1)))
        self.assertEqual(exchange.observe(frame(12, WALK_ENABLED=1)), "start")

    def test_body_can_observe_frames_while_http_request_is_pending(self):
        from robot.live_inputs import Receipt
        receipt = Receipt()
        exchange = CommandExchange(lambda _: receipt, 30)
        exchange.command("start")
        for i in range(20):
            self.assertIsNone(exchange.observe(frame(i, WALK_ENABLED=1)))
        self.assertEqual(exchange.pending_action, "start")

    def test_stop_replaces_pending_start_without_ack_wait(self):
        records = []
        exchange = CommandExchange(self.sender(), 30, records.append)
        exchange.command("start")
        exchange.command("stop")
        self.assertEqual(exchange.observe(frame(11, REST_ACTIVE=1)), "stop")
        self.assertEqual([r['replacement'] for r in records if r['kind']=='command_superseded'], ['stop'])
        self.assertEqual(len(self.sent), 2)

    def test_goal_timeout_reports_state_without_resending(self):
        exchange = CommandExchange(self.sender(), 30)
        exchange.command("start")
        exchange.receipt.accepted_at = 100
        with patch("robot.exchange.time.monotonic", return_value=130):
            with self.assertRaisesRegex(TimeoutError, "WALK_ENABLED=0, REST_ACTIVE=1"):
                exchange.observe(frame(11, REST_ACTIVE=1))
        self.assertEqual(len(self.sent), 1)
        with self.assertRaises(RuntimeError):
            exchange.command("start")

    def test_publication_error_is_not_treated_as_goal_acceptance(self):
        exchange = CommandExchange(self.sender(), 30)
        exchange.command("stop")
        exchange.receipt.error = "request rejected"
        with self.assertRaisesRegex(RuntimeError, "request rejected"):
            exchange.observe(frame(11, REST_ACTIVE=1))

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
                PHASE_A_REQUEST=1,
                PHASE_B_REQUEST=1,
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

    def test_reward_and_tilt_populations_are_separate_from_commands(self):
        self.assertEqual(
            COMMAND_INPUT_SIZES, dict(WALK_START=1, WALK_STOP=1, TRANSPORT_ACK=1)
        )
        self.assertEqual(
            INPUT_SIZES,
            {
                **COMMAND_INPUT_SIZES,
                REWARD_INPUT: REWARD_INPUT_NEURONS,
                **dict.fromkeys(TILT_INPUTS, TILT_NEURONS),
            },
        )


if __name__ == "__main__":
    unittest.main()

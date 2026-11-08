import contextlib
import importlib.util
import io
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from test_runtime import Frames, frame

from robot.configuration import ROOT


class ControllerIntegrationTests(unittest.TestCase):
    def exercise(
        self,
        native_frames,
        keyboard_steps,
        last_body_step,
        *,
        mode="walk",
        moving=False,
        reject_reward=False,
    ):
        with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as stack:
            root = Path(tmp)
            calls = []
            sent = []

            class Device:
                def enable(self, dt):
                    pass

                def getMaxVelocity(self):
                    return 2

                def setVelocity(self, value):
                    pass

                def setPosition(self, value):
                    pass

                def getValue(self):
                    return 0

                def getValues(self):
                    return [body.steps * 0.01 if moving else 0, 0, 0.624]

                def getRollPitchYaw(self):
                    return [0, 0, 0]

            class Keyboard(Device):
                last_read_step = -1

                def getKey(self):
                    if self.last_read_step == body.steps:
                        return -1
                    self.last_read_step = body.steps
                    return keyboard_steps.get(body.steps, -1)

            class Body:
                steps = 0

                def getDevice(self, name):
                    return Device()

                def getKeyboard(self):
                    return Keyboard()

                def getTime(self):
                    return self.steps * 0.032

                def step(self, dt):
                    self.steps += 1
                    calls.append("physics")
                    if self.steps > last_body_step:
                        raise AssertionError("Controller did not honor Q")
                    return 0

            body = Body()

            class Buffer(Frames):
                def __init__(self, *a, record, **kw):
                    super().__init__(native_frames)
                    self.record = record

                def wait_one(self, deadline):
                    result = super().wait_one(deadline)
                    self.record(result)
                    calls.append("frame" + str(result["step"]))
                    return result

                def check_health(self):
                    pass

                def on_output(self, e):
                    pass

                def on_control(self, e):
                    pass

            session = MagicMock()

            def publish(payload, **kw):
                sent.append((body.steps, payload))
                return dict(ok=True, queued_for_hardware=True, atomic_frame=True)

            session.publish_sensor_frame.side_effect = publish
            session.publish_reward.return_value = dict(
                ok=not reject_reward, queued_for_hardware=not reject_reward
            )
            client = MagicMock()
            client.start_from_env.return_value = session
            stack.enter_context(
                patch.dict(
                    "sys.modules",
                    {"controller": types.SimpleNamespace(Robot=lambda: body)},
                )
            )
            stack.enter_context(patch.dict("os.environ", {"SPOT_RUN_MODE": mode}))
            stack.enter_context(patch("ab.ABClient.from_env", return_value=client))
            stack.enter_context(patch("robot.application.verify_installed"))
            output = io.StringIO()
            stack.enter_context(contextlib.redirect_stdout(output))
            spec = importlib.util.spec_from_file_location(
                "robot._controller_test", ROOT / "robot/controller.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.ROOT, module.EventBuffer = root, Buffer
            if reject_reward:
                with self.assertRaisesRegex(RuntimeError, "Reward input"):
                    module.main()
            else:
                module.main()
            rows = [
                json.loads(line)
                for path in root.glob("logs/run-*/observations.jsonl")
                for line in path.read_text().splitlines()
            ]
            session.stop.assert_called_once()
            self.reward_calls = list(session.publish_reward.call_args_list)
            self.assertEqual(self.reward_calls[0].args[1], 0.0)
            self.assertEqual(self.reward_calls[-1].args[1], 0.0)
            client.close.assert_called_once()
            self.assertEqual(
                json.loads((root / "logs/run_state.json").read_text())["state"],
                "ERROR" if reject_reward else "STOPPED",
            )

            return rows, sent, calls, output.getvalue()

    def test_failed_reward_clear_still_stops_the_brain(self):
        self.exercise([], {}, 1, mode="learn", reject_reward=True)

    def test_start_stream_stop_has_no_periodic_input_or_host_phase_switch(self):
        rows, sent, calls, output = self.exercise(
            [
                frame(1),
                frame(2, TRANSPORT_ACK_OUT=1, REST_ACTIVE=1),
                frame(3, REST_ACTIVE=1),
                frame(4, TRANSPORT_ACK_OUT=1, WALK_ENABLED=1, FL_HIP_POS=1),
                frame(5, WALK_ENABLED=1, PHASE_A_OUT=1, FL_HIP_POS=1),
                frame(6, WALK_ENABLED=1, PHASE_B_OUT=1, FR_HIP_POS=1),
                frame(7, WALK_ENABLED=1),
                frame(8, TRANSPORT_ACK_OUT=1, REST_ACTIVE=1),
            ],
            {2: ord("W"), 5: ord("S"), 6: ord("Q")},
            6,
        )
        self.assertEqual(len(sent), 10)  # Initial zeros + command/ACK-clear/goal-clear.
        self.assertEqual(sum(p.get("WALK_START", [0])[0] for _, p in sent), 1)
        self.assertEqual(sum(p.get("WALK_STOP", [0])[0] for _, p in sent), 2)
        self.assertEqual([r["native_step"] for r in rows], [2, 4, 5, 6, 8])
        self.assertEqual(calls.count("physics"), 6)
        self.assertGreater(rows[1]["joint_target_rad"]["FL_HIP"], 0)
        self.assertEqual(rows[-1]["joint_target_rad"]["FL_HIP"], 0)
        self.assertIn("W received", output)
        self.assertIn("START confirmed", output)

    def test_physics_keeps_advancing_after_ack_while_rest_is_still_active(self):
        rows, sent, calls, output = self.exercise(
            [
                frame(1),
                frame(2, TRANSPORT_ACK_OUT=1, REST_ACTIVE=1),
                frame(3, REST_ACTIVE=1),
                frame(4, TRANSPORT_ACK_OUT=1, REST_ACTIVE=1),
                frame(5, REST_ACTIVE=1),
                frame(6, REST_ACTIVE=1),
                frame(7, WALK_ENABLED=1, FL_HIP_POS=1),
                frame(8, WALK_ENABLED=1),
            ],
            {2: ord("W"), 7: ord("Q")},
            7,
        )
        self.assertEqual([r["native_step"] for r in rows], [2, 4, 5, 6, 7, 8])
        self.assertEqual(
            [r["pending_command"] for r in rows],
            [None, "start", "start", "start", None, None],
        )
        self.assertEqual(calls.count("physics"), len(rows) + 1)
        self.assertEqual(
            len(sent), 7
        )  # No sends during the three pending motor frames.
        self.assertEqual(
            sent[-1][0], 5
        )  # Confirmation clears START after body has advanced.
        self.assertEqual(sum(p.get("WALK_START", [0])[0] for _, p in sent), 1)
        self.assertIn("START ACK received", output)
        self.assertIn("START confirmed", output)

    def test_a_fresh_w_keypress_can_request_start_again(self):
        rows, sent, calls, output = self.exercise(
            [
                frame(1),
                frame(2, TRANSPORT_ACK_OUT=1, REST_ACTIVE=1),
                frame(3, REST_ACTIVE=1),
                frame(4, TRANSPORT_ACK_OUT=1, WALK_ENABLED=1),
                frame(5, WALK_ENABLED=1),
                frame(6, WALK_ENABLED=1),
                frame(7, TRANSPORT_ACK_OUT=1, WALK_ENABLED=1),
                frame(8, WALK_ENABLED=1),
            ],
            {2: ord("W"), 4: ord("W"), 6: ord("Q")},
            6,
        )
        self.assertEqual(sum(p.get("WALK_START", [0])[0] for _, p in sent), 2)
        self.assertEqual(output.count("W received"), 2)

    def test_learning_reward_uses_post_step_movement_only_after_confirmation(self):
        rows, sent, calls, output = self.exercise(
            [
                frame(1),
                frame(2, TRANSPORT_ACK_OUT=1, REST_ACTIVE=1),
                frame(3, REST_ACTIVE=1),
                frame(4, TRANSPORT_ACK_OUT=1, REST_ACTIVE=1),
                frame(5, REST_ACTIVE=1),
                frame(6, WALK_ENABLED=1),
                frame(7, WALK_ENABLED=1),
                frame(8, TRANSPORT_ACK_OUT=1, REST_ACTIVE=1),
            ],
            {2: ord("W"), 5: ord("S"), 6: ord("Q")},
            6,
            mode="learn",
            moving=True,
        )
        self.assertEqual([r["reward"]["value"] for r in rows], [0, 0, 0, 1, 0])
        self.assertEqual(
            [r["simulation_time"] for r in rows], [i * 0.032 for i in range(2, 7)]
        )
        self.assertEqual([c.args[1] for c in self.reward_calls], [0, 1, 0, 0])
        self.assertTrue(all("GAIT_REWARD_IN" not in p for _, p in sent))
        self.assertEqual(calls.count("physics"), len(rows) + 1)

    def test_rhythm_and_walk_modes_do_not_publish_positive_reward(self):
        for mode in ("rhythm", "walk"):
            rows, _, _, _ = self.exercise(
                [
                    frame(1),
                    frame(2, TRANSPORT_ACK_OUT=1, REST_ACTIVE=1),
                    frame(3),
                    frame(4, TRANSPORT_ACK_OUT=1, WALK_ENABLED=1),
                    frame(5, WALK_ENABLED=1),
                ],
                {2: ord("W"), 4: ord("Q")},
                4,
                mode=mode,
                moving=True,
            )
            self.assertTrue(all(r["reward"]["value"] == 0 for r in rows))
            self.assertTrue(all(c.args[1] == 0 for c in self.reward_calls))


if __name__ == "__main__":
    unittest.main()

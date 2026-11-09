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

from robot.live_inputs import LiveInputs
from robot.configuration import ROOT
from robot.contracts import COMMAND_INPUT_SIZES, TILT_INPUTS, TILT_NEURONS, REWARD_INPUT, CONTACT_INPUTS, AIR_INPUTS, CONTACT_DEVICE_NAMES, LEGS


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
        recovery_settings=None,
        fallen_from_step=None,
        physics_step_ms=32,
        tilt_rpy=None,
        reject_tilt=False,
        contact_values=None,
    ):
        with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as stack:
            root = Path(tmp)
            calls = []
            sent = []

            class Device:
                BUMPER = 0

                def __init__(self, name=""):
                    self.name = name

                def getType(self):
                    return self.BUMPER

                def enable(self, dt):
                    pass

                def getMaxVelocity(self):
                    return 2

                def enableTorqueFeedback(self, dt):
                    pass

                def getTorqueFeedback(self):
                    return 12.5

                def setVelocity(self, value):
                    pass

                def setPosition(self, value):
                    pass

                def getValue(self):
                    for leg, name in CONTACT_DEVICE_NAMES.items():
                        if self.name == name:
                            return (contact_values or dict.fromkeys(LEGS, 0))[leg]
                    return 0

                def getValues(self):
                    return [body.steps * 0.01 if moving else 0, 0, 0.624]

                def getRollPitchYaw(self):
                    if (
                        fallen_from_step is not None
                        and body.steps >= fallen_from_step
                        and not body.restored
                    ):
                        return [3.14, 0, 0]
                    return (
                        tilt_rpy
                        if tilt_rpy and body.steps >= 3 and not body.restored
                        else [0, 0, 0]
                    )

            class Keyboard(Device):
                last_read_step = -1

                def getKey(self):
                    if self.last_read_step == body.steps:
                        return -1
                    self.last_read_step = body.steps
                    return keyboard_steps.get(body.steps, -1)

            class Body:
                steps = 0
                restored = False
                elapsed = 0.0

                def getSelf(self):
                    return self

                def getCenterOfMass(self):
                    return [0.0, 0.0, 0.5]

                def getFromDevice(self, device):
                    return types.SimpleNamespace(getPosition=lambda: [0.1, 0.2, 0.03])

                def loadState(self, name):
                    self.restored = True
                    calls.append("restore:" + name)

                def resetPhysics(self):
                    calls.append("reset_physics")

                def getDevice(self, name):
                    return Device(name)

                def getKeyboard(self):
                    return Keyboard()

                def getTime(self):
                    return self.elapsed

                def step(self, dt):
                    self.steps += 1
                    self.elapsed = self.steps * dt / 1000
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
                if (reject_tilt and set(TILT_INPUTS) <= set(payload)) or (
                    reject_reward and REWARD_INPUT in payload
                ):
                    return dict(ok=False)
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
                    {"controller": types.SimpleNamespace(Supervisor=lambda: body)},
                )
            )
            stack.enter_context(patch.dict("os.environ", {"SPOT_RUN_MODE": mode}))
            stack.enter_context(patch("ab.ABClient.from_env", return_value=client))
            stack.enter_context(patch("robot.application.verify_installed"))
            from ab import Brain
            companion = "static" if mode == "walk" else "learning"
            stack.enter_context(patch("robot.application.saved_design", return_value=Brain.load(ROOT / "designs" / (companion + ".abdesign.json"))))
            recorder = stack.enter_context(
                patch("robot.neuron_recording.NeuronRecorder")
            )
            output = io.StringIO()
            stack.enter_context(contextlib.redirect_stdout(output))
            spec = importlib.util.spec_from_file_location(
                "robot._controller_test", ROOT / "robot/controller.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            class InlineInputs(LiveInputs):
                # Deterministic integration harness. Threaded delivery is tested
                # separately with actual blocked HTTP requests in test_live_inputs.
                def __enter__(self):
                    return self

                def command(self, payload):
                    receipt = super().command(payload)
                    self._deliver(command=self.commands.popleft())
                    return receipt

                def feedback(self, *args, **kwargs):
                    tilt = super().feedback(*args, **kwargs)
                    capture, self.latest = self.latest, None
                    self._deliver(capture=capture)
                    return tilt

            module.LiveInputs = InlineInputs
            module.ROOT, module.EventBuffer = root, Buffer
            config = module.load_config()
            config["physics_step_ms"] = physics_step_ms
            if recovery_settings:
                config["recovery"].update(recovery_settings)
            module.load_config = lambda: config
            if reject_reward or reject_tilt:
                with self.assertRaisesRegex(
                    RuntimeError, "Reward input|Tilt inputs|queue acceptance"
                ):
                    module.main()
            else:
                module.main()
            rows = [
                json.loads(line)
                for path in root.glob("logs/run-*/observations.jsonl")
                for line in path.read_text().splitlines()
            ]
            for row in rows:
                self.assertEqual(row["center_of_mass_xyz_m"], [0.0, 0.0, 0.5])
                self.assertEqual(len(row["foot_center_xyz_m"]), 4)
                self.assertEqual(len(row["joint_motor_torque_nm"]), 12)
                self.assertEqual(row["physical_measurement_errors"], {})
            self.run_settings = json.loads(
                next(root.glob("logs/run-*/settings.json")).read_text()
            )
            recorder.return_value.start.assert_called_once()
            recorder.return_value.stop.assert_called_once()
            session.stop.assert_called_once()
            self.reward_calls = list(session.publish_reward.call_args_list)
            self.assertEqual(self.reward_calls[0].args[1], 0.0)
            self.assertEqual(self.reward_calls[-1].args[1], 0.0)
            client.close.assert_called_once()
            self.assertEqual(
                json.loads((root / "logs/run_state.json").read_text())["state"],
                "ERROR" if reject_reward or reject_tilt else "STOPPED",
            )

            self.tilt_calls = [
                (step, p) for step, p in sent if set(p) == set(TILT_INPUTS)
            ]
            self.contact_clear_calls = [
                (step, p) for step, p in sent if set(p) == set((*CONTACT_INPUTS.values(), *AIR_INPUTS.values()))
            ]
            command_calls = [
                (step, p) for step, p in sent if set(p) <= set(COMMAND_INPUT_SIZES)
            ]
            self.feedback_calls = [
                (step, p) for step, p in sent if REWARD_INPUT in p
            ]
            self.assertEqual(
                len(command_calls) + len(self.tilt_calls) + len(self.feedback_calls) + len(self.contact_clear_calls),
                len(sent),
            )
            self.assertFalse(any(p.get("TRANSPORT_ACK", [0])[0] for _, p in sent))
            return rows, command_calls, calls, output.getvalue()

    def test_w_pending_goal_keeps_every_frame_and_physics_running_without_ack(self):
        frames = [frame(1, REST_ACTIVE=1), frame(2, REST_ACTIVE=1),
                  frame(3, REST_ACTIVE=1), frame(4, WALK_ENABLED=1, FL_HIP_POS=1),
                  frame(5, WALK_ENABLED=1)]
        rows, sent, calls, output = self.exercise(frames, {2: ord("W"), 6: ord("Q")}, 6)
        self.assertEqual([r["native_step"] for r in rows], [1, 2, 3, 4, 5])
        self.assertEqual([r["pending_command"] for r in rows],
                         [None, "start", "start", None, None])
        self.assertEqual(calls.count("physics"), len(rows) + 1)
        self.assertEqual(sum(p.get("WALK_START", [0])[0] for _, p in sent), 1)
        self.assertEqual(len(sent), 3)  # Initial zero, STOP, W event.
        self.assertIn("START confirmed", output)
        self.assertNotIn("ACK received", output)
        self.assertGreater(rows[3]["joint_target_rad"]["FL_HIP"], 0)
        self.assertEqual(rows[4]["joint_target_rad"]["FL_HIP"], 0)

    def test_start_stop_preserves_motor_frames_and_sdk_stop_save(self):
        rows, sent, calls, output = self.exercise(
            [frame(1, REST_ACTIVE=1),
             frame(2, WALK_ENABLED=1, STEP_FR_ACTIVE=1, FL_HIP_POS=1),
             frame(3, WALK_ENABLED=1, STEP_RL_ACTIVE=1, FR_HIP_POS=1),
             frame(4, WALK_ENABLED=1), frame(5, REST_ACTIVE=1)],
            {2: ord("W"), 4: ord("S"), 6: ord("Q")}, 6,
        )
        self.assertEqual([r["native_step"] for r in rows], list(range(1, 6)))
        self.assertEqual(sum(p.get("WALK_START", [0])[0] for _, p in sent), 1)
        self.assertEqual(sum(p.get("WALK_STOP", [0])[0] for _, p in sent), 2)
        self.assertEqual(len(sent), 4)
        self.assertIn("STOP confirmed", output)
        self.assertEqual(calls.count("physics"), 6)

    def test_fast_reflex_has_its_own_speed_and_next_normal_frame_restores_speed(self):
        rows, _, _, _ = self.exercise(
            [frame(1, REST_ACTIVE=1),
             frame(2, WALK_ENABLED=1, FL_KNEE_REFLEX_EXTEND=1),
             frame(3, WALK_ENABLED=1, FL_KNEE_NEG=1)],
            {2: ord("W"), 4: ord("Q")}, 4,
        )
        self.assertEqual(rows[1]["joint_speed_limit_rad_s"]["FL_KNEE"], 2)
        self.assertEqual(rows[2]["joint_speed_limit_rad_s"]["FL_KNEE"], 1.5)
        self.assertAlmostEqual(rows[1]["joint_target_rad"]["FL_KNEE"], -0.22)
        self.assertAlmostEqual(rows[2]["joint_target_rad"]["FL_KNEE"], -0.08)
        self.assertEqual(self.run_settings["reward_input_neurons"], 10)

    def test_64ms_still_applies_one_body_step_per_native_frame(self):
        rows, _, calls, _ = self.exercise(
            [frame(1, REST_ACTIVE=1), frame(2, WALK_ENABLED=1, FL_HIP_POS=1),
             frame(3, WALK_ENABLED=1)], {2: ord("W"), 4: ord("Q")}, 4,
            physics_step_ms=64,
        )
        self.assertEqual([r["simulation_time"] for r in rows], [0.128, 0.192, 0.256])
        self.assertEqual([r["joint_target_rad"]["FL_HIP"] for r in rows], [0, 0.2, 0])
        self.assertEqual(calls.count("physics"), 4)

    def test_poststep_tilt_contact_and_reward_share_the_same_publication(self):
        rows, _, _, _ = self.exercise(
            [frame(1, REST_ACTIVE=1), frame(2, REST_ACTIVE=1),
             frame(3, WALK_ENABLED=1), frame(4, WALK_ENABLED=1)],
            {2: ord("W"), 5: ord("Q")}, 5, mode="learn", moving=True,
            tilt_rpy=[-0.2, 0.2, 0], contact_values=dict(FL=1, FR=0, RL=1, RR=0),
        )
        self.assertEqual([r["reward"]["value"] for r in rows], [0, 0, 1, 1])
        by_body_step = dict(self.feedback_calls)
        self.assertEqual(by_body_step[3]["TILT_ROLL_NEG"], [1] * TILT_NEURONS)
        self.assertEqual(by_body_step[3]["TILT_PITCH_POS"], [1] * TILT_NEURONS)
        self.assertEqual(by_body_step[3][REWARD_INPUT]["signal"], 0)
        self.assertEqual(by_body_step[4][REWARD_INPUT]["signal"], 1)
        self.assertEqual(rows[-1]["foot_contact"], dict(FL=1, FR=0, RL=1, RR=0))
        self.assertEqual(by_body_step[4][CONTACT_INPUTS["FL"]], [1] * 4)
        self.assertEqual(by_body_step[4][CONTACT_INPUTS["FR"]], [0] * 4)
        self.assertEqual(self.run_settings["contact_input_neurons"], 32)
        self.assertTrue(all(not any(v) for _, p in self.contact_clear_calls for v in p.values()))
        self.assertTrue(all(set(p) == {*TILT_INPUTS, *CONTACT_INPUTS.values(), *AIR_INPUTS.values(), REWARD_INPUT}
                            for _, p in self.feedback_calls))

    def test_failed_input_publication_still_stops_and_saves(self):
        self.exercise([], {}, 1, reject_tilt=True)
        self.exercise([], {}, 1, mode="learn", reject_reward=True)

    def recovery_trial(self, *, automatic=False, cancel_resume=False):
        frames = [frame(1, REST_ACTIVE=1), frame(2, WALK_ENABLED=1),
                  frame(3, WALK_ENABLED=1), frame(4, REST_ACTIVE=1, FL_HIP_POS=1),
                  *[frame(n, REST_ACTIVE=1) for n in range(5, 10)],
                  frame(10, WALK_ENABLED=1), frame(11, WALK_ENABLED=1)]
        keys = {2: ord("W"), 12: ord("Q")}
        if not automatic:
            keys[4] = ord("R")
        if cancel_resume:
            keys[6] = ord("S")
        return self.exercise(
            frames, keys, 12, mode="learn", moving=True,
            recovery_settings=dict(automatic=automatic, settle_seconds=0.05,
                                   fall_delay_seconds=0.03),
            fallen_from_step=3 if automatic else None,
        )

    def test_recovery_waits_for_rest_and_quiet_outputs_then_resumes_once(self):
        rows, sent, calls, output = self.recovery_trial()
        self.assertEqual(calls.count("restore:__init__"), 1)
        self.assertLess(calls.index("frame5"), calls.index("restore:__init__"))
        self.assertEqual(calls.count("reset_physics"), 1)
        self.assertEqual(sum(p.get("WALK_START", [0])[0] for _, p in sent), 2)
        self.assertEqual(sum(p.get("WALK_STOP", [0])[0] for _, p in sent), 2)
        assisted = [r for r in rows if r["recovery_state"] != "idle"]
        self.assertTrue(assisted)
        self.assertTrue(all(r["reward"]["value"] == 0 for r in assisted))
        self.assertTrue(all(r["joint_target_rad"]["FL_HIP"] == 0 for r in assisted))
        self.assertIn("Recovery complete", output)

    def test_automatic_recovery_and_s_cancel_resume_still_work_without_ack(self):
        for cancel in (False, True):
            _, sent, calls, output = self.recovery_trial(automatic=True, cancel_resume=cancel)
            self.assertEqual(calls.count("restore:__init__"), 1)
            self.assertIn("fall detected", output)
            self.assertEqual(sum(p.get("WALK_START", [0])[0] for _, p in sent),
                             1 if cancel else 2)

    def test_recovery_from_rest_does_not_start_walking(self):
        _, sent, calls, output = self.exercise(
            [frame(n, REST_ACTIVE=1) for n in range(1, 8)],
            {2: ord("R"), 8: ord("Q")}, 8,
            recovery_settings=dict(settle_seconds=0.05),
        )
        self.assertEqual(calls.count("restore:__init__"), 1)
        self.assertFalse(any(p.get("WALK_START", [0])[0] for _, p in sent))
        self.assertIn("Recovery complete", output)

    def test_fresh_w_event_is_captured_once_without_periodic_resending(self):
        _, sent, _, output = self.exercise(
            [frame(n, WALK_ENABLED=int(n > 1), REST_ACTIVE=int(n == 1))
             for n in range(1, 6)],
            {2: ord("W"), 4: ord("W"), 6: ord("Q")}, 6,
        )
        self.assertEqual(sum(p.get("WALK_START", [0])[0] for _, p in sent), 2)
        self.assertEqual(output.count("W received"), 2)

    def test_rhythm_and_walk_do_not_reward_and_rhythm_does_not_move(self):
        for mode in ("rhythm", "walk"):
            rows, _, _, _ = self.exercise(
                [frame(1, REST_ACTIVE=1), frame(2, WALK_ENABLED=1, FL_HIP_POS=1),
                 frame(3, WALK_ENABLED=1, FL_KNEE_REFLEX_EXTEND=1)],
                {2: ord("W"), 4: ord("Q")}, 4, mode=mode, moving=True,
            )
            self.assertTrue(all(r["reward"]["value"] == 0 for r in rows))
            self.assertTrue(all(p[REWARD_INPUT]["signal"] == 0
                                for _, p in self.feedback_calls))
            if mode == "rhythm":
                self.assertTrue(all(r["joint_target_rad"]["FL_HIP"] == 0 for r in rows))


if __name__ == "__main__":
    unittest.main()

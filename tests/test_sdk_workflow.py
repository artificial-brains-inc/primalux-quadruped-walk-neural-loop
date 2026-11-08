import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from ab import Brain
from ab_sdk.__main__ import main
from ab_sdk.design_submit import design_sha256

from design_brain import create_brain
from robot.contracts import REWARD_INPUT
from robot.reward import RewardPublisher


class SDKWorkflowTests(unittest.TestCase):
    def test_reward_uses_native_sdk_encoding_and_named_input_transport(self):
        from ab_sdk.encoder import SpikeEncoder
        from ab_sdk.maps import InputSensorMap
        from ab_sdk.session import RealtimeSession

        session = RealtimeSession.__new__(RealtimeSession)
        session.compile_id = "test-install"
        session.encoder = SpikeEncoder(
            InputSensorMap(
                [
                    {"inputId": REWARD_INPUT, "sensor": REWARD_INPUT, "n": 1},
                ]
            )
        )
        session.input_client = MagicMock()
        session.input_client.send_input.return_value = {
            "ok": True,
            "queued_for_hardware": True,
        }
        publisher = RewardPublisher(session.publish_reward)
        for value in (0, 1, 0):
            publisher.send({"value": value})
        for call, expected in zip(
            session.input_client.send_input.call_args_list, (0, 1, 0), strict=True
        ):
            payload = call.kwargs["payload"]
            self.assertEqual(payload["compileId"], "test-install")
            self.assertEqual(len(payload["events"]), 1)
            event = payload["events"][0]
            self.assertEqual(event["target"], REWARD_INPUT)
            self.assertEqual(event["payload"], [expected])
            self.assertNotIn("step", event)

    def test_native_design_loads_the_saved_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            brain = create_brain()
            brain.save(root / "brain.abdesign.json")
            with patch("ab_designer.server.serve") as serve:
                code = main(
                    [
                        "design",
                        "--project",
                        temp,
                        "--brain",
                        "brain.abdesign.json",
                        "--no-browser",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertEqual(
                design_sha256(serve.call_args.args[0]), design_sha256(brain)
            )

    def test_native_build_submits_edited_saved_design(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            edited = create_brain().to_dict()
            next(n for n in edited["nodes"] if n["name"] == "FRONT_LEFT_HIP_NEG_BETA")[
                "tnorm"
            ] = 4.9
            brain = Brain.from_dict(edited)
            brain.save(root / "brain.abdesign.json")
            with (
                patch("ab_sdk.__main__.PrimaLuxClient.from_env"),
                patch("ab_sdk.__main__.build_on_device") as submit,
            ):
                submit.return_value = {"status": "READY", "device_ready": True}
                with contextlib.redirect_stdout(io.StringIO()):
                    code = main(
                        [
                            "build",
                            "brain",
                            "--project",
                            temp,
                            "--brain",
                            "brain.abdesign.json",
                            "--env",
                            str(root / ".env"),
                        ]
                    )
            self.assertEqual(code, 0)
            self.assertEqual(
                design_sha256(submit.call_args.args[1]), design_sha256(brain)
            )

    def test_native_run_dispatches_application_and_explicit_env(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "run.py").write_text("print('application entry')\n")
            env = root / "selected.env"
            with (
                patch("ab_sdk.__main__.PrimaLuxClient.from_env") as device,
                patch("ab_sdk.__main__.subprocess.call") as launch,
            ):
                device.return_value.__enter__.return_value.status.return_value = {
                    "engine": {
                        "has_brain": True,
                        "state": "READY",
                        "native_brain_name": "Example",
                    }
                }
                launch.return_value = 0
                code = main(["run", "-ab", "--project", temp, "--env", str(env)])
            self.assertEqual(code, 0)
            self.assertEqual(launch.call_args.args[0][1], str(root / "run.py"))
            self.assertEqual(launch.call_args.kwargs["env"]["AB_ENV"], str(env))
            self.assertEqual(
                launch.call_args.kwargs["env"]["AB_UNIFIED_TARGET"], "primalux"
            )

    def test_native_run_forwards_application_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "run.py").write_text("pass\n")
            with (
                patch("ab_sdk.__main__.PrimaLuxClient.from_env") as device,
                patch("ab_sdk.__main__.subprocess.call", return_value=0) as launch,
            ):
                device.return_value.__enter__.return_value.status.return_value = {
                    "engine": {"has_brain": True, "state": "READY"}
                }
                code = main(
                    [
                        "run",
                        "-ab",
                        "--project",
                        temp,
                        "--env",
                        str(root / ".env"),
                        "rhythm",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertEqual(launch.call_args.args[0][-1], "rhythm")


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from robot import application


class LaunchTimingTests(unittest.TestCase):
    def test_rendered_fast_mode_removes_realtime_pacing_and_retains_shutdown(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            process = MagicMock(returncode=0)
            process.poll.return_value = 0
            with (
                patch.object(application, "ROOT", root),
                patch.object(application, "verify_installed"),
                patch.object(application, "ensure_brain_stopped") as stop,
                patch.object(application, "save_launcher_report"),
                patch.object(
                    application.subprocess, "Popen", return_value=process
                ) as launch,
                patch("world_assets.check_world_assets"),
                patch("launcher_support.find_webots", return_value="/existing/webots"),
                patch("launcher_support.check_webots"),
                patch("launcher_support.write_controller_runtime"),
                patch("launcher_support.webots_environment", return_value={}),
            ):
                application.launch("learn")
            args = launch.call_args.args[0]
            self.assertIn("--mode=fast", args)
            self.assertNotIn("--mode=realtime", args)
            self.assertNotIn("--no-rendering", args)
            self.assertEqual(launch.call_args.kwargs["env"]["SPOT_RUN_MODE"], "learn")
            stop.assert_called_once()


class ModeGuardTests(unittest.TestCase):
    def test_matching_static_and_learning_modes_are_accepted(self):
        from design_brain import create_brain
        self.assertEqual(application.validate_run_mode(create_brain(learning=False), "walk"), [])
        self.assertEqual(len(application.validate_run_mode(create_brain(), "learn")), 4)

    def test_learn_cannot_silently_run_the_static_graph(self):
        from design_brain import create_brain
        with self.assertRaisesRegex(ValueError, "designs/learning.abdesign.json"):
            application.validate_run_mode(create_brain(learning=False), "learn")
        with self.assertRaisesRegex(ValueError, "designs/static.abdesign.json"):
            application.validate_run_mode(create_brain(), "walk")

    def test_excitatory_or_ltd_or_missing_plastic_edge_is_rejected(self):
        from ab import Brain
        from design_brain import create_brain
        for field, value in (("type", "exc"), ("reward_type", "LTD"), ("rule", None)):
            d = create_brain().to_dict()
            edge = next(e for e in d["connections"] if "rule" in e)
            if value is None:
                for key in ("rule", "reward", "reward_type"):
                    edge.pop(key)
            else:
                edge[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                application.validate_run_mode(Brain.from_dict(d), "learn")

    def test_mismatch_fails_before_webots_or_device_access(self):
        from design_brain import create_brain
        with (patch.object(application, "saved_design", return_value=create_brain(learning=False)),
              patch.object(application, "verify_installed") as device,
              patch("launcher_support.find_webots") as find,
              patch.object(application.subprocess, "Popen") as process):
            with self.assertRaises(ValueError):
                application.launch("learn")
            device.assert_not_called()
            find.assert_not_called()
            process.assert_not_called()

    def test_default_mode_matches_learning_root(self):
        with patch.object(application, "launch") as launch:
            self.assertEqual(application.main([]), 0)
            launch.assert_called_once_with("learn")

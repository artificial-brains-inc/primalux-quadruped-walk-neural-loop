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

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from robot import cleanup as application


def status(state="RUNNING", busy=False):
    return {"engine": {"state": state, "busy": busy, "available": True}}


class ShutdownTests(unittest.TestCase):
    def setUp(self):
        self.device = MagicMock()
        self.device.__enter__.return_value = self.device
        self.device.status.return_value = status()
        self.device.stop_and_wait.return_value = {"confirmed": True, "state": "STOPPED"}
        self.factory = self.enterContext(
            patch("ab_sdk.primalux.PrimaLuxClient.from_env", return_value=self.device)
        )
        self.enterContext(patch.object(application.time, "sleep"))

    def test_running_brain_uses_sdk_stop_and_wait_with_selected_env(self):
        with patch.dict("os.environ", {"AB_ENV": "/tmp/selected-demo.env"}):
            application.ensure_brain_stopped()
        self.factory.assert_called_once_with(Path("/tmp/selected-demo.env"))
        self.device.stop_and_wait.assert_called_once()

    def test_idle_stopped_brain_needs_no_duplicate_stop(self):
        self.device.status.return_value = status("STOPPED")
        application.ensure_brain_stopped()
        self.device.stop_and_wait.assert_not_called()

    def test_in_progress_save_is_allowed_to_finish(self):
        self.device.status.side_effect = [
            status("RUNNING", True),
            status("STOPPED", True),
            status("STOPPED"),
        ]
        application.ensure_brain_stopped()
        self.device.stop_and_wait.assert_not_called()
        self.assertEqual(self.device.status.call_count, 3)

    def test_failed_initial_status_does_not_prevent_stop_attempt(self):
        self.device.status.side_effect = OSError("Temporary connection failure")
        application.ensure_brain_stopped()
        self.device.stop_and_wait.assert_called_once()

    def test_malformed_initial_status_does_not_prevent_stop_attempt(self):
        for report in (None, {}, {"engine": "unusable"}):
            with self.subTest(report=report):
                self.device.status.return_value = report
                self.device.stop_and_wait.reset_mock()
                application.ensure_brain_stopped()
                self.device.stop_and_wait.assert_called_once()

    def test_racing_controller_stop_can_be_confirmed_without_retry(self):
        self.device.status.side_effect = [
            status(),
            status("STOPPED", True),
            status("STOPPED"),
        ]
        self.device.stop_and_wait.side_effect = RuntimeError("Stop already in progress")
        application.ensure_brain_stopped()
        self.device.stop_and_wait.assert_called_once()

    def test_ready_or_request_acceptance_alone_is_not_save_confirmation(self):
        for result in ({"ok": True}, {"confirmed": True, "state": "READY"}):
            with self.subTest(result=result):
                self.device.stop_and_wait.return_value = result
                with self.assertRaisesRegex(RuntimeError, "did not confirm"):
                    application.ensure_brain_stopped()

    def test_busy_save_timeout_is_reported(self):
        self.device.status.return_value = status("STOPPED", True)
        with self.assertRaisesRegex(RuntimeError, "remained busy"):
            application.ensure_brain_stopped(timeout=0)
        self.device.stop_and_wait.assert_not_called()

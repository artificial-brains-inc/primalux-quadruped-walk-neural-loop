import math
import unittest

from robot.configuration import load_config
from robot.recovery import Recovery


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        config = load_config()
        self.r = Recovery(config["recovery"], config["reward"])
        self.xyz = [0, 0, 0.6]

    def update(self, now, *, stopped=True, rpy=(0, 0, 0)):
        return self.r.update(now, stopped=stopped, xyz=self.xyz, rpy=rpy)

    def test_fall_is_debounced_and_wobble_resets_timer(self):
        self.assertFalse(self.r.detect_fall(0, self.xyz, [math.pi, 0, 0]))
        self.assertFalse(self.r.detect_fall(0.3, self.xyz, [0, 0, 0]))
        self.assertFalse(self.r.detect_fall(0.4, self.xyz, [math.pi, 0, 0]))
        self.assertFalse(self.r.detect_fall(0.8, self.xyz, [math.pi, 0, 0]))
        self.assertTrue(self.r.detect_fall(1, self.xyz, [math.pi, 0, 0]))

    def test_low_height_and_disabled_or_invalid_sensors(self):
        self.assertFalse(self.r.detect_fall(0, [0, 0, 0.2], [0, 0, 0]))
        self.assertTrue(self.r.detect_fall(1, [0, 0, 0.2], [0, 0, 0]))
        self.assertFalse(self.r.detect_fall(2, [math.nan, 0, 0.2], [0, 0, 0]))
        self.r.settings["automatic"] = False
        self.assertFalse(self.r.detect_fall(3, self.xyz, [math.pi, 0, 0]))
        self.assertTrue(self.r.begin(3, resume=False, reason="R key"))

    def test_stop_then_restore_once_then_continuous_upright_settle_and_cooldown(self):
        self.r.begin(0, resume=True, reason="fall")
        self.assertFalse(self.r.begin(0.1, resume=False, reason="duplicate"))
        self.assertIsNone(self.update(0.1, stopped=False))
        self.assertEqual(self.update(0.2), "restore")
        self.assertIsNone(self.update(0.3))
        self.assertIsNone(self.update(1, rpy=(1.5, 0, 0)))
        self.assertIsNone(self.update(1.1))
        self.assertIsNone(self.update(1.9))
        self.assertEqual(self.update(2.2), "ready")
        self.assertEqual(self.r.count, 1)
        self.assertFalse(self.r.detect_fall(2.3, self.xyz, [math.pi, 0, 0]))
        self.assertFalse(self.r.detect_fall(4.3, self.xyz, [math.pi, 0, 0]))
        self.assertTrue(self.r.detect_fall(4.9, self.xyz, [math.pi, 0, 0]))

    def test_stop_and_settle_timeouts_do_not_repeatedly_teleport(self):
        self.r.begin(0, resume=True, reason="fall")
        with self.assertRaisesRegex(TimeoutError, "quiet motor"):
            self.update(6, stopped=False)
        self.assertEqual(self.r.count, 0)
        self.assertEqual(self.update(6), "restore")
        with self.assertRaisesRegex(TimeoutError, "settle upright"):
            self.update(12, rpy=(math.pi, 0, 0))
        self.assertEqual(self.r.count, 1)

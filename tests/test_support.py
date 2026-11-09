"""Support calibration and its observable timing, without a controller gait."""
import json
import math
import tempfile
import unittest
from pathlib import Path
from robot.configuration import load_config
from robot.contracts import LEGS, NEXT_LEG, SUPPORT_DIRECTIONS
from robot.decoder import joint_targets
from robot.evaluation import summarize
from test_evaluation import row
from test_runtime import frame


class SupportTests(unittest.TestCase):
    def test_motor_offsets_are_independent_of_phase_readouts_and_mirror_by_direction(self):
        c = load_config()
        for leg in LEGS:
            for joint in ("HIP", "ABD"):
                base = frame(0, **{f"{leg}_{joint}_NEG": 1})
                q = joint_targets(base, c)[leg, joint]
                for side, sign in (("POS", 1), ("NEG", -1)):
                    f = frame(1, **{f"{leg}_{joint}_NEG": 1, f"{leg}_{joint}_SUPPORT_{side}": 1})
                    self.assertAlmostEqual(joint_targets(f, c)[leg, joint], q + sign*c["support_shift"][joint+"_offset_rad"])
                    f["actuation"]["channels"]["STEP_FR_PREPARE"] = 1
                    self.assertAlmostEqual(joint_targets(f, c)[leg, joint], q + sign*c["support_shift"][joint+"_offset_rad"])
                    f["actuation"]["channels"][f"{leg}_{joint}_SUPPORT_{'NEG' if side == 'POS' else 'POS'}"] = 1
                    self.assertAlmostEqual(joint_targets(f, c)[leg, joint], q)
        neutral = joint_targets(frame(0), c)
        all_plans = frame(0, **{f"STEP_{l}_PREPARE": 1 for l in LEGS})
        self.assertEqual(joint_targets(all_plans, c), neutral)

    def test_combined_stroke_and_support_limits_are_checked(self):
        for joint, bad in (("HIP", 2), ("ABD", .6), ("HIP", -1), ("ABD", math.nan)):
            c = load_config()
            c["support_shift"][joint+"_offset_rad"] = bad
            with tempfile.TemporaryDirectory() as d:
                (Path(d)/"config.json").write_text(json.dumps(c))
                with self.assertRaises(ValueError): load_config(Path(d))
        c = load_config()
        c["support_shift"] = {k: 0 for k in c["support_shift"]}
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/"config.json").write_text(json.dumps(c))
            self.assertEqual(load_config(Path(d))["support_shift"]["HIP_offset_rad"], 0)

    def test_early_push_metric_requires_measured_air_and_actual_motor_output(self):
        rows = []
        for leg, following in NEXT_LEG.items():
            r = row(1, "start", WALK_ENABLED=1, **{f"STEP_{leg}_ACTIVE": 1, f"STEP_{following}_PREPARE": 1, f"{following}_KNEE_PUSH": 1})
            r["foot_contact"] = {leg: 0}
            rows.append(r)
        self.assertEqual(summarize(rows)["next_push_before_previous_touchdown_frames"], dict.fromkeys(LEGS, 1))
        for r in rows: r["foot_contact"] = dict.fromkeys(LEGS, 1)
        self.assertEqual(summarize(rows)["next_push_before_previous_touchdown_frames"], dict.fromkeys(LEGS, 0))

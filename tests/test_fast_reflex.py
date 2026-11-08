import json
import math
import tempfile
import unittest
from pathlib import Path

from design_brain import create_brain
from robot.configuration import load_config
from robot.contracts import LEGS, MOTOR_OUTPUTS, motor_population
from robot.decoder import joint_speeds, joint_targets
from test_runtime import frame


class FastReflexTests(unittest.TestCase):
    def test_fast_output_has_own_calibration_and_returns_to_normal_on_clear(self):
        config = load_config()
        for leg in LEGS:
            key = (leg, "KNEE")
            normal = frame(1, **{f"{leg}_KNEE_NEG": 1})
            fast = frame(2, **{f"{leg}_KNEE_NEG": 1, f"{leg}_KNEE_REFLEX_EXTEND": 1})
            self.assertAlmostEqual(joint_targets(normal, config)[key], -0.08)
            self.assertAlmostEqual(joint_targets(fast, config)[key], -0.22)
            self.assertEqual(joint_speeds(normal, config)[key], 1.5)
            self.assertEqual(joint_speeds(fast, config)[key], 3.0)
            self.assertEqual(joint_speeds(normal, config)[key], 1.5)
            for other in LEGS:
                if other != leg:
                    self.assertEqual(joint_targets(fast, config)[other, "KNEE"], 0)
                    self.assertEqual(joint_speeds(fast, config)[other, "KNEE"], 1.5)

    def test_diagnostics_do_not_drive_motor_and_antagonists_still_cancel(self):
        config = load_config()
        diagnostic = frame(1, REFLEX_FL_ACTIVE=1, PHASE_A_OUT=1)
        self.assertEqual(
            joint_targets(diagnostic, config), joint_targets(frame(0), config)
        )
        conflict = frame(2, FL_KNEE_POS=1, FL_KNEE_REFLEX_EXTEND=1)
        self.assertEqual(joint_targets(conflict, config)["FL", "KNEE"], 0)
        self.assertEqual(joint_speeds(conflict, config)["FL", "KNEE"], 1.5)
        fast = frame(3, FL_KNEE_REFLEX_EXTEND=1)
        self.assertEqual(joint_targets(fast, config, rhythm_only=True)["FL", "KNEE"], 0)
        self.assertEqual(
            joint_speeds(fast, config, rhythm_only=True)["FL", "KNEE"], 1.5
        )

    def test_fast_output_clears_from_its_own_activity_and_rest(self):
        doc = create_brain().to_dict()
        edges = {(e["from"], e["to"]): e for e in doc["connections"]}
        for leg in LEGS:
            fast = f"{leg}_KNEE_REFLEX_EXTEND"
            reset = f"REFLEX_{leg}_OUTPUT_RESET_HG"
            relay = f"REFLEX_{leg}_NORMAL_RELAY_HG"
            self.assertIn(fast, MOTOR_OUTPUTS)
            self.assertEqual(edges[fast, reset]["type"], "exc")
            for source in (reset, "REST_NUCLEUS", "STOP_REQUEST_HG"):
                self.assertEqual(edges[source, fast]["type"], "inh")
                self.assertNotIn("rule", edges[source, fast])
            self.assertEqual(edges[fast, relay]["type"], "exc")
            teaching = edges[relay, motor_population(leg, "KNEE", "NEG")]
            self.assertEqual(teaching["type"], "exc")
            self.assertEqual(teaching["rule"], "STDP3")

    def test_config_rejects_invalid_corrective_speed_and_endpoint(self):
        for name, value in (
            ("extension_speed_rad_s", 0),
            ("extension_speed_rad_s", math.inf),
            ("extension_excursion_rad", 0.46),
            ("extension_excursion_rad", math.nan),
        ):
            config = load_config()
            config["reflex"][name] = value
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp)
                (path / "config.json").write_text(json.dumps(config))
                with self.assertRaises(ValueError):
                    load_config(path)

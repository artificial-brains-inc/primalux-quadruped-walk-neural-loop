import json
import math
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from design_brain import create_brain
from robot.configuration import ROOT, load_config
from robot.contracts import (
    COMMAND_INPUT_SIZES,
    LEGS,
    REFLEX_CUES,
    REFLEX_OUTPUTS,
    REWARD_INPUT,
    SWING_PHASE,
    TILT_INPUTS,
    TILT_NEURONS,
    motor_population,
)
from robot.reflex import TiltPublisher, encode_tilt


class TiltTests(unittest.TestCase):
    def setUp(self):
        self.settings = load_config()["reflex"]

    def test_four_signed_measurements_and_neutral_deadband(self):
        for roll, pitch, expected in (
            (0, 0, ()),
            (-0.2, 0, ("TILT_ROLL_NEG",)),
            (0.2, 0, ("TILT_ROLL_POS",)),
            (0, -0.2, ("TILT_PITCH_NEG",)),
            (0, 0.2, ("TILT_PITCH_POS",)),
            (-0.2, 0.2, ("TILT_ROLL_NEG", "TILT_PITCH_POS")),
        ):
            p = encode_tilt([roll, pitch, 1.2], self.settings)
            self.assertEqual(set(p), set(TILT_INPUTS))
            self.assertTrue(all(len(v) == 12 and set(v) <= {0, 1} for v in p.values()))
            self.assertEqual(
                {k for k, v in p.items() if v == [1] * TILT_NEURONS}, set(expected)
            )
        self.assertFalse(
            any(v[0] for v in encode_tilt([0.04, -0.04, 0], self.settings).values())
        )
        with self.assertRaises(ValueError):
            encode_tilt([math.nan, 0, 0], self.settings)

    def test_every_nonzero_sample_is_a_fresh_atomic_event(self):
        calls, logs = [], []

        def publish(payload):
            calls.append(payload)
            return dict(ok=True, queued_for_hardware=True, atomic_frame=True)

        p = TiltPublisher(publish, self.settings, logs.append)
        for sample in ([0, 0, 0], [0, 0, 0], [-0.2, 0, 0], [-0.2, 0, 0], [0, 0, 0]):
            p.send(sample)
        self.assertEqual(len(calls), 4)
        self.assertEqual(calls[1], calls[2])
        self.assertTrue(all(set(c) == set(TILT_INPUTS) for c in calls))
        self.assertTrue(
            all(not set(c) & (set(COMMAND_INPUT_SIZES) | {REWARD_INPUT}) for c in calls)
        )
        p.send([-0.3, 0.3, 0], suspended=True, force=True)
        self.assertEqual(calls[-1], {name: [0] * 12 for name in TILT_INPUTS})
        self.assertTrue(logs[-1]["suspended"])

    def test_rejected_tilt_input_is_an_error_not_assumed_delivery(self):
        for result in (
            {"ok": True},
            dict(ok=True, queued_for_hardware=True, atomic_frame=False),
        ):
            with self.assertRaisesRegex(RuntimeError, "Tilt inputs"):
                TiltPublisher(lambda p: result, self.settings).send([0.2, 0, 0])

    def test_native_sdk_preserves_all_48_tilt_neurons_in_one_frame(self):
        from ab_sdk.encoder import SpikeEncoder
        from ab_sdk.maps import InputSensorMap
        from ab_sdk.session import RealtimeSession

        session = RealtimeSession.__new__(RealtimeSession)
        session.compile_id = "test-install"
        session.encoder = SpikeEncoder(
            InputSensorMap(
                [
                    {"inputId": name, "sensor": name, "n": TILT_NEURONS}
                    for name in TILT_INPUTS
                ]
            )
        )
        session.input_client = MagicMock()
        session.input_client.send_frame.return_value = dict(
            ok=True, queued_for_hardware=True, atomic_frame=True
        )
        TiltPublisher(session.publish_sensor_frame, self.settings).send([-0.2, 0.2, 0])
        session.input_client.send_frame.assert_called_once()
        payload = session.input_client.send_frame.call_args.kwargs
        self.assertEqual(
            {e["target"]: e["payload"] for e in payload["events"]},
            {
                name: [int(name in ("TILT_ROLL_NEG", "TILT_PITCH_POS"))] * TILT_NEURONS
                for name in TILT_INPUTS
            },
        )
        self.assertTrue(all("step" not in e for e in payload["events"]))

    def test_config_rejects_late_or_nonfinite_reflex_thresholds(self):
        for threshold in (0, -0.1, math.inf, 1.05):
            c = load_config()
            c["reflex"]["tilt_threshold_rad"] = threshold
            with tempfile.TemporaryDirectory() as temp:
                p = Path(temp)
                (p / "config.json").write_text(json.dumps(c))
                with self.assertRaisesRegex(ValueError, "Reflex tilt"):
                    load_config(p)


class ReflexGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        d = create_brain().to_dict()
        cls.nodes = {n["name"]: n for n in d["nodes"]}
        cls.edges = {(e["from"], e["to"]): e for e in d["connections"]}

    def test_high_gamma_directly_drives_reflex_and_inhibits_local_flexion(self):
        for leg in LEGS:
            stem = "REFLEX_" + leg
            trigger, reset, active = (
                stem + "_HG",
                stem + "_OUTPUT_RESET_BETA",
                stem + "_ACTIVE",
            )
            fast = f"{leg}_KNEE_REFLEX_EXTEND"
            self.assertNotIn(stem + "_EXTENSION_BETA", self.nodes)
            self.assertNotIn(stem + "_RESET_HG", self.nodes)
            self.assertNotIn(stem + "_NORMAL_RELAY_HG", self.nodes)
            for cue in REFLEX_CUES[leg]:
                self.assertEqual(self.nodes[cue]["neurons"], 12)
                self.assertEqual(self.edges[cue, trigger]["type"], "exc")
            for source, target in (
                (trigger, fast),
                (trigger, active),
                (fast, stem + "_RECOVERY_BETA"),
                (stem + "_RECOVERY_BETA", reset),
            ):
                self.assertEqual(self.edges[source, target]["type"], "exc")
            self.assertEqual(self.edges[trigger, trigger]["role"], "feedback")
            for target in (trigger, active, fast):
                edge = self.edges[reset, target]
                self.assertEqual(edge["type"], "inh")
                self.assertEqual(edge["strength"], 4)
                self.assertEqual(
                    edge.get("role"), "feedback" if target == trigger else None
                )
            gate = stem + "_EXTENSION_VETO_HG"
            for target in (
                motor_population(leg, "KNEE", "POS"),
                f"{leg}_KNEE_POS",
                gate,
            ):
                self.assertEqual(self.edges[trigger, target]["strength"], 64)
            self.assertEqual(
                (self.nodes[trigger]["rhythm"], self.nodes[trigger]["tnorm"]),
                ("high-gamma", 5),
            )
            self.assertEqual(
                (self.nodes[reset]["rhythm"], self.nodes[reset]["tnorm"]),
                ("beta", 3),
            )
            for name in (trigger, reset, active, gate, fast):
                for source in ("REST_NUCLEUS", "STOP_REQUEST_HG"):
                    self.assertEqual(self.edges[source, name]["strength"], 4)
        for (source, target), edge in self.edges.items():
            if (
                source.startswith(("REFLEX_", "TILT_")) or target.startswith("REFLEX_")
            ):
                self.assertNotIn("rule", edge)
        self.assertFalse(any("GUARD" in n for n in self.nodes))
        self.assertFalse(any(s in REFLEX_OUTPUTS for s, _ in self.edges))

    def test_fast_reflex_recruits_regular_beta_without_waiting_for_it(self):
        for leg in LEGS:
            stance = "B" if SWING_PHASE[leg] == "A" else "A"
            gait = motor_population(leg, "KNEE", "NEG")
            output, fast = f"{leg}_KNEE_NEG", f"{leg}_KNEE_REFLEX_EXTEND"
            for target, expected in (
                (
                    gait,
                    {
                        f"PHASE_{stance}_DRIVE_HG",
                        f"LEG_{leg}_DONE_HG",
                        f"REFLEX_{leg}_HG",
                    },
                ),
                (output, {gait, f"LEG_{leg}_RETURN_BETA", f"LEG_{leg}_DONE_HG"}),
                (fast, {f"REFLEX_{leg}_HG"}),
            ):
                self.assertEqual(
                    {
                        s
                        for (s, t), e in self.edges.items()
                        if t == target and e["type"] == "exc"
                    },
                    expected,
                )
            self.assertEqual(
                (self.nodes[gait]["rhythm"], self.nodes[gait]["tnorm"]), ("beta", 5)
            )
            for source in (
                f"PHASE_{stance}_DRIVE_HG",
                f"LEG_{leg}_DONE_HG",
                f"REFLEX_{leg}_HG",
            ):
                self.assertEqual(self.edges[source, gait]["role"], "operand")
                self.assertEqual(self.edges[source, gait]["units"], 1)
            gate = f"REFLEX_{leg}_EXTENSION_VETO_HG"
            self.assertEqual(
                self.edges[f"LEG_{leg}_SWING_READY_HG", gate]["type"], "exc"
            )
            self.assertEqual({t for s, t in self.edges if s == gate}, {output})
            self.assertEqual(self.nodes[gate]["tnorm"], 10)
            self.assertEqual(self.edges[gate, output]["strength"], 64)
            self.assertNotIn((gate, fast), self.edges)

    def test_reflex_never_targets_another_leg_or_a_phase(self):
        for leg in LEGS:
            stem = "REFLEX_" + leg + "_"
            allowed = {
                f"{leg}_KNEE_POS",
                f"{leg}_KNEE_NEG",
                f"{leg}_KNEE_REFLEX_EXTEND",
                motor_population(leg, "KNEE", "POS"),
                motor_population(leg, "KNEE", "NEG"),
            }
            for (source, target), edge in self.edges.items():
                if source.startswith(stem):
                    self.assertTrue(
                        target.startswith(stem) or target in allowed, (source, target)
                    )
                if target.startswith(stem) and source in TILT_INPUTS:
                    self.assertIn(source, REFLEX_CUES[leg])
                    self.assertEqual(edge["type"], "exc")
        for (source, target), edge in self.edges.items():
            if source in TILT_INPUTS:
                self.assertEqual(edge["type"], "exc")
        # Shared left/front evidence remains available to independent legs.
        for source, expected in (
            ("TILT_ROLL_NEG", {"FL", "RL"}),
            ("TILT_PITCH_POS", {"FL", "FR"}),
        ):
            self.assertEqual(
                {t for s, t in self.edges if s == source},
                {f"REFLEX_{leg}_HG" for leg in expected},
            )

    def test_enu_axis_signs_lower_the_supported_body_side(self):
        self.assertIn(
            'coordinateSystem "ENU"', (ROOT / "worlds/spot_neural_walk.wbt").read_text()
        )
        # Rz(yaw) Ry(pitch) Rx(roll); yaw does not change vertical displacement.
        points = {
            "FL": (0.36, 0.2),
            "FR": (0.36, -0.2),
            "RL": (-0.31, 0.2),
            "RR": (-0.31, -0.2),
        }
        for leg, cues in REFLEX_CUES.items():
            x, y = points[leg]
            for cue in cues:
                angle = -0.2 if cue.endswith("NEG") else 0.2
                z = y * math.sin(angle) if "ROLL" in cue else -x * math.sin(angle)
                self.assertLess(z, 0, (leg, cue))

    def test_bundled_knee_geometry_extends_toward_floor_in_calibrated_range(self):
        source = (ROOT / "protos/spot/SpotLeg.proto").read_text()
        forearm = source.split("endPoint DEF FOREARM Solid {", 1)[1]
        foot = forearm.split("boundingObject DEF FOREARM_BO", 1)[1]
        match = re.search(
            r"translation %<=sign \* ([\d.]+)>% (-?[\d.]+) (-?[\d.]+)", foot
        )
        self.assertIsNotNone(match)
        fy, fz = float(match[2]), float(match[3])
        # The model's default hinge axis is local +X; its common leg rotation
        # maps local +Y to body +Z (within the PROTO rotation's rounding).
        config = load_config()
        for hip in (-0.2, 0, 0.2):

            def height(knee):
                y = -0.319729 + fy * math.cos(knee) - fz * math.sin(knee)
                z = 0.182338 + fy * math.sin(knee) + fz * math.cos(knee)
                return y * math.cos(hip) - z * math.sin(hip)

            ext = -config["joint_targets"]["KNEE"]["negative_excursion"]
            flex = config["joint_targets"]["KNEE"]["positive_excursion"]
            self.assertLess(
                height(-config["reflex"]["extension_excursion_rad"]), height(ext)
            )
            self.assertLess(height(ext), height(0))
            self.assertLess(height(0), height(flex))


if __name__ == "__main__":
    unittest.main()

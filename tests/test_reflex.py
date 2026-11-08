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
    REWARD_INPUT,
    REFLEX_CUES,
    REFLEX_OUTPUTS,
    TILT_INPUTS,
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
            self.assertEqual({k for k, v in p.items() if v == [1]}, set(expected))
        self.assertFalse(
            any(v[0] for v in encode_tilt([0.1, -0.1, 0], self.settings).values())
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
        self.assertFalse(any(v[0] for v in calls[-1].values()))
        self.assertTrue(logs[-1]["suspended"])

    def test_rejected_tilt_input_is_an_error_not_assumed_delivery(self):
        for result in (
            {"ok": True},
            dict(ok=True, queued_for_hardware=True, atomic_frame=False),
        ):
            with self.assertRaisesRegex(RuntimeError, "Tilt inputs"):
                TiltPublisher(lambda p: result, self.settings).send([0.2, 0, 0])

    def test_native_sdk_preserves_four_single_neuron_inputs_in_one_frame(self):
        from ab_sdk.encoder import SpikeEncoder
        from ab_sdk.maps import InputSensorMap
        from ab_sdk.session import RealtimeSession

        session = RealtimeSession.__new__(RealtimeSession)
        session.compile_id = "test-install"
        session.encoder = SpikeEncoder(
            InputSensorMap(
                [{"inputId": name, "sensor": name, "n": 1} for name in TILT_INPUTS]
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
                name: [int(name in ("TILT_ROLL_NEG", "TILT_PITCH_POS"))]
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

    def test_fast_static_reflex_has_directional_veto_and_explicit_self_cutoff(self):
        for leg in LEGS:
            stem = "REFLEX_" + leg
            trigger, active, guard = stem + "_HG", stem + "_ACTIVE", stem + "_GUARD_HG"
            for cue in REFLEX_CUES[leg]:
                self.assertEqual(self.edges[(cue + "_HG", trigger)]["type"], "exc")
                opposite = cue[:-3] + ("POS" if cue.endswith("NEG") else "NEG")
                for target in (trigger, active):
                    self.assertEqual(
                        self.edges[(opposite + "_HG", target)]["type"], "inh"
                    )
            previous = guard
            for stage in range(1, 4):
                reset = f"{stem}_RESET_{stage}_HG"
                self.assertEqual(self.edges[(previous, reset)]["type"], "exc")
                previous = reset
            for target in (trigger, active, f"{leg}_KNEE_NEG"):
                edge = self.edges[(previous, target)]
                self.assertEqual(edge["type"], "inh")
                self.assertEqual(
                    edge.get("role"), "feedback" if target == trigger else None
                )
            for source in (trigger, guard):
                for target in (motor_population(leg, "KNEE", "POS"), f"{leg}_KNEE_POS"):
                    self.assertEqual(self.edges[(source, target)]["strength"], 4)
            self.assertEqual(self.edges[(trigger, f"{leg}_KNEE_NEG")]["type"], "exc")
        for name, node in self.nodes.items():
            if name.startswith("REFLEX_"):
                if node["kind"] == "opu":
                    self.assertEqual(
                        (node["rhythm"], node["tnorm"]), ("high-gamma", 10)
                    )
                for source in ("REST_NUCLEUS", "STOP_REQUEST_HG"):
                    self.assertEqual(self.edges[(source, name)]["strength"], 4)
        for (source, target), edge in self.edges.items():
            if source.startswith(("REFLEX_", "TILT_")) or target.startswith("REFLEX_"):
                self.assertNotIn("rule", edge)
            if source in REFLEX_OUTPUTS:
                self.assertNotEqual(target, source.replace("_ACTIVE", "_HG"))

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
            self.assertLess(height(ext), height(0))
            self.assertLess(height(0), height(flex))


if __name__ == "__main__":
    unittest.main()

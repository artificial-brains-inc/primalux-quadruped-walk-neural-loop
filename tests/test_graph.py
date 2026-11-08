import json
import unittest

from ab import Brain
from ab_sdk.design_submit import design_sha256

from design_brain import create_brain
from robot.configuration import ROOT
from robot.contracts import (
    INPUT_SIZES,
    JOINTS,
    LEGS,
    MOTOR_OUTPUTS,
    OUTPUT_SIZES,
    SWING_PHASE,
    motor_population,
)


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.brain = create_brain()
        d = self.brain.to_dict()
        self.nodes = {n["name"]: n for n in d["nodes"]}
        self.edges = {(e["from"], e["to"]): e for e in d["connections"]}

    def assert_inhibits(self, source, target, minimum=1):
        edge = self.edges[(source, target)]
        self.assertEqual(edge["type"], "inh")
        self.assertGreaterEqual(edge.get("strength", 1), minimum)

    def test_eight_populations_61_input_neurons_and_matching_saved_design(self):
        self.assertEqual(self.brain.validate(), [])
        self.assertEqual(len(INPUT_SIZES), 8)
        self.assertEqual(sum(INPUT_SIZES.values()), 61)
        for kind, expected in (("input", INPUT_SIZES), ("output", OUTPUT_SIZES)):
            self.assertEqual(
                {
                    n["name"]: n["neurons"]
                    for n in self.nodes.values()
                    if n["kind"] == kind
                },
                expected,
            )
        saved = Brain.load(ROOT / "brain.abdesign.json")
        self.assertEqual(design_sha256(self.brain), design_sha256(saved))
        report = json.loads((ROOT / "docs/RESOURCE_CHECK.json").read_text())
        self.assertEqual(report["design_sha256"], design_sha256(saved))
        self.assertEqual(report["code"], "CONSTRUCTION_OK")
        reward = next(p for p in report["populations"] if p["name"] == "GAIT_REWARD")
        self.assertEqual(reward["classification"], "dopaminergic")
        self.assertGreaterEqual(reward["neurons"], 10)
        self.assertLess(report["resources"]["total_neurons"], 10000)
        self.assertLess(report["resources"]["matrix_storage_bytes"], 32 * 1024 * 1024)

    def test_every_opu_has_a_feedforward_construction_path(self):
        reached = set(INPUT_SIZES)
        while True:
            expanded = reached | {
                t
                for (s, t), e in self.edges.items()
                if s in reached and e["type"] == "exc" and e.get("role") != "feedback"
            }
            if expanded == reached:
                break
            reached = expanded
        self.assertEqual(reached, set(self.nodes))

    def test_command_reinforcement_has_explicit_opposing_clear_paths(self):
        for state, nucleus, clear, opposite in (
            ("WALK_ENABLED", "WALK_NUCLEUS", "STOP_REQUEST_HG", "REST_NUCLEUS"),
            ("REST_ACTIVE", "REST_NUCLEUS", "START_REQUEST_HG", "WALK_NUCLEUS"),
        ):
            for source, target in ((state, nucleus), (nucleus, state)):
                self.assertEqual(self.edges[(source, target)]["type"], "exc")
            for source in (clear, opposite):
                for target in (state, nucleus):
                    self.assert_inhibits(source, target, 4)

    def test_command_event_has_an_unopposed_neural_capture_path(self):
        for action, other, success in (
            ("START", "STOP", "WALK_NUCLEUS"),
            ("STOP", "START", "REST_NUCLEUS"),
        ):
            cue = "WALK_" + action + "_HG"
            request, driver = action + "_REQUEST", action + "_REQUEST_HG"
            for source, target in (
                (cue, request),
                (request, driver),
                (driver, request),
            ):
                self.assertEqual(self.edges[(source, target)]["type"], "exc")
                self.assertNotIn("rule", self.edges[(source, target)])
            self.assertFalse(
                any(t == cue and e["type"] == "inh" for (s, t), e in self.edges.items())
            )
            for target in (request, driver):
                self.assert_inhibits(success, target, 4)
                self.assert_inhibits("WALK_" + other + "_HG", target, 4)
                # REST must not prevent capture of a new START, or vice versa.
                opposing_goal = "REST_NUCLEUS" if action == "START" else "WALK_NUCLEUS"
                self.assertNotIn((opposing_goal, target), self.edges)

    def test_switch_retains_states_and_captures_the_next_handoff(self):
        for phase, other in (("A", "B"), ("B", "A")):
            stem, opp = f"PHASE_{phase}", f"PHASE_{other}"
            for source, target in (
                (stem + "_REQUEST", stem + "_REQUEST_HG"),
                (stem + "_REQUEST_HG", stem + "_REQUEST"),
                (stem + "_REQUEST_HG", stem + "_OUT"),
                (stem + "_OUT", stem + "_DRIVE_HG"),
                (stem + "_DRIVE_HG", stem + "_OUT"),
                (stem + "_RELEASE", opp + "_REQUEST"),
            ):
                self.assertEqual(self.edges[source, target]["type"], "exc")
                self.assertNotIn("rule", self.edges[source, target])
            for target in (opp + "_OUT", opp + "_DRIVE_HG"):
                for source in (stem + "_DRIVE_HG", stem + "_REQUEST_HG"):
                    self.assert_inhibits(source, target, 4)
                    self.assertNotIn("rule", self.edges[source, target])
            for target in (stem + "_REQUEST", stem + "_REQUEST_HG"):
                self.assert_inhibits(stem + "_DRIVE_HG", target, 64)
        self.assertIn(("START_REQUEST_HG", "PHASE_A_REQUEST"), self.edges)
        self.assertNotIn(("START_REQUEST_HG", "PHASE_B_REQUEST"), self.edges)

    def test_handoff_uses_internal_motor_activity_not_external_progress(self):
        expected = {
            "A": {"FL_HIP_NEG", "RR_HIP_NEG", "FR_HIP_POS", "RL_HIP_POS"},
            "B": {"FL_HIP_POS", "RR_HIP_POS", "FR_HIP_NEG", "RL_HIP_NEG"},
        }
        for phase, sources in expected.items():
            stem = f"PHASE_{phase}"
            target = stem + "_MOTOR_FEEDBACK_HG"
            self.assertEqual(
                {
                    s
                    for (s, t), e in self.edges.items()
                    if t == target and e["type"] == "exc"
                },
                sources,
            )
            for a, b in (
                ("MOTOR_FEEDBACK_HG", "FEEDBACK_BETA"),
                ("FEEDBACK_BETA", "BETA"),
                ("BETA", "RELEASE"),
            ):
                self.assertEqual(
                    self.edges[stem + "_" + a, stem + "_" + b]["type"], "exc"
                )
            for suffix, tnorm in (("FEEDBACK_BETA", 5), ("BETA", 5), ("RELEASE", 3)):
                n = self.nodes[stem + "_" + suffix]
                self.assertEqual((n["rhythm"], n["tnorm"]), ("beta", tnorm))

    def test_switch_drives_complementary_patterns_through_motor_betas(self):
        self.assertEqual(SWING_PHASE, dict(FL="B", RR="B", FR="A", RL="A"))
        populations = set()
        for leg in LEGS:
            for joint in JOINTS:
                swing_side = "NEG" if joint == "ABD" and leg in ("FL", "RL") else "POS"
                for side, opposite_side in (("POS", "NEG"), ("NEG", "POS")):
                    population, channel = (
                        motor_population(leg, joint, side),
                        f"{leg}_{joint}_{side}",
                    )
                    populations.add(population)
                    phase = (
                        SWING_PHASE[leg]
                        if side == swing_side
                        else ("B" if SWING_PHASE[leg] == "A" else "A")
                    )
                    other = "B" if phase == "A" else "A"
                    n = self.nodes[population]
                    self.assertEqual((n["rhythm"], n["tnorm"]), ("beta", 5))
                    self.assertEqual(
                        {
                            s
                            for (s, t), e in self.edges.items()
                            if t == population and e["type"] == "exc"
                        },
                        {f"PHASE_{phase}_DRIVE_HG"}
                        | (
                            {f"REFLEX_{leg}_NORMAL_RELAY_HG"}
                            if joint == "KNEE" and side == "NEG"
                            else set()
                        ),
                    )
                    self.assertEqual(self.edges[population, channel]["type"], "exc")
                    veto = (
                        f"REFLEX_{leg}_EXTENSION_VETO_HG"
                        if joint == "KNEE" and side == "NEG"
                        else f"PHASE_{other}_DRIVE_HG"
                    )
                    for target in (population, channel):
                        self.assert_inhibits(veto, target, 4)
                        self.assertNotIn("rule", self.edges[veto, target])
                        self.assert_inhibits("REST_NUCLEUS", target, 4)
                        self.assert_inhibits(
                            motor_population(leg, joint, opposite_side), target
                        )
        self.assertEqual(len(populations), 24)

    def test_stop_clears_switch_requests_and_all_motor_outputs(self):
        for name in self.nodes:
            if (
                name.startswith(
                    (
                        "PHASE_",
                        "REFLEX_",
                        "FRONT_LEFT_",
                        "FRONT_RIGHT_",
                        "REAR_LEFT_",
                        "REAR_RIGHT_",
                    )
                )
                or name in MOTOR_OUTPUTS
            ):
                self.assert_inhibits("REST_NUCLEUS", name, 4)
        for target in (
            "WALK_ENABLED",
            "WALK_NUCLEUS",
            "PHASE_A_REQUEST",
            "PHASE_B_REQUEST",
            "PHASE_A_OUT",
            "PHASE_B_OUT",
        ):
            self.assert_inhibits("STOP_REQUEST_HG", target, 4)
        for target in ("REST_ACTIVE", "REST_NUCLEUS"):
            self.assert_inhibits("START_REQUEST_HG", target, 4)

    def test_ack_is_isolated_from_behavior(self):
        for source, target in self.edges:
            self.assertEqual(
                source.startswith("TRANSPORT_ACK"), target.startswith("TRANSPORT_ACK")
            )


if __name__ == "__main__":
    unittest.main()

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

    def test_eight_populations_52_input_neurons_and_matching_saved_design(self):
        self.assertEqual(self.brain.validate(), [])
        self.assertEqual(len(INPUT_SIZES), 8)
        self.assertEqual(sum(INPUT_SIZES.values()), 52)
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

    def test_continuing_phase_drive_and_preparation_are_symmetric(self):
        for phase, other in (("A", "B"), ("B", "A")):
            sources = {
                s: e
                for (s, t), e in self.edges.items()
                if t == f"PHASE_{phase}_T1" and e["type"] == "exc"
            }
            self.assertEqual(set(sources), {"WALK_DRIVE", f"PHASE_{other}_T2"})
            self.assertNotIn("role", sources["WALK_DRIVE"])
            self.assertEqual(sources[f"PHASE_{other}_T2"]["role"], "feedback")
            self.assertEqual(
                {(self.nodes[s]["rhythm"], self.nodes[s]["tnorm"]) for s in sources},
                {("theta", 2.01)},
            )
            for suffix, rhythm, tnorm in (
                ("T1", "theta", 3),
                ("T2", "theta", 2.01),
                ("BETA", "beta", 5),
                ("INHIBITOR", "beta", 5),
                ("RELEASE", "beta", 3),
            ):
                node = self.nodes[f"PHASE_{phase}_{suffix}"]
                self.assertEqual((node["rhythm"], node["tnorm"]), (rhythm, tnorm))

    def test_downstream_releases_opposite_phase_by_inhibiting_own_inhibitor(self):
        for phase, other in (("A", "B"), ("B", "A")):
            stem = f"PHASE_{phase}"
            inhibitor, release = stem + "_INHIBITOR", stem + "_RELEASE"
            self.assertEqual(self.edges[(stem + "_T2", inhibitor)]["type"], "exc")
            self.assertEqual(self.edges[(stem + "_BETA", release)]["type"], "exc")
            self.assert_inhibits(release, inhibitor, 1)
            self.assertEqual(self.edges[(release, inhibitor)]["role"], "feedback")
            self.assert_inhibits(release, inhibitor + "_OUT", 1)
            for suffix in (
                "T2",
                "BETA",
                "INHIBITOR",
                "RELEASE",
                "OUT",
                "INHIBITOR_OUT",
                "RELEASE_OUT",
            ):
                self.assert_inhibits(inhibitor, f"PHASE_{other}_{suffix}", 1)
            # No remaining direct Beta veto can defeat the intended release.
            self.assertFalse(
                any(
                    s == stem + "_BETA" and e["type"] == "inh"
                    for (s, _), e in self.edges.items()
                )
            )
            self.assertEqual(
                {
                    t
                    for (s, t), e in self.edges.items()
                    if s == release and e["type"] == "inh"
                },
                {inhibitor, inhibitor + "_OUT"},
            )

    def test_start_bias_is_cleared_by_inhibitor_recruitment(self):
        for suffix in ("T2", "BETA", "INHIBITOR"):
            self.assert_inhibits("START_A_BIAS_HG", "PHASE_B_" + suffix, 1)
        for source in ("PHASE_A_INHIBITOR", "STOP_REQUEST_HG", "REST_NUCLEUS"):
            self.assert_inhibits(
                source, "START_A_BIAS", 1 if source == "PHASE_A_INHIBITOR" else 4
            )
        self.assertFalse(
            any(
                s.startswith("START_A_BIAS") and t.startswith("PHASE_A")
                for s, t in self.edges
            )
        )

    def test_four_leg_groups_keep_all_24_opposing_motor_populations(self):
        self.assertEqual(SWING_PHASE, dict(FL="A", RR="A", FR="B", RL="B"))
        populations = set()
        for leg in LEGS:
            for joint in JOINTS:
                swing_side = "NEG" if joint == "ABD" and leg in ("FL", "RL") else "POS"
                for side, opposite_side in (("POS", "NEG"), ("NEG", "POS")):
                    population = motor_population(leg, joint, side)
                    populations.add(population)
                    channel = f"{leg}_{joint}_{side}"
                    phase = (
                        SWING_PHASE[leg]
                        if side == swing_side
                        else ("B" if SWING_PHASE[leg] == "A" else "A")
                    )
                    other = "B" if phase == "A" else "A"
                    node = self.nodes[population]
                    self.assertEqual((node["rhythm"], node["tnorm"]), ("beta", 5))
                    self.assertEqual(
                        {
                            s
                            for (s, t), e in self.edges.items()
                            if t == population and e["type"] == "exc"
                        },
                        (
                            {f"PHASE_{phase}_KNEE_DRIVE_HG", f"REFLEX_{leg}_HG"}
                            if joint == "KNEE" and side == "NEG"
                            else {f"PHASE_{phase}_BETA"}
                        ),
                    )
                    self.assertEqual(self.edges[(population, channel)]["type"], "exc")
                    for target in (population, channel):
                        self.assert_inhibits(
                            f"REFLEX_{leg}_EXTENSION_VETO_HG"
                            if joint == "KNEE" and side == "NEG"
                            else f"PHASE_{other}_INHIBITOR",
                            target,
                            1,
                        )
                        self.assert_inhibits("REST_NUCLEUS", target, 4)
                        self.assert_inhibits(
                            motor_population(leg, joint, opposite_side), target
                        )
        self.assertEqual(len(populations), 24)
        self.assertEqual(len(MOTOR_OUTPUTS), 24)

    def test_stop_clears_all_phase_motor_states_and_retained_start_bias(self):
        for name in self.nodes:
            if (
                name.startswith("PHASE_")
                or name in MOTOR_OUTPUTS
                or name.startswith(
                    ("FRONT_LEFT_", "FRONT_RIGHT_", "REAR_LEFT_", "REAR_RIGHT_")
                )
            ):
                self.assert_inhibits("REST_NUCLEUS", name, 4)
        for target in (
            "WALK_ENABLED",
            "WALK_NUCLEUS",
            "START_A_BIAS",
            "PHASE_A_T2",
            "PHASE_B_T2",
            "PHASE_A_BETA",
            "PHASE_B_BETA",
        ):
            self.assert_inhibits("STOP_REQUEST_HG", target, 4)
        self.assert_inhibits("START_REQUEST_HG", "REST_ACTIVE", 4)
        self.assert_inhibits("START_REQUEST_HG", "REST_NUCLEUS", 4)

    def test_ack_is_isolated_from_behavior(self):
        for source, target in self.edges:
            self.assertEqual(
                source.startswith("TRANSPORT_ACK"), target.startswith("TRANSPORT_ACK")
            )


if __name__ == "__main__":
    unittest.main()

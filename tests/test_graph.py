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
    REAR_FRONT_PARTNER,
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
            "A": {"LEG_RL_DONE_HG"},
            "B": {"LEG_RR_DONE_HG"},
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

    def test_local_motor_betas_receive_move_or_support_evidence(self):
        self.assertEqual(SWING_PHASE, dict(FL="B", RR="B", FR="A", RL="A"))
        populations = set()
        for leg in LEGS:
            stem = f"LEG_{leg}"
            support = "A" if SWING_PHASE[leg] == "B" else "B"
            for joint in JOINTS:
                swing_side = "NEG" if joint == "ABD" and leg in ("FL", "RL") else "POS"
                for side in ("POS", "NEG"):
                    population = motor_population(leg, joint, side)
                    populations.add(population)
                    channel = f"{leg}_{joint}_{side}"
                    expected = (
                        {stem + "_MOVE_HG"}
                        if side == swing_side
                        else {f"PHASE_{support}_DRIVE_HG", stem + "_DONE_HG"}
                    )
                    if joint == "KNEE" and side == "NEG":
                        expected.add(f"REFLEX_{leg}_HG")
                        self.assertNotIn(
                            (f"REFLEX_{leg}_EXTENSION_VETO_HG", population), self.edges
                        )
                        self.assertNotIn(
                            (motor_population(leg, "KNEE", "POS"), population),
                            self.edges,
                        )
                    self.assertEqual(
                        {
                            a
                            for (a, b), e in self.edges.items()
                            if b == population and e["type"] == "exc"
                        },
                        expected,
                    )
                    self.assertEqual(
                        (
                            self.nodes[population]["rhythm"],
                            self.nodes[population]["tnorm"],
                        ),
                        ("beta", 5),
                    )
                    self.assertEqual(self.edges[population, channel]["type"], "exc")
                    self.assert_inhibits("REST_NUCLEUS", population, 4)
                    self.assert_inhibits("REST_NUCLEUS", channel, 4)
        self.assertEqual(len(populations), 24)

    def test_stop_clears_switch_requests_and_all_motor_outputs(self):
        for name in self.nodes:
            if (
                name.startswith(
                    (
                        "PHASE_",
                        "LEG_",
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

    def test_rear_moves_follow_front_return_without_reflex_triggering_handoff(self):
        for rear, front in REAR_FRONT_PARTNER.items():
            relay = f"LEG_{rear}_MOVE_HG"
            sources = {
                a
                for (a, b), e in self.edges.items()
                if b == relay and e["type"] == "exc"
            }
            self.assertEqual(sources, {f"LEG_{front}_HANDOFF_BETA"})
            self.assertEqual(
                self.edges[f"LEG_{front}_DONE_HG", f"LEG_{front}_HANDOFF_BETA"]["type"],
                "exc",
            )
            self.assertEqual(self.nodes[f"LEG_{front}_HANDOFF_BETA"]["tnorm"], 3)
            self.assertNotIn((f"{front}_KNEE_NEG", relay), self.edges)
            self.assertNotIn((f"{front}_HIP_POS", relay), self.edges)
        for leg in LEGS:
            stem = f"LEG_{leg}"
            self.assertEqual(
                self.edges[f"{leg}_KNEE_POS", stem + "_RETURN_BETA"]["type"], "exc"
            )
            self.assertEqual(
                self.edges[stem + "_RETURN_BETA", stem + "_DONE"]["type"], "exc"
            )
            self.assertEqual(
                self.edges[stem + "_DONE_HG", stem + "_DONE"]["type"], "exc"
            )
            self.assert_inhibits(stem + "_DONE_HG", stem + "_MOVE_HG", 64)

    def test_push_runs_beside_motor_beta_and_clears_from_retained_readiness(self):
        for leg in LEGS:
            stem = f"LEG_{leg}"
            for a, b in [
                (stem + "_MOVE_HG", stem + "_PUSH_HG"),
                (stem + "_PUSH_HG", f"{leg}_KNEE_PUSH"),
                (motor_population(leg, "HIP", "POS"), stem + "_SWING_READY"),
                (stem + "_SWING_READY", stem + "_SWING_READY_HG"),
                (stem + "_SWING_READY_HG", stem + "_SWING_READY"),
            ]:
                self.assertEqual(self.edges[a, b]["type"], "exc")
                self.assertNotIn("rule", self.edges[a, b])
            self.assert_inhibits(stem + "_PUSH_HG", f"{leg}_KNEE_POS", 64)
            self.assertNotIn(
                (stem + "_PUSH_HG", motor_population(leg, "HIP", "POS")), self.edges
            )
            for target in [stem + "_PUSH_HG", f"{leg}_KNEE_PUSH"]:
                self.assert_inhibits(stem + "_SWING_READY_HG", target, 64)
                self.assert_inhibits(stem + "_DONE_HG", target, 64)

    def test_landing_does_not_wait_for_support_beta_or_leave_flexion_latched(self):
        for leg in LEGS:
            for source in (f"LEG_{leg}_RETURN_BETA", f"LEG_{leg}_DONE_HG"):
                edge = self.edges[source, f"{leg}_KNEE_NEG"]
                self.assertEqual(edge["type"], "exc")
                self.assertNotIn("rule", edge)
                self.assert_inhibits(source, f"{leg}_KNEE_POS", 64)
                self.assert_inhibits(source, f"REFLEX_{leg}_EXTENSION_VETO_HG", 64)
            # The fixed landing branch must not remove the regular motor path
            # or its fixed reflex teaching input.
            beta = motor_population(leg, "KNEE", "NEG")
            self.assertEqual(self.edges[beta, f"{leg}_KNEE_NEG"]["type"], "exc")
            self.assertNotIn("rule", self.edges[f"REFLEX_{leg}_HG", beta])

    def test_ack_is_isolated_from_behavior(self):
        for source, target in self.edges:
            self.assertEqual(
                source.startswith("TRANSPORT_ACK"), target.startswith("TRANSPORT_ACK")
            )


if __name__ == "__main__":
    unittest.main()

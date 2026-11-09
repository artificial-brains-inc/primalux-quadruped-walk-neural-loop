import json
import unittest

from ab import Brain
from ab_sdk.design_submit import design_sha256

from design_brain import create_brain
from robot.configuration import ROOT
from robot.contracts import (
    INPUT_SIZES,
    CONTACT_INPUTS,
    JOINTS,
    LEGS,
    MOTOR_OUTPUTS,
    OUTPUT_SIZES,
    NEXT_LEG,
    AIR_INPUTS,
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


    def test_sixteen_populations_93_input_neurons_and_matching_saved_design(self):
        self.assertEqual(self.brain.validate(), [])
        self.assertEqual(len(INPUT_SIZES), 16)
        self.assertEqual(sum(INPUT_SIZES.values()), 93)
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

    def test_liftoff_and_landing_require_local_neural_permission(self):
        for leg in LEGS:
            stem = f"LEG_{leg}"
            for rail in (CONTACT_INPUTS[leg], AIR_INPUTS[leg]):
                self.assertEqual(self.nodes[rail]["neurons"], 4)
                self.assertEqual(self.edges[rail, rail + "_HG"]["type"], "exc")
            for veto, permission, match, rail in (
                ("AIR_ACTIVE_VETO_HG", f"STEP_{leg}_ACTIVE_HG", "AIR_MATCH_HG", AIR_INPUTS[leg]),
                ("CONTACT_AIR_VETO_HG", stem + "_AIR_SEEN_HG", "CONTACT_MATCH_HG", CONTACT_INPUTS[leg]),
                ("CONTACT_RETURN_VETO_HG", stem + "_DONE_HG", "CONTACT_MATCH_HG", CONTACT_INPUTS[leg]),
            ):
                self.assertEqual(self.edges[rail, stem + "_" + veto]["type"], "exc")
                self.assert_inhibits(permission, stem + "_" + veto, 64)
                self.assert_inhibits(stem + "_" + veto, stem + "_" + match, 64)
                for source in ("REST_NUCLEUS", "STOP_REQUEST_HG"):
                    self.assertNotIn((source, stem + "_" + veto), self.edges)
            for suffix in ("AIR_MATCH_HG", "AIR_SEEN", "AIR_SEEN_HG", "CONTACT_MATCH_HG", "CONTACT_READY", "CONTACT_READY_HG"):
                for source in (f"STEP_{leg}_REQUEST_HG", f"STEP_{leg}_STANCE_HG", "STOP_REQUEST_HG", "REST_NUCLEUS"):
                    self.assert_inhibits(source, stem + "_" + suffix, 64)
            sources = {a for (a, b), e in self.edges.items() if b == f"STEP_{leg}_HANDOFF_BETA" and e["type"] == "exc"}
            self.assertEqual(sources, {stem + "_CONTACT_READY_HG"})
            for (a, b), edge in self.edges.items():
                if "CONTACT" in a or "CONTACT" in b or "AIR_" in a or "AIR_" in b:
                    self.assertNotIn("rule", edge)

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

    def test_cascade_retains_each_turn_and_hands_off_in_order(self):
        self.assertEqual(NEXT_LEG, dict(FR="RL", RL="FL", FL="RR", RR="FR"))
        self.assertFalse(any(n.startswith("PHASE_") for n in self.nodes))
        for leg, following in NEXT_LEG.items():
            stem, nxt = f"STEP_{leg}", f"STEP_{following}"
            for state in ("ACTIVE", "STANCE", "REQUEST"):
                for a, b in ((state, state + "_HG"), (state + "_HG", state)):
                    self.assertEqual(self.edges[stem + "_" + a, stem + "_" + b]["type"], "exc")
            self.assertEqual(self.edges[stem + "_HANDOFF_BETA", nxt + "_REQUEST"]["type"], "exc")
            self.assertEqual(self.edges[nxt + "_ACTIVE_HG", stem + "_STANCE"]["type"], "exc")
            for state in ("ACTIVE", "ACTIVE_HG", "REQUEST", "REQUEST_HG"):
                self.assert_inhibits(nxt + "_REQUEST_HG", stem + "_" + state, 64)
                self.assert_inhibits(nxt + "_ACTIVE_HG", stem + "_" + state, 4)
        starts = {b for (a,b),e in self.edges.items() if a == "START_REQUEST_HG" and b.startswith("STEP_") and e["type"] == "exc"}
        self.assertEqual(starts, {"STEP_FR_REQUEST", "STEP_RL_STANCE", "STEP_FL_STANCE", "STEP_RR_STANCE"})

    def test_beta_brake_is_recruited_before_contact_and_controls_handoff(self):
        for leg in LEGS:
            stem = f"STEP_{leg}"
            for suffix in ("HANDOFF_BETA", "BRAKE_BETA"):
                self.assertEqual((self.nodes[stem + "_" + suffix]["rhythm"], self.nodes[stem + "_" + suffix]["tnorm"]), ("beta", 5))
            self.assertEqual(self.edges[stem + "_ACTIVE_HG", stem + "_BRAKE_BETA"]["type"], "exc")
            self.assertEqual(self.edges[stem + "_HANDOFF_BETA", stem + "_BRAKE_BETA"]["role"], "feedback")
            edge = self.edges[stem + "_BRAKE_BETA", stem + "_HANDOFF_BETA"]
            self.assertEqual((edge["type"], edge["role"], edge["strength"]), ("inh", "feedback", 0.5))
            self.assertNotIn("rule", edge)

    def test_local_motor_betas_receive_move_or_support_evidence(self):
        populations = set()
        for leg in LEGS:
            stem = f"LEG_{leg}"
            for joint in JOINTS:
                swing_side = "NEG" if joint == "ABD" and leg in ("FL", "RL") else "POS"
                for side in ("POS", "NEG"):
                    population = motor_population(leg, joint, side)
                    populations.add(population)
                    channel = f"{leg}_{joint}_{side}"
                    expected = (
                        {stem + "_MOVE_HG"}
                        if side == swing_side
                        else {f"STEP_{leg}_STANCE_HG", stem + "_DONE_HG"}
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
            if not name.endswith(("_AIR_ACTIVE_VETO_HG", "_CONTACT_AIR_VETO_HG", "_CONTACT_RETURN_VETO_HG")) and (
                name.startswith(
                    (
                        "STEP_",
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
            *(f"STEP_{leg}_{state}" for leg in LEGS for state in ("REQUEST", "ACTIVE", "STANCE")),
        ):
            self.assert_inhibits("STOP_REQUEST_HG", target, 4)
        for target in ("REST_ACTIVE", "REST_NUCLEUS"):
            self.assert_inhibits("START_REQUEST_HG", target, 4)

    def test_local_motor_return_and_rear_input_rhythm_are_preserved(self):
        for rear in ("RL", "RR"):
            relay = f"LEG_{rear}_DRIVE_BETA"
            self.assertEqual(self.nodes[relay]["tnorm"], 3)
            self.assertEqual(self.edges[f"STEP_{rear}_ACTIVE_HG", relay]["type"], "exc")
            self.assertEqual(self.edges[relay, f"LEG_{rear}_MOVE_HG"]["type"], "exc")
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
            # or its fixed reflex input.
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

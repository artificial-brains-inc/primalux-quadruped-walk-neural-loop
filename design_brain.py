"""Reciprocal disinhibition coordinates four explicit leg motor groups.

START, STOP, ACK, reward and four signed tilt neurons enter from outside.
Independent gamma reflexes veto local knee flexion, extend and self-inhibit.
"""

from pathlib import Path

from ab import Brain

from robot.contracts import (
    COMMAND_INPUT_SIZES,
    JOINTS,
    LEGS,
    MOTOR_OUTPUTS,
    REFLEX_CUES,
    REWARD_INPUT,
    SWING_PHASE,
    TILT_INPUTS,
    motor_population,
)

ROOT = Path(__file__).resolve().parent
# Multipliers of the SDK's calculated inhibitory reference, not TNorm values.
# Initial settings to test on Prima-Lux, not measured veto thresholds.
CROSS_INHIBITION = 1.0
RELEASE_INHIBITION = 1.0
STOP_INHIBITION = 4.0
REFLEX_INHIBITION = 4.0
REFLEX_TNORM = 3.0
REFLEX_RESET_TNORM = 3.0
REFLEX_OUTPUT_RELAY_TNORM = 3.0
GAIT_LEARNING_RULE = "STDP3"
GAIT_REWARD_TYPE = "LTP"


def create_brain(*, learning=True):
    b = Brain(
        "Spot - Learning Coordination and Support Reflexes"
        if learning
        else "Spot - Static Coordination and Support Reflexes"
    )
    coordinates = {}
    motor_populations = []

    def opu(name, rhythm, tnorm, x, y):
        b.opu(name, rhythm, tnorm)
        coordinates[name] = (x, y)

    def output(name, x, y):
        b.output(name)
        coordinates[name] = (x, y)

    def inhibit(source, target, strength, *, feedback=False, plastic=False):
        b.connect(
            source,
            target,
            "inh",
            strength=strength,
            role="feedback" if feedback else None,
            **(
                dict(
                    rule=GAIT_LEARNING_RULE,
                    reward="GAIT_REWARD",
                    reward_type=GAIT_REWARD_TYPE,
                )
                if plastic and learning
                else {}
            ),
        )

    for i, name in enumerate(COMMAND_INPUT_SIZES):
        b.input(name, COMMAND_INPUT_SIZES[name])
        coordinates[name] = (0, i * 180)
        opu(name + "_HG", "high-gamma", 10, 220, i * 180)
        b.connect(name, name + "_HG")

    b.input(REWARD_INPUT, 1)
    coordinates[REWARD_INPUT] = (2200, 0)
    opu("GAIT_REWARD_RELAY", "high-gamma", 10, 2500, 0)
    opu("GAIT_REWARD", "dopaminergic", 3, 2800, 0)
    b.connect(REWARD_INPUT, "GAIT_REWARD_RELAY")
    b.connect("GAIT_REWARD_RELAY", "GAIT_REWARD")

    output("WALK_ENABLED", 1080, 0)
    output("REST_ACTIVE", 1080, 180)
    opu("WALK_NUCLEUS", "high-gamma", 10, 1360, 0)
    opu("REST_NUCLEUS", "high-gamma", 10, 1360, 180)
    # A live input is one event, not a held level. Capture it in an unopposed
    # request latch, then retain its drive neurally until the goal takes over.
    for i, (action, opposite, success) in enumerate(
        (
            ("START", "STOP", "WALK_NUCLEUS"),
            ("STOP", "START", "REST_NUCLEUS"),
        )
    ):
        request, driver = action + "_REQUEST", action + "_REQUEST_HG"
        output(request, 500, i * 180)
        opu(driver, "high-gamma", 10, 780, i * 180)
        b.connect("WALK_" + action + "_HG", request)
        b.connect(request, driver)
        b.connect(driver, request)
        for target in (request, driver):
            inhibit("WALK_" + opposite + "_HG", target, STOP_INHIBITION)
            inhibit(success, target, STOP_INHIBITION)

    # Reinforcement lives inside the graph, never in periodic host resends.
    # Ordinary output-to-helper edges provide the helper construction path.
    for state, nucleus, command, opposite_command in (
        ("WALK_ENABLED", "WALK_NUCLEUS", "START_REQUEST_HG", "STOP_REQUEST_HG"),
        ("REST_ACTIVE", "REST_NUCLEUS", "STOP_REQUEST_HG", "START_REQUEST_HG"),
    ):
        b.connect(command, state)
        b.connect(state, nucleus)
        b.connect(nucleus, state)
        inhibit(opposite_command, state, STOP_INHIBITION)
        inhibit(opposite_command, nucleus, STOP_INHIBITION)
    for source, state, nucleus in (
        ("REST_NUCLEUS", "WALK_ENABLED", "WALK_NUCLEUS"),
        ("WALK_NUCLEUS", "REST_ACTIVE", "REST_NUCLEUS"),
    ):
        inhibit(source, state, STOP_INHIBITION)
        inhibit(source, nucleus, STOP_INHIBITION, feedback=True)
    opu("WALK_DRIVE", "theta", 2.01, 1660, 0)
    b.connect("WALK_NUCLEUS", "WALK_DRIVE")

    output("START_A_BIAS", 500, 540)
    opu("START_A_BIAS_HG", "high-gamma", 10, 780, 540)
    b.connect("START_REQUEST_HG", "START_A_BIAS")
    b.connect("START_A_BIAS", "START_A_BIAS_HG")
    inhibit("STOP_REQUEST_HG", "START_A_BIAS", STOP_INHIBITION)

    for i, phase in enumerate(("A", "B")):
        stem = "PHASE_" + phase
        y = 780 + i * 420
        opu(stem + "_T1", "theta", 3, 0, y)
        opu(stem + "_T2", "theta", 2.01, 300, y)
        opu(stem + "_BETA", "beta", 5, 620, y)
        opu(stem + "_INHIBITOR", "beta", 5, 620, y + 180)
        opu(stem + "_RELEASE", "beta", 3, 960, y)
        output(stem + "_OUT", 1320, y)
        output(stem + "_INHIBITOR_OUT", 960, y + 180)
        output(stem + "_RELEASE_OUT", 1320, y + 180)
        b.connect("WALK_DRIVE", stem + "_T1")
        b.connect(stem + "_T1", stem + "_T2")
        b.connect(stem + "_T2", stem + "_BETA")
        b.connect(stem + "_T2", stem + "_INHIBITOR")
        b.connect(stem + "_BETA", stem + "_OUT")
        b.connect(stem + "_BETA", stem + "_RELEASE")
        b.connect(stem + "_INHIBITOR", stem + "_INHIBITOR_OUT")
        b.connect(stem + "_RELEASE", stem + "_RELEASE_OUT")
        # Downstream A suppresses I_A, which releases B (and vice versa).
        inhibit(
            stem + "_RELEASE",
            stem + "_INHIBITOR",
            RELEASE_INHIBITION,
            feedback=True,
            plastic=True,
        )
        inhibit(
            stem + "_RELEASE", stem + "_INHIBITOR_OUT", RELEASE_INHIBITION, plastic=True
        )

    for suffix in ("T2", "BETA", "INHIBITOR"):
        inhibit("START_A_BIAS_HG", "PHASE_B_" + suffix, CROSS_INHIBITION)
    inhibit("PHASE_A_INHIBITOR", "START_A_BIAS", CROSS_INHIBITION)
    for phase, other in (("A", "B"), ("B", "A")):
        b.connect(f"PHASE_{phase}_T2", f"PHASE_{other}_T1", role="feedback")
        source = f"PHASE_{phase}_INHIBITOR"
        for suffix in ("T2", "BETA", "INHIBITOR", "RELEASE"):
            inhibit(
                source,
                f"PHASE_{other}_{suffix}",
                CROSS_INHIBITION,
                feedback=True,
                plastic=True,
            )
        for suffix in ("OUT", "INHIBITOR_OUT", "RELEASE_OUT"):
            inhibit(source, f"PHASE_{other}_{suffix}", CROSS_INHIBITION, plastic=True)

    # Four separate leg columns; opposing populations for three joints each.
    # The phase shares preparation; local Beta T5 -> Beta T5 relays express it.
    for li, leg in enumerate(LEGS):
        swing = SWING_PHASE[leg]
        stance = "B" if swing == "A" else "A"
        for ji, joint in enumerate(JOINTS):
            swing_side = "NEG" if joint == "ABD" and leg in ("FL", "RL") else "POS"
            for si, side in enumerate(("POS", "NEG")):
                channel = f"{leg}_{joint}_{side}"
                population = motor_population(leg, joint, side)
                motor_populations.append(population)
                phase = swing if side == swing_side else stance
                other = "B" if phase == "A" else "A"
                x, y = li * 900, 1760 + ji * 380 + si * 170
                opu(population, "beta", 5, x, y)
                output(channel, x + 500, y)
                b.connect(f"PHASE_{phase}_BETA", population)
                b.connect(population, channel)
                for target in (population, channel):
                    inhibit(
                        f"PHASE_{other}_INHIBITOR",
                        target,
                        CROSS_INHIBITION,
                        plastic=True,
                    )
            for side, other in (("POS", "NEG"), ("NEG", "POS")):
                b.connect(
                    motor_population(leg, joint, side),
                    motor_population(leg, joint, other),
                    "inh",
                    role="feedback",
                )
                b.connect(
                    motor_population(leg, joint, side), f"{leg}_{joint}_{other}", "inh"
                )

    # Each independent reflex receives two one-neuron sensory paths directly.
    # Shared sensory evidence can recruit several legs; no corner veto is used.
    reflex_nodes = []
    for i, name in enumerate(TILT_INPUTS):
        b.input(name, 1)
        coordinates[name] = (i * 900, 3120)
    for li, leg in enumerate(LEGS):
        x = li * 900
        stem = "REFLEX_" + leg
        trigger, reset = stem + "_GAMMA", stem + "_RESET_GAMMA"
        motor, clear, active = stem + "_MOTOR_HG", stem + "_CLEAR_HG", stem + "_ACTIVE"
        opu(trigger, "gamma", REFLEX_TNORM, x, 3340)
        opu(reset, "gamma", REFLEX_RESET_TNORM, x, 3580)
        # Builder 0.4.11 accepts beta/high-gamma as output sources, including
        # inhibitory clearing. These two relays only adapt the output boundary.
        opu(motor, "high-gamma", REFLEX_OUTPUT_RELAY_TNORM, x + 300, 3340)
        opu(clear, "high-gamma", REFLEX_OUTPUT_RELAY_TNORM, x + 300, 3580)
        output(active, x + 580, 3340)
        reflex_nodes.extend((trigger, reset, motor, clear, active))
        for cue in REFLEX_CUES[leg]:
            b.connect(cue, trigger)
        b.connect(trigger, motor)
        b.connect(trigger, reset)
        b.connect(reset, clear)
        inhibit(reset, trigger, REFLEX_INHIBITION, feedback=True)
        inhibit(reset, motor, REFLEX_INHIBITION)
        b.connect(motor, f"{leg}_KNEE_NEG")
        b.connect(motor, active)
        for target in (motor_population(leg, "KNEE", "POS"), f"{leg}_KNEE_POS"):
            inhibit(motor, target, REFLEX_INHIBITION)
        for target in (active, f"{leg}_KNEE_NEG"):
            inhibit(clear, target, REFLEX_INHIBITION)
    for target in reflex_nodes:
        inhibit("REST_NUCLEUS", target, STOP_INHIBITION)
        inhibit("STOP_REQUEST_HG", target, STOP_INHIBITION)

    phase_nodes = [
        n["name"] for n in b.to_dict()["nodes"] if n["name"].startswith("PHASE_")
    ]
    for target in (
        "WALK_DRIVE",
        "START_A_BIAS",
        "START_A_BIAS_HG",
        *phase_nodes,
        *motor_populations,
        *MOTOR_OUTPUTS,
    ):
        inhibit("REST_NUCLEUS", target, STOP_INHIBITION)
    for phase in ("A", "B"):
        for suffix in ("T2", "BETA", "INHIBITOR", "RELEASE"):
            inhibit("STOP_REQUEST_HG", f"PHASE_{phase}_{suffix}", STOP_INHIBITION)

    output("TRANSPORT_ACK_OUT", 500, 360)
    opu("TRANSPORT_ACK_RESET", "high-gamma", 10, 780, 360)
    b.connect("TRANSPORT_ACK_HG", "TRANSPORT_ACK_OUT")
    b.connect("TRANSPORT_ACK_OUT", "TRANSPORT_ACK_RESET")
    b.connect("TRANSPORT_ACK_RESET", "TRANSPORT_ACK_OUT", "inh")
    doc = b.to_dict()
    for node in doc["nodes"]:
        node["x"], node["y"] = coordinates[node["name"]]
    return Brain.from_dict(doc)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Author the Spot design, then inspect/build it with the SDK."
    )
    parser.add_argument(
        "--static",
        action="store_true",
        help="Use static connections for a controlled baseline.",
    )
    brain = create_brain(learning=not parser.parse_args().static)
    brain.save(ROOT / "brain.abdesign.json")
    print("Saved brain.abdesign.json. Inspect with ab design, then build with the SDK.")

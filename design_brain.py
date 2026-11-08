"""A retained neural switch coordinates diagonal support and swing.

Local motor activity recruits a push, swing and return sequence. High-gamma
reflexes directly command fast extension and recruit the regular motor path.
"""

from pathlib import Path

from ab import Brain

from robot.contracts import (
    COMMAND_INPUT_SIZES,
    JOINTS,
    LEGS,
    MOTOR_OUTPUTS,
    REAR_FRONT_PARTNER,
    REFLEX_CUES,
    REWARD_INPUT,
    REWARD_INPUT_NEURONS,
    SUPPORT_PHASE,
    SWING_PHASE,
    TILT_INPUTS,
    TILT_NEURONS,
    motor_population,
)

ROOT = Path(__file__).resolve().parent
# Multipliers of the SDK's calculated inhibitory reference, not TNorm values.
# Initial settings to test on Prima-Lux, not measured veto thresholds.
CROSS_INHIBITION = 4.0
RELEASE_INHIBITION = 4.0
STOP_INHIBITION = 4.0
REFLEX_INHIBITION = 64.0
REFLEX_RESET_INHIBITION = 4.0
REFLEX_TNORM = 5.0
REQUEST_CLEAR_INHIBITION = 64.0
GAIT_LEARNING_RULE = "STDP3"
GAIT_REWARD_TYPE = "LTP"


def create_brain(*, learning=True):
    b = Brain(
        "Spot - Neural Switch with Learning and Local Reflexes"
        if learning
        else "Spot - Neural Switch and Local Reflexes"
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

    b.input(REWARD_INPUT, REWARD_INPUT_NEURONS)
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
    # One switch, two retained states. START captures A once. A successful
    # handoff clears its request, while its state persists until the other wins.
    phase_nodes = []
    for pi, phase in enumerate(("A", "B")):
        stem, y = f"PHASE_{phase}", 760 + pi * 610
        for suffix, rhythm, tnorm, x, dy in (
            ("REQUEST_HG", "high-gamma", 10, 280, 0),
            ("DRIVE_HG", "high-gamma", 10, 900, 0),
            ("MOTOR_FEEDBACK_HG", "high-gamma", 10, 0, 250),
            ("FEEDBACK_BETA", "beta", 5, 330, 250),
            ("BETA", "beta", 5, 660, 250),
            ("RELEASE", "beta", 3, 990, 250),
        ):
            name = f"{stem}_{suffix}"
            opu(name, rhythm, tnorm, x, y + dy)
            phase_nodes.append(name)
        for suffix, x, dy in (
            ("REQUEST", 0, 0),
            ("OUT", 600, 0),
            ("RELEASE_OUT", 1310, 250),
        ):
            name = f"{stem}_{suffix}"
            output(name, x, y + dy)
            phase_nodes.append(name)
    b.connect("START_REQUEST_HG", "PHASE_A_REQUEST")
    for phase, other in (("A", "B"), ("B", "A")):
        stem, opposite = f"PHASE_{phase}", f"PHASE_{other}"
        for source, target in (
            (stem + "_REQUEST", stem + "_REQUEST_HG"),
            (stem + "_REQUEST_HG", stem + "_REQUEST"),
            (stem + "_REQUEST_HG", stem + "_OUT"),
            (stem + "_OUT", stem + "_DRIVE_HG"),
            (stem + "_DRIVE_HG", stem + "_OUT"),
            (stem + "_MOTOR_FEEDBACK_HG", stem + "_FEEDBACK_BETA"),
            (stem + "_FEEDBACK_BETA", stem + "_BETA"),
            (stem + "_BETA", stem + "_RELEASE"),
            (stem + "_RELEASE", stem + "_RELEASE_OUT"),
            (stem + "_RELEASE", opposite + "_REQUEST"),
        ):
            b.connect(source, target)
        for suffix in ("REQUEST", "REQUEST_HG"):
            inhibit(stem + "_DRIVE_HG", stem + "_" + suffix, REQUEST_CLEAR_INHIBITION)
        # The request continues through competition until the new state is on.
        # Its clearing burst resets the old feedback path, not the actuators.
        for suffix in (
            "OUT",
            "DRIVE_HG",
            "MOTOR_FEEDBACK_HG",
            "FEEDBACK_BETA",
            "BETA",
            "RELEASE",
        ):
            inhibit(
                stem + "_REQUEST_HG",
                opposite + "_" + suffix,
                STOP_INHIBITION,
                feedback=suffix
                in ("MOTOR_FEEDBACK_HG", "FEEDBACK_BETA", "BETA", "RELEASE"),
            )
        for suffix in ("OUT", "DRIVE_HG", "MOTOR_FEEDBACK_HG"):
            inhibit(
                stem + "_DRIVE_HG",
                opposite + "_" + suffix,
                CROSS_INHIBITION,
                feedback=suffix != "OUT",
            )
        inhibit(stem + "_DRIVE_HG", opposite + "_RELEASE_OUT", CROSS_INHIBITION)
        # Learning may adjust local release recovery. State retention, handoff
        # capture, interlocks and all motor vetoes remain static.
        for suffix in ("FEEDBACK_BETA", "BETA"):
            inhibit(
                stem + "_RELEASE",
                stem + "_" + suffix,
                RELEASE_INHIBITION,
                feedback=True,
                plastic=True,
            )

    for li, leg in enumerate(LEGS):
        for ji, joint in enumerate(JOINTS):
            for si, side in enumerate(("POS", "NEG")):
                population = motor_population(leg, joint, side)
                opu(population, "beta", 5, li * 1400, 3800 + ji * 600 + si * 260)
                motor_populations.append(population)
                output(
                    f"{leg}_{joint}_{side}", li * 1400 + 650, 3800 + ji * 600 + si * 260
                )

    # A and B select diagonal sequences: front push/swing/return, then rear.
    # Each local movement has an early push branch beside its motor Betas.
    gait_nodes = []
    for li, leg in enumerate(LEGS):
        stem, x, y = f"LEG_{leg}", li * 1400, 2000
        swing, support = SWING_PHASE[leg], SUPPORT_PHASE[leg]
        for suffix, rhythm, tnorm, dy in (
            ("MOVE_HG", "high-gamma", 10, 0),
            ("PUSH_HG", "high-gamma", 10, 280),
            ("SWING_READY_HG", "high-gamma", 10, 560),
            ("RETURN_BETA", "beta", 3, 840),
            ("DONE_HG", "high-gamma", 10, 1120),
        ):
            opu(stem + "_" + suffix, rhythm, tnorm, x, y + dy)
            gait_nodes.append(stem + "_" + suffix)
        if leg not in REAR_FRONT_PARTNER:
            opu(stem + "_HANDOFF_BETA", "beta", 3, x + 650, y + 1400)
            gait_nodes.append(stem + "_HANDOFF_BETA")
            b.connect(stem + "_DONE_HG", stem + "_HANDOFF_BETA")
            inhibit(
                f"PHASE_{support}_DRIVE_HG", stem + "_HANDOFF_BETA", CROSS_INHIBITION
            )
        output(stem + "_SWING_READY", x + 650, y + 560)
        gait_nodes.append(stem + "_SWING_READY")
        output(stem + "_DONE", x + 650, y + 1120)
        output(f"{leg}_KNEE_PUSH", x + 650, y + 280)
        gait_nodes.append(stem + "_DONE")
        source = (
            f"LEG_{REAR_FRONT_PARTNER[leg]}_HANDOFF_BETA"
            if leg in REAR_FRONT_PARTNER
            else f"PHASE_{swing}_DRIVE_HG"
        )
        b.connect(source, stem + "_MOVE_HG")
        b.connect(stem + "_MOVE_HG", stem + "_PUSH_HG")
        b.connect(stem + "_PUSH_HG", f"{leg}_KNEE_PUSH")
        b.connect(f"{leg}_KNEE_PUSH", stem + "_PUSH_HG", role="feedback")
        # Read actual knee flexion output before recruiting the return.
        b.connect(f"{leg}_KNEE_POS", stem + "_RETURN_BETA")
        b.connect(stem + "_RETURN_BETA", stem + "_DONE")
        b.connect(stem + "_DONE", stem + "_DONE_HG")
        b.connect(stem + "_DONE_HG", stem + "_DONE")
        for suffix in (
            "MOVE_HG",
            "PUSH_HG",
            "SWING_READY",
            "SWING_READY_HG",
            "RETURN_BETA",
            "DONE",
            "DONE_HG",
        ):
            inhibit(f"PHASE_{support}_DRIVE_HG", stem + "_" + suffix, CROSS_INHIBITION)
        for target in (
            stem + "_MOVE_HG",
            stem + "_PUSH_HG",
            stem + "_SWING_READY",
            stem + "_SWING_READY_HG",
            f"{leg}_KNEE_PUSH",
        ):
            inhibit(stem + "_DONE_HG", target, REQUEST_CLEAR_INHIBITION)
        inhibit(f"PHASE_{support}_DRIVE_HG", f"{leg}_KNEE_PUSH", CROSS_INHIBITION)
        # Motor Beta activity ends the preparation branch while its output
        # is still being recruited. No Python minimum stroke or delay.
        b.connect(motor_population(leg, "HIP", "POS"), stem + "_SWING_READY")
        b.connect(stem + "_SWING_READY", stem + "_SWING_READY_HG")
        b.connect(stem + "_SWING_READY_HG", stem + "_SWING_READY")
        for target in (stem + "_PUSH_HG", f"{leg}_KNEE_PUSH"):
            inhibit(stem + "_SWING_READY_HG", target, REQUEST_CLEAR_INHIBITION)
        inhibit(stem + "_PUSH_HG", f"{leg}_KNEE_POS", REFLEX_INHIBITION)

    reflex_nodes = []
    for li, leg in enumerate(LEGS):
        swing, support = SWING_PHASE[leg], SUPPORT_PHASE[leg]
        stem, x, y = f"LEG_{leg}", li * 1400, 3800
        gate = f"REFLEX_{leg}_EXTENSION_VETO_HG"
        opu(gate, "high-gamma", 10, x, y + 1800)
        reflex_nodes.append(gate)
        b.connect(stem + "_SWING_READY_HG", gate)
        # Begin landing from the return pathway itself. Do not wait for the
        # ordinary support Beta to recruit its output after a completed swing.
        # DONE_HG retains this extension while the following leg prepares.
        for source in (stem + "_RETURN_BETA", stem + "_DONE_HG"):
            b.connect(source, f"{leg}_KNEE_NEG")
            inhibit(source, gate, REFLEX_INHIBITION)
        inhibit(stem + "_RETURN_BETA", f"{leg}_KNEE_POS", REFLEX_INHIBITION)
        for ji, joint in enumerate(JOINTS):
            swing_side = "NEG" if joint == "ABD" and leg in ("FL", "RL") else "POS"
            for si, side in enumerate(("POS", "NEG")):
                population = motor_population(leg, joint, side)
                channel = f"{leg}_{joint}_{side}"
                is_swing = side == swing_side
                if is_swing:
                    b.connect(stem + "_MOVE_HG", population)
                    for target in (population, channel):
                        inhibit(f"PHASE_{support}_DRIVE_HG", target, CROSS_INHIBITION)
                        inhibit(
                            stem + "_DONE_HG",
                            target,
                            REFLEX_INHIBITION
                            if joint == "KNEE" and target == channel
                            else CROSS_INHIBITION,
                        )
                else:
                    # Support remains available after this leg's local return.
                    for source in (f"PHASE_{support}_DRIVE_HG", stem + "_DONE_HG"):
                        b.connect(source, population, role="operand", units=1)
                    veto = gate if joint == "KNEE" else stem + "_MOVE_HG"
                    # Do not accumulate swing-veto inhibition inside extension
                    # Beta: it must receive reflex evidence during a swing.
                    inhibit(
                        veto,
                        channel,
                        REFLEX_INHIBITION if joint == "KNEE" else CROSS_INHIBITION,
                    )
                    if joint != "KNEE":
                        inhibit(veto, population, CROSS_INHIBITION)
                b.connect(population, channel)
            for side, opposite_side in (("POS", "NEG"), ("NEG", "POS")):
                source = motor_population(leg, joint, side)
                if joint != "KNEE":
                    inhibit(
                        source,
                        motor_population(leg, joint, opposite_side),
                        1,
                        feedback=True,
                    )
                    inhibit(source, f"{leg}_{joint}_{opposite_side}", 1)

    # A phase advances only after its rear leg reaches its return state.
    # This is internal motor history, not a claim of measured foot contact.
    for rear in REAR_FRONT_PARTNER:
        b.connect(f"LEG_{rear}_DONE_HG", f"PHASE_{SWING_PHASE[rear]}_MOTOR_FEEDBACK_HG")

    for i, name in enumerate(TILT_INPUTS):
        b.input(name, TILT_NEURONS)
        coordinates[name] = (i * 1400, 6200)
    for li, leg in enumerate(LEGS):
        x, stem = li * 1400, f"REFLEX_{leg}"
        trigger = stem + "_HG"
        active, gate = (
            stem + "_ACTIVE",
            stem + "_EXTENSION_VETO_HG",
        )
        opu(trigger, "high-gamma", REFLEX_TNORM, x, 6500)
        output(active, x + 650, 6500)
        fast = f"{leg}_KNEE_REFLEX_EXTEND"
        output(fast, x + 650, 6800)
        recovery = stem + "_RECOVERY_BETA"
        clear = stem + "_OUTPUT_RESET_BETA"
        opu(recovery, "beta", 3, x, 7100)
        opu(clear, "beta", 3, x + 650, 7100)
        reflex_nodes.extend((trigger, active, recovery, clear))
        for cue in REFLEX_CUES[leg]:
            b.connect(cue, trigger)
        b.connect(trigger, trigger, role="feedback")
        b.connect(trigger, fast)
        # The same high-gamma neurons directly recruit the regular Beta.
        # This connection carries eligibility for reward-modulated learning;
        # the fast reflex output has its own fixed excitatory connection.
        b.connect(
            trigger,
            motor_population(leg, "KNEE", "NEG"),
            role="operand",
            units=1,
            **(
                dict(rule="STDP3", reward="GAIT_REWARD", reward_type="LTP")
                if learning
                else {}
            ),
        )
        b.connect(trigger, active)
        for target in (motor_population(leg, "KNEE", "POS"), f"{leg}_KNEE_POS", gate):
            inhibit(trigger, target, REFLEX_INHIBITION)
        # Clear the bistable motor command from its own activity, so a late
        # motor spike cannot outlive the upstream reflex-reset burst.
        b.connect(fast, recovery)
        b.connect(recovery, clear)
        inhibit(clear, fast, REFLEX_RESET_INHIBITION)
        inhibit(clear, trigger, REFLEX_RESET_INHIBITION, feedback=True)
        inhibit(clear, active, REFLEX_RESET_INHIBITION)
        inhibit("STOP_REQUEST_HG", fast, STOP_INHIBITION)

    for target in (*phase_nodes, *gait_nodes, *motor_populations, *reflex_nodes):
        inhibit("REST_NUCLEUS", target, STOP_INHIBITION)
        inhibit("STOP_REQUEST_HG", target, STOP_INHIBITION)
    for target in MOTOR_OUTPUTS:
        inhibit("REST_NUCLEUS", target, STOP_INHIBITION)
        if target.endswith("_KNEE_PUSH"):
            inhibit("STOP_REQUEST_HG", target, STOP_INHIBITION)

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
        description="Author the neural switch, then inspect/build its saved JSON with the SDK."
    )
    parser.add_argument(
        "--static",
        action="store_true",
        help="Omit learning metadata for a static comparison.",
    )
    brain = create_brain(learning=not parser.parse_args().static)
    brain.save(ROOT / "brain.abdesign.json")
    print("Saved brain.abdesign.json. Inspect with ab design, then build with the SDK.")

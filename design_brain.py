"""A contact-driven cascade coordinates four independent leg stages.

Local motor activity recruits a push, swing and return sequence. High-gamma
reflexes directly command fast extension and recruit the regular motor path.
"""

from pathlib import Path

from ab import Brain

from robot.contracts import (
    COMMAND_INPUT_SIZES,
    CONTACT_INPUTS,
    CONTACT_NEURONS,
    JOINTS,
    LEGS,
    MOTOR_OUTPUTS,
    NEXT_LEG,
    AIR_INPUTS,
    REFLEX_CUES,
    REWARD_INPUT,
    REWARD_INPUT_NEURONS,
    TILT_INPUTS,
    TILT_NEURONS,
    motor_population,
)

ROOT = Path(__file__).resolve().parent
# Multipliers of the SDK's calculated inhibitory reference, not TNorm values.
# Initial settings to test on Prima-Lux, not measured veto thresholds.
CROSS_INHIBITION = 4.0
STOP_INHIBITION = 4.0
REFLEX_INHIBITION = 64.0
REFLEX_RESET_INHIBITION = 4.0
REFLEX_TNORM = 5.0
REQUEST_CLEAR_INHIBITION = 64.0
GAIT_LEARNING_RULE = "STDP3"
RELEASE_REWARD_TYPE = "LTP"
CONTACT_CLEAR_INHIBITION = 64.0


def create_brain(*, learning=False, handoff_inhibition=0.5):
    b = Brain(
        "Spot - Contact Cascade with Inhibitory LTP"
        if learning
        else "Spot - Contact Cascade, Static Baseline"
    )
    pending_connections = []

    def connect(*args, **kwargs):
        pending_connections.append((args, kwargs))

    coordinates = {}
    motor_populations = []

    def opu(name, rhythm, tnorm, x, y):
        b.opu(name, rhythm, tnorm)
        coordinates[name] = (x, y)

    def output(name, x, y):
        b.output(name)
        coordinates[name] = (x, y)

    def inhibit(source, target, strength, *, feedback=False, plastic=False):
        connect(
            source,
            target,
            "inh",
            strength=strength,
            role="feedback" if feedback else None,
            **(
                dict(
                    rule=GAIT_LEARNING_RULE,
                    reward="GAIT_REWARD",
                    reward_type=RELEASE_REWARD_TYPE,
                )
                if plastic and learning
                else {}
            ),
        )

    for i, name in enumerate(COMMAND_INPUT_SIZES):
        b.input(name, COMMAND_INPUT_SIZES[name])
        coordinates[name] = (0, i * 180)
        opu(name + "_HG", "high-gamma", 10, 220, i * 180)
        connect(name, name + "_HG")

    b.input(REWARD_INPUT, REWARD_INPUT_NEURONS)
    coordinates[REWARD_INPUT] = (2200, 0)
    opu("GAIT_REWARD_RELAY", "high-gamma", 10, 2500, 0)
    opu("GAIT_REWARD", "dopaminergic", 3, 2800, 0)
    connect(REWARD_INPUT, "GAIT_REWARD_RELAY")
    connect("GAIT_REWARD_RELAY", "GAIT_REWARD")

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
        connect("WALK_" + action + "_HG", request)
        connect(request, driver)
        connect(driver, request)
        for target in (request, driver):
            inhibit("WALK_" + opposite + "_HG", target, STOP_INHIBITION)
            inhibit(success, target, STOP_INHIBITION)

    # Reinforcement lives inside the graph, never in periodic host resends.
    # Ordinary output-to-helper edges provide the helper construction path.
    for state, nucleus, command, opposite_command in (
        ("WALK_ENABLED", "WALK_NUCLEUS", "START_REQUEST_HG", "STOP_REQUEST_HG"),
        ("REST_ACTIVE", "REST_NUCLEUS", "STOP_REQUEST_HG", "START_REQUEST_HG"),
    ):
        connect(command, state)
        connect(state, nucleus)
        connect(nucleus, state)
        inhibit(opposite_command, state, STOP_INHIBITION)
        inhibit(opposite_command, nucleus, STOP_INHIBITION)
    for source, state, nucleus in (
        ("REST_NUCLEUS", "WALK_ENABLED", "WALK_NUCLEUS"),
        ("WALK_NUCLEUS", "REST_ACTIVE", "REST_NUCLEUS"),
    ):
        inhibit(source, state, STOP_INHIBITION)
        inhibit(source, nucleus, STOP_INHIBITION, feedback=True)
    # Four local stages. Each retains its turn until the next stage captures it.
    stage_nodes = []
    for li, leg in enumerate(LEGS):
        stem = f"STEP_{leg}"
        for suffix in ("REQUEST", "ACTIVE", "STANCE"):
            output(stem + "_" + suffix, li * 1400, 900 + 180 * ("REQUEST", "ACTIVE", "STANCE").index(suffix))
            opu(stem + "_" + suffix + "_HG", "high-gamma", 10, li * 1400 + 240, 900 + 180 * ("REQUEST", "ACTIVE", "STANCE").index(suffix))
            stage_nodes.extend((stem + "_" + suffix, stem + "_" + suffix + "_HG"))
            connect(stem + "_" + suffix, stem + "_" + suffix + "_HG")
            connect(stem + "_" + suffix + "_HG", stem + "_" + suffix)
        connect(stem + "_REQUEST_HG", stem + "_ACTIVE")
        for suffix in ("REQUEST", "REQUEST_HG"):
            inhibit(stem + "_ACTIVE_HG", stem + "_" + suffix, REQUEST_CLEAR_INHIBITION)
        for suffix in ("STANCE", "STANCE_HG"):
            inhibit(stem + "_REQUEST_HG", stem + "_" + suffix, REQUEST_CLEAR_INHIBITION)
            inhibit(stem + "_ACTIVE_HG", stem + "_" + suffix, CROSS_INHIBITION)
        for suffix in ("ACTIVE", "ACTIVE_HG"):
            inhibit(stem + "_STANCE_HG", stem + "_" + suffix, CROSS_INHIBITION)
        nxt = f"STEP_{NEXT_LEG[leg]}"
        connect(nxt + "_ACTIVE_HG", stem + "_STANCE")
        for suffix in ("ACTIVE", "ACTIVE_HG", "REQUEST", "REQUEST_HG"):
            inhibit(nxt + "_REQUEST_HG", stem + "_" + suffix, REQUEST_CLEAR_INHIBITION)
            inhibit(nxt + "_ACTIVE_HG", stem + "_" + suffix, CROSS_INHIBITION)
        if leg != "FR":
            connect("START_REQUEST_HG", stem + "_STANCE")
        # A beta-to-beta feedback brake is active before landing. Its plastic
        # return can affect the first handoff, not only an after-the-fact reset.
        for name in ("BRAKE_BETA", "HANDOFF_BETA"):
            opu(stem + "_" + name, "beta", 5, li * 1400 + 500, 1450 if name == "BRAKE_BETA" else 1700)
            stage_nodes.append(stem + "_" + name)
        connect(stem + "_ACTIVE_HG", stem + "_BRAKE_BETA")
        connect(stem + "_HANDOFF_BETA", stem + "_BRAKE_BETA", role="feedback")
        inhibit(stem + "_BRAKE_BETA", stem + "_HANDOFF_BETA", handoff_inhibition, feedback=True, plastic=True)
        connect(stem + "_HANDOFF_BETA", nxt + "_REQUEST")
        for name in ("BRAKE_BETA", "HANDOFF_BETA"):
            inhibit(stem + "_STANCE_HG", stem + "_" + name, REQUEST_CLEAR_INHIBITION)
    connect("START_REQUEST_HG", "STEP_FR_REQUEST")

    for li, leg in enumerate(LEGS):
        for ji, joint in enumerate(JOINTS):
            for si, side in enumerate(("POS", "NEG")):
                population = motor_population(leg, joint, side)
                opu(population, "beta", 5, li * 1400, 3800 + ji * 600 + si * 260)
                motor_populations.append(population)
                output(
                    f"{leg}_{joint}_{side}", li * 1400 + 650, 3800 + ji * 600 + si * 260
                )

    # Explicit contact and no-contact rails encode the same four bumpers.
    # Silence in asynchronous transport is never treated as lift-off evidence.
    sensor_state_nodes = []
    for li, leg in enumerate(LEGS):
        for rail, name in (("CONTACT", CONTACT_INPUTS[leg]), ("AIR", AIR_INPUTS[leg])):
            b.input(name, CONTACT_NEURONS)
            coordinates[name] = (li * 1400, 7800 if rail == "CONTACT" else 8100)
            opu(name + "_HG", "high-gamma", 10, li * 1400 + 220, 7800 if rail == "CONTACT" else 8100)
            connect(name, name + "_HG")
        stem = f"LEG_{leg}"
        for n in ("AIR_MATCH_HG", "AIR_ACTIVE_VETO_HG", "CONTACT_MATCH_HG", "CONTACT_AIR_VETO_HG", "CONTACT_RETURN_VETO_HG"):
            opu(stem + "_" + n, "high-gamma", 10, li * 1400 + 400, 8400 + 170 * ("AIR_MATCH_HG", "AIR_ACTIVE_VETO_HG", "CONTACT_MATCH_HG", "CONTACT_AIR_VETO_HG", "CONTACT_RETURN_VETO_HG").index(n))
        for state in ("AIR_SEEN", "CONTACT_READY"):
            output(stem + "_" + state, li * 1400 + 650, 8600 if state == "AIR_SEEN" else 9000)
            opu(stem + "_" + state + "_HG", "high-gamma", 10, li * 1400 + 900, 8600 if state == "AIR_SEEN" else 9000)
            connect(stem + "_" + state, stem + "_" + state + "_HG")
            connect(stem + "_" + state + "_HG", stem + "_" + state)
        connect(AIR_INPUTS[leg], stem + "_AIR_ACTIVE_VETO_HG")
        connect(AIR_INPUTS[leg] + "_HG", stem + "_AIR_MATCH_HG")
        inhibit(f"STEP_{leg}_ACTIVE_HG", stem + "_AIR_ACTIVE_VETO_HG", CONTACT_CLEAR_INHIBITION)
        inhibit(stem + "_AIR_ACTIVE_VETO_HG", stem + "_AIR_MATCH_HG", CONTACT_CLEAR_INHIBITION)
        connect(stem + "_AIR_MATCH_HG", stem + "_AIR_SEEN")
        connect(CONTACT_INPUTS[leg] + "_HG", stem + "_CONTACT_MATCH_HG")
        for veto, permission in (("CONTACT_AIR_VETO_HG", "AIR_SEEN_HG"), ("CONTACT_RETURN_VETO_HG", "DONE_HG")):
            connect(CONTACT_INPUTS[leg], stem + "_" + veto)
            inhibit(stem + "_" + permission, stem + "_" + veto, CONTACT_CLEAR_INHIBITION)
            inhibit(stem + "_" + veto, stem + "_CONTACT_MATCH_HG", CONTACT_CLEAR_INHIBITION)
        connect(stem + "_CONTACT_MATCH_HG", stem + "_CONTACT_READY")
        connect(stem + "_CONTACT_READY_HG", f"STEP_{leg}_HANDOFF_BETA")
        for suffix in ("AIR_MATCH_HG", "AIR_SEEN", "AIR_SEEN_HG", "CONTACT_MATCH_HG", "CONTACT_READY", "CONTACT_READY_HG"):
            target = stem + "_" + suffix
            sensor_state_nodes.append(target)
            for source in (f"STEP_{leg}_REQUEST_HG", f"STEP_{leg}_STANCE_HG"):
                inhibit(source, target, CONTACT_CLEAR_INHIBITION)

    # Preserve each leg's established local push/swing/return primitive.
    # Each local movement has an early push branch beside its motor Betas.
    gait_nodes = []
    for li, leg in enumerate(LEGS):
        stem, x, y = f"LEG_{leg}", li * 1400, 2000
        support_source = f"STEP_{leg}_STANCE_HG"
        for suffix, rhythm, tnorm, dy in (
            ("MOVE_HG", "high-gamma", 10, 0),
            ("PUSH_HG", "high-gamma", 10, 280),
            ("SWING_READY_HG", "high-gamma", 10, 560),
            ("RETURN_BETA", "beta", 3, 840),
            ("DONE_HG", "high-gamma", 10, 1120),
        ):
            opu(stem + "_" + suffix, rhythm, tnorm, x, y + dy)
            gait_nodes.append(stem + "_" + suffix)
        output(stem + "_SWING_READY", x + 650, y + 560)
        gait_nodes.append(stem + "_SWING_READY")
        output(stem + "_DONE", x + 650, y + 1120)
        output(f"{leg}_KNEE_PUSH", x + 650, y + 280)
        gait_nodes.append(stem + "_DONE")
        source = f"STEP_{leg}_ACTIVE_HG"
        if leg in ("RL", "RR"):
            # Retain the rear MOVE input's beta T3 rhythm and two-neuron width.
            opu(stem + "_DRIVE_BETA", "beta", 3, x + 650, y - 150)
            gait_nodes.append(stem + "_DRIVE_BETA")
            connect(source, stem + "_DRIVE_BETA")
            inhibit(support_source, stem + "_DRIVE_BETA", CROSS_INHIBITION)
            source = stem + "_DRIVE_BETA"
        connect(source, stem + "_MOVE_HG")
        connect(stem + "_MOVE_HG", stem + "_PUSH_HG")
        connect(stem + "_PUSH_HG", f"{leg}_KNEE_PUSH")
        connect(f"{leg}_KNEE_PUSH", stem + "_PUSH_HG", role="feedback")
        # Read actual knee flexion output before recruiting the return.
        connect(f"{leg}_KNEE_POS", stem + "_RETURN_BETA")
        connect(stem + "_RETURN_BETA", stem + "_DONE")
        connect(stem + "_DONE", stem + "_DONE_HG")
        connect(stem + "_DONE_HG", stem + "_DONE")
        for suffix in (
            "MOVE_HG",
            "PUSH_HG",
            "SWING_READY",
            "SWING_READY_HG",
            "RETURN_BETA",
            "DONE",
            "DONE_HG",
        ):
            inhibit(support_source, stem + "_" + suffix, CROSS_INHIBITION)
        for target in (
            stem + "_MOVE_HG",
            stem + "_PUSH_HG",
            stem + "_SWING_READY",
            stem + "_SWING_READY_HG",
            f"{leg}_KNEE_PUSH",
        ):
            inhibit(stem + "_DONE_HG", target, REQUEST_CLEAR_INHIBITION)
        inhibit(support_source, f"{leg}_KNEE_PUSH", CROSS_INHIBITION)
        for suffix in ("DONE", "DONE_HG", "RETURN_BETA", "SWING_READY", "SWING_READY_HG"):
            inhibit(f"STEP_{leg}_REQUEST_HG", stem + "_" + suffix, REQUEST_CLEAR_INHIBITION)
        # Motor Beta activity ends the preparation branch while its output
        # is still being recruited. No Python minimum stroke or delay.
        connect(motor_population(leg, "HIP", "POS"), stem + "_SWING_READY")
        connect(stem + "_SWING_READY", stem + "_SWING_READY_HG")
        connect(stem + "_SWING_READY_HG", stem + "_SWING_READY")
        for target in (stem + "_PUSH_HG", f"{leg}_KNEE_PUSH"):
            inhibit(stem + "_SWING_READY_HG", target, REQUEST_CLEAR_INHIBITION)
        inhibit(stem + "_PUSH_HG", f"{leg}_KNEE_POS", REFLEX_INHIBITION)

    reflex_nodes = []
    for li, leg in enumerate(LEGS):
        support_source = f"STEP_{leg}_STANCE_HG"
        stem, x, y = f"LEG_{leg}", li * 1400, 3800
        gate = f"REFLEX_{leg}_EXTENSION_VETO_HG"
        opu(gate, "high-gamma", 10, x, y + 1800)
        reflex_nodes.append(gate)
        connect(stem + "_SWING_READY_HG", gate)
        # Begin landing from the return pathway itself. Do not wait for the
        # ordinary support Beta to recruit its output after a completed swing.
        # DONE_HG retains this extension while the following leg prepares.
        for source in (stem + "_RETURN_BETA", stem + "_DONE_HG"):
            connect(source, f"{leg}_KNEE_NEG")
            inhibit(source, gate, REFLEX_INHIBITION)
        inhibit(stem + "_RETURN_BETA", f"{leg}_KNEE_POS", REFLEX_INHIBITION)
        for ji, joint in enumerate(JOINTS):
            swing_side = "NEG" if joint == "ABD" and leg in ("FL", "RL") else "POS"
            for si, side in enumerate(("POS", "NEG")):
                population = motor_population(leg, joint, side)
                channel = f"{leg}_{joint}_{side}"
                is_swing = side == swing_side
                if is_swing:
                    connect(stem + "_MOVE_HG", population)
                    for target in (population, channel):
                        inhibit(support_source, target, CROSS_INHIBITION)
                        inhibit(
                            stem + "_DONE_HG",
                            target,
                            REFLEX_INHIBITION
                            if joint == "KNEE" and target == channel
                            else CROSS_INHIBITION,
                        )
                else:
                    # Support remains available after this leg's local return.
                    for source in (support_source, stem + "_DONE_HG"):
                        # Every excitatory motor path stays fixed. Only the
                        # four inhibitory handoff-feedback paths can learn.
                        connect(
                            source,
                            population,
                            role="operand",
                            units=1,
                        )
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
                connect(population, channel)
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
            connect(cue, trigger)
        connect(trigger, trigger, role="feedback")
        connect(trigger, fast)
        # The same high-gamma neurons directly recruit the regular Beta.
        # Both reflex branches and every other excitatory input stay fixed.
        connect(
            trigger,
            motor_population(leg, "KNEE", "NEG"),
            role="operand",
            units=1,
        )
        connect(trigger, active)
        for target in (motor_population(leg, "KNEE", "POS"), f"{leg}_KNEE_POS", gate):
            inhibit(trigger, target, REFLEX_INHIBITION)
        # Clear the bistable motor command from its own activity, so a late
        # motor spike cannot outlive the upstream reflex-reset burst.
        connect(fast, recovery)
        connect(recovery, clear)
        inhibit(clear, fast, REFLEX_RESET_INHIBITION)
        inhibit(clear, trigger, REFLEX_RESET_INHIBITION, feedback=True)
        inhibit(clear, active, REFLEX_RESET_INHIBITION)
        inhibit("STOP_REQUEST_HG", fast, STOP_INHIBITION)

    for target in (*stage_nodes, *gait_nodes, *motor_populations, *reflex_nodes):
        inhibit("REST_NUCLEUS", target, STOP_INHIBITION)
        inhibit("STOP_REQUEST_HG", target, STOP_INHIBITION)
    for target in sensor_state_nodes:
        inhibit("REST_NUCLEUS", target, CONTACT_CLEAR_INHIBITION)
        inhibit("STOP_REQUEST_HG", target, CONTACT_CLEAR_INHIBITION)
    for target in MOTOR_OUTPUTS:
        inhibit("REST_NUCLEUS", target, STOP_INHIBITION)
        if target.endswith("_KNEE_PUSH"):
            inhibit("STOP_REQUEST_HG", target, STOP_INHIBITION)

    output("TRANSPORT_ACK_OUT", 500, 360)
    opu("TRANSPORT_ACK_RESET", "high-gamma", 10, 780, 360)
    connect("TRANSPORT_ACK_HG", "TRANSPORT_ACK_OUT")
    connect("TRANSPORT_ACK_OUT", "TRANSPORT_ACK_RESET")
    connect("TRANSPORT_ACK_RESET", "TRANSPORT_ACK_OUT", "inh")
    for args, kwargs in pending_connections:
        b.connect(*args, **kwargs)
    doc = b.to_dict()
    for node in doc["nodes"]:
        node["x"], node["y"] = coordinates[node["name"]]
    return Brain.from_dict(doc)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Author the contact cascade using SDK public fields.")
    parser.add_argument("--learning", action="store_true", help="Enable four inhibitory STDP3/LTP paths.")
    parser.add_argument("--handoff-inhibition", type=float, default=0.5, help="Initial multiplier on each local timing feedback connection.")
    args = parser.parse_args()
    if args.handoff_inhibition < 0.1:
        parser.error("handoff inhibition must be at least 0.1")
    brain = create_brain(learning=args.learning, handoff_inhibition=args.handoff_inhibition)
    brain.save(ROOT / "brain.abdesign.json")
    print("Saved brain.abdesign.json. Inspect with ab design, then build with the SDK.")

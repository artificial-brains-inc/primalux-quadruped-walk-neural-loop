"""Eight named inputs: 3 command, 10 reward and 48 tilt neurons."""

LEGS = ("FL", "FR", "RL", "RR")
LEG_NAMES = dict(FL="front left", FR="front right", RL="rear left", RR="rear right")
LEG_PREFIXES = {leg: name.upper().replace(" ", "_") for leg, name in LEG_NAMES.items()}
JOINTS = ("ABD", "HIP", "KNEE")
JOINT_NAMES = dict(ABD="shoulder abduction", HIP="shoulder rotation", KNEE="elbow")
SUPPORT_PHASE = dict(FL="A", RR="A", FR="B", RL="B")
SWING_PHASE = {
    leg: "B" if phase == "A" else "A" for leg, phase in SUPPORT_PHASE.items()
}
COMMAND_INPUT_SIZES = {"WALK_START": 1, "WALK_STOP": 1, "TRANSPORT_ACK": 1}
REWARD_INPUT = "GAIT_REWARD_IN"
REWARD_INPUT_NEURONS = 10
REWARD_CLASSIFICATION = {
    "population": "GAIT_REWARD",
    "neuron_class": "dopaminergic",
    "tnorm": 3,
    "outcome": "upright_forward_progress",
    "rule": "STDP3",
    "reward_type": "LTP",
}
TILT_INPUTS = ("TILT_ROLL_NEG", "TILT_ROLL_POS", "TILT_PITCH_NEG", "TILT_PITCH_POS")
TILT_NEURONS = 12
INPUT_SIZES = {
    **COMMAND_INPUT_SIZES,
    REWARD_INPUT: REWARD_INPUT_NEURONS,
    **dict.fromkeys(TILT_INPUTS, TILT_NEURONS),
}
# Webots ENU: negative roll lowers the left side; positive pitch lowers the nose.
# These are neural wiring choices, never a controller-side leg selector.
REFLEX_CUES = {
    "FL": ("TILT_ROLL_NEG", "TILT_PITCH_POS"),
    "FR": ("TILT_ROLL_POS", "TILT_PITCH_POS"),
    "RL": ("TILT_ROLL_NEG", "TILT_PITCH_NEG"),
    "RR": ("TILT_ROLL_POS", "TILT_PITCH_NEG"),
}
REFLEX_OUTPUTS = tuple(f"REFLEX_{leg}_ACTIVE" for leg in LEGS)
REFLEX_MOTOR_OUTPUTS = tuple(f"{leg}_KNEE_REFLEX_EXTEND" for leg in LEGS)
GAIT_MOTOR_OUTPUTS = tuple(
    f"{leg}_{joint}_{side}"
    for leg in LEGS
    for joint in JOINTS
    for side in ("POS", "NEG")
)
MOTOR_OUTPUTS = (*GAIT_MOTOR_OUTPUTS, *REFLEX_MOTOR_OUTPUTS)
OUTPUT_SIZES = {
    name: 1
    for name in (
        *MOTOR_OUTPUTS,
        *REFLEX_OUTPUTS,
        "WALK_ENABLED",
        "REST_ACTIVE",
        "START_REQUEST",
        "STOP_REQUEST",
        "PHASE_A_OUT",
        "PHASE_B_OUT",
        "PHASE_A_REQUEST",
        "PHASE_B_REQUEST",
        "PHASE_A_RELEASE_OUT",
        "PHASE_B_RELEASE_OUT",
        "TRANSPORT_ACK_OUT",
    )
}


def motor_population(leg, joint, side):
    return f"{LEG_PREFIXES[leg]}_{joint}_{side}_BETA"


def validate_channels(event):
    c = (event.get("actuation") or {}).get("channels")
    if (
        type(event.get("step")) is not int
        or not isinstance(c, dict)
        or set(c) != set(OUTPUT_SIZES)
    ):
        raise ValueError("Expected the complete native walking output contract")
    if any(type(v) not in (int, float) or v not in (0, 1) for v in c.values()):
        raise ValueError("Single-neuron outputs must be zero or one")
    return c

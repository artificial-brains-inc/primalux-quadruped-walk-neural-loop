"""Three command neurons and one outcome-reward neuron; neural gait timing."""

LEGS = ("FL", "FR", "RL", "RR")
LEG_NAMES = dict(FL="front left", FR="front right", RL="rear left", RR="rear right")
LEG_PREFIXES = {leg: name.upper().replace(" ", "_") for leg, name in LEG_NAMES.items()}
JOINTS = ("ABD", "HIP", "KNEE")
JOINT_NAMES = dict(ABD="shoulder abduction", HIP="shoulder rotation", KNEE="elbow")
SWING_PHASE = dict(FL="A", RR="A", FR="B", RL="B")
COMMAND_INPUT_SIZES = {"WALK_START": 1, "WALK_STOP": 1, "TRANSPORT_ACK": 1}
REWARD_INPUT = "GAIT_REWARD_IN"
INPUT_SIZES = {**COMMAND_INPUT_SIZES, REWARD_INPUT: 1}
MOTOR_OUTPUTS = tuple(
    f"{leg}_{joint}_{side}"
    for leg in LEGS
    for joint in JOINTS
    for side in ("POS", "NEG")
)
OUTPUT_SIZES = {
    name: 1
    for name in (
        *MOTOR_OUTPUTS,
        "WALK_ENABLED",
        "REST_ACTIVE",
        "START_A_BIAS",
        "PHASE_A_OUT",
        "PHASE_B_OUT",
        "PHASE_A_INHIBITOR_OUT",
        "PHASE_B_INHIBITOR_OUT",
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

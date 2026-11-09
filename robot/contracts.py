"""Sixteen input populations: 3 command, 10 reward, 48 tilt and 32 foot-state neurons."""

LEGS = ("FL", "FR", "RL", "RR")
LEG_NAMES = dict(FL="front left", FR="front right", RL="rear left", RR="rear right")
LEG_PREFIXES = {leg: name.upper().replace(" ", "_") for leg, name in LEG_NAMES.items()}
JOINTS = ("ABD", "HIP", "KNEE")
JOINT_NAMES = dict(ABD="shoulder abduction", HIP="shoulder rotation", KNEE="elbow")
SEQUENCE = ("FR", "RL", "FL", "RR")
NEXT_LEG = dict(zip(SEQUENCE, SEQUENCE[1:] + SEQUENCE[:1]))
# Fixed neural wiring: shift the supported body away from the next swing foot.
# Positive HIP moves a planted foot forward relative to the body; positive ABD
# moves it right. Body translation has the opposite sign for a planted foot.
SUPPORT_DIRECTIONS = {
    "FR": {"HIP": "POS", "ABD": "POS"},
    "RL": {"HIP": "NEG", "ABD": "NEG"},
    "FL": {"HIP": "POS", "ABD": "NEG"},
    "RR": {"HIP": "NEG", "ABD": "POS"},
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
    "reward_types": {"handoff_feedback": "LTP", "sensor_loop_inhibition": "LTP"},
}
TILT_INPUTS = ("TILT_ROLL_NEG", "TILT_ROLL_POS", "TILT_PITCH_NEG", "TILT_PITCH_POS")
TILT_NEURONS = 12
CONTACT_INPUTS = {leg: f"FOOT_{leg}_CONTACT" for leg in LEGS}
AIR_INPUTS = {leg: f"FOOT_{leg}_AIR" for leg in LEGS}
CONTACT_NEURONS = 4
CONTACT_DEVICE_NAMES = {leg: name + " foot touch" for leg, name in LEG_NAMES.items()}
INPUT_SIZES = {
    **COMMAND_INPUT_SIZES,
    REWARD_INPUT: REWARD_INPUT_NEURONS,
    **dict.fromkeys(TILT_INPUTS, TILT_NEURONS),
    **dict.fromkeys(CONTACT_INPUTS.values(), CONTACT_NEURONS),
    **dict.fromkeys(AIR_INPUTS.values(), CONTACT_NEURONS),
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
PUSH_MOTOR_OUTPUTS = tuple(f"{leg}_KNEE_PUSH" for leg in LEGS)
GAIT_MOTOR_OUTPUTS = tuple(
    f"{leg}_{joint}_{side}"
    for leg in LEGS
    for joint in JOINTS
    for side in ("POS", "NEG")
)
SUPPORT_MOTOR_OUTPUTS = tuple(
    f"{leg}_{joint}_SUPPORT_{side}"
    for leg in LEGS for joint in ("HIP", "ABD") for side in ("POS", "NEG")
)
MOTOR_OUTPUTS = (*GAIT_MOTOR_OUTPUTS, *REFLEX_MOTOR_OUTPUTS, *PUSH_MOTOR_OUTPUTS, *SUPPORT_MOTOR_OUTPUTS)
OUTPUT_SIZES = {
    name: 1
    for name in (
        *MOTOR_OUTPUTS,
        *REFLEX_OUTPUTS,
        *(f"LEG_{leg}_DONE" for leg in LEGS),
        *(f"LEG_{leg}_KICK_DONE" for leg in LEGS),
        *(f"LEG_{leg}_SWING_READY" for leg in LEGS),
        *(f"LEG_{leg}_CONTACT_READY" for leg in LEGS),
        "WALK_ENABLED",
        "REST_ACTIVE",
        "START_REQUEST",
        "STOP_REQUEST",
        *(f"STEP_{leg}_{state}" for leg in LEGS for state in ("ACTIVE", "STANCE", "REQUEST")),
        *(f"LEG_{leg}_AIR_SEEN" for leg in LEGS),
        *(f"STEP_{leg}_PREPARE" for leg in LEGS),
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

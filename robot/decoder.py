"""Fixed actuator calibration only; never reads a phase or chooses a gait."""

from .contracts import JOINTS, LEGS, validate_channels


def joint_targets(event, config, *, rhythm_only=False):
    channels = validate_channels(event)
    targets = {}
    for leg in LEGS:
        side = "left" if leg in ("FL", "RL") else "right"
        for joint in JOINTS:
            settings = config["joint_targets"][joint]
            q = settings["neutral_" + side]
            if not rhythm_only:
                positive = channels[f"{leg}_{joint}_POS"]
                negative = channels[f"{leg}_{joint}_NEG"]
                fast = joint == "KNEE" and channels[f"{leg}_KNEE_REFLEX_EXTEND"]
                push = joint == "KNEE" and channels[f"{leg}_KNEE_PUSH"]
                negative = max(negative, int(fast), int(push))
                # Independent output calibration; same-direction commands do
                # not add angles. Antagonists still cancel without a winner.
                direction = positive - negative
                extension = max(
                    settings["negative_excursion"] * negative,
                    config["reflex"]["extension_excursion_rad"] * int(fast),
                    config["push"]["extension_excursion_rad"] * int(push),
                )
                q += direction * (
                    settings["positive_excursion"] if direction > 0 else extension
                )
                if joint in ("HIP", "ABD"):
                    bias = channels[f"{leg}_{joint}_SUPPORT_POS"] - channels[f"{leg}_{joint}_SUPPORT_NEG"]
                    q += bias * config["support_shift"][joint + "_offset_rad"]
            targets[(leg, joint)] = q
    return targets


def joint_speeds(event, config, *, rhythm_only=False):
    """Fixed speed calibration of motor outputs, independent of tilt/ACTIVE."""
    channels = validate_channels(event)
    speeds = {}
    for leg in LEGS:
        for joint in JOINTS:
            speed = config["joint_targets"][joint]["speed_rad_s"]
            if joint == "KNEE" and not rhythm_only and not channels[f"{leg}_KNEE_POS"]:
                for branch, suffix in (("reflex", "REFLEX_EXTEND"), ("push", "PUSH")):
                    if channels[f"{leg}_KNEE_{suffix}"]:
                        speed = max(speed, config[branch]["extension_speed_rad_s"])
            speeds[leg, joint] = speed
    return speeds

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
                negative = max(negative, int(fast))
                # Simultaneous antagonists cancel; no winner or inferred phase.
                direction = positive - negative
                q += direction * (
                    config["reflex"]["extension_excursion_rad"]
                    if fast
                    else settings[
                        "positive_excursion" if direction > 0 else "negative_excursion"
                    ]
                )
            targets[(leg, joint)] = q
    return targets


def joint_speeds(event, config, *, rhythm_only=False):
    """Fixed speed calibration of motor outputs, independent of tilt/ACTIVE."""
    channels = validate_channels(event)
    return {
        (leg, joint): (
            config["reflex"]["extension_speed_rad_s"]
            if joint == "KNEE"
            and not rhythm_only
            and channels[f"{leg}_KNEE_REFLEX_EXTEND"]
            and not channels[f"{leg}_KNEE_POS"]
            else config["joint_targets"][joint]["speed_rad_s"]
        )
        for leg in LEGS
        for joint in JOINTS
    }

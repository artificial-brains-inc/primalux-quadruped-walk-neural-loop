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
                # Simultaneous antagonists cancel; no winner or inferred phase.
                direction = positive - negative
                q += (
                    direction
                    * settings[
                        "positive_excursion" if direction > 0 else "negative_excursion"
                    ]
                )
            targets[(leg, joint)] = q
    return targets

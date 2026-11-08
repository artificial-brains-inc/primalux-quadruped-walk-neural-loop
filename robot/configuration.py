import json
import math
import os
from pathlib import Path

from .contracts import JOINTS

ROOT = Path(__file__).resolve().parents[1]
MODEL_LIMITS = {"ABD": (-0.6, 0.5), "HIP": (-1.7, 1.7), "KNEE": (-0.45, 1.6)}


def environment_path():
    return Path(os.environ.get("AB_ENV", str(ROOT / ".env"))).expanduser().resolve()


def load_config(root=ROOT):
    c = json.loads((root / "config.json").read_text())
    step = c["physics_step_ms"]
    if type(step) is not int or step <= 0 or step % 16:
        raise ValueError("physics_step_ms must be a positive multiple of 16")
    for key in (
        "output_timeout_seconds",
        "ack_timeout_seconds",
        "max_run_wall_seconds",
    ):
        if type(c[key]) not in (int, float) or not math.isfinite(c[key]) or c[key] <= 0:
            raise ValueError(f"{key} must be positive and finite")
    if set(c["joint_targets"]) != set(JOINTS):
        raise ValueError("Expected ABD, HIP and KNEE actuator settings")
    for key in (
        "min_forward_speed_m_s",
        "max_abs_roll_rad",
        "max_abs_pitch_rad",
        "min_body_height_m",
        "progress_epsilon_m",
    ):
        value = c["reward"][key]
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"reward.{key} must be positive and finite")
    if any(
        c["reward"][k] >= math.pi / 2 for k in ("max_abs_roll_rad", "max_abs_pitch_rad")
    ):
        raise ValueError("Upright roll/pitch thresholds must be below pi/2")
    for joint, values in c["joint_targets"].items():
        if any(
            type(v) not in (int, float) or not math.isfinite(v) for v in values.values()
        ):
            raise ValueError("Finite joint settings required")
        for key in ("positive_excursion", "negative_excursion", "speed_rad_s"):
            if values[key] <= 0:
                raise ValueError("Positive excursions and servo speed required")
        low, high = MODEL_LIMITS[joint]
        for side in ("left", "right"):
            q = values["neutral_" + side]
            if (
                not low
                <= q - values["negative_excursion"]
                <= q + values["positive_excursion"]
                <= high
            ):
                raise ValueError(f"{joint} endpoints exceed the Spot model limits")
    return c

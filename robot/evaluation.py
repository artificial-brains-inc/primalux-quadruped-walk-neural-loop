"""Measurements only. This module never changes neural or physical commands."""

from .contracts import JOINTS, LEGS, MOTOR_OUTPUTS


def summarize(rows):
    if not rows:
        return {"frames": 0}
    walking = [r for r in rows if r["requested_command"] == "start"]
    entries, previous, previous_sequence = [], None, None
    both = active = 0
    for row in walking:
        if row["command_sequence"] != previous_sequence:
            previous = None
        previous_sequence = row["command_sequence"]
        c = row["outputs"]
        a, b = c["PHASE_A_OUT"], c["PHASE_B_OUT"]
        state = "BOTH" if a and b else "A" if a else "B" if b else "NONE"
        both += bool(a and b)
        active += any(c[k] for k in MOTOR_OUTPUTS)
        if state in ("A", "B") and state != previous:
            entries.append((row["command_sequence"], state))
        previous = state
    alternations = sum(
        s1 == s2 and p1 != p2 for (s1, p1), (s2, p2) in zip(entries, entries[1:])
    )
    repeats = sum(
        s1 == s2 and p1 == p2 for (s1, p1), (s2, p2) in zip(entries, entries[1:])
    )
    stopped = [r for r in rows if r["requested_command"] == "stop"]
    overlapping = {
        f"{leg}_{joint}": sum(
            bool(
                r["outputs"][f"{leg}_{joint}_POS"]
                and r["outputs"][f"{leg}_{joint}_NEG"]
            )
            for r in walking
        )
        for leg in LEGS
        for joint in JOINTS
    }
    stop_sequences = {
        b["command_sequence"]
        for a, b in zip(rows, rows[1:])
        if a["requested_command"] == "start"
        and b["requested_command"] == "stop"
        and a["command_sequence"] != b["command_sequence"]
    }
    return dict(
        frames=len(rows),
        walking_frames=len(walking),
        reward_active_frames=sum(r.get("reward", {}).get("value", 0) for r in rows),
        best_reward_forward_progress_m=max(
            (r.get("reward", {}).get("forward_high_water_m", 0.0) for r in rows),
            default=0.0,
        ),
        motor_active_walking_frames=active,
        phase_a_entries=sum(p == "A" for _, p in entries),
        phase_b_entries=sum(p == "B" for _, p in entries),
        alternating_phase_entries=alternations,
        repeated_same_phase_entries=repeats,
        both_phases_active_frames=both,
        motor_antagonist_overlap_frames=sum(
            any(
                r["outputs"][f"{joint}_POS"] and r["outputs"][f"{joint}_NEG"]
                for joint in overlapping
            )
            for r in walking
        ),
        motor_antagonist_overlap_by_joint=overlapping,
        start_bias_active_walking_frames=sum(
            bool(r["outputs"].get("START_A_BIAS", 0)) for r in walking
        ),
        diagnostic_active_walking_frames={
            name: sum(bool(r["outputs"].get(name, 0)) for r in walking)
            for name in (
                "WALK_ENABLED",
                "REST_ACTIVE",
                "PHASE_A_INHIBITOR_OUT",
                "PHASE_B_INHIBITOR_OUT",
                "PHASE_A_RELEASE_OUT",
                "PHASE_B_RELEASE_OUT",
            )
        },
        stop_commands_observed_after_walking=len(stop_sequences),
        motor_active_after_stop_request_frames=sum(
            any(r["outputs"][k] for k in MOTOR_OUTPUTS) for r in stopped
        ),
        displacement_xyz_m=[
            b - a for a, b in zip(rows[0]["body_xyz_m"], rows[-1]["body_xyz_m"])
        ],
        maximum_absolute_roll_rad=max(abs(r["body_rpy_rad"][0]) for r in rows),
        maximum_absolute_pitch_rad=max(abs(r["body_rpy_rad"][1]) for r in rows),
        maximum_queued_frames=max(r["queued_native_frames"] for r in rows),
        simulation_seconds=rows[-1]["simulation_time"] - rows[0]["simulation_time"],
        wall_seconds=rows[-1]["wall_seconds"] - rows[0]["wall_seconds"],
    )

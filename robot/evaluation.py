"""Measurements only. This module never changes neural or physical commands."""

from .contracts import JOINTS, LEGS, MOTOR_OUTPUTS, REFLEX_OUTPUTS, SUPPORT_PHASE


def motor_pattern_counts(rows):
    """Count actuator evidence; phase readouts never choose the classification."""
    confirmed = [
        r
        for r in rows
        if r["outputs"].get("WALK_ENABLED")
        and not r["outputs"].get("REST_ACTIVE")
        and r.get("pending_command") is None
    ]
    patterns = dict(A=0, B=0)
    same_side = dict(left=0, right=0)
    all_flex = 0
    single_leg = dict.fromkeys(LEGS, 0)
    overlapping_flexion = 0
    push_frames = dict.fromkeys(LEGS, 0)
    for row in confirmed:
        c = row["outputs"]
        for phase in patterns:
            match = True
            for leg in LEGS:
                side = "NEG" if SUPPORT_PHASE[leg] == phase else "POS"
                opposite = "POS" if side == "NEG" else "NEG"
                match &= all(
                    c[f"{leg}_{joint}_{side}"] == 1
                    and c[f"{leg}_{joint}_{opposite}"] == 0
                    for joint in ("HIP", "KNEE")
                )
            patterns[phase] += match
        flex = {
            leg: bool(c[f"{leg}_KNEE_POS"]) and not c[f"{leg}_KNEE_NEG"] for leg in LEGS
        }
        all_flex += all(flex.values())
        overlapping_flexion += sum(flex.values()) > 1
        for leg in LEGS:
            single_leg[leg] += flex[leg] and sum(flex.values()) == 1
            push_frames[leg] += bool(c.get(f"{leg}_KNEE_PUSH", 0))
        same_side["left"] += (
            flex["FL"] and flex["RL"] and not (flex["FR"] or flex["RR"])
        )
        same_side["right"] += (
            flex["FR"] and flex["RR"] and not (flex["FL"] or flex["RL"])
        )
    return dict(
        confirmed_walking_frames=len(confirmed),
        single_leg_swing_frames=single_leg,
        overlapping_knee_flexion_frames=overlapping_flexion,
        push_motor_frames=push_frames,
        complete_diagonal_motor_pattern_frames=patterns,
        all_four_knees_flexing_frames=all_flex,
        same_side_only_knee_flexion_frames=same_side,
    )


def summarize(rows):
    if not rows:
        return {"frames": 0}
    walking = [
        r
        for r in rows
        if r["requested_command"] == "start"
        and r.get("recovery_state", "idle") == "idle"
    ]
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
        **motor_pattern_counts(walking),
        frames=len(rows),
        recoveries=max(r.get("recovery_count", 0) for r in rows),
        recovery_frames=sum(r.get("recovery_state", "idle") != "idle" for r in rows),
        walking_frames=len(walking),
        reward_active_frames=sum(r.get("reward", {}).get("value", 0) for r in rows),
        reflex_active_frames={
            name: sum(bool(r["outputs"].get(name, 0)) for r in rows)
            for name in REFLEX_OUTPUTS
        },
        reflex_entries={
            name: sum(
                bool(r["outputs"].get(name, 0))
                and (i == 0 or not rows[i - 1]["outputs"].get(name, 0))
                for i, r in enumerate(rows)
            )
            for name in REFLEX_OUTPUTS
        },
        best_reward_forward_progress_m=max(
            (r.get("reward", {}).get("forward_high_water_m", 0.0) for r in rows),
            default=0.0,
        ),
        motor_active_walking_frames=active,
        motor_quiet_walking_frames=len(walking) - active,
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
        diagnostic_active_walking_frames={
            name: sum(bool(r["outputs"].get(name, 0)) for r in walking)
            for name in (
                "WALK_ENABLED",
                "REST_ACTIVE",
                "PHASE_A_REQUEST",
                "PHASE_B_REQUEST",
                "PHASE_A_RELEASE_OUT",
                "PHASE_B_RELEASE_OUT",
            )
        },
        stop_commands_observed_after_walking=len(stop_sequences),
        motor_active_after_stop_request_frames=sum(
            any(r["outputs"][k] for k in MOTOR_OUTPUTS) for r in stopped
        ),
        displacement_xyz_m=[
            sum(
                b["body_xyz_m"][i] - a["body_xyz_m"][i]
                for a, b in zip(rows, rows[1:])
                if a.get("recovery_state", "idle")
                == b.get("recovery_state", "idle")
                == "idle"
                and a.get("recovery_count", 0) == b.get("recovery_count", 0)
            )
            for i in range(3)
        ],
        maximum_absolute_roll_rad=max(abs(r["body_rpy_rad"][0]) for r in rows),
        maximum_absolute_pitch_rad=max(abs(r["body_rpy_rad"][1]) for r in rows),
        maximum_queued_frames=max(r["queued_native_frames"] for r in rows),
        simulation_seconds=rows[-1]["simulation_time"] - rows[0]["simulation_time"],
        wall_seconds=rows[-1]["wall_seconds"] - rows[0]["wall_seconds"],
    )

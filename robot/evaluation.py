"""Measurements only. This module never changes neural or physical commands."""

import math

from .contracts import JOINTS, LEGS, MOTOR_OUTPUTS, REFLEX_OUTPUTS, NEXT_LEG


def motor_pattern_counts(rows):
    """Count actuator evidence; phase readouts never choose the classification."""
    confirmed = [
        r
        for r in rows
        if r["outputs"].get("WALK_ENABLED")
        and not r["outputs"].get("REST_ACTIVE")
        and r.get("pending_command") is None
    ]

    same_side = dict(left=0, right=0)
    all_flex = 0
    single_leg = dict.fromkeys(LEGS, 0)
    overlapping_flexion = 0
    push_frames = dict.fromkeys(LEGS, 0)
    for row in confirmed:
        c = row["outputs"]
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
        all_four_knees_flexing_frames=all_flex,
        same_side_only_knee_flexion_frames=same_side,
    )


def walking_progress(rows):
    """Project each walking episode along its initial heading; exclude recovery jumps."""
    seconds = forward = 0.0
    heading = None
    previous = None
    for row in rows:
        c = row["outputs"]
        confirmed = (row["requested_command"] == "start" and c.get("WALK_ENABLED")
                     and not c.get("REST_ACTIVE") and row.get("pending_command") is None
                     and row.get("recovery_state", "idle") == "idle")
        if not confirmed:
            previous = None
            heading = None
            continue
        if previous is None or row["command_sequence"] != previous["command_sequence"] or row.get("recovery_count", 0) != previous.get("recovery_count", 0):
            heading = row["body_rpy_rad"][2]
        else:
            dt = row["simulation_time"] - previous["simulation_time"]
            if dt > 0:
                seconds += dt
                dx, dy = (row["body_xyz_m"][i] - previous["body_xyz_m"][i] for i in (0, 1))
                forward += dx * math.cos(heading) + dy * math.sin(heading)
        previous = row
    recovery_events = sum(b.get("recovery_count", 0) > a.get("recovery_count", 0) for a, b in zip(rows, rows[1:]))
    return dict(confirmed_walking_seconds=seconds, forward_distance_m=forward,
                forward_speed_m_s=forward / seconds if seconds else None,
                recoveries_per_walking_minute=recovery_events * 60 / seconds if seconds else None)


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
    ready_times = {}
    handoff_delays = {leg: [] for leg in LEGS}
    for row in walking:
        if row["command_sequence"] != previous_sequence:
            previous = None
            ready_times.clear()
        previous_sequence = row["command_sequence"]
        c = row["outputs"]
        for leg in LEGS:
            if c.get(f"LEG_{leg}_CONTACT_READY") and leg not in ready_times:
                ready_times[leg] = row.get("native_step", row.get("step", 0))
        selected = [leg for leg in LEGS if c.get(f"STEP_{leg}_ACTIVE")]
        both += len(selected) > 1
        active += any(c[k] for k in MOTOR_OUTPUTS)
        if len(selected) == 1 and selected[0] != previous:
            leg = selected[0]
            if previous is not None and NEXT_LEG.get(previous) == leg and previous in ready_times:
                handoff_delays[previous].append(row.get("native_step", row.get("step", 0)) - ready_times[previous])
            if previous is not None:
                ready_times.pop(previous, None)
            entries.append((row["command_sequence"], leg))
            previous = leg
    valid = sum(s1 == s2 and NEXT_LEG[p1] == p2 for (s1, p1), (s2, p2) in zip(entries, entries[1:]))
    invalid = sum(s1 == s2 and NEXT_LEG[p1] != p2 for (s1, p1), (s2, p2) in zip(entries, entries[1:]))
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
        **walking_progress(rows),
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
        stage_entries={leg: sum(p == leg for _, p in entries) for leg in LEGS},
        sequence_transitions=valid,
        out_of_order_stage_transitions=invalid,
        simultaneous_stage_frames=both,
        contact_to_next_stage_native_steps=handoff_delays,
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
                *(f"STEP_{leg}_REQUEST" for leg in LEGS),
                *(f"LEG_{leg}_AIR_SEEN" for leg in LEGS),
                *(f"LEG_{leg}_CONTACT_READY" for leg in LEGS),
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

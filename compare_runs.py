"""Compare two saved runs without changing a brain, checkpoint or simulator."""
import argparse
import json
from pathlib import Path

from robot.evaluation import summarize


def read_run(directory):
    settings = json.loads((directory / "settings.json").read_text())
    rows = [json.loads(line) for line in (directory / "observations.jsonl").read_text().splitlines() if line.strip()]
    report = summarize(rows)
    metrics = {name: report.get(name) for name in (
        "frames", "simulation_seconds", "wall_seconds", "confirmed_walking_seconds",
        "forward_distance_m", "forward_speed_m_s", "recoveries", "recoveries_per_walking_minute",
        "stage_entries", "sequence_transitions", "out_of_order_stage_transitions",
        "simultaneous_stage_frames", "contact_to_next_stage_native_steps",
        "motor_antagonist_overlap_frames", "maximum_absolute_roll_rad", "maximum_absolute_pitch_rad",
        "reward_active_frames", "reflex_entries", "maximum_queued_frames",
    )}
    return dict(directory=str(directory), mode=settings.get("mode"), design_sha256=settings.get("design_sha256"),
                plastic_paths=settings.get("plastic_paths"), initial_handoff_inhibition=settings.get("initial_handoff_inhibition"),
                metrics=metrics), settings


def compare(static_directory, learning_directory):
    static, a = read_run(static_directory)
    learning, b = read_run(learning_directory)
    notes = []
    if a.get("plastic_paths") != []:
        notes.append("First run is not recorded as a graph with zero plastic paths.")
    paths = b.get("plastic_paths")
    if not isinstance(paths, list) or len(paths) != 4 or any(e.get("type") != "inh" or e.get("rule") != "STDP3" or e.get("reward_type") != "LTP" for e in paths):
        notes.append("Second run does not record exactly four inhibitory STDP3/LTP paths.")
    if a.get("config") != b.get("config"):
        notes.append("Run configurations differ; this is not a controlled comparison.")
    if not a.get("initial_handoff_inhibition") or a.get("initial_handoff_inhibition") != b.get("initial_handoff_inhibition"):
        notes.append("Matching initial inhibitory strengths are not established by these logs.")
    if a.get("mode") != "walk" or b.get("mode") != "learn":
        notes.append("Expected static walk followed by learning learn modes.")
    notes.append("Initial-strength metadata describes the submitted design, not live or restored weights. Confirm fresh-build conditions; repeat trials before attributing a difference to learning.")
    return dict(static=static, learning=learning, comparison_notes=notes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("static_run", type=Path)
    parser.add_argument("learning_run", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.static_run, args.learning_run), indent=2))

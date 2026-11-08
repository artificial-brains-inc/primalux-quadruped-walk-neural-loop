"""SDK application launcher, using an existing Webots installation."""

import argparse
import os
import subprocess
import sys
import time

from .cleanup import controller_report, ensure_brain_stopped, save_launcher_report
from .configuration import ROOT, environment_path, load_config
from .contracts import INPUT_SIZES, OUTPUT_SIZES
from .lifecycle import require_installed


def saved_design(root=ROOT):
    from ab import Brain
    from ab_sdk.design_submit import find_design

    find_design(root)
    b = Brain.load(root / "brain.abdesign.json")
    nodes = b.to_dict()["nodes"]
    for kind, contract in (("input", INPUT_SIZES), ("output", OUTPUT_SIZES)):
        if {n["name"]: n["neurons"] for n in nodes if n["kind"] == kind} != contract:
            raise ValueError(f"Saved {kind} contract does not match this Spot adapter")
    return b


def verify_installed():
    from ab_sdk.design_submit import design_sha256
    from ab_sdk.primalux import PrimaLuxClient

    with PrimaLuxClient.from_env(environment_path()) as device:
        require_installed(device.status(), design_sha256(saved_design()))


def launch(mode):
    from launcher_support import (
        check_webots,
        find_webots,
        webots_environment,
        write_controller_runtime,
    )
    from world_assets import check_world_assets

    load_config()
    check_world_assets(ROOT)
    executable = find_webots(ROOT)
    check_webots(executable)
    verify_installed()
    write_controller_runtime(ROOT)
    (ROOT / "logs").mkdir(exist_ok=True)
    (ROOT / ".stop-request").unlink(missing_ok=True)
    state = ROOT / "logs/run_state.json"
    state.unlink(missing_ok=True)
    env = webots_environment(ROOT)
    env["SPOT_RUN_MODE"] = mode
    print(
        "Focus the Webots 3D view: W starts stepping, S inhibits walking, "
        "R restores upright, Q ends the run.",
        flush=True,
    )
    process = None
    try:
        process = subprocess.Popen(
            [
                executable,
                "--stdout",
                "--stderr",
                # The neural stream paces the adapter. Realtime mode would add
                # a wall-clock wait to each simulated body advance.
                "--mode=fast",
                str(ROOT / "worlds/spot_neural_walk.wbt"),
            ],
            cwd=ROOT,
            env=env,
            start_new_session=True,
        )
        while process.poll() is None:
            report = controller_report(state)
            if report.get("state") == "ERROR":
                raise RuntimeError("Controller failed; inspect logs/run_state.json")
            if report.get("state") == "STOPPED":
                break
            time.sleep(0.25)
    except KeyboardInterrupt:
        print("Stop requested; confirming neural-state saving...", flush=True)
    finally:
        (ROOT / ".stop-request").write_text("stop\n")
        try:
            ensure_brain_stopped()
        except BaseException as exc:
            save_launcher_report(
                state="STOP_UNCONFIRMED",
                neural_stop_confirmed=False,
                error_type=type(exc).__name__,
            )
            raise
        save_launcher_report(state="STOPPED", neural_stop_confirmed=True)
        print(
            "Prima-Lux Stop/save confirmed. You can close any remaining Webots window.",
            flush=True,
        )
    if controller_report(state).get("state") == "ERROR":
        raise RuntimeError("The Spot controller failed; Prima-Lux is stopped")
    if process is not None and process.returncode not in (None, 0):
        raise RuntimeError(f"Webots exited with code {process.returncode}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Spot neural walking example")
    parser.add_argument(
        "mode", nargs="?", default="learn", choices=("learn", "walk", "rhythm")
    )
    args = parser.parse_args(argv)
    try:
        os.chdir(ROOT)
        launch(args.mode)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

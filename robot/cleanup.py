"""Independent native Stop/save confirmation."""

import json
import sys
import time

from .configuration import ROOT, environment_path
from .lifecycle import engine_status


def controller_report(path):
    try:
        report = json.loads(path.read_text())
        return report if isinstance(report, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def ensure_brain_stopped(timeout=180.0):
    """Confirm native Stop/save even when Webots killed its controller."""
    from ab_sdk.primalux import PrimaLuxClient

    deadline = time.monotonic() + timeout
    with PrimaLuxClient.from_env(environment_path()) as device:
        try:
            status = device.status()
        except Exception:
            # A failed initial status request must not prevent a Stop attempt.
            status = {}
        engine, state = wait_until_idle(device, status, deadline)
        if state == "STOPPED" and not engine.get("busy"):
            engine_status({"engine": engine})
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError("Automatic Stop/save deadline expired.")
        try:
            result = device.stop_and_wait(timeout=remaining)
        except Exception:
            # The controller may have issued Stop after our initial status
            # read. Confirm that operation instead of sending a blind retry.
            engine, state = wait_until_idle(device, device.status(), deadline)
            if state == "STOPPED" and not engine.get("busy"):
                engine_status({"engine": engine})
                return
            raise
        if result.get("confirmed") is not True or result.get("state") != "STOPPED":
            raise RuntimeError("Prima-Lux did not confirm Stop/save completion.")


def wait_until_idle(device, status, deadline):
    engine = status.get("engine") if isinstance(status, dict) else None
    engine = engine if isinstance(engine, dict) else {}
    state = str(engine.get("state", "")).upper()
    while engine.get("busy"):
        engine_status(status)
        if time.monotonic() >= deadline:
            raise RuntimeError(
                "Prima-Lux remained busy; automatic Stop/save is unconfirmed."
            )
        time.sleep(min(0.25, max(0, deadline - time.monotonic())))
        status = device.status()
        engine, state = engine_status(status)
    return engine, state


def save_launcher_report(**fields):
    path = ROOT / "logs/launcher_state.json"
    try:
        path.parent.mkdir(exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps({"time": time.time(), **fields}) + "\n")
        temp.replace(path)
    except OSError as exc:
        print(f"Could not write launcher status: {exc}", file=sys.stderr, flush=True)

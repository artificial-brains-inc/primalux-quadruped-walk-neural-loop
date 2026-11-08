"""Webots entry point; runtime.ini chooses the project Python."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
if __name__ == "__main__":
    try:
        from robot.controller import main

        main()
    except Exception as exc:
        # Even an import/device-setup failure must notify the external launcher.
        root = Path(__file__).resolve().parents[2]
        path = root / "logs/run_state.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(
            json.dumps(
                dict(state="ERROR", error_type=type(exc).__name__, message=str(exc))
            )
            + "\n"
        )
        raise

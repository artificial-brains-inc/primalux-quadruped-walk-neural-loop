import argparse
import json
from pathlib import Path

from robot.evaluation import summarize

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Summarize observed cascade and body behavior"
    )
    parser.add_argument("run_directory", type=Path)
    args = parser.parse_args()
    rows = [
        json.loads(line)
        for line in (args.run_directory / "observations.jsonl").read_text().splitlines()
    ]
    print(json.dumps(summarize(rows), indent=2))

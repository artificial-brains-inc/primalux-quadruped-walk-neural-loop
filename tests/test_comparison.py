import json
import tempfile
import unittest
from pathlib import Path
from compare_runs import compare
from test_evaluation import row


class ComparisonTests(unittest.TestCase):
    def test_metadata_mismatch_is_visible_and_observations_stay_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a, b = root / "static", root / "learning"
            for path, mode, paths in ((a, "walk", []), (b, "learn", [dict(type="inh", rule="STDP3", reward_type="LTP")] * 4)):
                path.mkdir()
                (path / "settings.json").write_text(json.dumps(dict(mode=mode, plastic_paths=paths, config={}, initial_handoff_inhibition={"FR": .5})))
                rows = [row(1, "start", WALK_ENABLED=1), row(1, "start", WALK_ENABLED=1)]
                rows[-1]["simulation_time"] = 2
                rows[-1]["body_xyz_m"][0] = 1
                (path / "observations.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
            before = (a / "observations.jsonl").read_bytes()
            report = compare(a, b)
            self.assertEqual(len(report["comparison_notes"]), 1)
            self.assertEqual(report["static"]["metrics"]["forward_speed_m_s"], .5)
            self.assertEqual((a / "observations.jsonl").read_bytes(), before)
            settings = json.loads((b / "settings.json").read_text())
            settings["plastic_paths"][0]["type"] = "exc"
            (b / "settings.json").write_text(json.dumps(settings))
            self.assertTrue(any("inhibitory STDP3" in x for x in compare(a, b)["comparison_notes"]))

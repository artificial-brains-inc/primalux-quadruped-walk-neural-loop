import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from robot import application
from world_assets import check_world_assets

ROOT = Path(__file__).resolve().parents[1]


class WorldAssetsTests(unittest.TestCase):
    def test_complete_world_has_only_existing_local_dependencies(self):
        self.assertEqual(check_world_assets(ROOT), 86)
        world = (ROOT / "worlds/spot_neural_walk.wbt").read_text()
        self.assertIn('EXTERNPROTO "../protos/spot/Spot.proto"', world)
        self.assertNotIn("webots://", world)
        self.assertNotIn("TexturedBackground", world)
        self.assertNotIn("RectangleArena", world)

    def test_bundled_assets_match_verified_upstream_manifest(self):
        manifest = json.loads((ROOT / "assets/webots-assets.json").read_text())
        self.assertEqual(manifest["release"], "R2025a")
        for item in manifest["files"]:
            with self.subTest(asset=item["path"]):
                data = (ROOT / item["path"]).read_bytes()
                self.assertEqual(len(data), item["bytes"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"])
                if not item["modified"]:
                    self.assertEqual(item["sha256"], item["upstream_sha256"])
        self.assertEqual(
            {x["path"] for x in manifest["files"] if x["modified"]},
            {"protos/spot/Spot.proto", "protos/spot/SpotLeg.proto"},
        )

    def test_both_plastic_template_options_have_every_texture(self):
        directory = ROOT / "protos/appearances/textures/plastic"
        for kind, maps in (
            ("rough", ("roughness", "normal")),
            ("padded", ("base_color", "metalness", "roughness", "normal", "occlusion")),
        ):
            for name in maps:
                self.assertTrue((directory / f"plastic_{kind}_{name}.jpg").is_file())

    def test_incomplete_package_fails_before_device_or_webots_launch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "assets").mkdir()
            (root / "worlds").mkdir()
            (root / "worlds/spot_neural_walk.wbt").write_text(
                "#VRML_SIM R2025a utf8\nWorldInfo {}\n"
            )
            (root / "assets/webots-assets.json").write_text(
                json.dumps(
                    {
                        "files": [{"path": "protos/spot/Spot.proto"}],
                    }
                )
            )
            with (
                patch.object(application, "ROOT", root),
                patch.object(application, "load_config"),
                patch.object(application, "verify_installed") as device,
                patch.object(application.subprocess, "Popen") as webots,
                patch("launcher_support.find_webots") as find,
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "Missing bundled Webots asset: protos/spot/Spot.proto"
                ):
                    application.launch("rhythm")
                device.assert_not_called()
                webots.assert_not_called()
                find.assert_not_called()


if __name__ == "__main__":
    unittest.main()

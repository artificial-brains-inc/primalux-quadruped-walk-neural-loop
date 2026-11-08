import hashlib
import json
import math
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from robot import application
from world_assets import check_world_assets
from tools.generate_floor_markings import build

ROOT = Path(__file__).resolve().parents[1]


class WorldAssetsTests(unittest.TestCase):
    def test_floor_markings_are_local_noncollision_geometry_with_valid_faces(self):
        source = (ROOT / "protos/FloorMarkings.proto").read_text()
        self.assertEqual(source, build())
        self.assertNotIn("boundingObject", source)
        self.assertNotIn("Physics {", source)
        geometries = source.split("geometry IndexedFaceSet {")[1:]
        self.assertEqual(len(geometries), 4)
        for geometry in geometries:
            points_text = geometry.split("point [", 1)[1].split("]", 1)[0]
            vertices = [
                [float(v) for v in line.split()]
                for line in points_text.strip().split(",")
            ]
            for x, y, z in vertices:
                self.assertTrue(-15.02 <= x <= 15.02 and -15.02 <= y <= 15.02)
                self.assertTrue(0 < z < 0.01)
            faces = geometry.split("coordIndex [", 1)[1].split("]", 1)[0]
            for face in faces.strip().split(","):
                indices = [int(v) for v in face.split()]
                self.assertEqual(indices[-1], -1)
                self.assertTrue(all(0 <= i < len(vertices) for i in indices[:-1]))

    def test_opening_view_aims_at_spot_with_level_horizon(self):
        world = (ROOT / "worlds/spot_neural_walk.wbt").read_text()
        block = world.split("Viewpoint {", 1)[1].split("}", 1)[0]
        axis_angle = [
            float(n) for n in re.search(r"orientation (.*)", block)[1].split()
        ]
        position = [float(n) for n in re.search(r"position (.*)", block)[1].split()]
        x, y, z, angle = axis_angle
        self.assertAlmostEqual(x * x + y * y + z * z, 1)
        c, s = math.cos(angle), math.sin(angle)
        # R2025a Viewpoint looks along local +X; local +Z is screen up.
        forward = [
            c + x * x * (1 - c),
            y * x * (1 - c) + z * s,
            z * x * (1 - c) - y * s,
        ]
        up = [x * z * (1 - c) + y * s, y * z * (1 - c) - x * s, c + z * z * (1 - c)]
        toward = [b - a for a, b in zip(position, [0, 0, 0.45])]
        length = math.sqrt(sum(v * v for v in toward))
        self.assertAlmostEqual(sum(a * b / length for a, b in zip(forward, toward)), 1)
        self.assertGreater(up[2], 0.9)
        self.assertAlmostEqual(forward[0] * up[1] - forward[1] * up[0], 0)

    def test_no_onboard_camera_devices_and_recovery_has_supervisor_access(self):
        source = (ROOT / "protos/spot/Spot.proto").read_text()
        self.assertIsNone(re.search(r"\b(?:Camera|RangeFinder)\s*\{", source))
        world = (ROOT / "worlds/spot_neural_walk.wbt").read_text()
        self.assertIn("supervisor TRUE", world)
        self.assertIn("size 30 30 0.1", world)
        self.assertIn('followType "Tracking Shot"', world)

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

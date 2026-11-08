"""Check the world's packaged assets before starting Webots or Prima-Lux."""

import json
import re
from pathlib import Path

ASSET_REFERENCE = re.compile(r'"([^"\n]+\.(?:proto|obj|stl|dae|jpg|jpeg|png|hdr|mtl))"')


def asset_references(path):
    """Literal URLs in a world/PROTO, excluding documentation and JS templates.

    Plastic's computed URLs are covered by the complete asset manifest.
    """
    source = "\n".join(
        line
        for line in path.read_text().splitlines()
        if not line.lstrip().startswith("#") and "%<" not in line
    )
    return ASSET_REFERENCE.findall(source)


def check_world_assets(root):
    root = Path(root).resolve()
    manifest = root / "assets/webots-assets.json"
    if not manifest.is_file():
        raise RuntimeError(
            "Missing bundled Webots asset manifest; restore the complete demo package."
        )
    records = json.loads(manifest.read_text())["files"]
    files = [root / "worlds/spot_neural_walk.wbt"]
    for record in records:
        path = (root / record["path"]).resolve()
        if not path.is_relative_to(root):
            raise RuntimeError("Asset manifest contains a path outside this project")
        files.append(path)
    for path in files:
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(
                f"Missing bundled Webots asset: {path.relative_to(root)}. Restore the complete demo package."
            )
        if path.suffix not in (".proto", ".wbt"):
            continue
        for reference in asset_references(path):
            target = (path.parent / reference).resolve()
            if (
                "://" in reference
                or Path(reference).is_absolute()
                or not target.is_relative_to(root)
            ):
                raise RuntimeError(
                    f"World asset must use a project-relative path: {reference}"
                )
            if not target.is_file() or target.stat().st_size == 0:
                raise RuntimeError(
                    f"Missing bundled Webots dependency: {target.relative_to(root)}"
                )
    return len(records)

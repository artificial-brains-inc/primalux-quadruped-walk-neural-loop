"""Author the static metre grid; run only when editing the world assets."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rectangle(x0, y0, x1, y1, z):
    return [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]


def shape(color, polygons):
    points, faces = [], []
    for polygon in polygons:
        start = len(points)
        points.extend(polygon)
        faces.append([*range(start, len(points)), -1])
    coords = ",\n".join("          " + " ".join(f"{v:g}" for v in p) for p in points)
    indices = ",\n".join("        " + " ".join(map(str, face)) for face in faces)
    return f"""    Shape {{
      appearance PBRAppearance {{ baseColor {color} roughness 1 metalness 0 }}
      geometry IndexedFaceSet {{
        coord Coordinate {{ point [
{coords}
        ] }}
        coordIndex [
{indices}
        ]
        solid FALSE
      }}
    }}"""


def build():
    minor, major, forward, origin = [], [], [], []
    for n in range(-15, 16):
        target, width, z = (major, 0.025, 0.002) if n % 5 == 0 else (minor, 0.01, 0.001)
        target.extend(
            [
                rectangle(n - width / 2, -15, n + width / 2, 15, z),
                rectangle(-15, n - width / 2, 15, n + width / 2, z),
            ]
        )
    forward.append(rectangle(0, -0.018, 14.8, 0.018, 0.004))
    for x in range(1, 15, 2):
        forward.append(
            [(x + 0.22, 0, 0.004), (x - 0.12, 0.13, 0.004), (x - 0.12, -0.13, 0.004)]
        )

    # Flat seven-segment distance labels face the initial oblique viewpoint.
    segments = {
        "a": (0, 0.23, 0.14, 0.25),
        "b": (0.12, 0.12, 0.14, 0.25),
        "c": (0.12, 0, 0.14, 0.13),
        "d": (0, 0, 0.14, 0.02),
        "e": (0, 0, 0.02, 0.13),
        "f": (0, 0.12, 0.02, 0.25),
        "g": (0, 0.115, 0.14, 0.135),
    }
    digits = (
        "abcdef",
        "bc",
        "abdeg",
        "abcdg",
        "bcfg",
        "acdfg",
        "acdefg",
        "abc",
        "abcdefg",
        "abcdfg",
    )
    for metre in range(15):
        text = str(metre)
        for index, digit in enumerate(text):
            offset = index * 0.20 - (len(text) * 0.20 - 0.06) / 2
            for segment in digits[int(digit)]:
                x0, y0, x1, y1 = segments[segment]
                forward.append(
                    rectangle(
                        metre - offset - x1,
                        -0.45 - y1,
                        metre - offset - x0,
                        -0.45 - y0,
                        0.004,
                    )
                )
    # A blue outlined square marks the fixed start, not the moving camera.
    for x0, y0, x1, y1 in (
        (-0.25, -0.25, 0.25, -0.225),
        (-0.25, 0.225, 0.25, 0.25),
        (-0.25, -0.25, -0.225, 0.25),
        (0.225, -0.25, 0.25, 0.25),
    ):
        origin.append(rectangle(x0, y0, x1, y1, 0.005))
    return (
        """#VRML_SIM R2025a utf8
# Authored floor markings: 1 metre grid, bold every 5 metres.
# Red arrows and labels follow world +X from the blue start square.
# Visual geometry only: no collision objects and no sensor devices.
PROTO FloorMarkings [] {
  Group {
    children [
"""
        + "\n".join(
            (
                shape("0.44 0.47 0.49", minor),
                shape("0.29 0.33 0.36", major),
                shape("0.68 0.13 0.08", forward),
                shape("0.05 0.3 0.75", origin),
            )
        )
        + """
    ]
  }
}
"""
    )


if __name__ == "__main__":
    (ROOT / "protos/FloorMarkings.proto").write_text(build())

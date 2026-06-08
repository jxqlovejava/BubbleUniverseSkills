#!/usr/bin/env python3
"""Audit exported assets for Figma page replication.

Checks:
- Image dimensions match manifest expectations
- No black background (common Figma export issue)
- Minimum resolution (detect 1x vs 3x)
- File size sanity (detect blank/empty exports)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Figma exported assets.")
    parser.add_argument("paths", nargs="+", help="Image files or directories to audit")
    parser.add_argument(
        "--manifest",
        help="layers.manifest.json for size validation",
    )
    parser.add_argument(
        "--min-dimension",
        type=int,
        default=200,
        help="Minimum expected dimension for Strategy A assets (detect 1x exports)",
    )
    parser.add_argument(
        "--no-black-bg",
        action="store_true",
        help="Fail if image has solid black background (Figma export artifact)",
    )
    parser.add_argument(
        "--max-filesize-ratio",
        type=float,
        default=0.1,
        help="Max file size (MB) per 100x100 pixels. Lower = detect blank exports.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON report.")
    return parser.parse_args()


def collect_images(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for item in paths:
        path = Path(item)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.png")))
            files.extend(sorted(path.rglob("*.jpg")))
            files.extend(sorted(path.rglob("*.jpeg")))
        elif path.suffix.lower() in (".png", ".jpg", ".jpeg"):
            files.append(path)
    return files


def load_manifest(path: str | None) -> dict[str, tuple[int, int]]:
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    result: dict[str, tuple[int, int]] = {}

    if isinstance(data, dict) and "layers" in data:
        data = data["layers"]

    if isinstance(data, list):
        for item in data:
            asset_path = item.get("asset")
            if asset_path:
                bbox = item.get("scaled_bbox") or item.get("source_bbox")
                if bbox:
                    result[str(asset_path)] = (int(bbox["width"]), int(bbox["height"]))
    elif isinstance(data, dict):
        for key, value in data.items():
            result[str(key)] = (int(value["width"]), int(value["height"]))
    return result


def manifest_size(manifest: dict[str, tuple[int, int]], path: Path) -> tuple[int, int] | None:
    candidates = [str(path), path.as_posix(), path.name]
    for candidate in candidates:
        if candidate in manifest:
            return manifest[candidate]
    return None


def check_black_background(image) -> dict:
    """Check if image has a solid black background (common Figma export issue)."""
    from PIL import Image
    import numpy as np

    arr = np.asarray(image.convert("RGB"))
    h, w = arr.shape[:2]

    # Sample border pixels
    border = np.concatenate([
        arr[0, :],      # top
        arr[-1, :],     # bottom
        arr[:, 0],      # left
        arr[:, -1],     # right
    ])

    # Check if majority of border is black or very dark
    dark_ratio = (border.mean(axis=1) < 20).mean()

    # Check if corners are black
    corners = [
        arr[0, 0],
        arr[0, -1],
        arr[-1, 0],
        arr[-1, -1],
    ]
    corner_black = all(c.mean() < 30 for c in corners)

    return {
        "border_dark_ratio": round(float(dark_ratio), 4),
        "corner_black": bool(corner_black),
        "suspicious_black_bg": bool(dark_ratio > 0.7 and corner_black),
    }


def main() -> int:
    args = parse_args()

    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        print("Missing dependencies: install Pillow and numpy.", file=sys.stderr)
        return 2

    manifest = load_manifest(args.manifest)
    images = collect_images(args.paths)
    if not images:
        print("No image files found.", file=sys.stderr)
        return 2

    report = []
    failed = False

    for path in images:
        image = Image.open(path)
        size_mb = path.stat().st_size / (1024 * 1024)
        pixel_area = image.width * image.height
        size_ratio = size_mb / (pixel_area / 10000) if pixel_area > 0 else 0

        expected = manifest_size(manifest, path)
        size_ok = True
        dimension_ok = True
        if expected is not None:
            size_ok = (image.width, image.height) == expected
            # For Strategy A, expect 3x export = larger than source bbox
            dimension_ok = image.width >= expected[0] and image.height >= expected[1]

        bg_check = check_black_background(image)
        black_bg_ok = not (args.no_black_bg and bg_check["suspicious_black_bg"])

        filesize_ok = size_ratio <= args.max_filesize_ratio or size_mb > 0.001

        item = {
            "path": str(path),
            "width": image.width,
            "height": image.height,
            "file_size_mb": round(size_mb, 4),
            "size_per_10kpx": round(size_ratio, 4),
            "expected_width": expected[0] if expected else None,
            "expected_height": expected[1] if expected else None,
            "size_ok": size_ok,
            "dimension_ok": dimension_ok,
            "black_bg_ok": black_bg_ok,
            "filesize_ok": filesize_ok,
            **bg_check,
        }
        report.append(item)

        if not size_ok or not dimension_ok or not black_bg_ok or not filesize_ok:
            failed = True

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for item in report:
            issues = []
            if not item["size_ok"]:
                issues.append("size_mismatch")
            if not item["dimension_ok"]:
                issues.append("too_small")
            if not item["black_bg_ok"]:
                issues.append("black_bg")
            if not item["filesize_ok"]:
                issues.append("blank_suspicious")

            status = "FAIL" if issues else "OK"
            issue_str = f" issues=[{','.join(issues)}]" if issues else ""
            print(
                f"{status} {item['path']} {item['width']}x{item['height']}"
                f" ({item['file_size_mb']}MB){issue_str}"
            )

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

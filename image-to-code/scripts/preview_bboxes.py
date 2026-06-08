#!/usr/bin/env python3
"""Draw manifest bounding boxes on the source image for QA.

Supports both image-to-code (bitmap/text/vector) and figma-page-replication
(strategy A/B overlay) workflows via --show-strategy flag.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview bboxes from a manifest on source image.")
    parser.add_argument("source", help="Source screenshot/design image")
    parser.add_argument("manifest", help="layers.manifest.json")
    parser.add_argument("output", help="Output preview PNG")
    parser.add_argument("--only-type", help="Only draw layers of this type, e.g. bitmap")
    parser.add_argument("--only-strategy", help="Only draw layers with this strategy, e.g. A")
    parser.add_argument("--show-strategy", action="store_true", help="Color by strategy (A=red, B=blue) instead of by type")
    return parser.parse_args()


def bbox_from_item(item: dict) -> dict | None:
    if "source_bbox" in item:
        return item["source_bbox"]
    if all(key in item for key in ("x", "y", "width", "height")):
        return item
    return None


def main() -> int:
    args = parse_args()

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Missing dependency: install Pillow.", file=sys.stderr)
        return 2

    source = Image.open(args.source).convert("RGBA")
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))

    # Support both {layers: [...]} and [...] formats
    if isinstance(data, dict) and "layers" in data:
        layers = data["layers"]
    elif isinstance(data, list):
        layers = data
    else:
        print("Manifest must be a JSON list or an object with 'layers'.", file=sys.stderr)
        return 2

    overlay = source.copy()
    draw = ImageDraw.Draw(overlay)
    font = ImageFont.load_default()

    # Color schemes
    type_colors = {
        "bitmap": (255, 0, 0, 255),
        "text": (0, 128, 255, 255),
        "vector": (0, 200, 80, 255),
        "container": (255, 200, 0, 255),
    }
    strategy_colors = {
        "A": (255, 0, 0, 255),   # Export whole image - red
        "B": (0, 128, 255, 255), # Native render - blue
    }

    count = 0
    for index, item in enumerate(layers, start=1):
        layer_type = item.get("type", "unknown")
        strategy = item.get("strategy", "")

        if args.only_type and layer_type != args.only_type:
            continue
        if args.only_strategy and strategy != args.only_strategy:
            continue

        bbox = bbox_from_item(item)
        if not bbox:
            continue

        x = int(round(float(bbox["x"])))
        y = int(round(float(bbox["y"])))
        w = int(round(float(bbox["width"])))
        h = int(round(float(bbox["height"])))
        if w <= 0 or h <= 0:
            continue

        if args.show_strategy and strategy:
            color = strategy_colors.get(strategy, (255, 200, 0, 255))
            label = f"{index}:{item.get('id', strategy)}[{strategy}]"
        else:
            color = type_colors.get(layer_type, (255, 200, 0, 255))
            label = f"{index}:{item.get('id', layer_type)}"

        draw.rectangle((x, y, x + w, y + h), outline=color, width=2)
        text_bbox = draw.textbbox((x, y), label, font=font)
        draw.rectangle(text_bbox, fill=(0, 0, 0, 180))
        draw.text((x, y), label, fill=(255, 255, 255, 255), font=font)
        count += 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    overlay.save(output)
    print(f"wrote {output} boxes={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

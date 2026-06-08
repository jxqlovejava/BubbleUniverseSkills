#!/usr/bin/env python3
"""Draw manifest module bounding boxes on a Figma screenshot for QA.

Visualizes strategy A (export) vs strategy B (native render) modules
to verify the analysis table before resource collection.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview module bboxes from manifest on screenshot.")
    parser.add_argument("screenshot", help="Figma screenshot or reference image")
    parser.add_argument("manifest", help="layers.manifest.json")
    parser.add_argument("output", help="Output preview PNG")
    parser.add_argument("--only-strategy", help="Only draw modules with this strategy, e.g. A")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Missing dependency: install Pillow.", file=sys.stderr)
        return 2

    source = Image.open(args.screenshot).convert("RGBA")
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))

    if isinstance(data, dict) and "layers" in data:
        layers = data["layers"]
    elif isinstance(data, list):
        layers = data
    else:
        print("Manifest must be a JSON list or object with 'layers'.", file=sys.stderr)
        return 2

    overlay = source.copy()
    draw = ImageDraw.Draw(overlay)
    font = ImageFont.load_default()

    strategy_colors = {
        "A": (255, 0, 0, 255),      # Export whole image - red
        "B": (0, 128, 255, 255),    # Native render - blue
    }

    count = 0
    for index, item in enumerate(layers, start=1):
        strategy = item.get("strategy", "")
        if args.only_strategy and strategy != args.only_strategy:
            continue

        bbox = item.get("scaled_bbox") or item.get("source_bbox")
        if not bbox:
            continue

        x = int(round(float(bbox["x"])))
        y = int(round(float(bbox["y"])))
        w = int(round(float(bbox["width"])))
        h = int(round(float(bbox["height"])))
        if w <= 0 or h <= 0:
            continue

        color = strategy_colors.get(strategy, (255, 200, 0, 255))
        draw.rectangle((x, y, x + w, y + h), outline=color, width=3)

        label = f"{index}:{item.get('id', 'unk')}[{strategy}]"
        text_bbox = draw.textbbox((x, y), label, font=font)
        draw.rectangle(text_bbox, fill=(0, 0, 0, 180))
        draw.text((x, y), label, fill=(255, 255, 255, 255), font=font)

        # Draw gap_to_next indicator if present
        gap = item.get("gap_to_next")
        if gap is not None:
            gap_y = y + h
            draw.line([(x, gap_y), (x + w, gap_y)], fill=(0, 255, 255, 255), width=1)
            gap_label = f"gap:{gap}"
            gap_bbox = draw.textbbox((x, gap_y), gap_label, font=font)
            draw.rectangle(gap_bbox, fill=(0, 0, 0, 150))
            draw.text((x, gap_y), gap_label, fill=(0, 255, 255, 255), font=font)

        count += 1

    # Legend
    legend_y = source.height - 40
    for i, (strategy, color) in enumerate(strategy_colors.items()):
        lx = 10 + i * 120
        draw.rectangle((lx, legend_y, lx + 15, legend_y + 15), fill=color)
        draw.text((lx + 20, legend_y), f"Strategy {strategy}", fill=(255, 255, 255, 255), font=font)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    overlay.save(output)
    print(f"wrote {output} modules={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

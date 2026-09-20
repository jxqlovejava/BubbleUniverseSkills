#!/usr/bin/env python3
"""抖音录屏贴纸生成：手撕便利贴 PNG（透明底，旋转已烘焙）。

用法：python3 gen_sticker.py [--copy <key>] [--rotate <度>]
输出：out/sticker-<key>.png（1200×660，600×330 @ DPR2）
文案在 content.json 里维护，--copy 选变体（默认取 content.json 的 default）。
"""
import argparse
import json
import pathlib

from playwright.sync_api import sync_playwright

BASE = pathlib.Path(__file__).parent
DPR = 2
VIEW_W, VIEW_H = 600, 330


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--copy", default=None, help="content.json 里的文案 key")
    ap.add_argument("--rotate", type=float, default=-2.5, help="贴纸旋转角度")
    args = ap.parse_args()

    cfg = json.loads((BASE / "content.json").read_text(encoding="utf-8"))
    key = args.copy or cfg["default"]
    copy = cfg["copies"][key]

    html = (BASE / "sticker.html").read_text(encoding="utf-8")
    html = (
        html.replace("{{LINE1}}", copy["line1"])
        .replace("{{LINE2}}", copy["line2"])
        .replace("{{ROTATE}}", str(args.rotate))
    )

    out = BASE / "out"
    out.mkdir(exist_ok=True)
    (out / "_sticker_preview.html").write_text(html, encoding="utf-8")
    target = out / f"sticker-{key}.png"
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(
            viewport={"width": VIEW_W, "height": VIEW_H}, device_scale_factor=DPR
        )
        page.set_content(html)
        page.wait_for_timeout(400)
        page.screenshot(path=str(target), omit_background=True)
        b.close()
    print(f"[done] {target} ({VIEW_W*DPR}x{VIEW_H*DPR}) 「{copy['line1']} / {copy['line2']}」")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""参考图反向解析：程序化提取风格矩阵（配色/亮度/饱和度/留白/细节密度/宫格结构）。

用于 /jimeng-image --ref 生图前拆解参考图，把风格约束写进 prompt，避免"元素堆砌/AI味/不干净"翻车。

用法:
  python3 analyze_reference.py <图片路径> [--cells 2x2] [--json]

输出:
  默认人类可读风格总结（中文，可直接拼进 prompt）；
  --json 输出完整风格矩阵 JSON。
"""
import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path


# ---- 颜色 → 中文风格名（低饱和优先归类）----
def classify_color(rgb):
    r, g, b = rgb
    mx, mn = max(rgb), min(rgb)
    sat = mx - mn
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    if lum < 45:
        return "近黑"
    if lum < 90:
        if sat < 25:
            return "暗灰"
        if b >= r and b >= g:
            return "墨蓝" if b - r > 12 else "暗蓝灰"
        if r >= b and r >= g:
            return "暖褐"
        return "暗灰"
    if lum < 160:
        if sat < 35:
            if b >= r:
                return "灰蓝"
            return "灰褐"
        if b >= r and b >= g:
            return "雾蓝"
        if r >= g and r >= b:
            return "暖杏"
        return "灰绿"
    # 亮区
    if sat < 30:
        return "奶油白" if lum > 190 else "浅灰"
    if r >= g and g >= b:
        return "米黄" if sat < 80 else "橙粉"
    if b >= r:
        return "淡蓝"
    return "淡紫"


def analyze(path: str, rows: int = 2, cols: int = 2) -> dict:
    from PIL import Image
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = list(im.getdata())
    n = len(px)

    lum = [0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2] for p in px]
    sat = [max(p) - min(p) for p in px]

    def pct(f):
        return round(sum(1 for l in lum if f(l)) / n * 100, 1)

    white_pct = pct(lambda l: l > 200)
    light_pct = pct(lambda l: l > 150)
    dark_pct = pct(lambda l: l < 80)
    mean_lum = round(sum(lum) / n)
    mean_sat = round(sum(sat) / n)

    # 主色（量化 32）
    q = [(p[0] // 32 * 32, p[1] // 32 * 32, p[2] // 32 * 32) for p in px]
    top = [(list(c), round(cnt / n * 100, 1)) for c, cnt in Counter(q).most_common(8)]

    # 宫格结构：每格亮度/细节
    cells = []
    for ry in range(rows):
        for rx in range(cols):
            box = (int(w * rx / cols), int(h * ry / rows),
                   int(w * (rx + 1) / cols), int(h * (ry + 1) / rows))
            cp = list(im.crop(box).getdata())
            m = len(cp)
            c_lum = sum(0.299 * q[0] + 0.587 * q[1] + 0.114 * q[2] for q in cp) / m
            c_std = round(sum(statistics.pstdev(q[k] for q in cp) for k in range(3)) / 3)
            cells.append({"row": ry, "col": rx, "brightness": round(c_lum),
                          "detail_std": c_std})

    avg_detail = round(sum(c["detail_std"] for c in cells) / len(cells))
    detail_level = "极简" if avg_detail < 25 else ("简洁" if avg_detail < 45 else
                     ("中等" if avg_detail < 65 else "丰富"))
    tone = "暗调" if mean_lum < 100 else ("中间调" if mean_lum < 160 else "明亮")
    sat_level = "低饱和(muted)" if mean_sat < 45 else ("中饱和" if mean_sat < 80 else "高饱和")
    neg_space = round(white_pct + light_pct, 1)

    color_names = [classify_color(tuple(c)) for c, _ in top]
    name_cnt = Counter(n for n in color_names if n)
    main_names = [n for n, _ in name_cnt.most_common(5) if n != "近黑"]
    if not main_names:
        main_names = [name_cnt.most_common(1)[0][0]]

    return {
        "size": [w, h],
        "aspect": round(w / h, 3),
        "luminance": {"mean": mean_lum, "white_pct": white_pct,
                      "light_pct": light_pct, "dark_pct": dark_pct,
                      "tone": tone},
        "saturation": {"mean": mean_sat, "level": sat_level},
        "dominant_colors": top,
        "color_names": color_names[:6],
        "main_palette": main_names,
        "negative_space_pct": neg_space,
        "grid": {"rows": rows, "cols": cols},
        "cells": cells,
        "detail_avg": avg_detail,
        "detail_level": detail_level,
    }


def style_summary(d: dict) -> str:
    """把风格矩阵转成可直接拼进 prompt 的中文风格约束段。"""
    tone = d["luminance"]["tone"]
    sat = d["saturation"]["level"]
    pal = "、".join(d["main_palette"][:4]) or "低饱和灰"
    det = d["detail_level"]
    neg = "，留大片负空间/空白" if d["negative_space_pct"] > 12 else ""
    grid = f"{d['grid']['rows']}×{d['grid']['cols']}宫格" if d["grid"]["rows"] > 1 or d["grid"]["cols"] > 1 else "单图"
    lines = [
        f"版式：{grid}，每格单一主体，不堆元素{neg}",
        f"配色：{tone}、{sat}（{pal}），无高饱和鲜艳色",
        f"细节：{det}，画面简洁干净",
        f"比例：参考图 {d['aspect']}（脚本默认输出 3:4）",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--cells", default="2x2", help="宫格划分，如 2x2 / 1x1")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        rows, cols = (int(x) for x in args.cells.lower().split("x"))
    except ValueError:
        rows, cols = 2, 2

    d = analyze(args.image, rows, cols)
    if args.json:
        print(json.dumps(d, ensure_ascii=False, indent=1))
    else:
        print(style_summary(d))
        print(json.dumps(d["dominant_colors"], ensure_ascii=False))


if __name__ == "__main__":
    main()

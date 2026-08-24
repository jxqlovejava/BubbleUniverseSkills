#!/usr/bin/env python3
"""封面校验：宫格数（OCR 选项标签计数）+ 主色（PIL 抽样）。

宫格数判据（jimeng skill）：OCR 选项标签坐标分布 → N 个标签 = N 宫格。
投影法会被弱分隔线误导，不用。OCR 走 ocrmac（Xcode python3 子进程）。
用法：
    python3 cover_verify.py <封面.png> --grid N [--colors #hex1 #hex2 ...]
exit code：宫格数不符（非 warn）→ 2
"""
import argparse
import json
import pathlib
import subprocess
import sys
import tempfile

OCR_PY = "/Applications/Xcode.app/Contents/Developer/usr/bin/python3"
OCR_SNIPPET = r'''
import json, sys
from ocrmac import ocrmac
path = sys.argv[1]
res = ocrmac.OCR(path, language_preference=["zh-Hans", "en-US"]).recognize()
print(json.dumps([{"t": t, "c": round(float(c), 2), "b": [round(float(x), 3) for x in box]} for t, c, box in res], ensure_ascii=False))
'''


def _ocr(png_path, target_long_edge: int = 800) -> list[dict]:
    """整图 OCR；长边 > target_long_edge 先缩到长边 target_long_edge 存临时 PNG 再识别，识别后删除临时文件。

    原因：ocrmac 对全尺寸大图单次识别会漏检小号/手绘选项标签（实测 3 宫格封面
    漏检 贰/叁），缩放到长边 800 后整图识别稳定返回全部标签。target_long_edge
    可调：路线 A 手绘标签用 800 最稳；路线 B 确定性 HTML 壹贰叁 字形在 800 长边
    识别随机抖动（实测偶发漏检 叁），1037（≈0.6 缩放）稳定读全，见 verify_cover_grid 双档。
    """
    tmp_path = None
    try:
        from PIL import Image
        img = Image.open(png_path)
        w, h = img.size
        target = png_path
        if max(w, h) > target_long_edge:
            scale = target_long_edge / max(w, h)
            nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
            tmpf = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp_path = tmpf.name
            tmpf.close()
            img.convert("RGB").resize((nw, nh)).save(tmp_path)
            target = tmp_path
        r = subprocess.run([OCR_PY, "-c", OCR_SNIPPET, str(target)], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise RuntimeError(f"OCR 失败: {r.stderr[-200:]}")
        return json.loads(r.stdout.strip())
    finally:
        if tmp_path is not None:
            try:
                pathlib.Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass


def _filter_labels(blobs: list[dict], top_ignore: float) -> list[dict]:
    """过滤出标签类文本；top_ignore > 0 时跳过图片顶部该比例区域内的标签
    （合成封面顶部有标题区，≤4 字短标题会被 is_label 误计为标签）。
    注：Vision bbox y 原点在左下；ocrmac bbox 为 [x, y_bottom, w, h]，
    中心 y = y_bottom + h/2，顶部区域 = 中心 y > 1 - top_ignore。
    """
    labels = []
    for b in blobs:
        if not is_label(b["t"]) or b["c"] < 0.25:
            continue
        if top_ignore > 0:
            bb = b.get("b")
            if bb and len(bb) == 4:
                # ocrmac bbox = [x, y_bottom, w, h]（Vision 原点左下），中心 y = y_bottom + h/2
                cy = bb[1] + bb[3] / 2
                if cy > 1 - top_ignore:
                    continue
        labels.append(b)
    return labels


def is_label(text: str) -> bool:
    t = (text or "").strip()
    if not (0 < len(t) <= 4):
        return False
    return any(ch.isalnum() or "一" <= ch <= "鿿" for ch in t)


def verify_cover_grid(png_path, expected_grid: int, top_ignore: float = 0.0) -> dict:
    """OCR 计数选项标签。top_ignore > 0 时跳过图片顶部该比例区域内的标签
    （合成封面顶部有标题区，≤4 字短标题会被 is_label 误计为标签）。
    注：Vision bbox y 原点在左下；ocrmac bbox 为 [x, y_bottom, w, h]，
    中心 y = y_bottom + h/2，顶部区域 = 中心 y > 1 - top_ignore。

    双档 OCR：路线 A（AI 手绘标签）在长边 800 识别最稳；路线 B（确定性 HTML
    壹贰叁 字形）在长边 800/1200 有系统性漏检（实测 叁 常丢，1200 也一样），
    1037（≈0.6 缩放）最稳。1037 读两次防单次随机抖动 + 800 兜底路线 A，
    取标签数多的一档作为结果——任一一档读全即计对，路线 A/B 兼容。
    """
    try:
        passes = [_ocr(png_path, t) for t in (1037, 1037, 800)]
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "warn": True, "count": 0, "texts": [], "reason": f"OCR 不可用: {e}"}
    labels = max((_filter_labels(p, top_ignore) for p in passes), key=len)
    texts = [b["t"] for b in labels]
    count = len(labels)
    if count == expected_grid:
        return {"ok": True, "warn": False, "count": count, "texts": texts,
                "reason": f"OCR 检测到 {count} 个选项标签，等于 {expected_grid} 宫格"}
    if count == 0:
        return {"ok": False, "warn": True, "count": 0, "texts": [],
                "reason": "OCR 未检测到选项标签（AI 可能没画/画了无法识别的标签）"}
    return {"ok": False, "warn": False, "count": count, "texts": texts,
            "reason": f"OCR 检测到 {count} 个标签，预期 {expected_grid}"}


def _hex_to_hue(hex_) -> float:
    from PIL import ImageColor
    r, g, b = ImageColor.getrgb(hex_)
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == mn:
        return -1.0
    d = mx - mn
    if mx == r:
        h = ((g - b) / d) % 6
    elif mx == g:
        h = ((b - r) / d) + 2
    else:
        h = ((r - g) / d) + 4
    return round(h * 60)


def cell_dominant_hues(png_path, grid: int) -> list[float]:
    """每格（纵向 N 等分条带）中心区平均色 → 色相角。"""
    from PIL import Image
    img = Image.open(png_path).convert("RGB")
    w, h = img.size
    hues = []
    for i in range(grid):
        top = int(h * i / grid) + int(h / grid * 0.3)
        bot = int(h * (i + 1) / grid) - int(h / grid * 0.3)
        if bot <= top:
            continue
        px = img.crop((0, top, w, bot)).resize((1, 1)).getpixel((0, 0))
        r, g, b = px
        mx, mn = max(r, g, b), min(r, g, b)
        if mx == mn:
            hues.append(-1.0)
            continue
        d = mx - mn
        if mx == r:
            hue = ((g - b) / d) % 6
        elif mx == g:
            hue = ((b - r) / d) + 2
        else:
            hue = ((r - g) / d) + 4
        hues.append(round(hue * 60))
    return hues


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("png")
    ap.add_argument("--grid", type=int, required=True)
    ap.add_argument("--colors", nargs="*", default=[], help="每格目标 hex，按顺序")
    args = ap.parse_args()
    v = verify_cover_grid(args.png, args.grid)
    print(json.dumps(v, ensure_ascii=False))
    if args.colors:
        hues = cell_dominant_hues(args.png, args.grid)
        for i, (h, hex_) in enumerate(zip(hues, args.colors)):
            th = _hex_to_hue(hex_)
            print(f"  第{i + 1}格 主色相 {h}° vs 目标 {th}°（差 {abs(h - th)}°）")
    if not v["ok"] and not v["warn"]:
        sys.exit(2)


if __name__ == "__main__":
    main()

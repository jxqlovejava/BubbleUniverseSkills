#!/usr/bin/env python3
"""贴纸池预处理：即梦产物抠白底→透明→内容bbox裁边，落位 assets/stickers/<角色>/{cry,happy}.png。

用法：python3 prep_stickers.py [贴纸临时根目录]
默认从 /tmp/sticker_pool/<角色>_<表情>/*.png 读，写到 skill assets/stickers/。
与 prep_assets.py 的 key_white 同源：与边缘连通的近白像素置透明，保内容。
"""
import collections
import pathlib
import sys

from PIL import Image

BASE = pathlib.Path(__file__).parent.parent  # skill 根
RAW_ROOT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("/tmp/sticker_pool")
OUT = BASE / "assets" / "stickers"
CHARACTERS = ["orange_cat", "corgi", "gray_rabbit", "hamster", "bear"]
EMO = ["cry", "happy"]


def key_white(src: pathlib.Path, dst: pathlib.Path, thr: int = 232) -> None:
    """把与边缘连通的近白像素抠成透明，再按内容 bbox 裁边。"""
    im = Image.open(src).convert("RGBA")
    w, h = im.size
    px = im.load()

    def is_white(p: tuple) -> bool:
        return p[0] > thr and p[1] > thr and p[2] > thr - 10

    bg = bytearray(w * h)
    q = collections.deque()
    for x in range(w):
        for y in (0, h - 1):
            if is_white(px[x, y]):
                bg[y * w + x] = 1
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if is_white(px[x, y]) and not bg[y * w + x]:
                bg[y * w + x] = 1
                q.append((x, y))
    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not bg[ny * w + nx] and is_white(px[nx, ny]):
                bg[ny * w + nx] = 1
                q.append((nx, ny))
    for y in range(h):
        for x in range(w):
            if bg[y * w + x]:
                r, g, b, _ = px[x, y]
                px[x, y] = (r, g, b, 0)
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    # 控制尺寸，避免资产臃肿
    if max(im.size) > 800:
        im.thumbnail((800, 800), Image.LANCZOS)
    im.save(dst)
    print(f"[prep] {dst.name} {im.size} transparent")


def main() -> None:
    for sp in CHARACTERS:
        for emo in EMO:
            raw = RAW_ROOT / f"{sp}_{emo}"
            imgs = sorted(raw.glob("*.png")) if raw.is_dir() else []
            if not imgs:
                print(f"[warn] 缺 {sp}_{emo}，跳过")
                continue
            d = OUT / sp
            d.mkdir(parents=True, exist_ok=True)
            key_white(imgs[0], d / f"{emo}.png")


if __name__ == "__main__":
    main()

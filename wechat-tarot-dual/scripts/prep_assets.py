#!/usr/bin/env python3
"""素材预处理：头像居中裁方，贴纸抠白底（边缘连通 BFS，保内容），背景图原样拷贝。

跑一次即可：python3 prep_assets.py
即梦原图在 assets/raw/，处理后落在 assets/：avatar_me.png / avatar_ta.png /
sticker_cry.png / sticker_happy.png / chat_bg.png
"""
import collections
import pathlib
import shutil

from PIL import Image

BASE = pathlib.Path(__file__).parent.parent  # skill 根（assets/ 在其下）
RAW = BASE / "assets" / "raw"

# 选定的即梦原图（_1/_2 里挑好的一张）
PICKS = {
    "avatar_me": "20260909_114216_软萌奶油白色小猫的大头头像_正面居中构图_圆脸大眼睛_粉色腮_1.png",
    "avatar_ta": "20260909_114308_软萌浅棕色小狗的大头头像_正面居中构图_圆眼黑鼻子_粉色腮红_1.png",
    "sticker_cry": "20260909_114238_微信表情包贴纸_一只奶油色小猫坐在地上嚎啕大哭_眼泪像两条喷_1.png",
    "sticker_happy": "20260909_114327_微信表情包贴纸_一只浅棕色小狗开心地眯眼大笑_右爪举起来挥手_1.png",
    "chat_bg": "20260909_120504_深夜俯视视角的空旷城市石阶照片_石阶从画面上方向画面下方延伸_2.png",  # 路灯在台阶左侧路边（上一版路灯在台阶中间，违反常识，弃用 _114416）
}


def crop_square(src: pathlib.Path, dst: pathlib.Path) -> None:
    im = Image.open(src).convert("RGB")
    w, h = im.size
    s = min(w, h)
    im = im.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2))
    im.save(dst)
    print(f"[prep] {dst.name} {im.size}")


def key_white(src: pathlib.Path, dst: pathlib.Path, thr: int = 230) -> None:
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
    im.save(dst)
    print(f"[prep] {dst.name} {im.size} transparent")


def main() -> None:
    crop_square(RAW / PICKS["avatar_me"], BASE / "assets" / "avatar_me.png")
    crop_square(RAW / PICKS["avatar_ta"], BASE / "assets" / "avatar_ta.png")
    key_white(RAW / PICKS["sticker_cry"], BASE / "assets" / "sticker_cry.png")
    key_white(RAW / PICKS["sticker_happy"], BASE / "assets" / "sticker_happy.png")
    shutil.copy(RAW / PICKS["chat_bg"], BASE / "assets" / "chat_bg.png")
    print(f"[prep] chat_bg.png copied")


if __name__ == "__main__":
    main()

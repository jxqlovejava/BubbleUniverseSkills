#!/usr/bin/env python3
"""自然感实拍照片 + 塔罗气泡解读卡片 · 抖音图文渲染。

复刻参考帖结构：满版自然感实拍照片（逆光发丝、写实肤质），左侧叠一张
半透明白底「塔罗气泡App 解读卡」浮层（品牌铭牌 + 占卜问题 + 三牌 + 解读开头）。

与 render_reading_shot.py 的区别：那是整屏 App 解读截图（1170×2532），
这是「照片 + 悬浮解读卡」——照片垫底，卡片只占约 42% 宽、自顶向下
解析度内容溢出处自然截断（真实截图感）。

UI 底座沿用 render_reading_shot.py 的 CSS tokens（品牌紫 #5B4DBC、苹方、牌圆角5、
解读卡圆角16 / 15px·1.7 与 App MarkdownInterpretationView 对齐）。

用法：python3 render_photo_share.py [content.json]
输出：out/自然照片产品截图.png（1728×2304，432×576 @ DPR4）+ out/发布文案.txt
"""
import html
import json
import pathlib
import re
import sys
from urllib.parse import quote

from playwright.sync_api import sync_playwright

# ── 手绘马克笔红色下划线（重复贴片，自包含 SVG 无外部资源）────────────
# 同 render_reading_shot.py：连续粗直线 + 叠一条淡副笔，马克笔没描直的天然感。
_MARKER_STROKE = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='64' height='14' viewBox='0 0 64 14'>"
    "<path d='M1 8.4 C14 7.8 30 8.9 46 8.2 C54 7.9 60 8.6 63 8.3' fill='none' stroke='#FF3B30' "
    "stroke-width='5' stroke-linecap='round' stroke-linejoin='round' opacity='.9'/>"
    "<path d='M2 9.4 C18 8.9 34 9.9 50 9.2 C56 8.9 60 9.5 62 9.3' fill='none' stroke='#FF3B30' "
    "stroke-width='2.2' stroke-linecap='round' opacity='.35'/>"
    "</svg>"
)
MARKER_UL_URI = "data:image/svg+xml," + quote(_MARKER_STROKE, safe="")

BASE = pathlib.Path(__file__).parent
PW, PH = 432, 576  # 逻辑尺寸（= 即梦文生图 3:4 @ 2K 的 1/4）
DPR = 4            # @4x = 1728×2304，与即梦 2K 同尺寸
FONT = "'PingFang SC','Hiragino Sans GB',sans-serif"
CONTENT_DIR = BASE

# ── 卡片以「App 真实尺寸界面」整体等比缩放 ─────────────────────────
# 参考帖的卡 = 一整块产品界面截图的等比缩小：内部元素（牌/文字/间距）保持 App 真实比例，
# 只整体缩放。我们内层 UI 用 App 原始尺寸（同 render_reading_shot.py），外层 scale() 缩小。
APP_W = 390            # App 解读屏逻辑宽（同 tarot 解读截图模板）
CARD_LEFT = 10         # 卡左边缘逻辑 px（整卡向左靠边）
CARD_TOP = 8           # 卡上边缘逻辑 px
CARD_W = 228           # 卡显示宽逻辑 px → SCALE = CARD_W / APP_W
SCALE = CARD_W / APP_W  # ≈0.585，整体等比缩小；内层牌74×130 / 文字15px 等全部按比例协同缩小
APP_SCREEN_H = 660     # App 界面内层高度（牌/Luna 上移后，解读可在卡底展示更长一截；底部自然截断）
CARD_H = int(APP_SCREEN_H * SCALE)  # 卡显示高 = 内层高 × scale（等比同步）
POSITIONS = {"left": "left", "right": "right"}

# ── SVG 图标（内联，避免外部资源）──────────────────────────────
def status_icons() -> str:
    return '''<svg width="76" height="14" viewBox="0 0 76 14" fill="#000">
<rect x="0" y="9" width="3" height="5" rx="1"/><rect x="5" y="7" width="3" height="7" rx="1"/>
<rect x="10" y="4.5" width="3" height="9.5" rx="1"/><rect x="15" y="2" width="3" height="12" rx="1"/>
<path d="M28 6.2a9 9 0 0 1 12 0l-1.7 1.8a7 7 0 0 0-8.6 0z"/>
<path d="M30.4 9a5.5 5.5 0 0 1 7.2 0l-1.7 1.8a3.6 3.6 0 0 0-3.8 0z"/><circle cx="34" cy="12" r="1.4"/>
<rect x="50" y="2.5" width="20" height="9" rx="2.8" fill="none" stroke="#000" stroke-opacity=".45" stroke-width="1"/>
<rect x="52" y="4.5" width="12.5" height="5" rx="1.2"/>
<path d="M71.5 5.2v3.6a2 2 0 0 0 0-3.6z" fill-opacity=".5"/></svg>'''

TB_BACK = '<svg width="10" height="18" viewBox="0 0 10 18" fill="none"><path d="M8.6 1.4 1.4 9l7.2 7.6" stroke="#1A143D" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>'
MORE = '<svg width="18" height="8" viewBox="0 0 18 8"><g fill="#1A1A1A"><circle cx="2.6" cy="4" r="1.4"/><circle cx="9" cy="4" r="1.4"/><circle cx="15.4" cy="4" r="1.4"/></g></svg>'


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def uri(rel: str) -> str:
    """素材解析：content.json 所在目录优先（实例可放自有 assets 覆盖默认），模板目录兜底。"""
    for base in (CONTENT_DIR, BASE):
        p = base / rel
        if p.exists():
            return p.as_uri()
    print(f"[warn] 缺图: {rel}")
    return ""


def fmt_para(text: str, phrases: list[str]) -> str:
    """段落渲染（与 App MarkdownInterpretationView 对齐）：转义 → **粗体** → 划线 → 换行。"""
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    spans: list[tuple[int, int]] = []
    for ph in phrases:
        start = 0
        while True:
            i = text.find(ph, start)
            if i == -1:
                break
            spans.append((i, i + len(ph)))
            start = i + len(ph)
    spans.sort()
    out, cur, end_at = [], 0, 0
    for s, e in spans:
        if s < end_at:  # 与已命中区间重叠，跳过
            continue
        out.append(text[cur:s])
        out.append(f'<span class="ul">{text[s:e]}</span>')
        cur, end_at = e, e
    out.append(text[cur:])
    return "".join(out).replace("\n", "<br>")


def read_card(cfg: dict) -> str:
    """塔罗气泡解读界面截图（App 原始尺寸），整块交给外层 scale() 等比缩小。

    内部元素全部用 App 真实比例（同 render_reading_shot.py）：牌 74×130、问题 20px、
    解读卡 15px/1.7 圆角16、Luna 头像 35px、品牌铭牌胶囊。只取解读开头几块，
    外层容器高度固定，超出部分底部自然截断（参考帖"截图没截完"）。
    """
    cards = "\n".join(
        f'''<div class="card2">
          <img class="cardimg{'' if not c.get('reversed') else ' rev'}" src="{uri(c['img'])}">
          <div class="cname">{esc(c['name'])}</div>
          <div class="cpos">{esc(c['position'])}</div>
        </div>'''
        for c in cfg["cards"]
    )
    underlines = cfg.get("underlines", [])
    full_text = "".join(cfg["interpretation"])
    for ph in underlines:  # 全局校验：整篇找不到才警告（防手滑写错字划线落空）
        if ph not in full_text:
            print(f"[warn] 划线词未命中: {ph}")
    paras = "\n".join(
        f'<div class="para">{fmt_para(p, underlines)}</div>' for p in cfg["interpretation"]
    )
    return f'''<div class="screen">
  <div class="status"><span>{esc(cfg.get('time') or '10:24')}</span>{status_icons()}</div>
  <div class="appbar">{TB_BACK}
    <div class="brand"><img src="{uri('assets/app_icon.png')}">
    <span>{esc(cfg.get('card_title') or '塔罗气泡')}</span></div>
    <div class="more">{MORE}</div>
  </div>
  <div class="topcard">
    <div class="q">{esc(cfg['question'])}</div>
    <div class="cards">{cards}</div>
  </div>
  <div class="luna">
    <div class="luna-head"><img src="{uri('assets/luna_avatar.png')}"><span>Luna</span></div>
    {paras}
    <div class="ai">{esc(cfg.get('ai_label') or '由云端AI提供')}</div>
  </div>
</div>'''


CSS = f"""
* {{ margin:0; padding:0; box-sizing:border-box; font-family:{FONT}; }}
body {{ width:{PW}px; height:{PH}px; overflow:hidden; }}
.frame {{ width:{PW}px; height:{PH}px; position:relative; overflow:hidden; }}
/* 满版自然感实拍照片垫底 */
.photo {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }}

/* ── 解读卡：一整块产品界面，整体 scale() 等比缩小 ── */
/* 外层 .card 只负责定位 + 等比缩放；内层 .screen 是 App 原始尺寸界面 */
.card {{ position:absolute; top:{CARD_TOP}px; width:{CARD_W}px; height:{CARD_H}px;
  overflow:hidden; z-index:2; border-radius:{18 * SCALE:.1f}px;
  box-shadow:0 {12 * SCALE:.1f}px {40 * SCALE:.1f}px rgba(0,0,0,.25); }}
.card.left  {{ left:{CARD_LEFT}px; }}
.card.right {{ right:{CARD_LEFT}px; }}
.card.center{{ left:50%; margin-left:{-CARD_W / 2:.0f}px; }}
/* 内层 = App 原始尺寸界面（390 宽），transform-origin 左上角，缩放后仍从左上贴住 .card */
.screen {{ width:{APP_W}px; height:{APP_SCREEN_H}px; background:linear-gradient(150deg,#FAF3FF 0%,#FDFAFF 35%,#FFFFFF 70%);
  transform:scale({SCALE:.4f}); transform-origin:top left; }}

/* 状态栏（App 原始尺寸 44px，只含时间+信号） */
.status {{ height:44px; display:flex; align-items:center; justify-content:space-between;
  padding:0 24px 0 28px; color:#000; font-size:15px; font-weight:600; }}

/* 导航行（返回键 + 居中品牌铭牌 + 三点），品牌铭牌与返回键/三点同一行对齐 */
.appbar {{ height:38px; position:relative; display:flex; align-items:center;
  justify-content:space-between; padding:0 16px; }}
.appbar .more {{ display:flex; }}
.brand {{ position:absolute; left:50%; top:50%; transform:translate(-50%,-50%);
  display:flex; align-items:center; gap:5px; background:#FFF; border-radius:10px;
  padding:4px 10px; box-shadow:0 1px 4px rgba(0,0,0,.08); }}
.brand img {{ width:18px; height:18px; border-radius:4px; display:block; }}
.brand span {{ font-size:15px; font-weight:600; color:#1A143D; letter-spacing:.5px; }}
.chip {{ border:.5px solid #5B4DBC; border-radius:10px; padding:4px 18px; color:#5B4DBC; font-size:13px; }}

.topcard {{ background:rgba(255,255,255,.55); border-radius:0 0 20px 20px;
  padding:2px 16px 14px; }}
.q {{ font-size:16px; font-weight:500; color:#000; text-align:center; margin:2px 24px 14px; line-height:1.4; }}
.cards {{ display:flex; justify-content:space-evenly; }}
.card2 {{ width:60px; text-align:center; }}
.cardimg {{ width:60px; height:106px; border-radius:5px; object-fit:cover; display:block;
  box-shadow:0 2px 4px rgba(0,0,0,.1); margin:0 auto; }}
.cardimg.rev {{ transform:rotate(180deg); }}
.cname {{ font-size:12px; color:#000; margin-top:6px; }}
.cpos {{ font-size:10px; color:rgba(0,0,0,.55); margin-top:1px; }}

.luna {{ padding:2px 19px; }}
.luna-head {{ display:flex; align-items:center; gap:11px; margin-bottom:5px; }}
.luna-head img {{ width:30px; height:30px; border-radius:50%; object-fit:cover; background:#FFF; }}
.luna-head span {{ font-size:16px; font-weight:500; color:#000; }}
.para {{ background:rgba(255,255,255,.7); border:.5px solid rgba(91,77,188,.15); border-radius:16px;
  padding:13px 15px; font-size:15px; line-height:1.7; color:#111; margin-bottom:10px; }}
.para b {{ font-weight:600; }}
.ul {{ padding:0 4px 7px; margin:0 -4px;  /* 左留 4px 线头微微超出，下垫 7px 让线落到文字下方 */
  background:url("{MARKER_UL_URI}") repeat-x 0 100% / auto 14px; }}
.ai {{ display:inline-block; background:rgba(255,255,255,.5); border:.5px solid rgba(91,77,188,.3);
  border-radius:12px; padding:3px 9px; font-size:11px; color:rgba(0,0,0,.45); }}
"""


def build_html(data: dict) -> str:
    pos = data.get("card_position", "left")
    if pos not in POSITIONS:
        print(f"[warn] card_position={pos} 非法，回退 left")
        pos = "left"
    return f'''<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<style>{CSS}</style></head>
<body><div class="frame">
  <img class="photo" src="{uri(data['photo'])}">
  <div class="card {pos}">{read_card(data)}</div>
</div></body></html>'''


def main() -> None:
    global CONTENT_DIR
    cfg_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "content.json"
    cfg_path = cfg_path.resolve()
    CONTENT_DIR = cfg_path.parent
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    out = BASE / "out"
    out.mkdir(exist_ok=True)
    html_path = out / "_preview.html"
    html_path.write_text(build_html(data), encoding="utf-8")
    # caption_full = gen_photo.py 组装好的完整发布文案（软植入句 + 正文 + 标签）；没有则退回
    # 只写 caption（旧 content.json 兼容）。别在这里重拼——会丢标签和软植入句。
    caption_full = data.get("caption_full") or data.get("caption")
    if caption_full:
        (out / "发布文案.txt").write_text(caption_full, encoding="utf-8")
    target = out / "自然照片产品截图.png"
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": PW, "height": PH}, device_scale_factor=DPR)
        page.goto(html_path.as_uri())
        page.wait_for_timeout(600)
        page.screenshot(path=str(target))
        b.close()
    print(f"[done] {target} ({PW*DPR}×{PH*DPR})")


if __name__ == "__main__":
    main()

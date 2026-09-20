#!/usr/bin/env python3
"""塔罗气泡解读截图 + 关键词划线 + 贴纸 · 单屏抖音图文渲染。

复刻抖音爆款结构（参考 quin 单屏帖）：一整屏塔罗气泡App解读界面，
解读正文里的关键词句划红色手绘线，牌卡区压一张紫色情绪贴纸。

UI 底座 = 塔罗气泡真实解读屏（样式取自 TarotBubble Flutter 源码
tarot_chat_history_screen.dart，同 wechat-tarot-dual 的 .tb 面板；用户拍板不要底部追问框）。

用法：python3 render_reading_shot.py [content.json]
输出：out/塔罗解读截图.png（1170×2532，390×844 @ DPR3）+ out/发布文案.txt
"""
import html
import json
import pathlib
import re
import sys
from urllib.parse import quote

from playwright.sync_api import sync_playwright

BASE = pathlib.Path(__file__).parent
PW, PH = 390, 844  # 单屏逻辑尺寸（iPhone 14）
DPR = 3  # @3x = 真机截图分辨率（1170×2532）
FONT = "'PingFang SC','Hiragino Sans GB',sans-serif"


def load_opener():
    """tarot-mass-divination/scripts/opener.py（ip-pipeline / vira 两种布局都认）。缺失返回 None。"""
    for c in (BASE.parent / ".claude" / "skills" / "tarot-mass-divination" / "scripts",
              BASE.parent / "tarot-mass-divination" / "scripts"):
        if (c / "opener.py").exists():
            sys.path.insert(0, str(c))
            import opener
            return opener
    print("[warn] 找不到 opener.py，发布文案不加软植入句")
    return None


def compose_caption(data: dict) -> str:
    """正文开头加软植入句（标题行后单独一行）。content.json 缺 opener 则原样输出。"""
    caption = str(data.get("caption") or "")
    op = load_opener()
    if not caption or not op or not data.get("opener"):
        return caption
    return op.insert_opener(caption, str(data["opener"]))

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


def esc(s: str) -> str:
    return html.escape(s, quote=True)


# ── 手绘马克笔红色下划线（重复贴片，自包含 SVG 无外部资源）────────────
# 参考 quin 单屏帖：连续的粗直线，但带一点手绘不规矩——轻微上下抖动、端头圆钝、
# 叠一条淡副笔做出「马克笔没描直」的天然感（不是波浪线）。
# 主笔宽 5、副笔宽 2.2 叠笔；竖直幅度仅 ±0.5px，接近直线而非波浪。
_MARKER_STROKE = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='64' height='14' viewBox='0 0 64 14'>"
    "<path d='M1 8.4 C14 7.8 30 8.9 46 8.2 C54 7.9 60 8.6 63 8.3' fill='none' stroke='#FF3B30' "
    "stroke-width='5' stroke-linecap='round' stroke-linejoin='round' opacity='.9'/>"
    "<path d='M2 9.4 C18 8.9 34 9.9 50 9.2 C56 8.9 60 9.5 62 9.3' fill='none' stroke='#FF3B30' "
    "stroke-width='2.2' stroke-linecap='round' opacity='.35'/>"
    "</svg>"
)
MARKER_UL_URI = "data:image/svg+xml," + quote(_MARKER_STROKE, safe="")


def uri(rel: str) -> str:
    p = BASE / rel
    if not p.exists():
        print(f"[warn] 缺图: {rel}")
        return ""
    return p.as_uri()


def fmt_para(text: str, phrases: list[str]) -> str:
    """段落渲染（与 App 的 MarkdownInterpretationView 对齐）：转义 → **粗体** → 划线 → 换行。"""
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


def tb_card(c: dict) -> str:
    rev = " rev" if c.get("reversed") else ""
    return f'''<div class="card">
      <img class="cardimg{rev}" src="{uri(c["img"])}">
      <div class="cname">{esc(c["name"])}</div>
      <div class="cpos">{esc(c["position"])}</div>
    </div>'''


def sticker_html(st: dict) -> str:
    lines = "<br>".join(esc(x) for x in st["text"].split("\n"))
    style = []
    if "top" in st:
        style.append(f"top:{st['top']}px")
    if "right" in st:
        style.append(f"right:{st['right']}px")
    if "rotate" in st:
        style.append(f"transform:rotate({st['rotate']}deg)")
    extra = f' style="{";".join(style)}"' if style else ""
    return f'<div class="sticker"{extra}>{lines}</div>'


def panel(cfg: dict) -> str:
    cards = "\n".join(tb_card(c) for c in cfg["cards"])
    underlines = cfg.get("underlines", [])
    full_text = "".join(cfg["interpretation"])
    for ph in underlines:  # 全局校验：整篇都找不到才警告（防手滑写错字划线落空）
        if ph not in full_text:
            print(f"[warn] 划线词未命中: {ph}")
    paras = "\n".join(
        f'<div class="para">{fmt_para(p, underlines)}</div>' for p in cfg["interpretation"]
    )
    return f'''
<div class="phone">
  <div class="status"><span>{esc(cfg["time"])}</span>{status_icons()}
    <div class="brand"><img src="{uri("assets/app_icon.png")}"><span>塔罗气泡</span></div>
  </div>
  <div class="appbar">{TB_BACK}<div class="chip">{esc(cfg.get("remaining_text") or "无限畅享占卜")}</div><div class="more"></div></div>
  <div class="content">
    <div class="topcard">
      <div class="q">{esc(cfg["question"])}</div>
      <div class="cards">{cards}</div>
      {sticker_html(cfg["sticker"]) if cfg.get("sticker") else ""}
    </div>
    <div class="luna">
      <div class="luna-head"><img src="{uri("assets/luna_avatar.png")}"><span>Luna</span></div>
      {paras}
      <div class="ai">{esc(cfg["ai_label"])}</div>
    </div>
  </div>
</div>'''


CSS = f"""
* {{ margin:0; padding:0; box-sizing:border-box; font-family:{FONT}; }}
body {{ width:{PW}px; height:{PH}px; }}
.phone {{ width:{PW}px; height:{PH}px; position:relative; overflow:hidden;
  background:linear-gradient(150deg,#FAF3FF 0%,#FDFAFF 35%,#FFFFFF 70%); }}

.status {{ position:absolute; top:0; left:0; right:0; height:44px; display:flex; align-items:center;
  justify-content:space-between; padding:0 24px 0 28px; color:#000; font-size:15px; font-weight:600; z-index:3; }}
/* 顶部居中品牌铭牌（参考 quin 状态栏胶囊：白底圆角矩形 + logo + 名称） */
.brand {{ position:absolute; left:50%; top:50%; transform:translate(-50%,-50%);
  display:flex; align-items:center; gap:5px; background:#FFF; border-radius:10px;
  padding:4px 10px; box-shadow:0 1px 4px rgba(0,0,0,.08); }}
.brand img {{ width:18px; height:18px; border-radius:4px; display:block; }}
.brand span {{ font-size:15px; font-weight:600; color:#1A143D; letter-spacing:.5px; }}
.appbar {{ position:absolute; top:44px; left:0; right:0; height:48px; display:flex; align-items:center;
  justify-content:space-between; padding:0 16px; z-index:3; }}
.appbar .more {{ width:10px; }}
.chip {{ border:.5px solid #5B4DBC; border-radius:10px; padding:4px 18px; color:#5B4DBC; font-size:13px; }}

.content {{ position:absolute; top:92px; left:0; right:0; bottom:0; }}
.topcard {{ position:relative; background:rgba(255,255,255,.55); border-radius:0 0 20px 20px;
  padding:14px 16px 18px; }}
.q {{ font-size:20px; font-weight:500; color:#000; text-align:center; margin:4px 24px 16px; line-height:1.4; }}
.cards {{ display:flex; justify-content:space-evenly; }}
.card {{ width:74px; text-align:center; }}
.cardimg {{ width:74px; height:130px; border-radius:5px; object-fit:cover; display:block;
  box-shadow:0 2px 4px rgba(0,0,0,.1); }}
.cardimg.rev {{ transform:rotate(180deg); }}
.cname {{ font-size:13px; color:#000; margin-top:8px; }}
.cpos {{ font-size:11px; color:rgba(0,0,0,.55); margin-top:2px; }}

/* 紫色情绪贴纸（压牌卡区右上，参考 quin 帖） */
.sticker {{ position:absolute; top:28%; right:10px; transform:rotate(-3deg); z-index:4;
  background:rgba(91,77,188,.82); color:#FFF; font-size:19px; font-weight:600; line-height:1.55;
  padding:14px 18px; border-radius:14px; box-shadow:0 6px 16px rgba(91,77,188,.3); }}

.luna {{ padding:14px 19px; }}
.luna-head {{ display:flex; align-items:center; gap:11px; margin-bottom:9px; }}
.luna-head img {{ width:35px; height:35px; border-radius:50%; object-fit:cover; background:#FFF; }}
.luna-head span {{ font-size:17px; font-weight:500; color:#000; }}
.para {{ background:rgba(255,255,255,.7); border:.5px solid rgba(91,77,188,.15); border-radius:16px;
  padding:13px 15px; font-size:15px; line-height:1.7; color:#111; margin-bottom:10px; }}
.para b {{ font-weight:600; }}
.ul {{ padding:0 4px 7px; margin:0 -4px;  /* 左右留 4px 线头微微超出，下垫 7px 让线落到文字下方 */
  background:url("{MARKER_UL_URI}") repeat-x 0 100% / auto 14px; }}
.ai {{ display:inline-block; background:rgba(255,255,255,.5); border:.5px solid rgba(91,77,188,.3);
  border-radius:12px; padding:3px 9px; font-size:11px; color:rgba(0,0,0,.45); }}
"""


def build_html(data: dict) -> str:
    return f'''<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<style>{CSS}</style></head>
<body>{panel(data)}</body></html>'''


def main() -> None:
    cfg_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "content.json"
    data = json.loads(pathlib.Path(cfg_path).read_text(encoding="utf-8"))
    out = BASE / "out"
    out.mkdir(exist_ok=True)
    html_path = out / "_preview.html"
    html_path.write_text(build_html(data), encoding="utf-8")
    caption_full = compose_caption(data)
    if caption_full:
        (out / "发布文案.txt").write_text(caption_full, encoding="utf-8")
        print("===== 发布文案 =====\n" + caption_full)
    target = out / "塔罗解读截图.png"
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

#!/usr/bin/env python3
"""大众占卜长图文渲染脚本。

复刻 TarotBubble App 分享长图文（LongTextShareTab）视觉：
1 个问题 + 4 个选项 → 封面(3:4) + 4 张解读超高长图。
设计逻辑宽度 390px（与 Flutter 逻辑 px 一致），Playwright device_scale_factor=4.0
→ 输出宽 1560px（与 Flutter pixelRatio=4.0 截图一致）。

用法：
    python3 render_mass_divination.py <数据目录>
数据目录需含 content.json（问题/选项/解读 markdown）与 logo/牌图。
输出到 <数据目录>/out/。
"""
import html
import io
import json
import pathlib
import re
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

W_LOGICAL = 390          # 设计逻辑宽度，与 Flutter MediaQuery 一致
DPR = 4.0                # 与 Flutter pixelRatio=4.0 一致 → 输出宽 1560（TarotBubble 同款，图片本身清晰）
COVER_H = int(W_LOGICAL * 4 / 3)   # 封面 3:4 → 520

FONT = "'Noto Sans SC',sans-serif"
FONT_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "fonts"
# @font-face 加载内置 Noto Sans SC（与 TarotBubble 一致），避免系统无此字体时回退 PingFang 导致渲染差异
FONT_FACES = "".join(
    f"@font-face{{font-family:'Noto Sans SC';src:url('{(FONT_DIR / f'NotoSansSC-{w}.ttf').resolve().as_uri()}') format('truetype');font-weight:{weight};}}"
    for w, weight in [("Regular", 400), ("Medium", 500), ("SemiBold", 600), ("Bold", 700)]
)

# ---- 复刻自 TarotBubble 分享长图文的颜色常量 ----
C_BG_A = "#FDF5E5"             # 渐变上 奶油白
C_BG_B = "#E5DDFC"             # 渐变下 浅紫
C_PURPLE = "#5B4DBC"           # 品牌紫
C_INK = "#000000"              # 正文黑
C_SUB = "#555555"              # 位置灰
C_TIP = "rgba(0,0,0,0.7)"      # AI 提示
C_BLOCK_BG = "rgba(255,255,255,0.7)"     # 白半透明内容块
C_BLOCK_BORDER = "rgba(91,77,188,0.15)"  # 内容块描边
C_QUOTE_BG = "rgba(132,132,132,0.06)"    # 引用块灰底
C_CODE = "#7B61FF"             # 行内代码紫


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def md_inline(text: str) -> str:
    """极简 markdown 行内解析：**粗体**、`行内代码`。"""
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`(.+?)`", lambda m: f'<span class="code">{m.group(1)}</span>', text)
    return text


def is_hr(line: str) -> bool:
    t = line.strip()
    if len(t) < 3:
        return False
    return bool(re.fullmatch(r"[-\s]{3,}", t)) or bool(re.fullmatch(r"[\*\s]{3,}", t))


def render_block(text: str) -> str:
    """渲染一个 markdown 分块（--- 之间），对应 Flutter MarkdownInterpretationView 的块容器。"""
    parts: list[str] = []
    para: list[str] = []

    def flush_para():
        nonlocal para
        if para:
            body = "<br>".join(md_inline(p) for p in para)
            parts.append(f'<p>{body}</p>')
            para = []

    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            flush_para()
            continue
        if line.startswith("> "):
            flush_para()
            q = line[2:].strip()
            parts.append(f'<div class="quote">{md_inline(q)}</div>')
        elif line.startswith("#"):
            flush_para()
            heading = line.lstrip("#").strip()
            parts.append(f'<h2>{md_inline(heading)}</h2>')
        else:
            para.append(line)
    flush_para()
    return f'<div class="block">{ "".join(parts) }</div>'


def md_to_blocks(text: str) -> str:
    """按 --- 横线把整段解读切成若干块容器（对应 _splitByHorizontalRules）。"""
    blocks, cur = [], []
    for raw in text.split("\n"):
        if is_hr(raw):
            if cur:
                blocks.append("\n".join(cur))
                cur = []
        else:
            cur.append(raw)
    if cur:
        blocks.append("\n".join(cur))
    return "".join(render_block(b) for b in blocks if b.strip())


def sheet_css() -> str:
    return f"""
{FONT_FACES}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#E9E2F5;display:flex;flex-direction:column;align-items:center;gap:20px;padding:20px}}
.sheet{{width:{W_LOGICAL}px;background:radial-gradient(ellipse at top center,{C_BG_A} 0%,{C_BG_B} 100%);
       font-family:{FONT};-webkit-font-smoothing:antialiased;position:relative}}
/* 页头：logo + 解读来自塔罗气泡 */
.header{{display:flex;justify-content:center;align-items:center;padding-top:35px}}
.header .logo{{width:32px;height:32px;border-radius:5px;object-fit:cover}}
.header .brand{{margin-left:8px;font-size:16px;font-weight:500;color:{C_PURPLE}}}
/* 问题 */
.question{{padding:24px 16px 0;font-size:18px;font-weight:bold;color:{C_PURPLE}}}
/* 牌卡网格（Wrap 左对齐） */
.cards{{display:flex;flex-wrap:wrap;gap:8px 8px;row-gap:12px;padding:20px 16px 0}}
.cardcol{{display:flex;flex-direction:column;align-items:center;width:50px}}
.cardcol img{{width:50px;height:87.5px;border-radius:5px;object-fit:cover}}
.cardcol .cname{{margin-top:5px;width:73px;text-align:center;font-size:10px;font-weight:400;color:{C_INK}}}
.cardcol .cpos{{width:61px;text-align:center;font-size:8px;font-weight:400;color:{C_SUB}}}
/* markdown 内容块（每块独立卡片，对齐 Flutter MarkdownInterpretationView） */
.blocks{{padding:12px 0 0}}
.block{{background:{C_BLOCK_BG};border:0.5px solid {C_BLOCK_BORDER};border-radius:16px;
       padding:16px;margin-bottom:12px;color:{C_INK}}}
.block p{{font-size:16px;font-weight:400;line-height:1.7;color:{C_INK}}}
.block p + p{{margin-top:10px}}
.block strong{{font-weight:600}}
.block h2{{font-size:16px;font-weight:600;line-height:1.3;color:{C_INK};margin-bottom:8px}}
.block .quote{{background:{C_QUOTE_BG};border-radius:12px;padding:12px 16px;margin:8px 0;
              font-size:15px;font-weight:400;line-height:1.5;color:{C_INK}}}
.block .code{{color:{C_CODE};font-family:Menlo,monospace;font-size:15px;background:#F5F5F5}}
/* AI 提示 */
.ai-tip{{padding:16px 20px 24px;font-size:10px;font-weight:400;color:{C_TIP}}}
.ai-tip.center{{text-align:center;margin-top:auto}}
/* 品牌 CTA */
.cta{{display:flex;justify-content:center;margin:4px 20px 0}}
.cta span{{background:linear-gradient(135deg,#E9DFFF,#F3E9FF);color:{C_PURPLE};border-radius:22px;
          padding:11px 24px;font-size:14px;font-weight:600;letter-spacing:1px;
          box-shadow:0 3px 10px rgba(91,77,188,.14)}}
/* 解读页：自适应长图（高度随内容，不固定 3:4，避免遮蔽） */
.opt-sheet{{display:flex;flex-direction:column;padding:20px 20px 16px}}
.opt-q{{text-align:center;font-size:17px;font-weight:bold;color:{C_PURPLE};line-height:1.4;padding:0 6px}}
.opt-cards{{display:flex;justify-content:center;flex-wrap:wrap;gap:10px 12px;margin:12px 0 10px}}
.opt-cards .cardcol{{width:44px}}
.opt-cards .cardcol img{{width:44px;height:77px;border-radius:5px}}
.opt-cards .cardcol .cname{{margin-top:4px;width:60px;font-size:9px}}
.opt-cards .cardcol .cpos{{width:52px;font-size:7.5px}}
/* 封面专用：浅色可爱风（对齐 material_cover_answer.py 素材1号） */
.cover-sheet{{--theme:{C_PURPLE};
             background:radial-gradient(ellipse at top center,#FFF7EC 0%,#FFE7EE 100%)}}
.deco{{position:absolute;z-index:0;opacity:.5;pointer-events:none}}
.d1{{top:30px;left:36px;font-size:24px;color:#F5A9C2;transform:rotate(18deg)}}
.d2{{top:44px;right:36px;font-size:19px;color:#D3BFF0;transform:rotate(-12deg)}}
.d3{{bottom:120px;left:48px;font-size:16px;color:#F5A9C2}}
.cover-q{{display:flex;flex-direction:column;align-items:center;text-align:center;
         padding:60px 24px 0;position:relative;z-index:1}}
.qt{{font-size:24px;font-weight:800;line-height:1.5;letter-spacing:1px}}
.qt-plain{{color:var(--theme)}}
.qt-stroke{{color:#fff;-webkit-text-stroke:1.5px var(--theme);
           text-shadow:0 3px 8px rgba(0,0,0,.08)}}
.cover-q .qsub{{margin-top:14px;font-size:13px;color:#B0858E;letter-spacing:1px}}
.pick-row{{display:flex;justify-content:center;gap:16px;padding:24px 0 0;position:relative;z-index:1}}
.pick-cell{{display:flex;flex-direction:column;align-items:center}}
.cback{{width:56px;height:98px;border-radius:10px;position:relative;
       background:linear-gradient(160deg,#FFE3EF,#E8D9FF);
       border:2px solid rgba(255,255,255,.85);
       box-shadow:inset 0 0 0 2px rgba(232,122,138,.16),0 6px 14px rgba(240,150,170,.25);
       display:flex;justify-content:center;align-items:center}}
.cback::before{{content:"";position:absolute;inset:7px;border-radius:6px;
               border:1.5px dashed rgba(232,122,138,.45)}}
.cback-orn{{font-size:17px;color:#E8788A;text-shadow:0 1px 3px rgba(232,120,138,.35)}}
.ctag{{margin-top:10px;min-width:26px;height:22px;padding:0 9px;border-radius:11px;color:#fff;
      font-size:13px;font-weight:800;display:flex;justify-content:center;align-items:center;
      background:var(--theme);box-shadow:0 3px 8px rgba(232,120,138,.35)}}
/* 选项页品牌钩子 logo（短图文三套主题共用，封面由即梦生成不走本 CSS） */
.sf-logo{{width:16px;height:16px;border-radius:4px;object-fit:cover}}
"""


def header_html(data: dict) -> str:
    logo = data.get("logo", "")
    brand = data.get("brand", "解读来自塔罗气泡")
    return f'<div class="header"><img class="logo" src="{esc(logo)}"><span class="brand">{esc(brand)}</span></div>'


def ai_tip_html(data: dict) -> str:
    tip = data.get("ai_tip", "*以上分析由塔罗气泡App使用AI生成，请理性看待")
    return f'<div class="ai-tip">{esc(tip)}</div>'


def cover_html(data: dict) -> str:
    """封面：浅色可爱风（对齐 material_cover_answer.py 素材1号 create_cover 接口）。
    无页头、内容整体上移；theme_color 主题色、title_style "stroke"|"plain"、
    4 张 CSS 卡背 + 中文分组标签、底部说明居中。"""
    question = data["question"]
    intro = data.get("intro", "凭第一感觉，选一组")
    theme = data.get("theme_color", "#E8788A")
    tstyle = data.get("title_style", "plain")
    tip = data.get("cover_ai_tip", "所有分析来自塔罗气泡App用AI生成，请理性看待")
    rots = [-4, 2, -2, 4]
    slots = "".join(
        f'<div class="pick-cell">'
        f'<div class="cback" style="transform:rotate({rots[i % len(rots)]}deg)">'
        f'<span class="cback-orn">✦</span></div>'
        f'<div class="ctag">{o["id"]}</div>'
        f"</div>"
        for i, o in enumerate(data["options"])
    )
    return f"""
<section class="sheet cover-sheet" style="--theme:{theme};height:{COVER_H}px;display:flex;flex-direction:column">
  <div class="deco d1">✦</div>
  <div class="deco d2">✧</div>
  <div class="deco d3">♡</div>
  <div class="cover-q">
    <div class="qt qt-{tstyle}">{esc(question)}</div>
    <div class="qsub">✨ {esc(intro)} ✨</div>
  </div>
  <div class="pick-row">{slots}</div>
  <div class="ai-tip center">{esc(tip)}</div>
</section>
"""


def option_html(data: dict, opt: dict) -> str:
    cards = "".join(
        f'<div class="cardcol">'
        f'<img src="{esc(c["img"])}" style="transform:{ "rotate(180deg)" if c.get("reversed") else "none" }">'
        f'<div class="cname">{esc(c.get("name", ""))}</div>'
        f'<div class="cpos">{esc(c.get("position", ""))}</div>'
        f"</div>"
        for c in opt.get("cards", [])
    )
    return f"""
<section class="sheet opt-sheet">
  <div class="opt-q">{esc(data["question"])}</div>
  <div class="opt-cards">{cards}</div>
  <div class="blocks">{md_to_blocks(opt.get("interpretation", ""))}</div>
</section>
"""


def build_html(data: dict) -> str:
    css = sheet_css()
    sheets = cover_html(data) + "".join(option_html(data, o) for o in data["options"])
    return (f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><style>{css}</style>'
            f'</head><body>{sheets}</body></html>')


def render(data_dir: pathlib.Path):
    data = json.loads((data_dir / "content.json").read_text(encoding="utf-8"))
    out_dir = data_dir / "out"
    out_dir.mkdir(exist_ok=True)
    # 清理旧 PNG：out/ 里的 + 问题目录下的封面/选项（最终 PNG 直接放问题目录，方便拷贝）
    for stale in list(out_dir.glob("*.png")) + list(data_dir.glob("01_封面.png")) + list(data_dir.glob("选项*.png")):
        stale.unlink()
    name = data_dir.name
    h = out_dir / f"{name}.html"
    h.write_text(build_html(data), encoding="utf-8")

    fnames = ["01_封面"]
    fnames += [f"选项{o['id']}" for i, o in enumerate(data["options"])]

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W_LOGICAL, "height": COVER_H}, device_scale_factor=DPR)
        pg.goto(h.resolve().as_uri())
        pg.wait_for_timeout(700)
        n = pg.locator(".sheet").count()
        for i in range(n):
            pg.locator(".sheet").nth(i).screenshot(path=str(data_dir / f"{fnames[i]}.png"))
        b.close()
    print(f"{name}: {n} sheets -> {data_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 render_mass_divination.py <数据目录>")
        sys.exit(1)
    render(pathlib.Path(sys.argv[1]))

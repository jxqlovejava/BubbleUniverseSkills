#!/usr/bin/env python3
"""大众占卜短图文渲染脚本（选项图固定 3:4）。

复用长图文渲染基建（Playwright HTML/CSS + 内置 Noto Sans SC + 3:4 封面），
但选项页改为**固定 3:4**（设计逻辑宽 390、高 520 → DPR4.0 输出 1560×2080，符合小红书 3:4），
视觉参考爆款参考图（即梦识图）：暖米羊皮纸底 #EFE8DB 统一配色 + 樱花粉 #C4677E 加粗分组标题 + 暖炭黑正文，
无边框无分割线。结构 = 组号 + 牌阵名 + 牌面小图行 + **关键词/星座与四元素**两组（粉色标题）+ 状态翻译散文。
正文超限时 JS 按 0.5px 步长缩字号（下限 9.5px，保证全文不溢出不截断）。

用法：
    python3 render_short_divination.py <数据目录> [--theme parchment|black]
    parchment（默认）= 羊皮纸爆款风；black = 抖音爆款纯黑风（纯黑底 + 纯白粗体 + emoji 标题，只换皮不改结构）。
数据目录需含 content.json（question/options/interpretation）与 logo/牌图。
输出到 <数据目录>/：选项A/B/C.png（全部 3:4）。封面由即梦 image skill 生成（AI 封面），本脚本不再渲染。
"""
import base64
import io
import json
import math
import pathlib
import random
import re
import sys
from datetime import datetime

from PIL import Image
from playwright.sync_api import sync_playwright

from render_mass_divination import (
    COVER_H,
    DPR,
    FONT,
    FONT_FACES,
    W_LOGICAL,
    esc,
    md_inline,
    sheet_css,
)

GROUP_LABELS = ["第一组", "第二组", "第三组", "第四组"]
# 抖音短图文选项页品牌钩子（承接解读 + 点塔罗气泡 + 下载理由；用户 2026-08-20 定稿三条，每次渲染随机出一条）
IP_LINES = [
    "纠结到睡不着的那个问题，塔罗气泡App给你答案",
    "心里那个解不开的结，塔罗气泡App接着帮你解",
    "感情、选择、想不通的事，塔罗气泡App接着为你解",
]


def brand_foot_html(data: dict, container_cls: str = "s-foot", app_cls: str = "sf-app") -> str:
    """抖音短图文选项页品牌钩子：logo + IP 行，App 名高亮（accent 色加粗）。
    放在正文缩放容器外，固定不随正文缩字，保证钩子永远清楚。"""
    line = data.get("ip_line") or random.choice(IP_LINES)
    logo = data.get("logo", "")
    # HTML 写在 out/ 下，cards 在数据目录（上一级）：logo 需 ../ 前缀（与牌图 ../cards/ 约定一致），否则破图
    if logo and logo.startswith("cards/"):
        logo = "../" + logo
    logo_img = f'<img class="sf-logo" src="{esc(logo)}">' if logo else ""
    hl = re.sub(r"塔罗气泡(?:App)?", lambda m: f'<b class="{app_cls}">{m.group(0)}</b>', line)
    return f'<div class="{container_cls}">{logo_img}<span>{hl}</span></div>'

# 爆款参考图配色（即梦识图 + 像素采样）：羊皮纸底统一、樱花粉标题、暖炭黑正文
PARCHMENT = "#E8D4B4"   # 背景（所有组统一，深暖褐羊皮纸·古朴）
# 古朴羊皮纸配楷体（Kaiti SC 书法感/古籍感最强；宋体 Songti SC 作回退）
SERIF = "'Kaiti SC','Songti SC',serif"
PINK = "#C4677E"        # 组号 + 关键词/星座与四元素 分组标题（深玫瑰红，深羊皮纸底上更清楚）
INK = "#3B3328"         # 正文暖炭黑
SUB = "#9A8F82"         # 牌阵名等辅助文字
# 开头固定两组（渲染成粉色标题块）
GROUP_KEYS = ("关键词", "星座与四元素")

# 主题：parchment = 羊皮纸爆款风（默认，保留不动）；
# black = 抖音爆款纯黑风（参考抖音大众占卜爆款帖：纯黑底 + 纯白粗体正文 + emoji 标题，3:4 不变）
THEMES = {
    "parchment": {
        "bg": PARCHMENT, "accent": PINK, "ink": INK, "sub": SUB,
        "sname": "#6E624F", "spos": "#8A7B62", "strong": "#2E2A22",
        "weight": 400, "font": SERIF, "texture": True, "emoji": {}, "gmt": 5,
    },
    "black": {
        "bg": "#000000", "accent": PINK, "ink": "rgba(255,255,255,.92)",
        "sub": "rgba(255,255,255,.55)", "sname": "rgba(255,255,255,.72)",
        "spos": "rgba(255,255,255,.50)", "strong": "#FFFFFF",
        "weight": 600, "font": "'PingFang SC','Hiragino Sans GB',sans-serif",
        "texture": False, "gmt": 12,
        "emoji": {"group": "🔮", "关键词": "💫", "星座与四元素": "✨"},
    },
    # memo = iOS 备忘录黑底爆款风（参考抖音备忘录截图：纯黑底 + 白字 + 橙色高亮 chip + 底部品牌水印）。
    # 结构与其他两套不同（无粉色素、有日期/大标题/水印），不走 short_css，占位仅供 CLI 校验。
    "memo": {},
}

# 各主题选项图文件名后缀（封面两/三主题共用 01_封面.png）
SUFFIX = {"parchment": "", "black": "-纯黑", "memo": "-备忘录"}

# 真实羊皮纸纹理（即梦识图：棉麻纸颗粒感 + 用户补充"颗粒不均匀、偶有纤维感"）。
# 程序化生成一张羊皮纸 PNG：米色底 + 逐像素细颗粒 + 低频正弦斑驳（明暗不均、天然无缝）
# + 随机纤维细线/细点。固定 seed 保证每次渲染纹理一致。
def _make_parchment_uri(seed: int = 42, size: int = 320) -> str:
    rng = random.Random(seed)
    base = (232, 212, 180)  # PARCHMENT #E8D4B4 深暖褐羊皮纸底（古朴）
    img = Image.new("RGB", (size, size), base)
    px = img.load()
    # 1) 细颗粒（中间档）：~1.5× 块（介于逐像素与 2×2 之间），对比 ±8
    gs = size * 2 // 3
    g = Image.new("L", (gs, gs))
    gp = g.load()
    for yy in range(gs):
        for xx in range(gs):
            gp[xx, yy] = 128 + rng.randint(-8, 8)
    g = g.resize((size, size), Image.NEAREST)
    gp = g.load()
    for y in range(size):
        for x in range(size):
            d = gp[x, y] - 128
            px[x, y] = (base[0] + d, base[1] + d, base[2] + d)
    # 2) 不均匀斑驳 + 暖褐老化：3 组低频正弦叠加（天然无缝，明暗不均）；
    #    暗处蓝通道压得多 → 偏棕，亮处偏暖 → 像旧纸的包浆
    waves = [(0.5, 1.1, 2.3), (0.8, 2.4, 0.7), (1.2, 0.9, 3.5)]
    for y in range(size):
        for x in range(size):
            c = 0.0
            for fx, p1, p2 in waves:
                c += math.sin(2 * math.pi * fx * x / size + p1) * math.sin(2 * math.pi * fx * y / size + p2)
            d = c / len(waves) * 15
            dr, dg, db = int(d), int(d * 0.8), int(d * 0.4)
            r, g, b = px[x, y]
            px[x, y] = (max(0, min(255, r + dr)), max(0, min(255, g + dg)), max(0, min(255, b + db)))
    # 3) 纤维：随机细长线（暗/亮），跨边界无缝 —— 只留"个别偶尔"（用户嫌多）
    for _ in range(int(size * size / 3000)):
        x0, y0 = rng.randrange(size), rng.randrange(size)
        ang = rng.uniform(0, math.pi)
        L = rng.randint(8, 26)
        dv = rng.choice([-1, 1]) * rng.randint(6, 13)
        for t in range(L):
            x = int(x0 + t * 0.8 * math.cos(ang)) % size
            y = int(y0 + t * 0.8 * math.sin(ang)) % size
            r, g, b = px[x, y]
            px[x, y] = (max(0, min(255, r + dv)), max(0, min(255, g + dv)), max(0, min(255, b + dv)))
    # 4) 细点：个别小斑点（纤维头/杂质）±12 —— 也减半
    for _ in range(int(size * size / 900)):
        x0, y0 = rng.randrange(size), rng.randrange(size)
        dv = rng.choice([-1, 1]) * rng.randint(10, 22)
        for dx in range(3):
            for dy in range(3):
                x, y = (x0 + dx) % size, (y0 + dy) % size
                r, g, b = px[x, y]
                px[x, y] = (max(0, min(255, r + dv)), max(0, min(255, g + dv)), max(0, min(255, b + dv)))
    # 5) 老化渍斑：几块大的柔褐斑（泛黄岁月痕迹，暗处偏棕）
    for _ in range(6):
        cx, cy = rng.randrange(size), rng.randrange(size)
        R = rng.randint(45, 100)
        A = rng.randint(9, 17)
        for dy in range(-R, R):
            for dx in range(-R, R):
                if dx * dx + dy * dy > R * R:
                    continue
                f = 1 - (dx * dx + dy * dy) ** 0.5 / R
                x, y = (cx + dx) % size, (cy + dy) % size
                r, g, b = px[x, y]
                off = int(A * f)
                px[x, y] = (max(0, min(255, r - int(off * 0.9))),
                            max(0, min(255, g - off)),
                            max(0, min(255, b - int(off * 0.6))))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


PARCH_URI = _make_parchment_uri()

# 正文超限自动缩字号（固定 3:4 必须全部可见；长图文的"无 JS 缩字"不适用于定高场景）。
# 目标 .s-scale（全篇 2 种字号的缩放容器）：缩 base 字号，标题 1.25em / 正文 1em 按比例同缩。
# 关键：**全局统一字号** —— 先各自缩到最小所需，再统一设成相同字号（取最长组需要的），三组一致。
# ⚠ 必须用 IIFE：pg.evaluate 传箭头函数字符串只会"定义不求值"，缩字不生效 → 末行被裁。
SHORT_FIT_JS = """
(function() {
  const scales = Array.from(document.querySelectorAll('.short-sheet .s-scale, .memo-sheet .m-scale')).filter(Boolean);
  if (!scales.length) return;
  const min = 8.0;
  const needed = scales.map(sc => {
    let fs = parseFloat(window.getComputedStyle(sc).fontSize);
    let guard = 0;
    while (sc.scrollHeight > sc.clientHeight + 1 && fs > min && guard++ < 40) {
      fs -= 0.5;
      sc.style.fontSize = fs + 'px';
    }
    return parseFloat(window.getComputedStyle(sc).fontSize);
  });
  const uniform = Math.min.apply(null, needed);
  scales.forEach(sc => { sc.style.fontSize = uniform + 'px'; });
})()
"""


def short_css(theme: dict | None = None) -> str:
    t = theme or THEMES["parchment"]
    bg_img = (f'background-image:url("{PARCH_URI}");background-repeat:repeat;'
              if t["texture"] else "background-image:none;")  # 无纹理主题必须显式 none，压掉 .sheet 基类的紫色渐变
    aging = (""".short-sheet::before{content:"";position:absolute;inset:0;pointer-events:none;z-index:0;
  background:radial-gradient(ellipse at 22% 0%,rgba(255,255,255,.22),transparent 55%),
             radial-gradient(ellipse at center, rgba(255,250,242,.22) 26%, rgba(128,88,44,.36) 100%)}"""
             if t["texture"] else "")
    return f"""
/* 短图文解读页：3:4 固定 · 暖米羊皮纸底（爆款参考图配色） */
.short-sheet{{width:{W_LOGICAL}px;height:{COVER_H}px;background-color:var(--bg,#E8D4B4);
  {bg_img}padding:16px 28px 10px;
  display:flex;flex-direction:column;position:relative;font-family:{t["font"]}}}
{aging}
.short-sheet>*{{position:relative;z-index:1}}
/* 全篇只有 2 种字号：标题 1.25em（加粗粉色）+ 其余 1em（统一）。
   s-scale 是缩放容器，缩字时整体按比例缩放，天然保持两档字号 */
.s-scale{{flex:1;overflow:hidden;display:flex;flex-direction:column;font-size:10.5px;line-height:1.6;
  font-weight:{t["weight"]};color:var(--ink,#3B3328)}}
.s-head{{flex:none;display:flex;align-items:baseline;gap:8px}}
.s-group{{flex:none;font-size:13px;font-weight:700;color:var(--accent,#C4677E);letter-spacing:2px}}
.s-q{{font-size:1em;color:var(--ink,#3B3328);letter-spacing:.5px}}
.s-cards{{flex:none;margin-top:5px;display:flex;justify-content:flex-start;gap:6px}}
/* 固定卡槽 70px：6 字长牌名（如 宝剑骑士逆位，10.5px≈63px）完整放下，牌距均匀不随牌名长短变化 */
.s-cards .scard{{display:flex;flex-direction:column;align-items:center;width:70px;flex:none}}
.s-cards img{{width:24px;height:42px;border-radius:3px;object-fit:cover;box-shadow:0 1px 2px rgba(0,0,0,.08)}}
.s-cards .sname{{margin-top:2px;font-size:1em;font-weight:600;color:var(--sname,#6E624F);white-space:nowrap}}
.s-cards .spos{{margin-top:1px;font-size:.9em;font-weight:500;color:var(--spos,#8A7B62);white-space:nowrap}}
/* 关键词 / 星座与四元素 两组：标题独占一行（粉色加粗大号），正文换行在其下一行 */
.s-groups{{flex:none;margin-top:var(--gmt,5px);display:flex;flex-direction:column;gap:14px}}
.s-g{{display:block}}
.s-gt{{font-size:13px;font-weight:700;color:var(--accent,#C4677E);letter-spacing:1px;margin-bottom:1px}}
.s-kwline{{display:flex;align-items:baseline;flex-wrap:wrap;margin-bottom:1px}}
.s-kwline .s-gt{{flex:none;margin-bottom:0;letter-spacing:.5px}}
.s-kw{{font-size:13px;font-weight:700;color:var(--accent,#C4677E);line-height:1.5}}
.s-bless{{font-size:1em;color:var(--ink,#3B3328);line-height:1.5}}
.s-gb{{font-size:1em;color:var(--ink,#3B3328);line-height:1.5}}
.s-body{{flex:1;margin-top:14px}}
.s-body p{{font-size:1em;margin:0 0 5px;color:var(--ink,#3B3328)}}
.s-body p:last-child{{margin-bottom:0}}
.s-body strong{{font-weight:700;color:var(--strong,#2E2A22)}}
/* 抖音品牌钩子（固定不缩：logo + IP 行，App 名 accent 加粗高亮） */
.s-foot{{flex:none;display:flex;align-items:center;justify-content:center;gap:6px;
  padding-top:7px;font-size:10px;color:var(--ink,#3B3328);position:relative;z-index:1}}
.sf-app{{font-weight:700;color:var(--accent,#C4677E)}}
"""


def card_names_line(cards: list[dict]) -> str:
    """牌面小图行：每张牌一张小图，图下牌名 + 牌阵位置名（逆位旋转 180° + 名标「逆位」）。"""
    cells = []
    for c in cards:
        rev = c.get("reversed")
        nm = esc(c.get("name", "") + ("逆位" if rev else ""))
        pos = esc(c.get("position", ""))
        rot = "transform:rotate(180deg);" if rev else ""
        cells.append(
            f'<div class="scard"><img src="{esc(c.get("img", ""))}" style="{rot}">'
            f'<div class="sname">{nm}</div>'
            f'<div class="spos">{pos}</div></div>'
        )
    return "".join(cells)


def split_groups(text: str) -> tuple[list[tuple[str, list[str]]], str]:
    """把开头两组（**关键词** / **星座与四元素**）与后面的状态翻译散文分开。
    每组正文到空行或下一组标题为止；返回 (groups: [(标题, 正文行列表)], prose: 散文文本)。
    关键词组正文第一行是关键词（粉色加粗）、其余行是祝福句。"""
    groups: list[tuple[str, list[str]]] = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        m = re.match(r"^\s*\*\*(关键词|星座与四元素)\*\*\s*[:：]?\s*(.*)$", lines[i])
        if not m:
            break
        title = m.group(1)
        body = [m.group(2).strip()] if m.group(2).strip() else []
        i += 1
        while (i < len(lines) and lines[i].strip()
               and not re.match(r"^\s*\*\*(关键词|星座与四元素)\*\*", lines[i])):
            body.append(lines[i].strip())
            i += 1
        groups.append((title, body))
        # 跳过组间空行，定位到下一组标题或散文开头
        while i < len(lines) and not lines[i].strip():
            i += 1
    prose = "\n".join(lines[i:]).strip()
    return groups, prose


def short_option_html(data: dict, opt: dict, index: int, theme: dict | None = None) -> str:
    """短图文选项页：组号 + 牌阵名 + 牌面小图行 + 关键词/星座与四元素（粉色标题）+ 状态翻译散文。
    全篇 2 种字号：标题 1.25em（粉色加粗）+ 正文 1em（统一）。black 主题标题带 emoji。"""
    t = theme or THEMES["parchment"]
    em = t["emoji"]
    # 组号按选项 id（A/B/C…）取，单选项补跑（content.json 只含一个选项）也不会错标成第一组
    oid = (opt.get("id") or "").upper()
    idx = ord(oid) - 65 if len(oid) == 1 and "A" <= oid <= "Z" else index
    group = GROUP_LABELS[idx] if 0 <= idx < len(GROUP_LABELS) else "第" + esc(opt.get("id", "")) + "组"
    if em.get("group"):
        group = f'{em["group"]} {group}'
    question = esc(data.get("question", ""))
    names = card_names_line(opt.get("cards", []))
    groups, prose = split_groups(opt.get("interpretation") or "")

    def group_html(title: str, body: list[str]) -> str:
        label = f'{em[title]} {title}' if em.get(title) else title
        gt = f'<div class="s-gt">{esc(label)}</div>'
        if title == "关键词" and len(body) > 1:
            # 关键词：标题 + 关键词同一行、同字号同样式（1.25em 粉色加粗），祝福句换行正常色
            line = f'<div class="s-kwline"><span class="s-gt">{esc(label)}：</span><span class="s-kw">{md_inline(body[0])}</span></div>'
            bless = f'<div class="s-bless">{md_inline(chr(10).join(body[1:]))}</div>'
            return f'<div class="s-g">{line}{bless}</div>'
        return f'<div class="s-g">{gt}<div class="s-gb">{md_inline("".join(body))}</div></div>'

    groups_html = "".join(group_html(title, b) for title, b in groups)
    paras = "".join(f"<p>{md_inline(p)}</p>" for p in prose.split("\n\n"))
    q_html = f'<span class="s-q">{question}</span>' if question else ""
    return f"""
<section class="sheet short-sheet" style="--accent:{t["accent"]};--bg:{t["bg"]};--ink:{t["ink"]};--sub:{t["sub"]};--sname:{t["sname"]};--spos:{t["spos"]};--strong:{t["strong"]};--gmt:{t["gmt"]}px">
  <div class="s-scale">
    <div class="s-head"><span class="s-group">{group}</span>{q_html}</div>
    <div class="s-cards">{names}</div>
    {f'<div class="s-groups">{groups_html}</div>' if groups_html else ""}
    <div class="s-body">{paras}</div>
  </div>
  {brand_foot_html(data)}
</section>
"""


def build_html(data: dict, theme: dict | None = None) -> str:
    css = sheet_css() + short_css(theme)
    # 封面由即梦 image skill 生成（AI 封面），脚本只渲染选项页
    sheets = "".join(
        short_option_html(data, o, i, theme) for i, o in enumerate(data["options"])
    )
    return (f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><style>{css}</style>'
            f'</head><body>{sheets}</body></html>')


# ---------- 第三套：memo（iOS 备忘录黑底爆款风） ----------
# 参考抖音爆款备忘录截图：纯黑底、顶部居中灰日期、大号粗白组标题、灰小字免责、
# 白粗体段落标题（带冒号）、正文白字、关键词/牌名打橙色高亮 chip（深棕底圆角）、底部品牌水印。
MEMO_FONT = "'PingFang SC','Hiragino Sans GB',sans-serif"
MEMO_CHIP_BG = "#332916"   # 高亮 chip 深棕底
MEMO_CHIP_FG = "#E8A23D"   # 高亮 chip 暖橙字
MEMO_YELLOW = "#E9B13B"    # iOS 备忘录工具栏黄


def _icon(path: str, size: int = 13) -> str:
    """iOS 风线条图标（stroke 制，currentColor 上色）。
    16px 小图标不用即梦栅格图：AI 生图会糊且粗细不一，SVG 矢量风格/大小天然一致。"""
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="1.3" stroke-linecap="round" '
            f'stroke-linejoin="round">{path}</svg>')


# 备忘录顶栏图标组（按参考图裁切放大后逐个校正：左侧边栏图标、双行清单、圈A、圈省略号）
ICONS = {
    "sidebar": _icon('<rect x="3.5" y="5" width="17" height="14" rx="2.5"/><path d="M9.5 5v14"/>'
                     '<path d="M5.6 8.2h1.7M5.6 11.2h1.7M5.6 14.2h1.7"/>'),
    "checklist": _icon('<path d="M9.8 7h10.2M9.8 16.5h10.2"/>'
                       '<circle cx="5.6" cy="7" r="2.3"/><path d="M4.5 6.9l.8.9 1.5-1.7"/>'
                       '<circle cx="5.6" cy="16.5" r="2.3"/>'),
    "table": _icon('<rect x="3.5" y="4.5" width="17" height="15" rx="2.5"/>'
                   '<path d="M3.5 9.5h17M3.5 14.5h17M9.3 4.5v15M14.8 4.5v15"/>'),
    "paperclip": _icon('<path d="M19.5 11.3l-7.6 7.6a4.6 4.6 0 0 1-6.5-6.5l8-8a3.1 3.1 0 0 1 4.4 4.4l-7.8 7.8a1.6 1.6 0 0 1-2.2-2.2l7.2-7.2"/>'),
    "share": _icon('<path d="M12 14.5V4"/><path d="M7.6 8.2L12 3.8l4.4 4.4"/>'
                   '<path d="M5.5 11.5V18a2 2 0 0 0 2 2h9a2 2 0 0 0 2-2v-6.5"/>'),
    "circled_a": _icon('<circle cx="12" cy="12" r="8.2"/>'
                       '<path d="M8.4 15.8L12 7.8l3.6 8M9.8 13.4h4.4"/>'),
    "ellipsis": _icon('<circle cx="12" cy="12" r="8.2"/>'
                      '<circle cx="8.4" cy="12" r="1" fill="currentColor" stroke="none"/>'
                      '<circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/>'
                      '<circle cx="15.6" cy="12" r="1" fill="currentColor" stroke="none"/>'),
    "compose": _icon('<path d="M12.8 4.8H6.5a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-6.3"/>'
                     '<path d="M17.9 3.4a1.7 1.7 0 0 1 2.7 2.7l-7.3 7.3-3.5.9.9-3.5z"/>'),
    # 状态栏（白色）
    "wifi": _icon('<path d="M4.5 10a11.5 11.5 0 0 1 15 0"/><path d="M7.5 13a7.5 7.5 0 0 1 9 0"/>'
                  '<circle cx="12" cy="16.3" r="1.3" fill="currentColor" stroke="none"/>', 12),
    "battery": _icon('<rect x="2.5" y="8.5" width="17" height="8" rx="2.2"/>'
                     '<path d="M21.8 11v3"/><rect x="4.3" y="10.3" width="8.5" height="4.4" rx="1.1" fill="currentColor" stroke="none"/>', 17),
}


def memo_css() -> str:
    return f"""
/* 短图文第三套：memo 备忘录黑底风（3:4 固定，与另两套同尺寸） */
.memo-sheet{{width:{W_LOGICAL}px;height:{COVER_H}px;background:#000;
  background-image:none;padding:10px 30px 12px;
  display:flex;flex-direction:column;position:relative;font-family:{MEMO_FONT}}}
.memo-sheet>*{{position:relative;z-index:1}}
/* 与另两套同思路：m-scale 为缩放容器，全篇字号按 em 比例，JS 缩 base 字号整体等比缩 */
.m-scale{{flex:1;overflow:hidden;display:flex;flex-direction:column;font-size:10.5px;
  line-height:1.55;font-weight:400;color:rgba(255,255,255,.92)}}
/* 状态栏 + 工具栏固定 px（不随 JS 缩字缩放，保持 iOS 截图 chrome 感） */
.m-status{{flex:none;display:flex;justify-content:space-between;align-items:center;
  font-size:9px;font-weight:600;color:#fff;margin-bottom:5px}}
.m-status .sicons{{display:flex;align-items:center;gap:4px;color:#fff;font-weight:400}}
.m-toolbar{{flex:none;display:flex;align-items:center;justify-content:space-between;
  color:{MEMO_YELLOW};margin-bottom:8px}}
.m-toolbar .tgroup{{display:flex;align-items:center;gap:12px}}
.m-toolbar .tlabel{{font-size:9px;font-weight:500;letter-spacing:1px;color:rgba(255,255,255,.45)}}
.m-date{{flex:none;text-align:center;font-size:.85em;color:rgba(255,255,255,.45);margin-bottom:4px}}
.m-title{{flex:none;font-size:1.4em;font-weight:700;color:#fff;letter-spacing:1px}}
.m-q{{flex:none;font-size:1.25em;font-weight:700;color:#fff;margin-top:2px}}
.m-disclaim{{flex:none;font-size:.9em;color:rgba(255,255,255,.4);margin:3px 0 2px}}
.m-cards{{flex:none;margin:6px 0 2px;display:flex;gap:6px}}
.m-cards .scard{{display:flex;flex-direction:column;align-items:center;width:70px;flex:none}}
.m-cards img{{width:24px;height:42px;border-radius:3px;object-fit:cover}}
.m-cards .sname{{margin-top:2px;font-size:.95em;font-weight:500;color:rgba(255,255,255,.75);white-space:nowrap}}
.m-cards .spos{{margin-top:1px;font-size:.85em;color:rgba(255,255,255,.45);white-space:nowrap}}
/* 区块间距：关键词/星座 标题上间距 = 散文与星座区间距（用户要求两处一致、放大） */
.m-sec{{flex:none;font-size:1.25em;font-weight:700;color:#fff;margin:12px 0 2px}}
.m-chips{{flex:none;display:flex;flex-wrap:wrap;gap:4px;margin-bottom:2px}}
.m-chip{{background:{MEMO_CHIP_BG};color:{MEMO_CHIP_FG};border-radius:4px;padding:1px 6px;font-weight:600}}
.m-bless{{flex:none;color:rgba(255,255,255,.92)}}
.m-gb{{flex:none;color:rgba(255,255,255,.92)}}
.m-body{{flex:1;margin-top:12px}}
.m-body p{{margin:0 0 5px}}
.m-body p:last-child{{margin-bottom:0}}
.hl{{background:{MEMO_CHIP_BG};color:{MEMO_CHIP_FG};border-radius:3px;padding:0 3px;font-weight:600}}
.m-foot{{flex:none;display:flex;align-items:center;justify-content:center;gap:6px;
  padding-top:7px;font-size:10px;color:rgba(255,255,255,.9);position:relative;z-index:1}}
.m-foot .m-app{{font-weight:700;color:{MEMO_YELLOW}}}
"""


def _hl_phrases(html: str, phrases: list[str]) -> str:
    """关键句子/关键词打橙色高亮 chip（iOS 备忘录高亮风）。
    在 md_inline 转义后调用；长度降序让长句优先命中（短词不会截胡长句）。
    注意：phrase 里别带 ** 等 markdown 字符（转义后对不上）；相互重叠的短语不保证嵌套正确。"""
    phrases = sorted({p.strip() for p in phrases if p and p.strip()}, key=len, reverse=True)
    if not phrases:
        return html
    pat = "|".join(re.escape(p) for p in phrases)
    return re.sub(pat, lambda m: f'<span class="hl">{m.group(0)}</span>', html)


def memo_option_html(data: dict, opt: dict, index: int) -> str:
    # 组号按选项 id（A/B/C…）取，单选项补跑（content.json 只含一个选项）也不会错标成第一组
    oid = (opt.get("id") or "").upper()
    idx = ord(oid) - 65 if len(oid) == 1 and "A" <= oid <= "Z" else index
    group = GROUP_LABELS[idx] if 0 <= idx < len(GROUP_LABELS) else "第" + esc(opt.get("id", "")) + "组"
    question = esc(data.get("question", ""))
    names = card_names_line(opt.get("cards", []))
    groups, prose = split_groups(opt.get("interpretation") or "")
    now = datetime.now()
    date = now.strftime("%Y年%-m月%-d日 %H:%M")
    weekday = "一二三四五六日"[now.weekday()]
    status_left = f"{now.strftime('%H:%M')}  {now.month}月{now.day}日周{weekday}"

    # 高亮：优先 content.json 里 LLM 挑好的关键句子（opt["highlights"]），其次关键词（≥2 字）
    kw_terms: list[str] = []
    for title, body in groups:
        if title == "关键词" and body:
            kw_terms = [w.strip() for w in re.split(r"[、,，]", body[0])
                        if len(w.strip()) >= 2]
    phrases = list(opt.get("highlights") or []) + kw_terms

    secs = []
    for title, body in groups:
        if title == "关键词" and body:
            chips = "".join(f'<span class="m-chip">{md_inline(w)}</span>'
                            for w in re.split(r"[、,，]", body[0]) if w.strip())
            bless = (f'<div class="m-bless">{md_inline(chr(10).join(body[1:]))}</div>'
                     if len(body) > 1 else "")
            secs.append(f'<div class="m-sec">关键词：</div>'
                        f'<div class="m-chips">{chips}</div>{bless}')
        else:
            secs.append(f'<div class="m-sec">{esc(title)}：</div>'
                        f'<div class="m-gb">{_hl_phrases(md_inline("".join(body)), phrases)}</div>')
    paras = "".join(f"<p>{_hl_phrases(md_inline(p), phrases)}</p>"
                    for p in prose.split("\n\n"))

    return f"""
<section class="sheet memo-sheet">
  <div class="m-scale">
    <div class="m-status"><span>{status_left}</span><span class="sicons">{ICONS["wifi"]}<span>21%</span>{ICONS["battery"]}</span></div>
    <div class="m-toolbar">
      <div class="tgroup">{ICONS["sidebar"]}</div>
      <div class="tgroup"><span class="tlabel">格式</span>{ICONS["checklist"]}{ICONS["table"]}{ICONS["paperclip"]}</div>
      <div class="tgroup">{ICONS["share"]}{ICONS["circled_a"]}{ICONS["ellipsis"]}{ICONS["compose"]}</div>
    </div>
    <div class="m-date">{date}</div>
    <div class="m-title">{group}</div>
    {f'<div class="m-q">{question}</div>' if question else ""}
    <div class="m-disclaim">大众对应，仅供娱乐～</div>
    <div class="m-cards">{names}</div>
    {''.join(secs)}
    <div class="m-body">{paras}</div>
  </div>
  {brand_foot_html(data, "m-foot", "m-app")}
</section>
"""


def memo_html(data: dict) -> str:
    css = sheet_css() + memo_css()
    # 封面由即梦 image skill 生成，脚本只渲染选项页
    sheets = "".join(
        memo_option_html(data, o, i) for i, o in enumerate(data["options"])
    )
    return (f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><style>{css}</style>'
            f'</head><body>{sheets}</body></html>')


def render(data_dir: pathlib.Path, theme_name: str = "parchment") -> None:
    theme = THEMES[theme_name]
    data = json.loads((data_dir / "content.json").read_text(encoding="utf-8"))
    # 品牌钩子随机出一条（本次渲染所有选项页一致；三套主题各发布独立随机）
    data["ip_line"] = random.choice(IP_LINES)
    out_dir = data_dir / "out"
    out_dir.mkdir(exist_ok=True)
    # 各主题选项图与另两套同目录共存：black 加「-纯黑」、memo 加「-备忘录」后缀。
    # 封面由即梦 image skill 生成（AI 封面），本脚本不渲染、不清理 01_封面.png。
    suffix = SUFFIX[theme_name]
    # 清理旧 PNG：out/ 里的 + 本次要渲染的选项（只清 content.json 里有的选项，
    # 部分选项补跑时不清空同目录其他选项图；另一主题的选项图不动）
    stale_opts = [data_dir / f"选项{o['id']}{suffix}.png" for o in data["options"]]
    for stale in list(out_dir.glob("*.png")) + stale_opts:
        if stale.exists():
            stale.unlink()
    name = data_dir.name
    h = out_dir / f"{name}.html"
    h.write_text(memo_html(data) if theme_name == "memo" else build_html(data, theme),
                 encoding="utf-8")

    fnames = [f"选项{o['id']}{suffix}" for o in data["options"]]

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W_LOGICAL, "height": COVER_H}, device_scale_factor=DPR)
        pg.goto(h.resolve().as_uri())
        pg.wait_for_timeout(700)
        pg.evaluate(SHORT_FIT_JS)
        pg.wait_for_timeout(150)
        sizes = pg.evaluate(
            "Array.from(document.querySelectorAll('.short-sheet .s-body, .memo-sheet .m-body')).map(b => getComputedStyle(b).fontSize).join(',')"
        )
        print(f"  正文缩字后字号: {sizes}（主题 {theme_name}）")
        n = pg.locator(".sheet").count()
        for i in range(n):
            pg.locator(".sheet").nth(i).screenshot(path=str(data_dir / f"{fnames[i]}.png"))
        b.close()
    print(f"{name}: {n} sheets（全部 3:4）-> {data_dir}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    theme_name = "parchment"
    if "--theme" in sys.argv:
        i = sys.argv.index("--theme")
        theme_name = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
    if not args or theme_name not in THEMES:
        print(f"用法: python3 render_short_divination.py <数据目录> [--theme {'|'.join(THEMES)}]")
        sys.exit(1)
    render(pathlib.Path(args[0]), theme_name)

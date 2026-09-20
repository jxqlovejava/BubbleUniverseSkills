#!/usr/bin/env python3
"""情侣四宫格图文帖渲染器：上排=产品界面截图 2 张（原色），下排=情侣照片 2 张。

复刻小红书「塔罗解读+情侣照片四宫格」帖。上排从 6 种真实产品页里选 2 个（content.json 的
pages 字段）：reading 解读页 / shuffle 洗牌页 / draw 抽牌页 / spread 牌阵选择页 /
spread_result 牌阵选择结果页（深色沉浸）/ history 历史记录页。

UI 底座取自 TarotBubble Flutter 源码（样式规格见 README.md）。

用法：python3 render_four_grid.py [content.json]
输出：out/情侣四宫格.png（1080×1620，2:3）+ out/发布文案.txt
依赖：playwright、PIL；assets 全在模板目录内。
"""
import html
import json
import pathlib
import random
import sys

from PIL import Image, ImageEnhance, ImageOps
from playwright.sync_api import sync_playwright

BASE = pathlib.Path(__file__).parent
PW, PH = 390, 844  # 解读页逻辑尺寸（iPhone 14 全屏，顶部自然截断）
SW, SH = 390, 585  # 其余页逻辑尺寸（2:3 直出）
DPR = 3
CELL_W, CELL_H = 540, 810  # 四宫格单格 2:3
FONT = "'PingFang SC','Hiragino Sans GB',sans-serif"
CN_NUM = "一二三四五六七八九十"


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def uri(rel: str) -> str:
    return (BASE / rel).as_uri()


# ── 共用：状态栏 / 品牌铭牌 / app bar ───────────────────────
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


def status_bar(time_str: str) -> str:
    return f'''<div class="status"><span>{esc(time_str)}</span>{status_icons()}
    <div class="brand"><img src="{uri("assets/app_icon.png")}"><span>塔罗气泡</span></div></div>'''


def app_bar(chip: str) -> str:
    return f'''<div class="appbar">{TB_BACK}<div class="chip">{esc(chip)}</div><div class="more"></div></div>'''


COMMON_CSS = f"""
* {{ margin:0; padding:0; box-sizing:border-box; font-family:{FONT}; }}
.status {{ position:absolute; top:0; left:0; right:0; height:44px; display:flex; align-items:center;
  justify-content:space-between; padding:0 24px 0 28px; color:#000; font-size:15px; font-weight:600; z-index:3; }}
.brand {{ position:absolute; left:50%; top:50%; transform:translate(-50%,-50%);
  display:flex; align-items:center; gap:5px; background:#FFF; border-radius:10px;
  padding:4px 10px; box-shadow:0 1px 4px rgba(0,0,0,.08); }}
.brand img {{ width:18px; height:18px; border-radius:4px; display:block; }}
.brand span {{ font-size:15px; font-weight:600; color:#1A143D; letter-spacing:.5px; }}
.appbar {{ position:absolute; top:44px; left:0; right:0; height:48px; display:flex; align-items:center;
  justify-content:space-between; padding:0 16px; z-index:3; }}
.appbar .more {{ width:10px; }}
.chip {{ border:.5px solid #5B4DBC; border-radius:10px; padding:4px 18px; color:#5B4DBC; font-size:13px; }}
"""


def page_html(cfg: dict, body: str, extra_css: str, dark: bool = False) -> str:
    """页面骨架：状态栏（深色页隐藏品牌铭牌，用白字状态栏）。"""
    if dark:
        top = f'''<div class="status" style="color:#FFF"><span>{esc(cfg["time"])}</span>
        <svg width="76" height="14" viewBox="0 0 76 14" fill="#FFF">
<rect x="0" y="9" width="3" height="5" rx="1"/><rect x="5" y="7" width="3" height="7" rx="1"/>
<rect x="10" y="4.5" width="3" height="9.5" rx="1"/><rect x="15" y="2" width="3" height="12" rx="1"/>
<path d="M28 6.2a9 9 0 0 1 12 0l-1.7 1.8a7 7 0 0 0-8.6 0z"/>
<path d="M30.4 9a5.5 5.5 0 0 1 7.2 0l-1.7 1.8a3.6 3.6 0 0 0-3.8 0z"/><circle cx="34" cy="12" r="1.4"/>
<rect x="50" y="2.5" width="20" height="9" rx="2.8" fill="none" stroke="#FFF" stroke-opacity=".45" stroke-width="1"/>
<rect x="52" y="4.5" width="12.5" height="5" rx="1.2"/>
<path d="M71.5 5.2v3.6a2 2 0 0 0 0-3.6z" fill-opacity=".5"/></svg></div>'''
    else:
        top = status_bar(cfg["time"])
    css = COMMON_CSS + extra_css
    return f'''<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><style>{css}</style></head>
<body><div class="phone">{top}{body}</div></body></html>'''


def spread_slots(positions: list, slot_w: int = 74, gap: int = 22) -> str:
    """牌阵空卡位（虚线圆角框 + 牌位名），近似 SpreadLayoutFactory 的 3 卡位横排。"""
    slots = "".join(
        f'<div class="slotwrap"><div class="slot"></div><div class="slotname">{esc(p)}</div></div>'
        for p in positions
    )
    return f'<div class="slots" style="gap:{gap}px">{slots}</div>'


SLOTS_CSS = """
.slots { display:flex; justify-content:center; }
.slotwrap { text-align:center; }
.slot { width:74px; height:130px; border-radius:6px; border:1.5px dashed rgba(91,77,188,.45);
  background:rgba(255,255,255,.35); }
.slotname { font-size:12px; color:rgba(0,0,0,.55); margin-top:8px; }
"""


# ── 1. 解读页 reading ─────────────────────────────────────
def tb_card(c: dict) -> str:
    rev = " rev" if c.get("reversed") else ""
    return f'''<div class="card">
      <img class="cardimg{rev}" src="{uri(c["img"])}">
      <div class="cname">{esc(c["name"])}</div>
      <div class="cpos">{esc(c["position"])}</div>
    </div>'''


def reading_html(cfg: dict) -> tuple[str, int, int]:
    cards = "\n".join(tb_card(c) for c in cfg["cards"])
    paras = "\n".join(
        f'<div class="para">{esc(p).replace(chr(10), "<br>")}</div>'
        for p in cfg["interpretation"]
    )
    body = f'''{app_bar(cfg.get("remaining_text") or "无限畅享占卜")}
<div class="content">
  <div class="topcard"><div class="q">{esc(cfg["question"])}</div><div class="cards">{cards}</div></div>
  <div class="luna">
    <div class="luna-head"><img src="{uri("assets/luna_avatar.png")}"><span>Luna</span></div>
    {paras}
    <div class="ai">{esc(cfg["ai_label"])}</div>
  </div>
</div>'''
    css = """
body { width:390px; height:844px; }
.phone { width:390px; height:844px; position:relative; overflow:hidden;
  background:linear-gradient(150deg,#FAF3FF 0%,#FDFAFF 35%,#FFFFFF 70%); }
.content { position:absolute; top:92px; left:0; right:0; bottom:0; }
.topcard { position:relative; background:rgba(255,255,255,.55); border-radius:0 0 20px 20px;
  padding:14px 16px 18px; }
.q { font-size:20px; font-weight:500; color:#000; text-align:center; margin:4px 24px 16px; line-height:1.4; }
.cards { display:flex; justify-content:space-evenly; }
.card { width:74px; text-align:center; }
.cardimg { width:74px; height:130px; border-radius:5px; object-fit:cover; display:block;
  box-shadow:0 2px 4px rgba(0,0,0,.1); }
.cardimg.rev { transform:rotate(180deg); }
.cname { font-size:13px; color:#000; margin-top:8px; }
.cpos { font-size:11px; color:rgba(0,0,0,.55); margin-top:2px; }
.luna { padding:14px 19px; }
.luna-head { display:flex; align-items:center; gap:11px; margin-bottom:9px; }
.luna-head img { width:35px; height:35px; border-radius:50%; object-fit:cover; background:#FFF; }
.luna-head span { font-size:17px; font-weight:500; color:#000; }
.para { background:rgba(255,255,255,.7); border:.5px solid rgba(91,77,188,.15); border-radius:16px;
  padding:13px 15px; font-size:15px; line-height:1.7; color:#111; margin-bottom:10px; }
.ai { display:inline-block; background:rgba(255,255,255,.5); border:.5px solid rgba(91,77,188,.3);
  border-radius:12px; padding:3px 9px; font-size:11px; color:rgba(0,0,0,.45); }
"""
    return page_html(cfg, body, css), PW, PH


# ── 2. 洗牌页 shuffle ─────────────────────────────────────
def pile_cards(n_core: int = 22, n_edge: int = 8, seed: int = 42) -> str:
    """App 洗牌页牌堆：核心高斯密堆 + 边缘散落。牌心限制在 pile 区内，
    底部避开「结束洗牌」按钮区（牌 74×130，半宽 37/半高 65 + 旋转余量）。"""
    rng = random.Random(seed)
    out = []

    def card(x: float, y: float, rot: float) -> str:
        return (
            f'<img class="pilecard" src="{uri("assets/card_back.webp")}" '
            f'style="left:{x - 37:.0f}px; top:{y - 65:.0f}px; transform:rotate({rot:.0f}deg)">'
        )

    for _ in range(n_core):
        x = min(max(rng.gauss(185, 48), 62), 308)
        y = min(max(rng.gauss(195, 42), 95), 315)
        out.append(card(x, y, rng.uniform(-65, 65)))
    for _ in range(n_edge):
        x = min(max(rng.gauss(185, 88), 62), 308)
        y = min(max(rng.gauss(195, 76), 95), 315)
        out.append(card(x, y, rng.uniform(-70, 70)))
    return "\n".join(out)


def shuffle_html(cfg: dict) -> tuple[str, int, int]:
    body = f'''{app_bar(cfg.get("remaining_text") or "无限畅享占卜")}
<div style="position:absolute;top:92px;left:0;right:0;bottom:0;">
  <div class="title">正在洗牌</div>
  <div class="sub">在心中默念问题三遍后，点击结束洗牌</div>
  <div class="pile">{pile_cards()}</div>
  <div class="shufflebtn">结束洗牌</div>
</div>'''
    css = """
body { width:390px; height:585px; }
.phone { width:390px; height:585px; position:relative; overflow:hidden;
  background:linear-gradient(135deg,#FAF3FF 0%,#FFFFFF 100%); }
.title { text-align:center; font-size:26px; font-weight:500; color:rgba(0,0,0,.8); margin-top:16px; }
.sub { text-align:center; font-size:16px; font-weight:400; color:rgba(0,0,0,.6); margin:14px 30px 0; }
.pile { position:relative; width:370px; height:400px; margin:6px auto 0; }
.pilecard { position:absolute; width:74px; height:130px; border-radius:5px; object-fit:cover;
  border:1px solid rgba(0,0,0,.22); box-shadow:0 3px 7px rgba(0,0,0,.3); }
.shufflebtn { position:absolute; left:19px; right:19px; bottom:16px; height:48px;
  background:#B0A5E1; border-radius:20px; display:flex; align-items:center; justify-content:center;
  color:#FFF; font-size:16px; font-weight:500; }
"""
    return page_html(cfg, body, css), SW, SH


# ── 3. 抽牌页 draw ────────────────────────────────────────
def fan_cards(n: int = 78, radius: float = 250.0, drop: float = 110.0) -> str:
    """App card_draw_page 扇形原版几何：78 张 120×210 牌背，以每张牌**左下角**为旋转枢轴
    （Transform alignment: bottomLeft + rotateZ），枢轴落在圆心 (屏宽/2, 屏高+220)、
    半径 250 的圆上，角度 -135°~+135°（_maxFanAngle = 1.5π）。可见的是中间 ±35° 一段。
    drop：App 圆心偏移 +220 对应 844 高真机屏；本模板 2:3 画布只有 585 高，
    整体再下移 110px，弧顶落到提示语下方且留出间隔，不遮挡抽到的牌、牌名和提示语。"""
    import math

    cx, cy = PW / 2, SH + 220 + drop  # 圆心：水平居中，屏底下方 220+75px
    out = []
    for i in range(n):
        a = -135.0 + 270.0 * i / (n - 1)
        rad = math.radians(a)
        px = cx + radius * math.sin(rad)
        py = cy - radius * math.cos(rad)
        out.append(
            f'<img class="fancard" src="{uri("assets/card_back.webp")}" '
            f'style="left:{px:.1f}px; top:{py - 210:.1f}px; transform:rotate({a:.2f}deg)">'
        )
    return "\n".join(out)


def draw_slots(cards: list) -> str:
    """抽到的牌放进牌阵位（正位/逆位如实，逆位转 180°）。"""
    items = "".join(
        f'<div class="slotwrap">'
        f'<img class="slotimg{" rev" if c.get("reversed") else ""}" src="{uri(c["img"])}">'
        f'<div class="slotname">{esc(c["position"])}</div></div>'
        for c in cards
    )
    return f'<div class="slots" style="gap:22px">{items}</div>'


def draw_html(cfg: dict) -> tuple[str, int, int]:
    positions = cfg.get("positions") or [c["position"] for c in cfg["cards"]]
    nth = min(len(cfg["cards"]), len(CN_NUM)) - 1
    body = f'''{app_bar(cfg.get("remaining_text") or "无限畅享占卜")}
<div style="position:absolute;top:92px;left:0;right:0;bottom:0;">
  <div class="title">抽取你的<span style="color:#5B4EB5">第{CN_NUM[nth]}张牌</span></div>
  <div class="sub">{esc(positions[-1])}</div>
  <div style="margin-top:26px">{draw_slots(cfg["cards"])}</div>
  <div class="hint">想象你的问题，保持专注，点击抽取卡牌</div>
</div>
<div class="fan">{fan_cards()}</div>'''
    css = SLOTS_CSS + """
body { width:390px; height:585px; }
.phone { width:390px; height:585px; position:relative; overflow:hidden;
  background:linear-gradient(135deg,#FAF3FF 0%,#FFFFFF 100%); }
.title { text-align:center; font-size:26px; font-weight:500; color:#000; margin-top:14px; }
.sub { text-align:center; font-size:26px; font-weight:500; color:#000; margin-top:10px; }
.hint { text-align:center; font-size:16px; color:#555; margin-top:22px; }
.slotimg { width:74px; height:130px; border-radius:6px; object-fit:cover; display:block;
  box-shadow:0 2px 6px rgba(0,0,0,.18); }
.slotimg.rev { transform:rotate(180deg); }
.fan { position:absolute; inset:0; }
.fancard { position:absolute; width:120px; height:210px; border-radius:8px; object-fit:cover;
  box-shadow:0 2px 6px rgba(0,0,0,.25); transform-origin:0 210px; }
"""
    return page_html(cfg, body, css), SW, SH


# ── 4. 牌阵选择页 spread（浅色流程页）─────────────────────
def spread_html(cfg: dict) -> tuple[str, int, int]:
    positions = cfg.get("positions") or [c["position"] for c in cfg["cards"]]
    body = f'''{app_bar(cfg.get("remaining_text") or "无限畅享占卜")}
<div style="position:absolute;top:96px;left:0;right:0;bottom:0;display:flex;flex-direction:column;align-items:center;">
  <img class="bigavatar" src="{uri("assets/luna_avatar.png")}">
  <div class="reason">{esc(cfg.get("spread_reason") or '点击“开始抽牌”，让我们一起探索吧！')}</div>
  <div class="sname">{esc(cfg.get("spread_name") or "我-对方-我们牌阵")}</div>
  <div style="margin:14px 0 0">{spread_slots(positions)}</div>
  <div class="drawbtn">开始抽牌</div>
  <div class="switch">切换牌阵</div>
</div>'''
    css = SLOTS_CSS + """
body { width:390px; height:585px; }
.phone { width:390px; height:585px; position:relative; overflow:hidden;
  background:linear-gradient(135deg,#FAF3FF 0%,#FFFFFF 100%); }
.bigavatar { width:88px; height:88px; border-radius:50%; object-fit:cover; background:#FFF;
  border:3px solid #FFF; box-shadow:0 2px 8px rgba(0,0,0,.08); margin-top:4px; }
.reason { width:321px; font-size:16px; color:rgba(0,0,0,.62); line-height:1.57; margin-top:14px; }
.sname { font-size:22px; color:rgba(0,0,0,.67); margin-top:14px; }
.drawbtn { position:absolute; left:16px; right:16px; bottom:64px; height:48px; background:#B0A5E1;
  border-radius:20px; display:flex; align-items:center; justify-content:center;
  color:#FFF; font-size:16px; font-weight:500; }
.switch { position:absolute; bottom:26px; left:0; right:0; text-align:center;
  font-size:16px; color:#717375; }
"""
    return page_html(cfg, body, css), SW, SH


# ── 5. 牌阵选择结果页 spread_result（深色沉浸页）──────────
def spread_result_html(cfg: dict) -> tuple[str, int, int]:
    positions = cfg.get("positions") or [c["position"] for c in cfg["cards"]]
    body = f'''<div class="dappbar">{TB_BACK.replace('stroke="#1A143D"', 'stroke="#FFF"')}
      <div class="dchip">占卜剩余：3次</div><div style="width:44px"></div></div>
<div style="position:absolute;top:118px;left:27px;right:27px;bottom:0;display:flex;flex-direction:column;align-items:center;">
  <img class="davatar" src="{uri("assets/luna_avatar.png")}">
  <div class="dreason">{esc(cfg.get("spread_reason") or '点击“开始抽牌”，让我们一起探索吧！')}</div>
  <div class="dname">{esc(cfg.get("spread_name") or "我-对方-我们牌阵")}</div>
  <div style="margin:14px 0 0">{spread_slots(positions)}</div>
  <div class="glowbtn">开始抽牌</div>
  <div class="dswitch">切换牌阵</div>
</div>'''
    css = SLOTS_CSS + """
body { width:390px; height:585px; }
.phone { width:390px; height:585px; position:relative; overflow:hidden;
  background:radial-gradient(120% 90% at 50% 0%, #241D4E 0%, #0F0C24 62%); }
.dappbar { position:absolute; top:44px; left:0; right:0; height:44px; display:flex;
  align-items:center; justify-content:space-between; padding:0 16px; }
.dchip { border:.5px solid rgba(131,112,255,.5); border-radius:20px; padding:5px 20px;
  color:#8370FF; font-size:12px; }
.davatar { width:80px; height:80px; border-radius:50%; object-fit:cover; background:#8F8FCC;
  border:3px solid rgba(255,255,255,.85); }
.dreason { width:321px; font-size:14px; color:#CAC7DB; line-height:1.57; margin-top:14px; }
.dname { font-size:22px; font-weight:500; color:#FFF; margin-top:14px; text-align:center; }
.slot { border:1.5px dashed rgba(131,112,255,.55); background:rgba(131,112,255,.08); }
.slotname { color:rgba(255,255,255,.6); }
.glowbtn { position:absolute; left:16px; right:16px; bottom:64px; height:48px; border-radius:24px;
  background:linear-gradient(90deg,#9A57FF 0%,#6B84FF 100%); display:flex; align-items:center;
  justify-content:center; color:#FFF; font-size:16px; font-weight:500; }
.dswitch { position:absolute; bottom:26px; left:0; right:0; text-align:center;
  font-size:16px; color:#8370FF; }
"""
    return page_html(cfg, body, css, dark=True), SW, SH


# ── 6. 历史记录页 history ─────────────────────────────────
def history_record(question: str, cards: list, summary: str, time_str: str) -> str:
    thumbs = "".join(
        f'<img class="thumb{" rev" if c.get("reversed") else ""}" src="{uri(c["img"])}">'
        for c in cards
    )
    return f'''<div class="rec">
  <div class="recq">{esc(question)}</div>
  <div class="thumbs">{thumbs}</div>
  <div class="recs">{esc(summary)}</div>
  <div class="recrow"><span class="rectime">{esc(time_str)}</span>
    <span class="recbtn">继续对话 <svg width="6" height="10" viewBox="0 0 6 10"><path d="M1 1l4 4-4 4" stroke="#FFF" stroke-width="1.4" fill="none" stroke-linecap="round"/></svg></span>
  </div>
</div>'''


def history_html(cfg: dict) -> tuple[str, int, int]:
    prev = cfg.get("history_prev") or {}
    pool = [c for c in cfg.get("extra_cards") or []][:3] or cfg["cards"]
    recs = history_record(cfg["question"], cfg["cards"], cfg["interpretation"][0], "刚刚")
    if prev:
        recs += history_record(
            prev.get("question", ""), pool, prev.get("summary", ""), prev.get("time", "3天前")
        )
    body = f'''<div class="happbar">{TB_BACK}
  <div class="tabs"><span class="tab on">占卜历史<div class="tline"></div></span><span class="tab">解梦历史</span></div>
  <div style="width:44px"></div></div>
<div class="list">{recs}</div>'''
    css = """
body { width:390px; height:585px; }
.phone { width:390px; height:585px; position:relative; overflow:hidden;
  background:linear-gradient(135deg,#EFEAFF 4%,#F4EEFF 36%,#FFFDF8 59%,#FFF3D5 96%); }
.happbar { position:absolute; top:44px; left:0; right:0; height:48px; display:flex;
  align-items:center; justify-content:space-between; padding:0 16px; }
.tabs { display:flex; gap:32px; }
.tab { position:relative; font-size:15px; color:rgba(0,0,0,.7); font-weight:500; padding-bottom:6px; }
.tab.on { color:#8B7DDB; font-weight:700; }
.tline { position:absolute; left:50%; transform:translateX(-50%); bottom:0; width:24px; height:4px;
  border-radius:3px; background:#8B7DDB; }
.list { position:absolute; top:96px; left:20px; right:20px; bottom:0; }
.rec { background:rgba(255,255,255,.5); border-radius:20px; padding:20px; margin-bottom:15px; }
.recq { font-size:17px; font-weight:500; color:#000; line-height:1.4; }
.thumbs { display:flex; gap:15px; margin-top:16px; height:79px; }
.thumb { width:45px; height:79px; border-radius:5px; object-fit:cover;
  box-shadow:0 2px 4px rgba(0,0,0,.1); }
.thumb.rev { transform:rotate(180deg); }
.recs { font-size:14px; color:#000; line-height:1.4; margin-top:16px; display:-webkit-box;
  -webkit-line-clamp:4; -webkit-box-orient:vertical; overflow:hidden; }
.recrow { display:flex; justify-content:space-between; align-items:center; margin-top:16px; }
.rectime { font-size:11px; color:#000; }
.recbtn { height:26px; padding:0 10px; border-radius:10px; display:inline-flex; align-items:center;
  gap:4px; background:linear-gradient(90deg,#C19AFF,#E6B6EA); color:#FFF; font-size:11px; }
"""
    return page_html(cfg, body, css), SW, SH


PAGES = {
    "reading": reading_html,
    "shuffle": shuffle_html,
    "draw": draw_html,
    "spread": spread_html,
    "spread_result": spread_result_html,
    "history": history_html,
}


# ── 渲染 / 合成 ───────────────────────────────────────────
def shoot(html_text: str, w: int, h: int, target: pathlib.Path) -> None:
    preview = BASE / "out" / f"_preview_{target.stem}.html"
    preview.write_text(html_text, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=DPR)
        page.goto(preview.as_uri())
        page.wait_for_timeout(600)
        page.screenshot(path=str(target))
        b.close()
    print(f"[shot] {target.name} ({w * DPR}×{h * DPR})")


def shot_cell(src: pathlib.Path, bw: bool = False) -> Image.Image:
    """截图 →（可选黑白）→ 顶部对齐裁 2:3 → 单格尺寸。"""
    im = Image.open(src)
    if bw:
        im = ImageOps.autocontrast(im.convert("L"), cutoff=2)
        im = ImageEnhance.Contrast(im).enhance(1.18)
    im = im.convert("RGB")
    crop_h = int(im.width * CELL_H / CELL_W)
    im = im.crop((0, 0, im.width, min(crop_h, im.height)))
    return im.resize((CELL_W, CELL_H), Image.LANCZOS)


def photo_cell(src: pathlib.Path) -> Image.Image:
    im = Image.open(src).convert("RGB")
    w, h = im.size
    target_w = int(h * CELL_W / CELL_H)
    left = (w - target_w) // 2
    return im.crop((left, 0, left + target_w, h)).resize((CELL_W, CELL_H), Image.LANCZOS)


def main() -> None:
    cfg_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "content.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    out = BASE / "out"
    out.mkdir(exist_ok=True)
    shots = BASE / "assets" / "shots"
    shots.mkdir(exist_ok=True)

    page_names = cfg.get("pages") or ["reading", "shuffle"]
    if len(page_names) != 2 or any(p not in PAGES for p in page_names):
        raise SystemExit(f"pages 必须是 2 个，可选：{'/'.join(PAGES)}")
    bw = bool(cfg.get("bw"))

    cells = []
    for name in page_names:
        html_text, w, h = PAGES[name](cfg)
        png = shots / f"{name}.png"
        shoot(html_text, w, h, png)
        cells.append(shot_cell(png, bw=bw))
    cells.append(photo_cell(BASE / cfg["photo_bl"]))
    cells.append(photo_cell(BASE / cfg["photo_br"]))

    grid = Image.new("RGB", (CELL_W * 2, CELL_H * 2))
    grid.paste(cells[0], (0, 0))
    grid.paste(cells[1], (CELL_W, 0))
    grid.paste(cells[2], (0, CELL_H))
    grid.paste(cells[3], (CELL_W, CELL_H))
    target = out / "情侣四宫格.png"
    grid.save(target)
    if cfg.get("caption"):
        (out / "发布文案.txt").write_text(cfg["caption"], encoding="utf-8")
    print(f"[done] {target} ({grid.width}×{grid.height}) pages={page_names} bw={bw}")


if __name__ == "__main__":
    main()

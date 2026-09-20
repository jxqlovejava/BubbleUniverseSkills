#!/usr/bin/env python3
"""微信聊天 + 塔罗气泡解读 双拼抖音图文渲染。

左半：微信聊天界面（背景/头像/消息全部由 content.json 驱动，背景可随意换）。
右半：塔罗气泡App 解读屏（样式取自 TarotBubble Flutter 源码 tarot_chat_history_screen.dart：
浅色渐变底 + 顶部白色半透问题卡 + 三牌位 + Luna 头像解读卡 + 底部追问输入框）。

用法：python3 render_wechat_tarot.py [content.json]
输出：out/微信聊天塔罗_双拼.png（1560×1688，DPR2）
"""
import html
import json
import pathlib
import re
import sys

from playwright.sync_api import sync_playwright

BASE = pathlib.Path(__file__).parent          # scripts/
SKILL = BASE.parent                            # skill 根（含 assets/）
CONTENT_DIR = SKILL                            # main() 里改为 content.json 所在目录
PW, PH = 390, 844  # 单屏逻辑尺寸（iPhone 14）
DPR = 2
FONT = "'PingFang SC','Hiragino Sans GB',sans-serif"

# ── SVG 图标（内联，避免外部资源）──────────────────────────────
def status_icons(dark: bool) -> str:
    c = "#000" if dark else "#FFF"
    return f'''<svg width="76" height="14" viewBox="0 0 76 14" fill="{c}">
<rect x="0" y="9" width="3" height="5" rx="1"/><rect x="5" y="7" width="3" height="7" rx="1"/>
<rect x="10" y="4.5" width="3" height="9.5" rx="1"/><rect x="15" y="2" width="3" height="12" rx="1"/>
<path d="M28 6.2a9 9 0 0 1 12 0l-1.7 1.8a7 7 0 0 0-8.6 0z"/>
<path d="M30.4 9a5.5 5.5 0 0 1 7.2 0l-1.7 1.8a3.6 3.6 0 0 0-3.8 0z"/><circle cx="34" cy="12" r="1.4"/>
<rect x="50" y="2.5" width="20" height="9" rx="2.8" fill="none" stroke="{c}" stroke-opacity=".45" stroke-width="1"/>
<rect x="52" y="4.5" width="12.5" height="5" rx="1.2"/>
<path d="M71.5 5.2v3.6a2 2 0 0 0 0-3.6z" fill-opacity=".5"/></svg>'''

BACK_CHEVRON = '<svg width="11" height="19" viewBox="0 0 11 19" fill="none"><path d="M9 1.5 1.7 9.2 9 17.5" stroke="#000" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
TB_BACK = '<svg width="10" height="18" viewBox="0 0 10 18" fill="none"><path d="M8.6 1.4 1.4 9l7.2 7.6" stroke="#1A143D" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>'
ICON_C = "#1A1A1A"
MORE = '<svg width="24" height="11" viewBox="0 0 24 11"><g fill="' + ICON_C + '"><circle cx="3.7" cy="5.5" r="1.85"/><circle cx="12" cy="5.5" r="1.85"/><circle cx="20.3" cy="5.5" r="1.85"/></g></svg>'
# 语音：圆圈内「扬声器+两股声波」（对照真实微信/参考图，非话筒）
VOICE = ('<svg width="25" height="25" viewBox="0 0 25 25" fill="none">'
         '<circle cx="12.5" cy="12.5" r="10.7" stroke="' + ICON_C + '" stroke-width="1.7"/>'
         '<path d="M7.4 9.9h1.8l3.3-2.6v9.4L9.2 14.1H7.4z" fill="' + ICON_C + '"/>'
         '<path d="M13.9 9.3a4.6 4.6 0 0 1 0 5.4" stroke="' + ICON_C + '" stroke-width="1.7" stroke-linecap="round"/>'
         '<path d="M15.9 7.4a7.6 7.6 0 0 1 0 9.2" stroke="' + ICON_C + '" stroke-width="1.7" stroke-linecap="round"/></svg>')
# 微笑：圆圈内「两眼点+宽开口弧嘴」（标准 emoji 笑脸）
EMOJI = ('<svg width="25" height="25" viewBox="0 0 25 25" fill="none">'
         '<circle cx="12.5" cy="12.5" r="10.2" stroke="' + ICON_C + '" stroke-width="1.7"/>'
         '<circle cx="9.3" cy="10" r="1.25" fill="' + ICON_C + '"/>'
         '<circle cx="15.7" cy="10" r="1.25" fill="' + ICON_C + '"/>'
         '<path d="M7.9 12.9a5.3 5.3 0 0 0 9.2 0" stroke="' + ICON_C + '" stroke-width="1.8" fill="none" stroke-linecap="round"/></svg>')
PLUS = '<svg width="25" height="25" viewBox="0 0 25 25" fill="none" stroke="' + ICON_C + '" stroke-width="1.7" stroke-linecap="round"><circle cx="12.5" cy="12.5" r="10.2"/><path d="M12.5 8.4v8.2M8.4 12.5h8.2"/></svg>'
SEND = '<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><circle cx="11" cy="11" r="10" fill="#B0A5E1"/><path d="M6.5 11.2 9.6 14.3 15.5 8" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def md_block(s: str) -> str:
    """解读块 markdown 内联渲染（与 App 的 MarkdownInterpretationView 对齐）：**加粗** + 换行。"""
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", esc(s))
    return out.replace("\n", "<br>")


def uri(rel: str) -> str:
    """素材解析：content.json 所在目录优先（实例可放自有 assets 覆盖默认），skill assets 兜底。"""
    for base in (CONTENT_DIR, SKILL):
        p = base / rel
        if p.exists():
            return p.as_uri()
    print(f"[warn] 缺图: {rel}")
    return ""


# ── 微信聊天面板 ─────────────────────────────────────────────
def wx_msg(m: dict, cfg: dict) -> str:
    me = m["from"] == "me"
    av = uri(cfg["me_avatar"] if me else cfg["ta_avatar"])
    if m["type"] == "sticker":
        body = f'<img class="wx-sticker" src="{uri(m["src"])}">'
        cls = "wx-msg sticker"
    else:
        body = f'<div class="wx-bubble">{esc(m["text"])}</div>'
        cls = "wx-msg"
    avatar = f'<img class="wx-avatar" src="{av}">'
    inner = body + avatar if me else avatar + body
    return f'<div class="{cls} {"me" if me else "ta"}">{inner}</div>'


def wx_panel(cfg: dict) -> str:
    msgs = "\n".join(wx_msg(m, cfg) for m in cfg["messages"])
    return f'''
<div class="phone wx">
  <img class="wx-bg" src="{uri(cfg["background"])}">
  <div class="wx-status"><span>{esc(cfg["time"])}</span>{status_icons(False)}</div>
  <div class="wx-nav">
    <div class="wx-back">{BACK_CHEVRON}<span class="wx-badge">{esc(cfg["unread"])}</span></div>
    <div class="wx-title">{esc(cfg["contact_name"])}</div>
    <div class="wx-more">{MORE}</div>
  </div>
  <div class="wx-chat">{msgs}</div>
  <div class="wx-inputbar">{VOICE}<div class="wx-field"></div>{EMOJI}{PLUS}</div>
</div>'''


# ── 塔罗气泡解读面板 ─────────────────────────────────────────
def tb_card(c: dict) -> str:
    rev = " rev" if c.get("reversed") else ""
    return f'''<div class="tb-card">
      <img class="tb-cardimg{rev}" src="{uri(c["img"])}">
      <div class="tb-cname">{esc(c["name"])}</div>
      <div class="tb-cpos">{esc(c["position"])}</div>
    </div>'''


def tb_panel(cfg: dict) -> str:
    cards = "\n".join(tb_card(c) for c in cfg["cards"])
    paras = "\n".join(f'<div class="tb-para">{md_block(p)}</div>' for p in cfg["interpretation"])
    return f'''
<div class="phone tb">
  <div class="tb-status"><span>{esc(cfg["time"])}</span>{status_icons(True)}
    <div class="tb-plate"><img src="{uri("assets/app_icon.png")}"><span>塔罗气泡</span></div></div>
  <div class="tb-appbar">{TB_BACK}<div class="tb-chip">{esc(cfg["remaining_text"])}</div><div class="tb-more"></div></div>
  <div class="tb-topcard">
    <div class="tb-q">{esc(cfg["question"])}</div>
    <div class="tb-cards">{cards}</div>
  </div>
  <div class="tb-luna">
    <div class="tb-luna-head"><img src="{uri("assets/luna_avatar.png")}"><span>Luna</span></div>
    {paras}
    <div class="tb-ai">{esc(cfg["ai_label"])}</div>
  </div>
  <div class="tb-inputbar"><span class="tb-hint">{esc(cfg["followup_hint"])}</span>{SEND}</div>
</div>'''


CSS = f"""
* {{ margin:0; padding:0; box-sizing:border-box; font-family:{FONT}; }}
body {{ width:{PW*2}px; height:{PH}px; display:flex; background:#000; }}
.phone {{ width:{PW}px; height:{PH}px; position:relative; overflow:hidden; flex-shrink:0; }}

/* ── 微信 ── */
.wx {{ background:#0B0B0D; }}
.wx-bg {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }}
.wx-status {{ position:absolute; top:0; left:0; right:0; height:44px; display:flex; align-items:center;
  justify-content:space-between; padding:0 24px 0 28px; color:#FFF; font-size:15px; font-weight:600;
  background:rgba(247,247,247,.94); z-index:3; }}
.wx-status span {{ color:#111; }}
.wx-status svg {{ filter:invert(1); }}
.wx-nav {{ position:absolute; top:44px; left:0; right:0; height:48px; background:rgba(247,247,247,.94);
  display:flex; align-items:center; justify-content:space-between; padding:0 14px; z-index:3; }}
.wx-back {{ display:flex; align-items:center; gap:7px; width:70px; }}
.wx-badge {{ width:20px; height:20px; border-radius:50%; background:#C8C8CD; color:#111;
  font-size:11.5px; display:flex; align-items:center; justify-content:center; font-weight:500; }}
.wx-title {{ font-size:16.5px; font-weight:600; color:#111; letter-spacing:.3px; }}
.wx-more {{ width:70px; display:flex; align-items:center; justify-content:flex-end; }}
.wx-chat {{ position:absolute; top:92px; bottom:56px; left:0; right:0; padding:14px 12px;
  display:flex; flex-direction:column; gap:15px; z-index:2; }}
.wx-msg {{ display:flex; align-items:flex-start; gap:8px; }}
.wx-msg.me {{ justify-content:flex-end; }}
.wx-avatar {{ width:40px; height:40px; border-radius:6px; object-fit:cover; background:#FFF; flex-shrink:0; }}
.wx-bubble {{ max-width:248px; padding:10px 12px; border-radius:7px; font-size:16px; line-height:1.42;
  color:#111; position:relative; word-break:break-all; }}
.me .wx-bubble {{ background:#95EC69; }}
.ta .wx-bubble {{ background:#FFF; }}
.me .wx-bubble::after {{ content:""; position:absolute; right:-5px; top:14px; width:10px; height:10px;
  background:#95EC69; clip-path:polygon(0 0, 100% 50%, 0 100%); }}
.ta .wx-bubble::after {{ content:""; position:absolute; left:-5px; top:14px; width:10px; height:10px;
  background:#FFF; clip-path:polygon(100% 0, 0 50%, 100% 100%); }}
.wx-msg.sticker .wx-sticker {{ width:118px; display:block; filter:drop-shadow(0 2px 4px rgba(0,0,0,.25)); }}
.wx-inputbar {{ position:absolute; bottom:0; left:0; right:0; height:56px; background:#F7F7F7;
  border-top:.5px solid #D8D8D8; display:flex; align-items:center; gap:10px; padding:0 12px; z-index:3; }}
.wx-field {{ flex:1; height:38px; background:#FFF; border-radius:7px; }}

/* ── 塔罗气泡 ── */
.tb {{ background:linear-gradient(150deg,#FAF3FF 0%,#FDFAFF 35%,#FFFFFF 70%); }}
.tb-status {{ position:absolute; top:0; left:0; right:0; height:44px; display:flex; align-items:center;
  justify-content:space-between; padding:0 24px 0 28px; color:#000; font-size:15px; font-weight:600; z-index:3; }}
.tb-appbar {{ position:absolute; top:44px; left:0; right:0; height:48px; display:flex; align-items:center;
  justify-content:space-between; padding:0 16px; z-index:3; }}
.tb-appbar .tb-more {{ width:10px; }}
/* 状态栏内居中品牌铭牌（参考 quin 状态栏胶囊，与塔罗解读截图模板 .brand 一致） */
.tb-plate {{ position:absolute; left:50%; top:50%; transform:translate(-50%,-50%);
  display:flex; align-items:center; gap:5px; background:#FFF; border-radius:10px;
  padding:4px 10px; box-shadow:0 1px 4px rgba(0,0,0,.08); }}
.tb-plate img {{ width:18px; height:18px; border-radius:4px; display:block; }}
.tb-plate span {{ font-size:15px; font-weight:600; color:#1A143D; letter-spacing:.5px; }}
.tb-chip {{ border:.5px solid #5B4DBC; border-radius:10px; padding:4px 18px; color:#5B4DBC; font-size:13px; }}
.tb-topcard {{ position:absolute; top:92px; left:0; right:0; background:rgba(255,255,255,.55);
  border-radius:0 0 20px 20px; padding:14px 16px 18px; z-index:2; }}
.tb-q {{ font-size:20px; font-weight:500; color:#000; text-align:center; margin:4px 24px 16px; }}
.tb-cards {{ display:flex; justify-content:space-evenly; }}
.tb-card {{ width:74px; text-align:center; }}
.tb-cardimg {{ width:74px; height:130px; border-radius:5px; object-fit:cover; display:block; }}
.tb-cardimg.rev {{ transform:rotate(180deg); }}
.tb-cname {{ font-size:13px; color:#000; margin-top:8px; }}
.tb-cpos {{ font-size:11px; color:rgba(0,0,0,.55); margin-top:2px; }}
.tb-luna {{ position:absolute; top:328px; left:0; right:0; bottom:0; padding:14px 19px; z-index:1; }}
.tb-luna-head {{ display:flex; align-items:center; gap:11px; margin-bottom:9px; }}
.tb-luna-head img {{ width:35px; height:35px; border-radius:50%; object-fit:cover; background:#FFF; }}
.tb-luna-head span {{ font-size:17px; font-weight:500; color:#000; }}
.tb-para {{ background:rgba(255,255,255,.7); border:.5px solid rgba(91,77,188,.15); border-radius:16px;
  padding:13px 15px; font-size:15px; line-height:1.7; color:#111; margin-bottom:10px; }}
.tb-para b {{ font-weight:600; }}
.tb-ai {{ display:inline-block; background:rgba(255,255,255,.5); border:.5px solid rgba(91,77,188,.3);
  border-radius:12px; padding:3px 9px; font-size:11px; color:rgba(0,0,0,.45); }}
.tb-inputbar {{ position:absolute; bottom:14px; left:16px; right:16px; height:50px; z-index:4;
  background:rgba(255,255,255,.78); border:.5px solid rgba(98,42,159,.24); border-radius:25px;
  display:flex; align-items:center; justify-content:space-between; padding:0 18px; }}
.tb-hint {{ font-size:14px; color:rgba(0,0,0,.5); }}
"""


def build_html(data: dict) -> str:
    return f'''<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<style>{CSS}</style></head>
<body>{wx_panel(data["wechat"])}{tb_panel(data["tarot"])}</body></html>'''


def main() -> None:
    global CONTENT_DIR
    cfg_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else SKILL / "content.json"
    cfg_path = cfg_path.resolve()
    CONTENT_DIR = cfg_path.parent
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    if CONTENT_DIR.name == ".src":
        # 清爽布局：成品直接落在实例顶层，预览 HTML 留在 .src 里
        out = CONTENT_DIR
        target = CONTENT_DIR.parent / "微信聊天塔罗_双拼.png"
    else:  # 旧布局兼容：out/ 子目录
        out = CONTENT_DIR / "out"
        out.mkdir(exist_ok=True)
        target = out / "微信聊天塔罗_双拼.png"
    html_path = out / "_preview.html"
    html_path.write_text(build_html(data), encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": PW * 2, "height": PH}, device_scale_factor=DPR)
        page.goto(html_path.as_uri())
        page.wait_for_timeout(600)
        page.screenshot(path=str(target))
        b.close()
    print(f"[done] {target} ({PW*2*DPR}×{PH*DPR})")


if __name__ == "__main__":
    main()

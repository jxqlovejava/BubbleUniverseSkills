#!/usr/bin/env python3
"""塔罗问题清单帖 · 渲染脚本：content.json → 封面 + 分页清单截图（备忘录风）。

封面仿 iOS 备忘录（白底点阵 + 黄色 Notes 导航 + 手札体大标题）；
正文仿备忘录截图（状态栏 + 工具栏 + 日期/字数行 + 受众分组清单，问题连续编号）。

用法：
    python3 render_question_list.py <数据目录>
输出（数据目录根）：01_封面.png + 02.png…（695×1489）；out/ 留 html 中间件。
"""
import html
import json
import pathlib
import sys
from datetime import datetime

from playwright.sync_api import sync_playwright

W, H, DPR = 695, 1489, 1  # 用户指定输出尺寸
NOTES_YELLOW = "#D9A514"
HAND_FONT = "'Hannotate SC','手札体-简','Hanzipen SC','翩翩体-简',sans-serif"
BODY_FONT = "'PingFang SC',sans-serif"


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


# ---------- SVG 图标（描边风，仿 iOS/便签工具栏） ----------
def svg(paths: str, size: int = 22, color: str = "#000", sw: float = 1.8) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="{sw}" stroke-linecap="round" '
            f'stroke-linejoin="round">{paths}</svg>')


IC_BACK = svg('<path d="M15 5l-7 7 7 7"/>', 26)
IC_UNDO = svg('<path d="M9 14L4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/>', 24)
IC_REDO_OFF = svg('<path d="M15 14l5-5-5-5"/><path d="M20 9H10a6 6 0 0 0 0 12h3"/>', 24, "#c7c7c7")
IC_SHARE = svg('<path d="M12 3v12"/><path d="M7 7l5-4 5 4"/><path d="M5 11v9h14v-9"/>', 24)
IC_MORE_V = svg('<circle cx="12" cy="5" r="1.4" fill="#000" stroke="none"/>'
                '<circle cx="12" cy="12" r="1.4" fill="#000" stroke="none"/>'
                '<circle cx="12" cy="19" r="1.4" fill="#000" stroke="none"/>', 22)
IC_SHARE_Y = svg('<path d="M12 3v12"/><path d="M7 7l5-4 5 4"/><path d="M5 11v9h14v-9"/>',
                 26, NOTES_YELLOW)
IC_MORE_CIRCLE_Y = svg(
    '<circle cx="12" cy="12" r="9"/>'
    '<circle cx="8" cy="12" r="1.2" fill="%s" stroke="none"/>'
    '<circle cx="12" cy="12" r="1.2" fill="%s" stroke="none"/>'
    '<circle cx="16" cy="12" r="1.2" fill="%s" stroke="none"/>' % ((NOTES_YELLOW,) * 3),
    26, NOTES_YELLOW)
# 底部编辑栏图标（仿便签输入工具栏）
IC_BRUSH = svg('<path d="M4 20l1-4L16 5l3 3L8 19l-4 1z"/><path d="M13 8l3 3"/>', 24, "#8a8a8a")
IC_CHECK_C = svg('<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.5 2.5L16 9.5"/>', 24, "#8a8a8a")
IC_MIC = svg('<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0"/>'
             '<path d="M12 18v3"/>', 24, "#8a8a8a")
IC_PLUS_C = svg('<circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/>', 24, "#8a8a8a")


def status_bar(now: datetime) -> str:
    """正文页手机状态栏：左时间，右信号/wifi/电池。"""
    t = now.strftime("%-H:%M")
    return f"""
<div class="statusbar">
  <span class="sb-time">{t}</span>
  <span class="sb-icons">
    <svg width="20" height="12" viewBox="0 0 20 12"><rect x="0" y="7" width="3" height="5" rx="0.8"/><rect x="5" y="5" width="3" height="7" rx="0.8"/><rect x="10" y="2.5" width="3" height="9.5" rx="0.8"/><rect x="15" y="0" width="3" height="12" rx="0.8"/></svg>
    <svg width="18" height="12" viewBox="0 0 18 12" fill="none" stroke="#000" stroke-width="1.6" stroke-linecap="round"><path d="M1.5 4.5a10 10 0 0 1 15 0"/><path d="M4.2 7.2a6.6 6.6 0 0 1 9.6 0"/><circle cx="9" cy="10" r="1.3" fill="#000" stroke="none"/></svg>
    <svg width="27" height="13" viewBox="0 0 27 13" fill="none"><rect x="0.5" y="0.5" width="22" height="12" rx="3.5" stroke="#000" opacity=".45"/><rect x="2.5" y="2.5" width="16" height="8" rx="1.8" fill="#000"/><path d="M25 4.5v4a2.2 2.2 0 0 0 0-4z" fill="#000" opacity=".45"/></svg>
  </span>
</div>"""


def toolbar() -> str:
    return f"""
<div class="toolbar">
  {IC_BACK}
  <span class="tb-right">{IC_UNDO}{IC_REDO_OFF}{IC_SHARE}{IC_MORE_V}</span>
</div>"""


def editbar() -> str:
    """底部编辑工具栏（仿便签截图）。"""
    return f"""
<div class="editbar">
  {IC_BRUSH}{IC_CHECK_C}{IC_MIC}<span class="eb-flex"></span>{IC_PLUS_C}
</div>"""


CTA_TEXT = "以上问题都可以在塔罗气泡App免费测算"


def cta() -> str:
    """底部居中品牌引流条（每页都有，在内容区与编辑栏之间）。"""
    return f'<div class="cta">✦ {CTA_TEXT} ✦</div>'


def cover_html(data: dict) -> str:
    title = esc(data.get("title", "100个塔罗牌问题清单"))
    # 长标题在「问题清单」前换行（仿参考图两行排版）；不含该词则单行
    if "问题清单" in title and not title.startswith("问题清单"):
        title = title.replace("问题清单", "\n问题清单", 1)
    title_html = title.replace("\n", "<br>")
    return f"""
<section class="sheet cover-sheet">
  <div class="c-nav">
    <span class="c-back">{svg('<path d="M15 5l-7 7 7 7"/>', 22, NOTES_YELLOW, 2.2)} Notes</span>
    <span class="c-actions">{IC_SHARE_Y}{IC_MORE_CIRCLE_Y}</span>
  </div>
  <div class="c-title">{title_html}</div>
</section>"""


def body_units(data: dict) -> str:
    """隐藏测量池：每组 = [组头+首问] 单元 + 其余问题单元（防组头孤行）。问题跨组连续编号。"""
    units: list[str] = []
    n = 0
    for gi, g in enumerate(data.get("groups", []), 1):
        qs = g.get("questions") or []
        if not qs:
            continue
        n += 1
        units.append(
            f'<div class="unit"><p class="ghead">{gi}.{esc(g["name"])}</p>'
            f'<p class="q">{n}. {esc(qs[0])}</p></div>')
        for q in qs[1:]:
            n += 1
            units.append(f'<div class="unit"><p class="q">{n}. {esc(q)}</p></div>')
    return "".join(units)


def build_html(data: dict) -> str:
    now = datetime.now()
    total_chars = sum(len(q) for g in data.get("groups", []) for q in g.get("questions", []))
    date_line = (f"{now.year}/{now.month}/{now.day} {now.strftime('%H:%M')}"
                 f"  |  {total_chars}字  |  默认笔记本")
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#666}}
.sheet{{width:{W}px;height:{H}px;background:#fff;position:relative;overflow:hidden;
  font-family:{BODY_FONT};color:#1a1a1a;margin:0 auto 20px}}

/* ---- 封面：iOS 备忘录白底点阵 + 手写体标题 ---- */
.cover-sheet{{background-image:radial-gradient(circle,#dcdcdc 1.6px,transparent 1.7px);
  background-size:30px 30px;background-position:14px 60px}}
.c-nav{{display:flex;justify-content:space-between;align-items:center;padding:22px 26px}}
.c-back{{display:flex;align-items:center;gap:2px;color:{NOTES_YELLOW};font-size:21px;font-weight:500}}
.c-actions{{display:flex;align-items:center;gap:18px}}
.c-title{{font-family:{HAND_FONT};font-size:88px;line-height:1.6;color:#111;
  margin:33vh 0 0 66px;letter-spacing:2px}}

/* ---- 正文：备忘录截图 chrome ---- */
.body-sheet{{display:flex;flex-direction:column}}
.statusbar{{flex:none;display:flex;justify-content:space-between;align-items:center;
  padding:14px 28px 6px}}
.sb-time{{font-size:15px;font-weight:600}}
.sb-icons{{display:flex;align-items:center;gap:6px}}
.toolbar{{flex:none;display:flex;justify-content:space-between;align-items:center;
  padding:8px 24px 10px;border-bottom:.5px solid #f0f0f0}}
.tb-right{{display:flex;align-items:center;gap:26px}}
.dateline{{font-size:12.5px;color:#9a9a9a;padding:16px 50px 0}}
.doc-title{{font-size:30px;font-weight:700;padding:16px 50px 0}}
.page-content{{flex:1;overflow:hidden;padding:26px 50px 0}}
/* 间距全走 padding（offsetHeight 不含 margin，JS 分页量不准会裁底行） */
/* 问题为图文主体：28px 大字号 + 宽间距（单问行高≈75px，对齐爆款清单帖参考图） */
.ghead{{font-size:28px;font-weight:700;padding:34px 0 16px}}
.q{{font-size:28px;line-height:1.45;padding-bottom:34px;color:#1a1a1a}}
.editbar{{flex:none;display:flex;align-items:center;gap:34px;
  padding:10px 34px 16px;border-top:.5px solid #f0f0f0}}
.cta{{flex:none;text-align:center;font-size:21px;font-weight:600;letter-spacing:1px;
  color:#E8788A;padding:6px 0 46px}}
.eb-flex{{flex:1}}

/* 隐藏测量池：与正文同宽，供 JS 量单元高度 */
#pool{{position:absolute;left:-9999px;top:0;width:{W - 100}px;visibility:hidden}}
#page-anchor{{position:absolute;left:-9999px;top:0;width:{W}px;visibility:hidden}}
</style></head><body>

{cover_html(data)}

<div id="page-anchor">
  {status_bar(now)}
  {toolbar()}
  <div id="first-meta"><div class="dateline">{date_line}</div>
  <div class="doc-title">{esc(data.get("title", ""))}</div></div>
  {cta()}
  {editbar()}
</div>
<div id="pool">{body_units(data)}</div>
<div id="pages"></div>

<script>
const H = {H};
const anchor = document.getElementById('page-anchor');
const chromeH = anchor.querySelector('.statusbar').offsetHeight
              + anchor.querySelector('.toolbar').offsetHeight
              + anchor.querySelector('.cta').offsetHeight
              + anchor.querySelector('.editbar').offsetHeight;
const metaH = document.getElementById('first-meta').offsetHeight + 26; // +page-content padding-top
const units = Array.from(document.querySelectorAll('#pool .unit'));
const heights = units.map(u => u.offsetHeight);
const pagesHost = document.getElementById('pages');
const statusbarHTML = anchor.querySelector('.statusbar').outerHTML;
const toolbarHTML = anchor.querySelector('.toolbar').outerHTML;
const editbarHTML = anchor.querySelector('.editbar').outerHTML;
const ctaHTML = anchor.querySelector('.cta').outerHTML;
const metaHTML = document.getElementById('first-meta').outerHTML;

let pageIdx = 0, used = 0, contentEl = null;
function newPage() {{
  const sheet = document.createElement('section');
  sheet.className = 'sheet body-sheet';
  sheet.innerHTML = statusbarHTML + toolbarHTML
    + (pageIdx === 0 ? metaHTML : '')
    + '<div class="page-content"></div>' + ctaHTML + editbarHTML;
  pagesHost.appendChild(sheet);
  contentEl = sheet.querySelector('.page-content');
  used = 0;
  pageIdx += 1;
}}
newPage();
units.forEach((u, i) => {{
  const capacity = H - chromeH - (pageIdx === 1 ? metaH : 26) - 24; // 24 = 底部余量
  if (used + heights[i] > capacity && used > 0) newPage();
  contentEl.appendChild(u.cloneNode(true));
  used += heights[i];
}});
</script>
</body></html>"""


def render(data_dir: pathlib.Path) -> None:
    data = json.loads((data_dir / "content.json").read_text(encoding="utf-8"))
    if data.get("type") != "question_list":
        sys.exit("content.json 缺少 type=question_list（非清单帖数据）")
    out_dir = data_dir / "out"
    out_dir.mkdir(exist_ok=True)
    for stale in list(data_dir.glob("0*.png")) + list(out_dir.glob("*.png")):
        stale.unlink()
    h = out_dir / f"{data_dir.name}.html"
    h.write_text(build_html(data), encoding="utf-8")

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=DPR)
        pg.goto(h.resolve().as_uri())
        pg.wait_for_timeout(600)
        n = pg.locator(".sheet").count()
        fnames = ["01_封面"] + [f"{i + 2:02d}" for i in range(n - 1)]
        for i in range(n):
            pg.locator(".sheet").nth(i).screenshot(path=str(data_dir / f"{fnames[i]}.png"))
        b.close()
    print(f"{data_dir.name}: 封面 + {n - 1} 页清单 -> {data_dir}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit("用法: python3 render_question_list.py <数据目录>")
    render(pathlib.Path(args[0]))

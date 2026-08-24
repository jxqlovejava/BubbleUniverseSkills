#!/usr/bin/env python3
"""路线 B 封面合成：HTML/CSS 拼格 + Playwright 渲染 3:4 封面 PNG。

输入：问题标题 + 每格 {img 分格图路径, label 壹贰叁, mood_color} + grid 数。
输出：1728×2304 PNG。宫格数 100% 确定，标签确定性叠字。
用法：
    python3 render_cover.py "<问题>" '<cells_json>' <grid> <out_png>
"""
import argparse, json, pathlib
from playwright.sync_api import sync_playwright

W_LOGICAL, DPR = 432, 4.0        # 逻辑宽 432 → 输出宽 1728
H_LOGICAL = int(W_LOGICAL * 4 / 3)   # 3:4 → 576


def _cell_div(c: dict) -> str:
    """单格 HTML。img 为空（分格图生成失败）时不输出 <img>，避免 src="file://" 坏引用触发 broken-image 图标；
    空底 cell 有 background:#F2E6D6 兜底，暗条+标签照叠。"""
    img = f'<img src="file://{c["img"]}">' if c["img"] else ""
    return (f'<div class="cell">{img}<div class="scrim"></div>'
            f'<span class="label">{c["label"]}</span></div>')


def build_cover_html(question: str, cells: list[dict], grid: int) -> str:
    """满版杂志风（对齐参考封面）：图片顶满 3:4 画布，无缝隙/圆角/描边/标题；
    底部渐变暗条 + 左下统一白字标签（暗条保证 OCR 可读）。question 仅保留
    签名兼容——封面不渲染标题，问题由笔记标题承载。"""
    if grid == 4:
        cell_css = "display:grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr;"
    else:
        cell_css = "display:flex; flex-direction:column;"
    cell_items = "\n".join(_cell_div(c) for c in cells)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body {{ margin:0; width:{W_LOGICAL}px; height:{H_LOGICAL}px; background:#F2E6D6;
       font-family:'Yuanti SC','PingFang SC',sans-serif; }}
.cells {{ {cell_css} width:100%; height:100%; }}
.cell {{ position:relative; flex:1; min-height:0; overflow:hidden; background:#F2E6D6; }}
.cell img {{ width:100%; height:100%; object-fit:cover; display:block; }}
.scrim {{ position:absolute; left:0; right:0; bottom:0; height:30%;
          background:linear-gradient(to bottom, rgba(25,15,8,0), rgba(25,15,8,.55)); }}
.label {{ position:absolute; left:16px; bottom:12px; color:#FFFBF5;
          font-size:26px; font-weight:700; letter-spacing:2px;
          text-shadow:0 1px 8px rgba(20,10,5,.5); }}
</style></head><body>
<div class="cells">{cell_items}</div>
</body></html>"""


def render(data_dir: pathlib.Path, question: str, cells: list[dict], grid: int, out_name: str = "封面.png") -> pathlib.Path:
    html = build_cover_html(question, cells, grid)
    h = data_dir / "cover.html"
    h.write_text(html, encoding="utf-8")
    out = data_dir / out_name
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W_LOGICAL, "height": H_LOGICAL}, device_scale_factor=DPR)
        pg.goto(h.resolve().as_uri())
        pg.wait_for_timeout(400)
        pg.screenshot(path=str(out))
        b.close()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question"); ap.add_argument("cells_json"); ap.add_argument("grid", type=int)
    ap.add_argument("out_png")
    args = ap.parse_args()
    cells = json.loads(args.cells_json)
    out = render(pathlib.Path(args.out_png).parent, args.question, cells, args.grid, pathlib.Path(args.out_png).name)
    print(out)


if __name__ == "__main__":
    main()

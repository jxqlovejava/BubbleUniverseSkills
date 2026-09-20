#!/usr/bin/env python3
"""塔罗解读截图模板 · 真实解读生成器。

content.json 里手写 question / sticker / underlines / caption（cards、interpretation、opener 不用写），
本脚本负责：抽牌（我-对方-我们牌阵，--seed 可复现）→ tarot-mass-divination 的 interpret.md
真实提示词生成长解读 → 按问题生成正文开头的软植入句（opener，AI + 固定池兜底）→ 回填
content.json → 调 render_reading_shot.py 渲染 + OCR。

解读很长，截图只展示开头、底部自然截断（真实截图感，不用凑整）。
underlines 短语必须命中解读开头可见部分，否则会 warn 且图上看不到线。

用法：
    python3 gen_reading.py [content.json] [--seed N] [--skip-render]
依赖：LLM_API_KEY（或 DEEPSEEK_API_KEY）环境变量。
"""
import argparse
import json
import pathlib
import random
import re
import shutil
import subprocess
import sys

BASE = pathlib.Path(__file__).parent            # 模板目录（塔罗解读截图模板/）


def find_mass_divination_scripts() -> pathlib.Path:
    """tarot-mass-divination 位置：ip-pipeline 布局（.claude/skills/ 下）/ vira 独立工作区布局（同级目录）。"""
    for c in (BASE.parent / ".claude" / "skills" / "tarot-mass-divination" / "scripts",
              BASE.parent / "tarot-mass-divination" / "scripts"):
        if (c / "generate_mass_divination.py").exists():
            return c
    raise RuntimeError("找不到 tarot-mass-divination/scripts（需要它的 LLM 管线、interpret.md 与牌图）")


GMD_SCRIPTS = find_mass_divination_scripts()
sys.path.insert(0, str(GMD_SCRIPTS))
import generate_mass_divination as gmd  # noqa: E402
import opener  # noqa: E402 - 正文开头软植入句（全项目唯一实现）

SPREAD_NAME = "我-对方-我们牌阵"


def load_spread() -> dict:
    spreads = json.loads((gmd.DATA / "spreads.json").read_text(encoding="utf-8"))
    items = spreads if isinstance(spreads, list) else list(spreads.values())
    return next(s for s in items if s.get("name") == SPREAD_NAME)


def copy_card_imgs(drawn: list[dict]) -> None:
    dst_dir = BASE / "assets" / "cards"
    dst_dir.mkdir(parents=True, exist_ok=True)
    for c in drawn:
        src = gmd.CARD_SRC / pathlib.Path(c["imagePath"]).name
        if src.exists():
            shutil.copy2(src, dst_dir / src.name)
        else:
            print(f"  [warn] 缺牌图: {src.name}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cfg", nargs="?", default=str(BASE / "content.json"), help="content.json 路径")
    ap.add_argument("--seed", type=int, default=None, help="抽牌随机种子（复现用）")
    ap.add_argument("--skip-render", action="store_true", help="只回填 content.json，不渲染")
    args = ap.parse_args()
    rng = random.Random(args.seed)

    cfg_path = pathlib.Path(args.cfg)
    content = json.loads(cfg_path.read_text(encoding="utf-8"))
    question = content.get("question", "").strip()
    if not question:
        raise SystemExit("content.json 缺少 question")

    print(f"问题：{question}")
    print(f"[1/3] 抽牌（{SPREAD_NAME}）...")
    spread = load_spread()
    drawn = gmd.draw_groups(spread, 1, rng)[0]
    copy_card_imgs(drawn)
    cards = [
        {
            "img": "assets/cards/" + pathlib.Path(c["imagePath"]).name,
            "name": c["name"],
            "position": c["position"],
            "reversed": c["direction"] == "REVERSED",
        }
        for c in drawn
    ]
    print("      " + "、".join(f"{c['position']}·{c['name']}({'逆' if c['reversed'] else '正'})" for c in cards))

    print("[2/3] 生成真实解读（interpret.md 管线）...")
    reading = gmd.generate_interpretation(question, spread, drawn)
    blocks = [b.strip() for b in re.split(r"\n\s*-{3,}\s*\n", reading) if b.strip()]

    # 正文开头软植入（AI 按问题生成，失败回退固定池）：标题行后单独一行，用户 2026-09-16 拍板
    content["opener"] = opener.gen_opener(question, llm_call=gmd.llm_call)
    print(f"      正文开头软植入句：{content['opener']}")

    content["cards"] = cards
    content["interpretation"] = blocks
    content["remaining_text"] = "无限畅享占卜"
    cfg_path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n===== 解读（{len(blocks)} 块，截图只展示开头）=====")
    for b in blocks:
        print("  " + b.replace("\n", "\n  ") + "\n  ---")
    print(f"\n[done] 已回填 {cfg_path}")

    if args.skip_render:
        return
    print("[3/3] 渲染 + OCR ...")
    subprocess.run([sys.executable, str(BASE / "render_reading_shot.py"), str(cfg_path)], check=True)
    ocr = GMD_SCRIPTS / "ocr_text.sh"
    if ocr.exists():
        subprocess.run(["bash", str(ocr), str(BASE / "out" / "塔罗解读截图.png")], check=False)


if __name__ == "__main__":
    main()

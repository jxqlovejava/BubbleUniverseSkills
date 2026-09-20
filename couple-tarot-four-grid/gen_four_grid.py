#!/usr/bin/env python3
"""情侣四宫格图文帖 · 一条命令主题生成器。

任意情侣主题 → LLM 出（问题/发布文案/牌阵推荐语/照片提示词/历史填充）→ 真实抽牌+解读
（tarot-mass-divination 管线，铁律：解读禁手写）→ 即梦出情侣照片（顺序跑、task-space 各自独立）
→ 回填 content.json → 调 render_four_grid.py 渲染 + OCR。

用法：
    python3 gen_four_grid.py "暗恋的同事要不要主动表白" [--pages reading shuffle]
        [--seed N] [--count 3] [--skip-photos] [--skip-render]
依赖：LLM_API_KEY（或 DEEPSEEK_API_KEY）；照片需 ego-lite 已登录即梦。
"""
import argparse
import datetime
import json
import pathlib
import random
import re
import shutil
import subprocess
import sys

BASE = pathlib.Path(__file__).parent  # 情侣四宫格图文模板/
JIMENG = BASE.parent / "jimeng-image" / "scripts" / "agent_generate.py"


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


def llm_theme_content(theme: str) -> dict:
    """主题 → 问题/文案/推荐语/照片提示词/历史填充。一次 LLM 调用出 JSON。"""
    system = "你是小红书塔罗赛道的爆款内容策划，输出严格 JSON，不要任何额外文字。"
    user = f"""情侣相关主题：「{theme}」。
为一个塔罗占卜 App 的小红书四宫格图文帖生成以下内容（JSON 字段名固定）：
{{
  "question": "用户向塔罗牌提的问题，第一人称、口语、15 字内，紧扣主题",
  "caption": "抖音正文标题行：一句有梗/有共鸣的短句，20 字内，不带话题标签、不带任何引号",
  "hashtags": "话题标签，空格分隔、每个 # 开头；必须含 #塔罗气泡 #塔罗牌 #情侣，可再加 1-2 个主题相关标签（如 #Crush）",
  "spread_reason": "塔罗师 Luna 推荐「我-对方-我们牌阵」的理由，40-60 字，温柔口语，紧扣主题",
  "photo_prompt_a": "即梦生图提示词：真实感情侣场景照片 A，不露脸（只拍局部：牵手/背影/街景局部等），写实摄影感，紧扣主题场景，50-90 字，含「五指完整清晰」约束",
  "photo_prompt_b": "即梦生图提示词：真实感情侣场景照片 B（与 A 不同场景/构图），约束同 A",
  "history_question": "同一用户 3 天前问过的另一个情侣问题，15 字内，与主题相关但不同",
  "history_summary": "那条历史占卜的 AI 摘要，40-60 字",
  "history_time": "相对时间，如 3天前"
}}"""
    raw = gmd.llm_call(system, user, temperature=0.8, max_tokens=2000, retries=2)
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise RuntimeError(f"LLM 未返回 JSON：{raw[:200]}")
    return json.loads(m.group(0))


def copy_card_imgs(drawn: list[dict]) -> None:
    dst_dir = BASE / "assets" / "cards"
    dst_dir.mkdir(parents=True, exist_ok=True)
    for c in drawn:
        src = gmd.CARD_SRC / pathlib.Path(c["imagePath"]).name
        if src.exists():
            shutil.copy2(src, dst_dir / src.name)
        else:
            print(f"  [warn] 缺牌图: {src.name}")


def gen_photo(prompt: str, out_dir: pathlib.Path, task_space: str, count: int) -> pathlib.Path:
    """即梦出图：顺序跑、独立 task-space（并行同名会串结果，见 README 踩坑）。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    before = set(out_dir.glob("*.png"))
    subprocess.run(
        [sys.executable, str(JIMENG), prompt, "--count", str(count), "--ratio", "3:4",
         "--task-space", task_space, "--out", str(out_dir)],
        check=True,
    )
    new = sorted(set(out_dir.glob("*.png")) - before, key=lambda p: p.stat().st_mtime)
    if not new:
        raise RuntimeError(f"即梦未产出新图：{out_dir}")
    pick = new[-1]  # 最新一张（可手动换 content.json 的 photo_bl/photo_br）
    print(f"  [photo] {out_dir.name}: {len(new)} 张新图，选用 {pick.name}")
    return pick


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("theme", help="情侣相关主题，如「暗恋的同事要不要主动表白」")
    ap.add_argument("--pages", nargs=2, default=["reading", "shuffle"],
                    choices=["reading", "shuffle", "draw", "spread", "spread_result", "history"],
                    help="上排 2 格用哪两个产品页（默认 解读页+洗牌页）")
    ap.add_argument("--seed", type=int, default=None, help="抽牌随机种子（复现用）")
    ap.add_argument("--count", type=int, default=3, help="每格照片即梦出图张数（默认 3，自动选最新 1 张）")
    ap.add_argument("--skip-photos", action="store_true", help="复用 content.json 里已有照片，不重新出图")
    ap.add_argument("--skip-render", action="store_true", help="只回填 content.json，不渲染")
    args = ap.parse_args()
    rng = random.Random(args.seed)

    cfg_path = BASE / "content.json"
    content = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}

    print(f"主题：{args.theme}")
    print("[1/4] LLM 生成主题内容（问题/文案/推荐语/照片提示词）...")
    tc = llm_theme_content(args.theme)
    question = tc["question"]
    print(f"  问题：{question}\n  文案：{tc['caption']}")

    print(f"[2/4] 抽牌 + 真实解读（{SPREAD_NAME}，interpret.md 管线）...")
    spreads = json.loads((gmd.DATA / "spreads.json").read_text(encoding="utf-8"))
    items = spreads if isinstance(spreads, list) else list(spreads.values())
    spread = next(s for s in items if s.get("name") == SPREAD_NAME)
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
    reading = gmd.generate_interpretation(question, spread, drawn)
    blocks = [b.strip() for b in re.split(r"\n\s*-{3,}\s*\n", reading) if b.strip()]
    print(f"      解读 {len(blocks)} 块（首块：{blocks[0][:50]}…）")

    if args.skip_photos and content.get("photo_bl") and content.get("photo_br"):
        photo_bl, photo_br = content["photo_bl"], content["photo_br"]
        print(f"[3/4] 跳过出图，复用 {photo_bl} / {photo_br}")
    else:
        print("[3/4] 即梦出情侣照片（顺序跑，独立 task-space）...")
        pa = gen_photo(tc["photo_prompt_a"], BASE / "assets" / "photos_a", "fourgrid-a", args.count)
        pb = gen_photo(tc["photo_prompt_b"], BASE / "assets" / "photos_b", "fourgrid-b", args.count)
        photo_bl = str(pa.relative_to(BASE))
        photo_br = str(pb.relative_to(BASE))

    # 发布文案 = 标题短句（标题行）→ 品牌软植入句（单独一行）→ 话题标签。
    # 软植入句 AI 按主题生成、失败回退固定池（用户 2026-09-16 拍板，全项目同结构）。
    soft = opener.gen_opener(args.theme, llm_call=gmd.llm_call)
    tags = str(tc.get("hashtags") or "#塔罗气泡 #塔罗牌 #情侣").strip()
    caption_full = f"{tc['caption'].strip()}\n{soft}\n{tags}"
    print(f"  软植入：{soft}\n  发布文案：\n" + "\n".join(f"    {l}" for l in caption_full.splitlines()))

    content.update({
        "theme": args.theme,
        "time": datetime.datetime.now().strftime("%H:%M"),
        "question": question,
        "cards": cards,
        "interpretation": blocks,
        "underlines": [],
        "ai_label": "此内容由AI生成，仅供娱乐参考",
        "caption": caption_full,   # 完整发布文案（render_four_grid 原样写 发布文案.txt）
        "opener": soft,
        "pages": args.pages,
        "spread_name": SPREAD_NAME,
        "spread_reason": tc["spread_reason"],
        "remaining_text": "无限畅享占卜",
        "history_prev": {
            "question": tc["history_question"],
            "summary": tc["history_summary"],
            "time": tc.get("history_time") or "3天前",
        },
        "photo_bl": photo_bl,
        "photo_br": photo_br,
    })
    cfg_path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[done] 已回填 {cfg_path}")

    if args.skip_render:
        return
    print("[4/4] 渲染 + OCR ...")
    subprocess.run([sys.executable, str(BASE / "render_four_grid.py"), str(cfg_path)], check=True)
    ocr = GMD_SCRIPTS / "ocr_text.sh"
    if ocr.exists():
        subprocess.run(["bash", str(ocr), str(BASE / "out" / "情侣四宫格.png")], check=False)


if __name__ == "__main__":
    main()

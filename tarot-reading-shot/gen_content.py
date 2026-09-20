#!/usr/bin/env python3
"""主题 → 塔罗解读截图帖全套素材。

流程：
1. DeepSeek + prompts/reading_shot.md：主题 → 占卜问题 / 贴纸句（欲言未尽留白感）/ 正文故事 / 话题标签
2. 我-对方-我们牌阵抽 3 张牌（--seed 可复现），牌图自动从 tarot-mass-divination 拷贝
3. DeepSeek + tarot-mass-divination 的 interpret.md 真实提示词 → 长解读（--- 分块）
4. 划线词自动从解读开头直球答案里挑（第一块的前两句短句，保证截图可见）
5. 回填 content.json → 渲染 → Vision OCR 校验

用法：
    python3 gen_content.py "毕业前要不要跟他表白"                 # 写回模板 content.json 并渲染
    python3 gen_content.py "主题" --seed 7 --skip-render         # 只生成内容
    python3 gen_content.py "主题" --out 别的.json                 # 写到别的 content.json
依赖：LLM_API_KEY（或 DEEPSEEK_API_KEY）环境变量。
"""
import argparse
import json
import pathlib
import random
import re
import subprocess
import sys

BASE = pathlib.Path(__file__).parent            # 模板根目录

sys.path.insert(0, str(BASE))
import gen_reading as gr  # 复用：gmd 导入链 / load_spread / copy_card_imgs  # noqa: E402

gmd = gr.gmd

QUOTE_CHARS = "「」“”\"'"


def load_prompt() -> tuple[str, str]:
    text = (BASE / "prompts" / "reading_shot.md").read_text(encoding="utf-8")
    sys_part, usr = text.split("# userPrompt", 1)
    return sys_part.replace("# systemPrompt", "", 1).strip(), usr.strip()


def validate_copy(d: dict) -> None:
    for k in ("question", "sticker", "caption", "hashtags"):
        if not d.get(k):
            raise ValueError(f"缺字段 {k}")
    q = str(d["question"])
    if len(q) > 22:
        raise ValueError(f"question 超22字: {q}")
    if any(c in q for c in QUOTE_CHARS):
        raise ValueError(f"question 含引号字符: {q}")
    lines = [s for s in str(d["sticker"]).split("\n") if s.strip()]
    if len(lines) != 3:
        raise ValueError(f"sticker 需恰好3行，实际 {len(lines)}")
    for ln in lines:
        if len(ln.strip()) > 10:
            raise ValueError(f"sticker 行超10字: {ln}")
        if any(c in ln for c in QUOTE_CHARS):
            raise ValueError(f"sticker 含引号字符: {ln}")
    if "…" not in d["sticker"] and "..." not in d["sticker"]:
        raise ValueError("sticker 缺少留白省略号（…）")
    cap = str(d["caption"])
    if not 60 <= len(cap) <= 260:
        raise ValueError(f"caption 需 60-260 字，实际 {len(cap)}")
    if any(c in cap for c in "「」"):
        raise ValueError("caption 含「」")
    if not str(d["hashtags"]).lstrip().startswith("#"):
        raise ValueError(f"hashtags 需以 # 开头: {d['hashtags']}")


def gen_copy(theme: str) -> dict:
    """主题 → 四件套 JSON。不合格重试一次。"""
    sys_p, usr_tpl = load_prompt()
    usr = usr_tpl.replace("{{theme}}", theme)
    hint = ""
    for attempt in range(2):
        out = gmd.llm_call(sys_p, usr + hint, temperature=1.0, max_tokens=2000)
        try:
            data = gmd.extract_json(out)
            validate_copy(data)
            return data
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠ 文案不合格({attempt + 1}/2): {e}")
            hint = ("\n\n【修正】上一次输出不合格：" + str(e) +
                    "。请重新输出合法 JSON：question ≤22字无引号；sticker 恰好3行、每行≤10字、带…留白；"
                    "caption 60-260字无「」；hashtags 以 # 开头。")
    raise RuntimeError("文案两次生成均不合格")


def pick_underlines(first_block: str) -> list[str]:
    """划线词 = 解读第一块（直球答案区）的一条连续直球答案句，红线从头划到尾（含逗号），
    保证同一行划线连续不断。只取首句去掉句末标点；超过 30 字则截到一分号/冒号前的连续段，
    避免一条线拖成长卷。
    """
    sentence = re.split(r"[。！？!?]", first_block)[0].strip().rstrip("。！？!?，, ")
    if not sentence:
        return []
    if len(sentence) > 30:
        cut = re.split(r"[，,；;]", sentence)[0].strip()
        sentence = cut if len(cut) >= 4 else sentence[:30]
    return [sentence]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("theme", help="帖子主题，如：毕业前要不要跟他表白")
    ap.add_argument("--seed", type=int, default=None, help="抽牌随机种子（复现用）")
    ap.add_argument("--skip-render", action="store_true", help="只生成 content.json，不渲染")
    ap.add_argument("--out", default="", help="content.json 输出路径（默认模板根目录 content.json）")
    args = ap.parse_args()
    rng = random.Random(args.seed)

    # 1. 主题 → 四件套
    print(f"主题：{args.theme}\n[1/4] 生成占卜问题 + 贴纸句 + 正文故事...")
    copy = gen_copy(args.theme)

    # 2. 抽牌
    print("[2/4] 抽牌（我-对方-我们牌阵）...")
    spread = gr.load_spread()
    drawn = gmd.draw_groups(spread, 1, rng)[0]
    gr.copy_card_imgs(drawn)
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

    # 3. 真实解读
    print("[3/4] 生成真实解读（interpret.md 管线）...")
    reading = gmd.generate_interpretation(copy["question"], spread, drawn)
    blocks = [b.strip() for b in re.split(r"\n\s*-{3,}\s*\n", reading) if b.strip()]

    # 4. 划线词 + 组装 content.json
    underlines = pick_underlines(blocks[0]) if blocks else []
    tags = copy["hashtags"].strip()
    if "#塔罗气泡" not in tags:
        tags += " #塔罗气泡"
    caption_full = copy["caption"].strip() + "\n" + tags
    # 正文开头软植入句（AI 按问题生成，失败回退固定池）：渲染时插到标题行后单独一行，
    # 用户 2026-09-16 拍板。软植入句不进 caption——否则重渲染会重复插入。
    soft = gr.opener.gen_opener(copy["question"], llm_call=gmd.llm_call)
    content = {
        "time": f"{rng.choice([22, 23])}:{rng.randint(10, 59):02d}",
        "remaining_text": "无限畅享占卜",
        "question": copy["question"],
        "cards": cards,
        "interpretation": blocks,
        "underlines": underlines,
        "sticker": {"text": copy["sticker"]},
        "ai_label": "由云端AI提供",
        "caption": caption_full,
        "opener": soft,
    }
    cfg_path = pathlib.Path(args.out) if args.out else BASE / "content.json"
    cfg_path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 控制台全量回显
    print(f"\n===== 占卜问题 =====\n  {content['question']}")
    print(f"\n===== 贴纸 =====\n  " + copy["sticker"].replace("\n", "\n  "))
    print(f"\n===== 划线词 =====\n  " + "、".join(underlines))
    print(f"\n===== 解读（{len(blocks)} 块，截图只展示开头）=====")
    for b in blocks:
        print("  " + b.replace("\n", "\n  ") + "\n  ---")
    print(f"\n===== 软植入句（正文开头）=====\n  {soft}")
    print(f"\n===== 发布文案 =====\n  " +
          gr.opener.insert_opener(caption_full, soft).replace("\n", "\n  "))
    print(f"\n[done] content.json → {cfg_path}")

    if args.skip_render:
        return
    print("[4/4] 渲染 + OCR ...")
    subprocess.run([sys.executable, str(BASE / "render_reading_shot.py"), str(cfg_path)], check=True)
    ocr = gr.GMD_SCRIPTS / "ocr_text.sh"
    if ocr.exists():
        subprocess.run(["bash", str(ocr), str(BASE / "out" / "塔罗解读截图.png")], check=False)


if __name__ == "__main__":
    main()

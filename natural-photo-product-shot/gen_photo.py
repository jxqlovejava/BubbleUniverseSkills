#!/usr/bin/env python3
"""自然感实拍照片 + 塔罗气泡解读卡片 · 抖音图文 主题生成器。

流程：
1. DeepSeek + prompts/photo_share.md：主题 → photo_prompt / question / underlines / caption（JSON）
2. 即梦按 photo_prompt 生 3:4 实拍照片（2 张取 1，--skip-bg 跳过，失败回退模板默认背景图）
3. 「我-对方-我们牌阵」抽 3 张牌（--seed 可复现）
4. DeepSeek + tarot-mass-divination 的 interpret.md 真实提示词 → 长解读（--- 分块）
5. 写 content.json + 发布文案.txt → 自动调 render_photo_share.py 渲染 → Vision OCR 校验

用法：
    python3 gen_photo.py "缘分回溯到相遇那天"                          # 默认自然感情侣照片
    python3 gen_photo.py "为何总遇到慢热的人" --seed 7 --skip-bg --card-position right
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

BASE = pathlib.Path(__file__).parent   # 模板目录（自然照片产品截图模板/）
# 双布局：ip-pipeline = <根>/.claude/skills/<skill> → 根=parents[2]；vira 独立工作区 = 根=parent
if BASE.parent.name == "skills" and BASE.parents[1].name == ".claude":
    PROJECT = BASE.parents[2]
else:
    PROJECT = BASE.parent

QUOTE_CHARS = "「」“”\"'"

# 平台防限流禁词：标题/正文/标签/卡片chip 一律不得出现（替代词：解读/测试/恋爱/情感）
BANNED_WORDS = ("塔罗", "占卜", "算命")


def banned_text(s: str) -> str | None:
    """返回 s 中命中禁词的第一个词；不含则返回 None。"""
    for w in BANNED_WORDS:
        if w in s:
            return w
    return None

# ── 照片英文固定骨架 ──────────────────────────────────────────
# 用户给定铁模板，逐字保留，只允许填槽位（face/scene/hair color/hair style/outfit/单人or情侣）。
# LLM 只给槽位值，程序拼回完整 prompt，保证每次生成的照片风格严格符合参考。
# 槽位语法：{slot_name} | {slot_a/slot_b}（二选一）。
# ⚠ 比例句：本模板照片按 3:4（1728×2304）输出，故骨架用 3:4 而非用户原稿的 9:16(2160x3840)
#   —— prompt 与输出口径必须一致，否则模型先预期高构图再被强裁会导致主体偏移/面部裁切。
PHOTO_SKELETON = """Cinematic portrait photography, ultra-photorealistic, vertical composition at 3:4 aspect ratio, 50mm or 85mm portrait lens rendering, shallow depth of field, clean translucent summer natural-light color grading — not overly yellow, not over-filtered. Subject: a young beautiful adult East Asian {subject_type}, {face}, overall vibe {mood}. Gaze highly engaging — bright, clear, natural catchlights, as if it speaks; corners of mouth slightly lifted, expression gentle, vivid, natural. She walks along a {scene}, {pov_hand} She glances back at the camera while her body stays in a forward walking motion, posture elegant and natural, clearly a candid captured moment with a faint in-love feeling. Long {hair_color} hair, {hair_style}, many strands tousled and flying in the wind, richly layered and dynamic. Strong natural side-backlight rims the hair edges — clean, crisp rim light and semi-translucent glow, hair edges lit as if by sunlight, light and luminous. This is the core highlight of the image. She wears {outfit}, fabric texture natural, material light and soft. Bright natural summer sunlight realistically warms her skin, shoulders, collarbone, and clothing with soft, clean highlight transitions. Skin texture: extremely realistic — visible fine pores, natural skin texture, faint imperfections, subtle tone variation, soft sheen. Cheeks, nose tip, shoulders show natural delicate gradations in sunlight. Translucent, healthy, real and refined — no plastic look, no waxwork, no over-smoothing. Background: soft atmospheric blur, never distracting. Avoid: over-smoothing, plastic skin, CG look, anime look, wig look, stiff expression, dead eyes, stiff poses, overall yellow cast, overexposed face, distorted features, wrong fingers, deformed hands, cluttered background, heavy influencer retouching."""

# 照片主体偏卡片对侧留白（叠卡不盖脸）——按卡片位置定主体偏移
_MAIN_SUBJECT_SIDE = {
    "left": "the entire woman is positioned clearly on the RIGHT half of the frame — her head, face and upper body in the upper-right area, tall and fully visible, nothing cropped at the top; the LEFT half keeps generous clean empty space for an overlaid card; only her hand reaching back appears in the lower-left;",
    "right": "the subject is positioned on the left side of the frame, leaving generous empty space on the upper-right for an overlaid card;",
    "center": "the subject is centered, with clean empty space in the upper half for an overlaid card;",
}


def fill_photo_skeleton(slots: dict, card_position: str = "left") -> str:
    """把槽位值填入 PHOTO_SKELETON 生成完整英文 prompt。缺失槽位用中括号占位（即梦会按字面处理）。"""
    prompt = PHOTO_SKELETON
    for key, val in slots.items():
        prompt = prompt.replace("{" + key + "}", str(val).strip())
    # 主体留白约束追加到结尾避坑清单前（叠卡不盖脸）
    side = _MAIN_SUBJECT_SIDE.get(card_position, _MAIN_SUBJECT_SIDE["left"])
    prompt = prompt.replace("Avoid: over-smoothing", f"{side} Avoid: over-smoothing")
    return prompt


def photo_slot_fields() -> dict:
    """photo_share.md 允许 LLM 填的照片槽位：默认值 + 说明。"""
    return {
        "subject_type": "woman (or, if the theme leans romantic/couple, a woman with her partner whose hand only appears in the frame corner)",
        "face": "soft heart-shaped face, refined classical features, bright almond/fox eyes, petite nose bridge, naturally full lips",
        "mood": "sweet, sunny, energetic, cute with a touch of allure",
        "scene": "garden stone path",
        "pov_hand": "right hand reaching back to hold the hand of someone behind her; only their hand appears in the lower-left corner — like a first-person couple's POV snapshot.",
        "hair_color": "chestnut brown",
        "hair_style": "naturally wavy",
        "outfit": "white lace slip dress",
    }


def find_mass_divination_scripts() -> pathlib.Path:
    """tarot-mass-divination skill 位置：ip-pipeline 布局（.claude/skills/ 下）/ vira 独立工作区布局（同级）。"""
    for c in (BASE.parent / ".claude" / "skills" / "tarot-mass-divination" / "scripts",
              BASE.parent / "tarot-mass-divination" / "scripts"):
        if (c / "generate_mass_divination.py").exists():
            return c
    raise RuntimeError("找不到 tarot-mass-divination/scripts（需要它的 LLM 管线、interpret.md 与牌图）")


GMD_SCRIPTS = find_mass_divination_scripts()
sys.path.insert(0, str(GMD_SCRIPTS))
import generate_mass_divination as gmd  # noqa: E402
import opener  # noqa: E402 - 正文开头软植入句（全项目唯一实现）


def find_jimeng() -> pathlib.Path | None:
    """jimeng-image 生图脚本：ip-pipeline 布局 / vira 独立工作区布局。找不到返回 None。"""
    for c in (PROJECT / ".claude" / "skills" / "jimeng-image" / "scripts" / "agent_generate.py",
              BASE.parent / "jimeng-image" / "scripts" / "agent_generate.py"):
        if c.exists():
            return c
    return None


def load_prompt() -> tuple[str, str]:
    text = (BASE / "prompts" / "photo_share.md").read_text(encoding="utf-8")
    sys_part, usr = text.split("# userPrompt", 1)
    return sys_part.replace("# systemPrompt", "", 1).strip(), usr.strip()


def gen_photo_content(theme: str, card_position: str) -> dict:
    """主题 → photo_slots/question/underlines/caption JSON。引号字符或字段缺失则重试一次。

    照片 prompt 不放开给 LLM 自由写——只让它填槽位（face/scene/hair/outfit/单人or情侣），
    程序用 fill_photo_skeleton() 拼回固定英文骨架，保证每次生成的照片风格严格符合参考。
    """
    sys_p, usr_tpl = load_prompt()
    usr = (usr_tpl.replace("{{theme}}", theme).replace("{{card_position}}", card_position))
    default_slots = photo_slot_fields()
    hint = ""
    for attempt in range(2):
        out = gmd.llm_call(sys_p, usr + hint, temperature=1.0, max_tokens=2000)
        try:
            data = gmd.extract_json(out)
            validate_photo(data)
            # 照片槽位：LLM 给出 → 填进骨架；缺/含引号则回退默认槽位。
            spans = default_slots | {k: v for k, v in data.get("photo_slots", {}).items() if k in default_slots}
            for k, v in list(spans.items()):
                v = str(v).strip()
                if not v or any(q in v for q in QUOTE_CHARS):
                    spans[k] = default_slots[k]
                else:
                    spans[k] = v
            data["photo_prompt"] = fill_photo_skeleton(spans, card_position)
            return data
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠ 内容不合格({attempt + 1}/2): {e}")
            hint = ("\n\n【修正】上一次输出不合格：" + str(e) +
                    "。请重新输出合法 JSON：question ≤20 字、underlines 是 2-4 个完整短语、caption ≤40 字。")
    raise RuntimeError("内容两次生成均不合格")


def validate_photo(d: dict) -> None:
    for k in ("question", "underlines", "caption", "hashtags", "photo_slots"):
        if not d.get(k):
            raise ValueError(f"缺字段 {k}")
    for k in ("question", "caption"):
        if any(q in str(d[k]) for q in QUOTE_CHARS):
            raise ValueError(f"{k} 含引号字符: {d[k]}")
    if not isinstance(d["underlines"], list) or not 1 <= len(d["underlines"]) <= 4:
        raise ValueError(f"underlines 需 1-4 个短语，实际 {d['underlines']}")
    if not isinstance(d["photo_slots"], dict):
        raise ValueError("photo_slots 需是对象")
    if not isinstance(d["hashtags"], list) or not 2 <= len(d["hashtags"]) <= 8:
        raise ValueError(f"hashtags 需 2-8 个标签，实际 {d['hashtags']}")
    for h in d["hashtags"]:
        if any(q in str(h) for q in QUOTE_CHARS) or "#" in str(h):
            raise ValueError(f"hashtag 含非法字符: {h}")
    # 平台防限流：标题/正文/标签一律不含 塔罗/占卜/算命
    for k in ("question", "caption"):
        if w := banned_text(str(d[k])):
            raise ValueError(f"{k} 含“{w}”字样(平台易限流): {d[k]}")
    for h in d["hashtags"]:
        if w := banned_text(str(h)):
            raise ValueError(f"hashtag 含“{w}”字样: {h}")


def load_spread(name: str) -> dict:
    spreads = json.loads((gmd.DATA / "spreads.json").read_text(encoding="utf-8"))
    items = spreads if isinstance(spreads, list) else list(spreads.values())
    return next(s for s in items if s.get("name") == name)


def copy_card_imgs(drawn: list[dict]) -> None:
    dst_dir = BASE / "assets" / "cards"
    dst_dir.mkdir(parents=True, exist_ok=True)
    for c in drawn:
        src = gmd.CARD_SRC / pathlib.Path(c["imagePath"]).name
        if src.exists():
            shutil.copy2(src, dst_dir / src.name)
        else:
            print(f"  [warn] 缺牌图: {src.name}")


def gen_bg(prompt: str) -> pathlib.Path | None:
    """即梦按主题生 3:4 实拍照片 → 模板 assets/photo_bg.png（实例 default 覆盖机制）。
    任何失败都回退 None，渲染时用模板默认背景兜底。"""
    jimeng = find_jimeng()
    if not jimeng:
        print("  ⚠ 找不到 jimeng-image skill，沿用默认背景")
        return None
    raw = BASE / "assets" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [sys.executable, str(jimeng), prompt, "--ratio", "3:4", "--count", "2", "--out", str(raw)],
            capture_output=True, text=True, timeout=480)
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠ 即梦生背景异常({e})，沿用默认背景")
        return None
    imgs = sorted(raw.glob("*.png"))
    if proc.returncode != 0 or not imgs:
        tail = (proc.stdout + proc.stderr)[-400:]
        print(f"  ⚠ 即梦生背景失败，沿用默认背景\n{tail}")
        return None
    dst = BASE / "assets" / "photo_bg.png"
    shutil.copy2(imgs[0], dst)
    alt = f"，备选在 assets/raw/{imgs[1].name} 可同名覆盖" if len(imgs) > 1 else ""
    print(f"      照片 → {dst}{alt}")
    return dst


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("theme", help="帖子主题，如：缘分回溯到相遇那天")
    ap.add_argument("--seed", type=int, default=None, help="抽牌/时间随机种子（复现用）")
    ap.add_argument("--card-position", default="left", choices=["left", "right", "center"],
                    help="解读卡位置（默认 left，人像在卡对侧留白）")
    ap.add_argument("--skip-bg", action="store_true", help="不按主题生照片图，用模板默认背景")
    ap.add_argument("--skip-render", action="store_true", help="只生成 content.json，不渲染")
    args = ap.parse_args()
    rng = random.Random(args.seed)

    # 1. 内容（photo_prompt/question/underlines/caption）
    print(f"主题：{args.theme}　卡片位置：{args.card_position}")
    print("[1/5] 生成主题内容（照片 prompt + 问题 + 划线 + 正文）...")
    content = gen_photo_content(args.theme, args.card_position)

    # 2. 即梦生 3:4 实拍照片
    if args.skip_bg:
        print("[2/5] --skip-bg，沿用模板默认背景")
    elif content["photo_prompt"]:
        print("[2/5] 按主题生成实拍照片（即梦 3:4，生 2 张取 1）...")
        gen_bg(content["photo_prompt"])
    else:
        print("[2/5] 内容未给合格 photo_prompt，沿用默认背景")

    # 3. 抽牌
    spread_name = content.get("spread_name") or "我-对方-我们牌阵"
    print(f"[3/5] 抽牌（{spread_name} 3 张）...")
    spread = load_spread(spread_name)
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

    # 4. 真实解读
    print("[4/5] 生成真实解读（interpret.md 管线）...")
    reading = gmd.generate_interpretation(content["question"], spread, drawn)
    blocks = [b.strip() for b in re.split(r"\n\s*-{3,}\s*\n", reading) if b.strip()]

    # ★ 组装 content.json + 发布文案（解读后、渲染前）
    data = {
        "theme": args.theme,
        "card_position": args.card_position,
        "photo": "assets/photo_bg.png",
        "card_title": content.get("card_title") or "塔罗气泡",
        "remaining_text": "无限畅享解读",
        "ai_label": "由云端AI提供",
        "question": content["question"],
        "cards": cards,
        "interpretation": blocks,
        "underlines": content["underlines"],
        "caption": content["caption"],
        "hashtags": content["hashtags"],
    }
    # 发布文案 = 正文（开头一句品牌软植入）+ 固定标签 + LLM 相关标签(去重)。
    # ⚠ 平台防限流：标题/正文/标签/卡片chip 一律不含 塔罗/占卜/算命，组装时对命中禁词的标签强制过滤兜底；
    #   唯一豁免是品牌名「塔罗气泡」（软植入句里必然出现）。
    # 软植入句：AI 按主题生成、失败回退固定池，标题行后单独一行（用户 2026-09-16 拍板）。
    data["opener"] = opener.gen_opener(args.theme, llm_call=gmd.llm_call)
    fixed_tags = ["情感测试", "恋爱日常", "脱单"]
    llm_tags = [t for t in content["hashtags"] if not banned_text(t)]
    seen: set[str] = set()
    tags = fixed_tags + llm_tags
    tag_str = " ".join(
        f"#{t}" for t in tags if not (t in seen or seen.add(t))
    )
    caption_full = f"{opener.insert_opener(data['caption'], data['opener'])}\n{tag_str}"
    data["caption_full"] = caption_full  # render 直接用它写 发布文案.txt，两边别再各拼一份（旧版会丢标签）
    cfg_path = BASE / "content.json"
    cfg_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (BASE / "out").mkdir(parents=True, exist_ok=True)
    (BASE / "out" / "发布文案.txt").write_text(caption_full + "\n", encoding="utf-8")

    # 控制台全量回显
    print(f"\n===== 占卜问题 =====\n  {data['question']}")
    print(f"\n===== 划线短语 =====\n  " + " / ".join(data['underlines']))
    print(f"\n===== 解读（{len(blocks)} 块）=====")
    for b in blocks:
        print("  " + b.replace("\n", "\n  ") + "\n  ---")
    print(f"\n===== 发布文案 =====\n  {caption_full}")
    print(f"\n[done] content.json → {cfg_path}")

    if args.skip_render:
        return
    print("[5/5] 渲染 + OCR ...")
    subprocess.run([sys.executable, str(BASE / "render_photo_share.py"), str(cfg_path)], check=True)
    ocr = GMD_SCRIPTS / "ocr_text.sh"
    if ocr.exists():
        print("[ocr] Vision OCR 校验：")
        subprocess.run(["bash", str(ocr), str(BASE / "out" / "自然照片产品截图.png")], check=False)


if __name__ == "__main__":
    main()

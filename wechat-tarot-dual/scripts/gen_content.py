#!/usr/bin/env python3
"""主题 → 微信聊天×塔罗气泡 双拼抖音帖全套素材。

流程：
1. DeepSeek + prompts/chat_script.md：主题 → 聊天剧本 / 占卜问题 / 正文金句 / 背景图提示词（JSON）
2. 即梦按 bg_prompt 生 9:16 微信聊天背景（2 张取 1，--skip-bg 跳过，失败回退 skill 默认图）
3. 时间流牌阵抽 3 张牌（过去/现在/未来，--seed 可复现）
4. DeepSeek + tarot-mass-divination 的 interpret.md 真实提示词 → 长解读（--- 分块）
5. 写 content.json + 发布文案.txt → 自动调 render_wechat_tarot.py 渲染 → Vision OCR 校验

用法：
    python3 gen_content.py "暧昧期想确认TA的心意"                 # 默认输出到 微信聊天塔罗素材/<月.日>-<主题>/
    python3 gen_content.py "异地恋吵架后" --seed 7 --skip-render  # 只生成内容不渲染
依赖：LLM_API_KEY（或 DEEPSEEK_API_KEY）环境变量。
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

BASE = pathlib.Path(__file__).parent          # scripts/
SKILL = BASE.parent                            # skill 根（含 assets/、prompts/）
# 双布局：ip-pipeline = <根>/.claude/skills/<skill> → 根=parents[2]；vira 独立工作区 = <根>/<skill> → 根=parent
if SKILL.parent.name == "skills" and SKILL.parents[1].name == ".claude":
    PROJECT = SKILL.parents[2]
else:
    PROJECT = SKILL.parent


def find_mass_divination_scripts() -> pathlib.Path:
    """tarot-mass-divination skill 位置：ip-pipeline 布局 / vira 独立工作区布局。"""
    for c in (SKILL.parent / "tarot-mass-divination" / "scripts",
              SKILL.parents[1] / "tarot-mass-divination" / "scripts"):
        if (c / "generate_mass_divination.py").exists():
            return c
    raise RuntimeError("找不到 tarot-mass-divination/scripts（需要它的 LLM 管线与 interpret.md）")


sys.path.insert(0, str(find_mass_divination_scripts()))
import generate_mass_divination as gmd  # noqa: E402
import opener  # noqa: E402 - 正文开头软植入句（全项目唯一实现）

SPREAD_NAME = "时间流牌阵"
STICKERS = {"cry": "assets/sticker_cry.png", "happy": "assets/sticker_happy.png"}  # 默认兜底贴纸
STICKER_EMO = tuple(STICKERS)  # 合法表情：cry/happy
# 5 物种统一角色体系：头像 + 哭/笑贴纸都来自同一角色，保证「贴纸=头像」一致
CHARACTERS = ["orange_cat", "corgi", "gray_rabbit", "hamster", "bear"]


def sticker_src(sender: str, emo: str, me_sp: str, ta_sp: str) -> str:
    """按发送方角色取贴纸：assets/stickers/<角色>/{cry,happy}.png；缺则回退默认。"""
    sp = me_sp if sender == "me" else ta_sp
    if (SKILL / "assets" / "stickers" / sp / f"{emo}.png").exists():
        return f"assets/stickers/{sp}/{emo}.png"
    return STICKERS[emo]


QUOTE_CHARS = "「」“”\"'"
# 平台防限流禁词：标题/正文/标签/卡片chip 一律不得出现（替代词：解读/测试/恋爱/情感）
# 唯一豁免：品牌名「塔罗气泡」（用户 2026-09-11 拍板照写，与抖音录屏贴纸模板一致）
BANNED_WORDS = ("塔罗", "占卜", "算命")


def banned_text(s: str) -> str | None:
    """返回 s 中命中禁词的第一个词；不含则返回 None（品牌名内的「塔罗」豁免）。"""
    body = s.replace(opener.BRAND, "")
    for w in BANNED_WORDS:
        if w in body:
            return w
    return None


NICK_POOL = SKILL / "assets" / "nicknames.txt"
AVATAR_POOL = SKILL / "assets" / "avatars"


def load_nick_pool() -> list[str]:
    return [s.strip() for s in NICK_POOL.read_text(encoding="utf-8").splitlines() if s.strip()]


def avatar_pair_ids() -> list[str]:
    """assets/avatars/pair_XX_me.png → [pair_XX, ...]。池未建时返回空，回退默认猫狗头像。"""
    if not AVATAR_POOL.is_dir():
        return []
    return sorted(p.name[:-7] for p in AVATAR_POOL.glob("pair_*_me.png"))


def load_chat_prompt() -> tuple[str, str]:
    text = (SKILL / "prompts" / "chat_script.md").read_text(encoding="utf-8")
    sys_part, usr = text.split("# userPrompt", 1)
    return sys_part.replace("# systemPrompt", "", 1).strip(), usr.strip()


def gen_chat(theme: str, nickname: str, nick_core: str) -> dict:
    """主题 → 聊天剧本 JSON。引号字符出现或字段缺失则重试一次。昵称由池子指定注入。"""
    sys_p, usr_tpl = load_chat_prompt()
    usr = (usr_tpl.replace("{{theme}}", theme)
                  .replace("{{nickname}}", nickname)
                  .replace("{{nick_core}}", nick_core))
    hint = ""
    for attempt in range(2):
        out = gmd.llm_call(sys_p, usr + hint, temperature=1.0, max_tokens=2000)
        try:
            data = gmd.extract_json(out)
            validate_chat(data)
            # bg_prompt 不合格不拖累整体：丢弃即可（背景回退默认图）
            bg = str(data.get("bg_prompt") or "").strip()
            if len(bg) > 200 or any(q in bg for q in QUOTE_CHARS):
                bg = ""
            data["bg_prompt"] = bg
            return data
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠ 聊天剧本不合格({attempt + 1}/2): {e}")
            hint = ("\n\n【修正】上一次输出不合格：" + str(e) +
                    "。请重新输出合法 JSON：对话文本不得含任何引号字符，messages 需 8-10 条且节奏正确。")
    raise RuntimeError("聊天剧本两次生成均不合格")


def validate_chat(d: dict) -> None:
    for k in ("contact_name", "question", "caption", "hashtag_theme", "messages"):
        if not d.get(k):
            raise ValueError(f"缺字段 {k}")
    for k in ("contact_name", "question", "caption", "hashtag_theme"):
        if any(q in str(d[k]) for q in QUOTE_CHARS):
            raise ValueError(f"{k} 含引号字符: {d[k]}")
    # 平台防限流：标题/正文/标签不含 塔罗/占卜/算命
    for k in ("question", "caption", "hashtag_theme"):
        if w := banned_text(str(d[k])):
            raise ValueError(f"{k} 含“{w}”字样(平台易限流): {d[k]}")
    msgs = d["messages"]
    if not 8 <= len(msgs) <= 10:
        raise ValueError(f"messages 需 8-10 条，实际 {len(msgs)}")
    cry = happy = 0
    for i, m in enumerate(msgs):
        if m.get("from") not in ("me", "ta"):
            raise ValueError(f"第{i + 1}条 from 非法: {m.get('from')}")
        if m.get("type") == "sticker":
            if m.get("sticker") not in STICKERS:
                raise ValueError(f"第{i + 1}条 sticker 非法: {m.get('sticker')}")
            cry += m["sticker"] == "cry"
            happy += m["sticker"] == "happy"
        elif m.get("type") == "text":
            t = str(m.get("text", ""))
            if not t or len(t) > 14:
                raise ValueError(f"第{i + 1}条文本为空或超14字: {t}")
            if any(q in t for q in QUOTE_CHARS):
                raise ValueError(f"第{i + 1}条文本含引号: {t}")
        else:
            raise ValueError(f"第{i + 1}条 type 非法: {m.get('type')}")
    if cry != 1 or happy != 1:
        raise ValueError(f"cry/happy 贴纸需各恰好一次，实际 {cry}/{happy}")


def spread_timeflow() -> dict:
    spreads = json.loads((gmd.DATA / "spreads.json").read_text(encoding="utf-8"))
    items = spreads if isinstance(spreads, list) else list(spreads.values())
    return next(s for s in items if s.get("name") == SPREAD_NAME)


def find_jimeng() -> pathlib.Path | None:
    """jimeng-image 生图脚本：ip-pipeline 布局 / vira 独立工作区布局。找不到返回 None。"""
    for c in (PROJECT / ".claude" / "skills" / "jimeng-image" / "scripts" / "agent_generate.py",
              SKILL.parent / "jimeng-image" / "scripts" / "agent_generate.py"):
        if c.exists():
            return c
    return None


def gen_bg(prompt: str, src_dir: pathlib.Path) -> pathlib.Path | None:
    """即梦按主题生微信聊天背景 → 实例 .src/assets/chat_bg.png（实例目录优先机制自动生效）。
    任何失败都回退 None，渲染时用 skill 默认背景兜底。"""
    jimeng = find_jimeng()
    if not jimeng:
        print("  ⚠ 找不到 jimeng-image skill，沿用默认背景")
        return None
    raw = src_dir / "assets" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [sys.executable, str(jimeng), prompt, "--ratio", "9:16", "--count", "2", "--out", str(raw)],
            capture_output=True, text=True, timeout=480)
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠ 即梦生背景异常({e})，沿用默认背景")
        return None
    imgs = sorted(raw.glob("*.png"))
    if proc.returncode != 0 or not imgs:
        tail = (proc.stdout + proc.stderr)[-400:]
        print(f"  ⚠ 即梦生背景失败，沿用默认背景\n{tail}")
        return None
    dst = src_dir / "assets" / "chat_bg.png"
    shutil.copy2(imgs[0], dst)
    alt = f"，不满意可拿 {imgs[1].name} 同名覆盖" if len(imgs) > 1 else ""
    print(f"      背景 → {dst}（备选在 .src/assets/raw/{alt}）")
    return dst


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("theme", help="帖子主题，如：暧昧期想确认TA的心意")
    ap.add_argument("--out", default="", help="输出目录（默认 微信聊天塔罗素材/<月.日>-<主题>/）")
    ap.add_argument("--seed", type=int, default=None, help="抽牌/时间随机种子（复现用）")
    ap.add_argument("--skip-bg", action="store_true", help="不按主题生背景图，用 skill 默认背景")
    ap.add_argument("--skip-render", action="store_true", help="只生成 content.json，不渲染")
    args = ap.parse_args()
    rng = random.Random(args.seed)

    today = datetime.date.today()
    slug = re.sub(r'[\\/:*?"<>|\s]+', "", args.theme)[:20]
    out_dir = pathlib.Path(args.out) if args.out else (
        PROJECT / "微信聊天塔罗素材" / f"{today.month}.{today.day}-{slug}")
    src_dir = out_dir / ".src"   # 中间产物藏这里，实例顶层只留成品图+发布文案
    src_dir.mkdir(parents=True, exist_ok=True)

    # 1. 池子选型：昵称 + 双角色（头像与贴纸同一角色，保持一致；seed 可复现）
    nick_core = rng.choice(load_nick_pool())
    contact_name = f"A{nick_core}宝宝{rng.randint(1, 12):02d}{rng.randint(1, 28):02d}"
    if len(CHARACTERS) >= 2:
        me_sp, ta_sp = rng.sample(CHARACTERS, 2)  # 双角色尽量不同，更具辨识度
    else:
        me_sp = ta_sp = rng.choice(CHARACTERS)
    me_avatar = f"assets/characters/{me_sp}.png"
    ta_avatar = f"assets/characters/{ta_sp}.png"
    print(f"主题：{args.theme}\n昵称：{contact_name}　角色：我={me_sp} TA={ta_sp}")

    # 2. 聊天剧本
    print("[1/5] 生成聊天剧本 + 占卜问题 + 正文金句...")
    chat = gen_chat(args.theme, contact_name, nick_core)
    chat["contact_name"] = contact_name  # 以池值为准，防 LLM 改写

    # 2. 按主题生微信聊天背景（即梦）
    if args.skip_bg:
        print("[2/5] --skip-bg，沿用默认背景")
    elif chat["bg_prompt"]:
        print("[2/5] 按主题生成微信聊天背景（即梦 9:16，生 2 张取 1）...")
        gen_bg(chat["bg_prompt"], src_dir)
    else:
        print("[2/5] 剧本未给 bg_prompt，沿用默认背景")

    # 3. 抽牌
    print("[3/5] 抽牌（时间流牌阵 3 张）...")
    spread = spread_timeflow()
    drawn = gmd.draw_groups(spread, 1, rng)[0]
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
    reading = gmd.generate_interpretation(chat["question"], spread, drawn)
    blocks = [b.strip() for b in re.split(r"\n\s*-{3,}\s*\n", reading) if b.strip()]

    # 5. 组装 content.json + 发布文案
    m1 = rng.randint(30, 56)
    m2 = m1 + rng.randint(1, 3)
    messages = [
        ({"from": m["from"], "type": "sticker", "src": sticker_src(m["from"], m["sticker"], me_sp, ta_sp)}
         if m["type"] == "sticker" else
         {"from": m["from"], "type": "text", "text": m["text"]})
        for m in chat["messages"]
    ]
    content = {
        "theme": args.theme,
        "wechat": {
            "time": f"23:{m1:02d}",
            "contact_name": chat["contact_name"],
            "unread": str(rng.randint(5, 19)),
            "background": "assets/chat_bg.png",
            "me_avatar": me_avatar,
            "ta_avatar": ta_avatar,
            "messages": messages,
        },
        "tarot": {
            "time": f"23:{m2:02d}" if m2 < 60 else f"00:{m2 - 60:02d}",
            "remaining_text": "无限畅享解读",
            "question": chat["question"],
            "cards": cards,
            "interpretation": blocks,
            "ai_label": "由云端AI提供",
            "followup_hint": "向 Luna 追问你的困惑…",
        },
        "caption": chat["caption"],
    }
    cfg_path = src_dir / "content.json"
    cfg_path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # 平台防限流：标题/正文/标签/卡片chip 不含 塔罗/占卜/算命。固定标签用情感向词，主题话题词命中禁词则丢弃。
    hashtag_theme = str(chat.get("hashtag_theme") or "")
    if banned_text(hashtag_theme):
        hashtag_theme = ""  # 命中禁词则丢弃主题话题词
    fixed_tags = "情感测试 恋爱日常 脱单"
    # 正文开头软植入（AI 按主题生成，失败回退固定池）：标题行后单独一行，用户 2026-09-16 拍板
    soft = opener.gen_opener(args.theme, llm_call=gmd.llm_call)
    tag_str = f"#{fixed_tags}" + (f" #{hashtag_theme}" if hashtag_theme else "")
    caption_full = f"{chat['caption']}\n{soft}\n{tag_str}"
    (out_dir / "发布文案.txt").write_text(caption_full + "\n", encoding="utf-8")

    # 控制台全量回显
    print(f"\n===== 聊天记录（{chat['contact_name']}）=====")
    for m in messages:
        who = "我" if m["from"] == "me" else "TA"
        print(f"  {who}: {m.get('text') or '[' + pathlib.Path(m['src']).stem + ' 贴纸]'}")
    print(f"\n===== 占卜问题 =====\n  {chat['question']}")
    print(f"\n===== 解读（{len(blocks)} 块，截图只展示开头）=====")
    for b in blocks:
        print("  " + b.replace("\n", "\n  ") + "\n  ---")
    print(f"\n===== 发布文案 =====\n  {caption_full}")
    print(f"\n[done] content.json → {cfg_path}")

    if args.skip_render:
        return
    render = BASE / "render_wechat_tarot.py"
    subprocess.run([sys.executable, str(render), str(cfg_path)], check=True)
    ocr = find_mass_divination_scripts() / "ocr_text.sh"
    if ocr.exists():
        print("[ocr] Vision OCR 校验：")
        subprocess.run(["bash", str(ocr), str(out_dir / "微信聊天塔罗_双拼.png")], check=False)


if __name__ == "__main__":
    main()

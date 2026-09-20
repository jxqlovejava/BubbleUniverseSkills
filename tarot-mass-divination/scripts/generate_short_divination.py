#!/usr/bin/env python3
"""大众占卜短图文解读生成脚本。

复用长图文管线（荐阵→抽牌→LLM 解读→content.json + cards/），但解读用
`interpret_short.md`（结论先行·深夜老友散文，250-350 字，单段自然流动，无 --- 分块）。
content.json schema 与长图文一致（多一个 format:"short" 标记），供
`render_short_divination.py` 渲染 3:4 短图文选项图。

用法：
    python3 generate_short_divination.py "<问题>" <数据目录>
        [--intro "凭第一感觉，选一组"] [--spread "牌阵名"] [--seed N]
        [--theme "#E8788A"] [--n-options 3] [--prompt interpret_short.md]
环境：DEEPSEEK_API_KEY（回退 LLM_API_KEY）、LLM_API_BASE、LLM_MODEL。
"""
import argparse
import json
import pathlib
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from generate_mass_divination import (
    CARD_BY_NUM,
    DATA,
    FALLBACK_SPREAD,
    SPREADS,
    build_cards_info,
    compute_stats,
    copy_cards,
    draw_groups,
    llm_call,
    load_prompt,
    postprocess,
    recommend_spread,
)

# 短图文牌阵：只用 3 或 4 张牌的牌阵（用户明确不要单张/两张牌的牌阵）
SPREADS_3_4 = {s["name"]: s for s in SPREADS if 3 <= len(s["positions"]) <= 4}

# 短图文解读绝不该出现的"长图文板块/报幕式"痕迹
BANNED = ("行动指引", "心灵启示", "这组牌告诉我们", "抽到的牌", "牌面显示", "综合解读", "接下来")
# 开头固定的两组（渲染成粉色标题块）
SHORT_GROUPS = ("**关键词**", "**星座与四元素**")
# 散文第一句禁用开头（报幕腔/人群画像抢跑--第一句必须是直球答案，可出现在第二句之后）
BAD_PROSE_OPENERS = ("会点开这组", "点开这组", "会问", "你问", "答案是", "直接回答", "先说结论",
                      "我的答案", "如果你")
# 状态回顾式时间开头（如「上半年你大概一直在渡一条窄河」）：时间词后紧跟「你」= 描写状态非答案。
# 时间词裸开头（如「上半年正缘靠近」）是时间类问题的合法答案，不能误伤。
STATE_TIME_RE = re.compile(r"^(上半年|这半年|过去那?半年?|最近你?)(你|的你)")


def cleanup_short(text: str) -> str:
    """确定性清理（替代长图文的 normalize）：去「」引号、破折号、括号，--- 分块压回自然段落。"""
    text = postprocess(text)
    text = re.sub(r"[「」]", "", text)
    text = re.sub(r"[—–]+", "，", text)
    text = re.sub(r"[()（）]", "", text)
    text = re.sub(r"\n\s*-{3,}\s*\n", "\n\n", text)
    return text.strip()


def missing_cards(text: str, cards: list[dict]) -> list[str]:
    """返回没被点到（牌名未出现）的牌名。"""
    return [c["name"] for c in cards if c["name"] not in text]


def prose_part(text: str) -> str:
    """取散文部分（星座与四元素组之后的正文）。开头两组里点名不算，散文必须亲自点到每张牌。"""
    idx = text.find("**星座与四元素**")
    if idx == -1:
        return ""
    m = re.search(r"\n\s*\n", text[idx:])
    return text[idx + m.end():] if m else ""


def first_sentence(text: str) -> str:
    """散文第一句（到第一个句末标点为止）。"""
    prose = prose_part(text).strip()
    m = re.search(r"[。！？!?]", prose)
    return prose[:m.end()] if m else prose[:60]


CARD_NAMES = tuple(c["name"] for c in CARD_BY_NUM.values())


def _dirty_open(s: str) -> bool:
    """单句是否带抢跑痕迹（报幕腔/人群画像/状态时间开头/描述牌面）。供首句校验与专修答案句复用。"""
    if any(s.startswith(p) for p in BAD_PROSE_OPENERS) or STATE_TIME_RE.match(s):
        return True
    if s.startswith(CARD_NAMES):
        return True
    if "正位" in s or "逆位" in s:
        return True
    return any(c in s for c in ("答案是", "这组牌", "直接回答你"))


def swap_first_sentence(text: str, new_first: str) -> str:
    """答案句提到散文第一位，原第一句（人群画像/报幕）降为第二句--内容零丢失，
    且人群画像放答案之后本就合规。"""
    idx = text.find("**星座与四元素**")
    if idx == -1:
        return text
    m = re.search(r"\n\s*\n", text[idx:])
    if not m:
        return text
    prose_start = idx + m.end()
    prose = text[prose_start:].lstrip()
    sm = re.search(r"[。！？!?]", prose)
    end = sm.end() if sm else 0
    old_first = prose[:end]
    return text[:prose_start] + new_first.strip().rstrip("。！？!?") + "。" + old_first + prose[end:]


def replace_first_sentence(text: str, new_first: str) -> str:
    """把散文第一句替换为 new_first，其余原样保留（首句专修的确定性合并--
    LLM 专修常只回一句而非全文，直接采用会丢整篇，必须拼回原文）。"""
    idx = text.find("**星座与四元素**")
    if idx == -1:
        return text
    m = re.search(r"\n\s*\n", text[idx:])
    if not m:
        return text
    prose_start = idx + m.end()
    prose = text[prose_start:].lstrip()
    sm = re.search(r"[。！？!?]", prose)
    end = sm.end() if sm else 0
    return text[:prose_start] + new_first.strip().rstrip("。！？!?") + "。" + prose[end:]


def strip_mcue_first(text: str) -> str:
    """确定性去报幕：第一句含「答案是」类报幕腔时，砍掉答案之前的报幕部分
    （如「你问下半年事业运，答案是稳中向好」->「稳中向好」）。答案太短则不动。"""
    first = first_sentence(text)
    m = re.search(r"答案是[:：]?", first)
    if not m:
        return text
    kept = first[m.end():].strip()
    if len(kept) < 8:
        return text
    return replace_first_sentence(text, kept)


def opener_issues(text: str) -> list[str]:
    """散文第一句开头问题：报幕腔/人群画像/牌面描述抢跑。第一句必须是直球回答问题本身的答案句。"""
    first = first_sentence(text)
    hit = next((p for p in BAD_PROSE_OPENERS if first.startswith(p)), None)
    if hit is None and STATE_TIME_RE.match(first):
        hit = "时间词+状态描写"
    if hit is not None:
        return [f"散文第一句以「{hit}」开头，抢跑了。第一句必须是直球回答问题本身的答案句"
                "（人群画像/状态描写/报幕腔只能放在第二句之后）"]
    if "正位" in first or "逆位" in first or first.startswith(CARD_NAMES):
        return ["散文第一句在描述牌面。第一句必须是直球回答问题本身的答案句，牌面放后面融进故事讲"]
    mcue = next((p for p in ("答案是", "这组牌", "直接回答你") if p in first), None)
    if mcue is not None:
        return [f"散文第一句含报幕腔「{mcue}」。第一句就是答案本身，不要复述问题、不要描述看牌动作"]
    return []


def _cap_total(text: str, max_total: int = 535) -> str:
    """确定性兜底：总长超限时**只截散文尾部**，截到最后一个句号。
    必须保留开头两组（关键词 + 星座与四元素）——旧版只取星座起导致关键词组被丢（bug 已修）。"""
    if len(text) <= max_total:
        return text
    idx = text.find("**星座与四元素**")
    if idx == -1:
        return text[:max_total].rstrip()
    # 散文起点 = 星座与四元素 之后的第一个空行；其前全部原样保留（含关键词组）
    m = re.search(r"\n\s*\n", text[idx:])
    if m:
        prose_start = idx + m.end()
        head = text[:prose_start].rstrip()
        prose = text[prose_start:].strip()
        budget = max_total - len(head) - 2
        if len(prose) > budget:
            window = prose[:budget]
            ends = [x.end() for x in re.finditer(r"[。！？!?]", window)]
            cut = ends[-1] if ends else budget
            prose = prose[:cut].rstrip()
        return head + "\n\n" + prose
    return text[:max_total].rstrip()


def _kw_issues(text: str) -> list[str]:
    """关键词组格式问题：祝福句缺失、关键词超 8 个。"""
    m = re.search(r"\*\*关键词\*\*[:：]?(.*?)\*\*星座与四元素\*\*", text, re.S)
    if not m:
        return ["缺 关键词 组"]
    lines = [l.strip() for l in m.group(1).split("\n") if l.strip()]
    issues = []
    if len(lines) < 2:
        issues.append("关键词后缺祝福句（换行另起一行写一句美好祝愿）")
    kws = lines[0].split("、")
    if len(kws) > 8:
        issues.append(f"关键词 {len(kws)} 个，最多 8 个")
    return issues


def is_complete_short(text: str, cards: list[dict]) -> bool:
    """短图文结构校验：开头两组（关键词/星座与四元素）+ 散文、篇幅 ≤540（统一 10.5px 字号能放下）、无 AI 味引号/破折号、每张牌都点到。"""
    if not (460 <= len(text) <= 540):
        return False
    if not all(g in text for g in SHORT_GROUPS):
        return False
    if _kw_issues(text):
        return False
    if any(k in text for k in BANNED):
        return False
    if "「" in text or "」" in text or "——" in text or "--" in text:
        return False
    # 散文第一句必须直球答题（报幕腔/人群画像抢跑 = 不达标）
    if opener_issues(text):
        return False
    # 散文必须亲自点到每张牌（只在关键词/四元素组里点名不算）
    if missing_cards(prose_part(text), cards):
        return False
    return True


def build_hint(out: str, cards: list[dict]) -> str:
    """按上次输出的具体缺陷拼修正提示（篇幅/缺组/漏牌/关键词格式分别点出）。"""
    parts = []
    if not (460 <= len(out) <= 540):
        parts.append(f"上次 {len(out)} 字，必须 460-540 字，目标 500-530 字，两组约 120-160 字、散文约 360-400 字，宁可精炼不要注水")
    miss_groups = [g for g in SHORT_GROUPS if g not in out]
    if miss_groups:
        parts.append(f"缺开头分组：{'、'.join(miss_groups)}，必须先输出这两组（标题用 ** 加粗），再写散文")
    parts.extend(_kw_issues(out))
    parts.extend(opener_issues(out))
    miss = missing_cards(prose_part(out), cards)
    if miss:
        parts.append(f"漏了牌：「{'、'.join(miss)}」散文里没点到，每张牌名都必须在散文里至少出现一次（只在关键词/四元素组里点名不算），写进画面不逐张报牌名解释")
    return "；".join(parts) or "结构不达标"


def _parse_highlights(raw: str, plain: str) -> list[str]:
    """解析 LLM 摘录结果并逐字校验：不在原文里的、含 markdown 字符的直接丢。"""
    m = re.search(r"\[.*\]", raw, re.S)
    if not m:
        return []
    try:
        items = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    out = []
    for p in items if isinstance(items, list) else []:
        if isinstance(p, str) and 2 <= len(p.strip()) <= 20 and "**" not in p:
            p = p.strip()
            if p in plain and p not in out:
                out.append(p)
    return out[:12]


def extract_highlights(text: str) -> list[str]:
    """让 LLM 从最终解读里逐字摘 8-12 个关键句子/短语（备忘录主题高亮用，渲染端回退关键词）。
    任何失败都返回 [] —— 高亮是锦上添花，不阻断主流程。"""
    plain = text.replace("**", "")
    usr = ("从下面的占卜解读里，挑出 8-12 个最戳人的关键句子或短语（每个 4-15 个字），"
           "必须逐字摘录、不得改写一个字。只返回 JSON 数组，不要任何其他文字。\n\n" + plain)
    try:
        raw = llm_call("你是小红书占卜文案的编辑，负责给正文划重点。",
                       usr, temperature=0.3, max_tokens=400)
    except Exception as e:
        print(f"    高亮摘录失败（忽略）：{e}")
        return []
    hl = _parse_highlights(raw, plain)
    print(f"    高亮 {len(hl)} 条")
    return hl


# 首句修答案等窄任务用最小系统（完整 interpret_short 结构规则在此场景无关，省 ~6.5KB/次）
SHORT_EDITOR_SYS = "你是小红书塔罗占卜文案的编辑，语气温暖治愈、口语化，只说人话。"


def generate_short_interpretation(question: str, spread: dict, cards: list[dict]) -> str:
    sys_p, usr = load_prompt("interpret_short.md")
    skills = (spread.get("usage_tips") or "").strip()
    if len(skills) > 200:
        skills = skills[:200]
    ctx = {
        "question": question,
        "spreadName": spread["name"],
        "spreadIntro": spread.get("brief_description", ""),
        "interpretSkills": skills,
        "curTime": datetime.now().strftime("%Y年%m月%d日 %H:%M"),
        "cardsInfo": build_cards_info(cards),
    }
    ctx.update(compute_stats(cards))
    for k, v in ctx.items():
        usr = usr.replace("{{" + k + "}}", str(v))

    out = ""
    for attempt in range(3):
        hint = ""
        if attempt:
            hint = (f"\n\n【第{attempt + 1}次修正】上一次输出不达标：{build_hint(out, cards)}。"
                    "写成一段自然连贯的散文；禁止 --- 分块、禁止「」、"
                    "禁止括号与破折号、禁止逐张报牌名解释、禁止出现行动指引/心灵启示等板块标题；"
                    "第一句直球结论，结尾轻轻落下。")
        out = cleanup_short(llm_call(sys_p, usr + hint, temperature=1.0, max_tokens=1500))
        ok = is_complete_short(out, cards)
        print(f"    解读 {len(out)} 字{' ✓' if ok else ' ✗ 不达标，重试...'}")
        if ok:
            return out
    # 超长兜底：压缩一轮，保证最终产物落在篇幅内（压缩也要求保留全部牌名与开头两组）
    if len(out) > 540:
        print(f"    超长（{len(out)} 字），压缩一轮...")
        compress = (f"请把下面这段解读压缩到 480-520 字（必须删减至少 80 字），保留开头的 **关键词** 和 **星座与四元素** 两组、"
                    "状态翻译式结论、对号入座场景和结尾落地动作，删除重复与次要描写，"
                    "不要丢失牌意，所有牌名必须在散文部分至少出现一次。\n\n" + out)
        out = cleanup_short(llm_call(sys_p, compress, temperature=0.8, max_tokens=1000))
        print(f"    压缩后 {len(out)} 字")
    # 压缩/兜底后仍不达标（漏祝福、关键词字长、漏牌等）→ 再修正一轮
    if not is_complete_short(out, cards):
        hint2 = build_hint(out, cards)
        out = cleanup_short(llm_call(sys_p, usr + f"\n\n【最终修正】{hint2}。只做最小改动，保持其余不动。",
                                     temperature=0.8, max_tokens=1200))
        print(f"    最终修正后 {len(out)} 字")
    # 首句直答终检（2026-08-24）：最终修正路径不再校验，可能引入报幕腔/人群画像抢跑。
    # 先确定性去报幕（「你问X，答案是Y」->「Y」，零成本），修不好再 LLM 专修第一句。
    stripped = strip_mcue_first(out)
    if len(stripped) != len(out):
        print(f"    确定性去报幕 {len(out)} -> {len(stripped)} 字")
        out = stripped
    if opener_issues(out):
        # 只要一句答案句（LLM 单句任务最不易翻车，重写全文常把原抢跑开头带回来），
        # 确定性换位：答案句提到第一，原画像句降第二，内容零丢失
        for _ in range(2):
            ans = llm_call(
                SHORT_EDITOR_SYS,
                "用不超过30字的一句话直球回答这个占卜问题。要求：答案句本身开头，"
                "不要复述问题，不要报幕腔（如 答案是/你问），不要人群画像（如 会点开这组的你），"
                "不要描述牌面。只返回这一句话。问题：" + question,
                temperature=0.7, max_tokens=80)
            ans = cleanup_short(ans).split("\n")[0].strip()
            if not ans or len(ans) > 45 or _dirty_open(ans):
                continue
            merged = swap_first_sentence(out, ans)
            if not opener_issues(merged):
                print(f"    首句换位 {len(out)} -> {len(merged)} 字")
                out = merged
                break
            # 换位后超长则退回替换（丢原画像句保篇幅）
            if len(merged) > 540:
                merged = replace_first_sentence(out, ans)
                if not opener_issues(merged):
                    print(f"    首句替换 {len(out)} -> {len(merged)} 字")
                    out = merged
                    break
    # 最终确定性兜底：仍超长则按句号截散文尾部，保证 ≤535（统一 10.5px 字号能放下，且防渲染裁末行）
    capped = _cap_total(out, 535)
    if len(capped) < len(out):
        print(f"    兜底截断到 {len(capped)} 字")
    return capped


def generate_short_option(question: str, spread: dict, cards: list[dict],
                          with_highlights: bool = True) -> tuple[str, list[str]]:
    """单选项完整产物：解读 + 高亮。解读必出；高亮仅 memo 主题渲染消费，羊皮纸/黑版
    （含 batch_divination 非 memo 批次）传 --no-highlights 跳过摘录 LLM，省 1 次调用/选项。
    高亮是锦上添花，需要时（memo 渲染）再带开重跑 generate 即可。"""
    interp = generate_short_interpretation(question, spread, cards)
    if not with_highlights:
        return interp, []
    return interp, extract_highlights(interp)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question", help="占卜问题")
    ap.add_argument("data_dir", help="输出数据目录（含 cards/）")
    ap.add_argument("--intro", default="凭第一感觉，选一组")
    ap.add_argument("--spread", default="", help="手动指定牌阵（跳过 LLM 推荐）")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--theme", default="#E8788A")
    ap.add_argument("--n-options", type=int, default=3)
    ap.add_argument("--prompt", default="interpret_short.md")
    ap.add_argument("--no-highlights", action="store_true",
                    help="跳过每选项 LLM 高亮摘录（仅 memo 主题渲染需要；羊皮纸/黑版省 1 次调用/选项）")
    args = ap.parse_args()

    data_dir = pathlib.Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    # ① 牌阵（短图文只用 3/4 张牌的牌阵）
    if args.spread:
        if args.spread not in SPREADS_3_4:
            print(f"错误：牌阵「{args.spread}」不可用（须库内且牌数为 3 或 4）。可选：", "、".join(SPREADS_3_4))
            sys.exit(1)
        spread = SPREADS_3_4[args.spread]
        reason = "手动指定"
        print(f"① 手动牌阵：{spread['name']}（{len(spread['positions'])} 张）")
    else:
        name, reason = recommend_spread(
            args.question, allowed=SPREADS_3_4, fallback=FALLBACK_SPREAD,
            intro_text="这是大众占卜短图文，每个选项组独立按该牌阵抽牌，请只推荐 3 或 4 张牌的牌阵。",
        )
        spread = SPREADS_3_4[name]

    # ② 抽牌
    print(f"② 抽牌（{args.n_options} 组 × {len(spread['positions'])} 张，78 张不重复）...")
    groups = draw_groups(spread, args.n_options, rng)
    for i, g in enumerate(groups):
        shown = "、".join(f"{c['name']}({'逆' if c['direction']=='REVERSED' else '正'})" for c in g)
        print(f"   选项{chr(65 + i)}：{shown}")

    # ③ 解读+高亮（并发：每选项「解读->高亮」整链为一个并发单元；--no-highlights 跳过摘录 LLM）
    print("③ 生成解读（并发）..." + ("已跳过 LLM 高亮摘录（--no-highlights）" if args.no_highlights else ""))
    with ThreadPoolExecutor(max_workers=len(groups)) as ex:
        results = list(ex.map(lambda g: generate_short_option(
            args.question, spread, g, with_highlights=not args.no_highlights), groups))
    options = []
    for i, g in enumerate(groups):
        lid = chr(65 + i)
        interp, highlights = results[i]
        cards_out = [{
            "img": f"../cards/{pathlib.Path(c['imagePath']).name}",
            "name": c["name"],
            "position": c["position"],
            "reversed": c["direction"] == "REVERSED",
        } for c in g]
        options.append({
            "id": lid,
            "name": g[0]["name"],
            "cards": cards_out,
            "interpretation": interp,
            "highlights": highlights,
        })
        print(f"   选项{lid} 解读 {len(interp)} 字 ✓")

    copy_cards(data_dir, groups)

    content = {
        "question": args.question,
        "format": "short",
        "intro": args.intro,
        "brand": "解读来自塔罗气泡",
        "logo": "cards/ic_launcher.png",
        "ai_tip": "*以上分析由塔罗气泡App使用AI生成，请理性看待",
        "cover_ai_tip": "所有分析来自塔罗气泡App用AI生成，请理性看待",
        "theme_color": args.theme,
        "title_style": "plain",
        "spread": {"name": spread["name"], "reason": reason},
        "options": options,
    }
    out = data_dir / "content.json"
    out.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 已写入 {out}（牌阵：{spread['name']}）")


if __name__ == "__main__":
    main()

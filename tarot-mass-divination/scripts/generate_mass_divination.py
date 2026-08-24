#!/usr/bin/env python3
"""大众占卜解读生成脚本：问题 → LLM 荐阵 → 抽牌 → LLM 解读 → content.json。

管线（复刻 TarotBubble + backend 逻辑）：
1. 牌阵推荐：DeepSeek 调「牌阵推荐提示词」→ JSON {spreadName, reason}（大众占卜约束 ≤5 张牌）
2. 抽牌：4 选项 × 该牌阵 card_count 张，从 78 张无放回（跨选项不重复），正逆位各 50%
3. 解读：每选项 DeepSeek 调「大众占卜解读提示词」→ markdown；截掉「你还可以追问」，追加品牌 CTA
4. 写 content.json（含 options[].cards 与 interpretation），并把所需牌图拷贝到 <数据目录>/cards/

用法：
    python3 generate_mass_divination.py "<问题>" <数据目录> [--intro "凭第一感觉，选一组"]
        [--spread "牌阵名"] [--seed N] [--theme "#E8788A"]
环境：DEEPSEEK_API_KEY（回退 LLM_API_KEY）、LLM_API_BASE、LLM_MODEL。
"""
import argparse
import json
import os
import pathlib
import random
import re
import shutil
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

SKILL = pathlib.Path(__file__).resolve().parent.parent
DATA = SKILL / "data"
CARDS = json.loads((DATA / "tarot_cards.json").read_text(encoding="utf-8"))
SPREADS = json.loads((DATA / "spreads.json").read_text(encoding="utf-8"))
# 大众占卜只允许 ≤5 张牌的牌阵（单页可读性），荐阵/手动指定都在此集合内校验
SPREADS_LE5 = {s["name"]: s for s in SPREADS if len(s["positions"]) <= 5}
CARD_BY_NUM = {c["cardNumber"]: c for c in CARDS}
# 牌图/logo：优先用 skill 内置副本（data/tarot-card/rider_waite、data/torot/），
# 缺才回退 TarotBubble 工程路径（老工作流）——保证 skill 单独拷给他人也能完整运行
CARD_SRC = DATA / "tarot-card" / "rider_waite"
if not CARD_SRC.exists():
    CARD_SRC = pathlib.Path(os.path.expanduser("~/Documents/workspace/TarotBubble/assets/tarot-card/rider_waite"))
LOGO_SRC = DATA / "torot" / "ic_launcher.png"
if not LOGO_SRC.exists():
    LOGO_SRC = pathlib.Path(os.path.expanduser("~/Documents/workspace/TarotBubble/assets/torot/ic_launcher.png"))
FALLBACK_SPREAD = "时间流牌阵"


# ---------- LLM ----------
def llm_call(system: str, user: str, temperature: float = 0.8, max_tokens: int = 4000, retries: int = 2) -> str:
    base = os.environ.get("LLM_API_BASE", "https://api.deepseek.com").rstrip("/")
    model = os.environ.get("LLM_MODEL", "deepseek-chat")
    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY")
    if not key:
        raise RuntimeError("缺少 DEEPSEEK_API_KEY / LLM_API_KEY")
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/chat/completions", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    last = None
    for i in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:  # noqa: BLE001
            last = e
            if i < retries:
                print(f"  ⚠ LLM 调用失败({i + 1}/{retries}): {e}，重试...")
    raise RuntimeError(f"LLM 调用最终失败: {last}")


def load_prompt(name: str) -> tuple[str, str]:
    """按 # userPrompt 切 system/user 两段。"""
    text = (DATA / "prompts" / name).read_text(encoding="utf-8")
    marker = "# userPrompt"
    if marker in text:
        sys_part, user_part = text.split(marker, 1)
        sys_part = sys_part.replace("# systemPrompt", "", 1).strip()
        return sys_part, user_part.strip()
    return text, ""


def extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?", "", text).strip().strip("`").strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError(f"无法从输出解析 JSON: {text[:200]}")
    return json.loads(m.group(0))


# ---------- 牌阵推荐 ----------
def recommend_spread(question: str, allowed: dict | None = None,
                     fallback: str = FALLBACK_SPREAD, intro_text: str = "") -> tuple[str, str]:
    """LLM 荐阵。`allowed` 限定可选的牌阵集合（默认 SPREADS_LE5，长图文沿用原行为）；
    `intro_text` 覆盖约束导语（默认长图文原文案）。"""
    if allowed is None:
        allowed = SPREADS_LE5
    print("① 牌阵推荐（LLM）...")
    sys_p, usr = load_prompt("spread_recommend.md")
    usr = usr.replace("{{question}}", question)
    intro = intro_text or ("这是大众占卜长图文，4 个选项组，每组将独立按该牌阵抽牌并生成解读。"
                           "为避免单页解读过长，")
    allowed_names = "、".join(allowed.keys())
    usr += (f"\n\n【大众占卜约束·最高优先级】{intro}"
            "你**只能从以下牌阵列表中选择一个推荐**（名称必须 100% 完全一致，一个字都不能差）："
            f"{allowed_names}。\n"
            "**严禁推荐列表之外的任何牌阵**（即使后文的主题优先级/随机多样性原则建议了列表外的主题牌阵，也必须放弃，改从本列表挑最贴近主题的一个）。")
    out = llm_call(sys_p, usr, temperature=0.5, max_tokens=400)
    try:
        res = extract_json(out)
        name = res.get("spreadName", "").strip()
        reason = res.get("reason", "").strip()
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠ 解析推荐结果失败: {e}\n  原始输出: {out[:200]}")
        name, reason = "", ""
    if name not in allowed:
        print(f"  ⚠ 推荐牌阵「{name}」不可用（不在库或不在许可牌数范围），回退「{fallback}」")
        name, reason = fallback, "自动回退到时间流牌阵。"
    spread = allowed[name]
    print(f"  ✅ 推荐牌阵：{name}（{len(spread['positions'])} 张）｜{reason}")
    return name, reason


# ---------- 抽牌 ----------
def draw_groups(spread: dict, n_options: int, rng: random.Random) -> list[list[dict]]:
    positions = spread["positions"]
    count = len(positions)
    used: set[int] = set()
    groups = []
    for _ in range(n_options):
        avail = [n for n in range(78) if n not in used]
        nums = rng.sample(avail, count)
        used.update(nums)
        cards = []
        for num, pos in zip(nums, positions):
            c = CARD_BY_NUM[num]
            reversed = rng.random() < 0.5
            cards.append({
                "number": num,
                "name": c["name"],
                "englishName": c["englishName"],
                "imagePath": c["imagePath"],
                "direction": "REVERSED" if reversed else "UPRIGHT",
                "position": pos["name"],
                "positionMeaning": pos.get("meaning", ""),
            })
        groups.append(cards)
    return groups


# ---------- 解读 ----------
def build_cards_info(cards: list[dict]) -> str:
    lines = []
    for i, c in enumerate(cards):
        major = 0 <= c["number"] <= 21
        lines += [
            f"位置{i + 1}",
            f"牌面：{c['name']}",
            f"该牌面属于：{'大阿卡纳牌' if major else '小阿卡纳牌'}",
            f"该牌面朝向：{'正位' if c['direction'] == 'UPRIGHT' else '逆位'}",
            f"该牌面对应牌阵位置名称：{c['position']}",
            f"该牌面对应牌阵位置含义：{c['positionMeaning']}",
            "",
        ]
    return "\n".join(lines).rstrip()


def compute_stats(cards: list[dict]) -> dict:
    n = len(cards)
    inv = sum(1 for c in cards if c["direction"] == "REVERSED")
    major = [c["name"] for c in cards if 0 <= c["number"] <= 21]
    minor = [c["name"] for c in cards if not 0 <= c["number"] <= 21]
    def cnt(f):
        return sum(1 for c in cards if f(c["number"]))
    return {
        "totalCardCount": n,
        "inversusCount": inv,
        "inversusExceedHalf": "是" if inv > n / 2 else "否",
        "majorCards": "、".join(major) or "无",
        "majorCardCount": len(major),
        "minorCards": "、".join(minor) or "无",
        "minorCardCount": len(minor),
        "swordCardCount": cnt(lambda x: 42 <= x <= 51 or 70 <= x <= 73),
        "wandCardCount": cnt(lambda x: 22 <= x <= 31 or 62 <= x <= 65),
        "cupCardCount": cnt(lambda x: 32 <= x <= 41 or 66 <= x <= 69),
        "starCoinCardCount": cnt(lambda x: 52 <= x <= 61 or 74 <= x <= 77),
    }


def postprocess(text: str) -> str:
    """清理：截掉「你还可以追问」尾巴与末尾多余 ---。"""
    for marker in ("**你还可以追问**", "你还可以追问", "1️⃣", "2️⃣", "3️⃣"):
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx]
            break
    return re.sub(r"(---\s*)+$", "", text).strip()


_TITLE_RE = r"\*\*(?:\d+\.|行动指引|心灵启示)"


def _split_middle(p: str) -> list[str]:
    """单段综合解读从最靠近中点的句尾切成两段；无法切则原样返回。"""
    ends = [m.end() for m in re.finditer(r"[。！？!?]", p)]
    if not ends:
        return [p]
    cut = min(ends, key=lambda e: abs(e - len(p) / 2))
    if cut >= len(p) - 5:
        return [p]
    return [p[:cut], p[cut:]]


# 综合解读两段篇幅红线（字）：interpret.md 已有提示词约束，这里是生成端安全网，
# 防 LLM 忽略提示时渲染出的第 2 张卡片（整体感受与串牌）过长。
CAP_P1 = 150   # 第1段 直球回答
CAP_P2 = 280   # 第2段 整体感受与串牌


def _cap_para(p: str, max_len: int) -> str:
    """超长段落截到 max_len 内最后一个句子结束符；无句号退到逗号级；再无则硬截。"""
    if len(p) <= max_len:
        return p
    window = p[:max_len]
    ends = [m.end() for m in re.finditer(r"[。！？!?]", window)]
    if ends:
        return p[:ends[-1]].rstrip()
    soft = [m.end() for m in re.finditer(r"[，、；]", window)]
    if soft:
        return p[:soft[-1]].rstrip()
    return p[:max_len].rstrip()


def normalize(text: str) -> str:
    """确定性结构修复（替代重新生成）：
    1. 并块拆分：块中间的 **N. / **行动指引 / **心灵启示 标题处切开，各自独立成块
    2. 缺标题补齐：行动指引/心灵启示都没写标题时，把标题补到最后两个无标题块上
    3. 综合解读固定两段：开头区（首个标题块之前）所有段落并为一段落块、恰好两段
       （1 段→中点切开；>2 段→第 1 段独立、其余并入第 2 段）
    内容缺失（整张单牌没写）不在此修复，交给 is_complete 判失败重新生成。"""
    raw_blocks = [b for b in re.split(r"\n\s*-{3,}\s*\n", text) if b.strip()]
    blocks: list[str] = []
    for b in raw_blocks:
        blocks.extend(p for p in re.split(rf"\n(?=\s*{_TITLE_RE})", b) if p.strip())
    is_title = lambda b: bool(re.match(rf"\s*{_TITLE_RE}", b))
    # 行动指引/心灵启示缺标题：补到最后两个块
    has_act = any(re.match(r"\s*\*\*行动指引", b) for b in blocks)
    has_rev = any(re.match(r"\s*\*\*心灵启示", b) for b in blocks)
    if not has_act and not has_rev and len(blocks) >= 4:
        blocks[-2] = "**行动指引**\n" + blocks[-2].strip()
        blocks[-1] = "**心灵启示**\n" + blocks[-1].strip()
    # 综合解读区：首个标题块之前的所有无标题段落 → 恰好两段的一个块
    first_title = next((i for i, b in enumerate(blocks) if is_title(b)), len(blocks))
    head, tail = blocks[:first_title], blocks[first_title:]
    paras: list[str] = []
    for b in head:
        paras.extend(p.strip() for p in re.split(r"\n\s*\n", b) if p.strip())
    if len(paras) > 2:
        paras = [paras[0], "\n\n".join(paras[1:])]
    elif len(paras) == 1:
        paras = _split_middle(paras[0])
    # 篇幅红线：第1段 ≤150 / 第2段 ≤280（安全网，正常长度不受影响）
    if paras:
        paras[0] = _cap_para(paras[0], CAP_P1)
    if len(paras) > 1:
        paras[1] = _cap_para(paras[1], CAP_P2)
    # 综合解读恰好两段 → 直接输出两块（--- 分隔）；finalize 对已拆文本幂等，不再二次 join 展开第二段内部空行
    head = paras if paras else []
    return "\n\n---\n\n".join(head + tail)


def finalize(text: str) -> str:
    """综合解读两段拆成两个 --- 块，渲染为两张独立卡片。"""
    m = re.search(r"\n\s*-{3,}\s*\n", text)
    if m:
        opening, rest = text[: m.start()], text[m.end():].strip()
        paras = [p.strip() for p in re.split(r"\n\s*\n", opening) if p.strip()]
        if len(paras) == 2:
            text = paras[0] + "\n\n---\n\n" + paras[1] + "\n\n---\n\n" + rest
    return text


def is_complete(text: str, cards: list[dict]) -> bool:
    """结构完整性校验（只验结构，不管篇幅）：行动指引/心灵启示 + 每张单牌标题独立成块 +
    综合解读恰好两段 + 板块数下限。"""
    if "行动指引" not in text or "心灵启示" not in text:
        return False
    blocks = [b for b in re.split(r"\n\s*-{3,}\s*\n", text) if b.strip()]
    # 每张单牌的 **N. 标题必须是某个块的首行（标题只出现但并块 = 渲染卡片缺失）
    title_blocks = [b for b in blocks if re.match(r"\s*\*\*\d+\.\s", b)]
    if len(title_blocks) < len(cards) or len(text) < 450:
        return False
    # 综合解读恰好两段：开头两个块均为无标题文本块（非 **N. / **行动指引 / **心灵启示）
    if len(blocks) < 3:
        return False
    if re.match(rf"\s*{_TITLE_RE}", blocks[0]) or re.match(rf"\s*{_TITLE_RE}", blocks[1]):
        return False
    # 综合解读两块之后必须紧跟 **1. 单牌标题（保证单牌解读前恰好两张卡片，无过渡块）
    if not re.match(r"\s*\*\*1\.\s", blocks[2]):
        return False
    # 板块数下限：综合解读2 + 单牌N + 行动指引 + 心灵启示（防止合并成一块导致渲染卡片缺失）
    return len(blocks) >= len(cards) + 4


def generate_interpretation(question: str, spread: dict, cards: list[dict]) -> str:
    sys_p, usr = load_prompt("interpret.md")
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
    # 篇幅完全按 LLM 默认输出（interpret.md 自带设计要求），不追加字数/句数约束
    for attempt in range(3):
        print(f"  生成解读（{len(cards)} 张牌）{'重试 ' + str(attempt) if attempt else ''}...")
        hint = ""
        if attempt > 0:
            hint = (f"\n\n【第{attempt + 1}次修正】上一次输出结构不达标：综合解读必须恰好两段（两段之间用一个空行分隔），"
                    "每个板块之间必须用 --- 分隔，心灵启示必须完整收尾，不得截断。")
        out = normalize(postprocess(llm_call(sys_p, usr + hint, temperature=1.0, max_tokens=4000)))
        if is_complete(out, cards):
            return finalize(out)
        print(f"    ⚠ 输出结构不达标（{len(out)} 字，需板块完整、综合解读两段、--- 分隔齐全），重新生成...")
    print(f"    ⚠ 多次不达标，接受最后一次输出")
    return finalize(out)


# ---------- 写 content.json + 拷贝牌图 ----------
def copy_cards(data_dir: pathlib.Path, groups: list[list[dict]]) -> None:
    cards_dir = data_dir / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)
    for group in groups:
        for c in group:
            src = CARD_SRC / pathlib.Path(c["imagePath"]).name
            if src.exists():
                shutil.copy2(src, cards_dir / src.name)
    if not (cards_dir / "ic_launcher.png").exists() and LOGO_SRC.exists():
        shutil.copy2(LOGO_SRC, cards_dir / "ic_launcher.png")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question", help="占卜问题")
    ap.add_argument("data_dir", help="输出数据目录（含 cards/）")
    ap.add_argument("--intro", default="凭第一感觉，选一组")
    ap.add_argument("--spread", default="", help="手动指定牌阵（跳过 LLM 推荐）")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--theme", default="#E8788A")
    ap.add_argument("--n-options", type=int, default=4)
    args = ap.parse_args()

    data_dir = pathlib.Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    # ① 牌阵
    if args.spread:
        if args.spread not in SPREADS_LE5:
            print(f"错误：牌阵「{args.spread}」不可用（须库内且牌数 ≤5）。可选：", "、".join(SPREADS_LE5))
            sys.exit(1)
        spread = SPREADS_LE5[args.spread]
        reason = "手动指定"
        print(f"① 手动牌阵：{spread['name']}（{len(spread['positions'])} 张）")
    else:
        name, reason = recommend_spread(args.question)
        spread = SPREADS_LE5[name]

    # ② 抽牌
    print(f"② 抽牌（{args.n_options} 组 × {len(spread['positions'])} 张，78 张不重复）...")
    groups = draw_groups(spread, args.n_options, rng)
    for i, g in enumerate(groups):
        shown = "、".join(f"{c['name']}({'逆' if c['direction']=='REVERSED' else '正'})" for c in g)
        print(f"   选项{chr(65 + i)}：{shown}")

    # ③ 解读（并发：每选项一次 LLM 调用，纯 I/O 等待，串行 N 组 ≈ N 倍耗时）
    print("③ 生成解读（每选项一次 LLM 调用，并发）...")
    with ThreadPoolExecutor(max_workers=len(groups)) as ex:
        interps = list(ex.map(lambda g: generate_interpretation(args.question, spread, g), groups))
    options = []
    for i, g in enumerate(groups):
        lid = chr(65 + i)
        interp = interps[i]
        first_name = g[0]["name"]
        cards_out = [{
            "img": f"../cards/{pathlib.Path(c['imagePath']).name}",
            "name": c["name"],
            "position": c["position"],
            "reversed": c["direction"] == "REVERSED",
        } for c in g]
        options.append({
            "id": lid,
            "name": first_name,
            "cards": cards_out,
            "interpretation": interp,
        })
        print(f"   选项{lid} 解读 {len(interp)} 字 ✓")

    copy_cards(data_dir, groups)

    content = {
        "question": args.question,
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

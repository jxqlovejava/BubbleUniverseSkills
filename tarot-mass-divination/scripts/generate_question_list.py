#!/usr/bin/env python3
"""塔罗问题清单帖 · 清单生成脚本：主题 → LLM 按受众智能分组生成问题清单 → content.json。

用法：
    python3 generate_question_list.py [主题] <数据目录> [--count 100] [--title "..."] [--seed N]
环境：DEEPSEEK_API_KEY（回退 LLM_API_KEY）、LLM_API_BASE、LLM_MODEL。
"""
import argparse
import json
import pathlib
import random
import re
import sys

from generate_mass_divination import extract_json, llm_call, load_prompt

DEFAULT_THEME = "综合（爱情/事业/财运/学业/自我成长全覆盖）"
COUNT_TOLERANCE = 0.2  # 总数偏差超过 ±20% 视为不达标，重试


def clean_groups(groups: list[dict]) -> list[dict]:
    """剔空组、strip 「」、跨组去重（保序）。"""
    seen: set[str] = set()
    out: list[dict] = []
    for g in groups:
        name = re.sub(r"[「」]", "", str(g.get("name", ""))).strip()
        questions: list[str] = []
        for q in g.get("questions") or []:
            q = re.sub(r"[「」]", "", str(q)).strip()
            if q and q not in seen:
                seen.add(q)
                questions.append(q)
        if name and questions:
            out.append({"name": name, "questions": questions})
    return out


def trim_to_count(groups: list[dict], count: int) -> list[dict]:
    """超量时按比例缩每组条数（最大余数法），合计恰好 count、不留空组。
    LLM 计数不精确，超量靠裁剪兜底，比重试省 token 且结果确定。"""
    total = sum(len(g["questions"]) for g in groups)
    if total <= count:
        return groups
    if count < len(groups):  # 目标比组数还少：直接砍尾部组
        groups = groups[:count]
        total = sum(len(g["questions"]) for g in groups)
    quotas = [len(g["questions"]) * count / total for g in groups]
    base = [max(1, int(q)) for q in quotas]
    while sum(base) > count:
        i = max(range(len(groups)),
                key=lambda k: base[k] - quotas[k] if base[k] > 1 else -1)
        base[i] -= 1
    while sum(base) < count:
        i = max(range(len(groups)),
                key=lambda k: quotas[k] - base[k]
                if base[k] < len(groups[k]["questions"]) else -1)
        if base[i] >= len(groups[i]["questions"]):
            break  # 全部组已取满（理论到不了：total > count）
        base[i] += 1
    return [{"name": g["name"], "questions": g["questions"][:b]}
            for g, b in zip(groups, base)]


LONG_MIN = 21  # ≥21 字才稳定折两行（实测 28px/595px 一行容量 ~20 字，17~20 字仍是一行）


def group_long_shortage(groups: list[dict]) -> list[str]:
    """逐组检查长句数量：组 ≥6 条要求 ≥2 条长句，3~5 条要求 ≥1 条（用户定的排版规则）。
    返回不达标组名列表（空 = 全达标）。"""
    bad = []
    for g in groups:
        qs = g["questions"]
        need = 2 if len(qs) >= 6 else (1 if len(qs) >= 3 else 0)
        longs = sum(1 for q in qs if len(q) >= LONG_MIN)
        if longs < need:
            bad.append(f"{g['name']}（{longs}/{need} 长句）")
    return bad


LENGTHEN_SYS = (
    "你是中文文案编辑。把用户给的塔罗提问扩写：保持原意、第一人称和问号结尾，"
    "加场景/条件/顾虑状语（如「在…情况下」「而不引发…」「未来3个月内」），"
    "结果必须 21~26 字、口语化。只输出扩写后的一句话，不要任何解释。"
)


def lengthen_question(q: str) -> str:
    """把短句扩写成 21~26 字长句（LLM 微调小调用）。失败兜底返回最长可用结果。"""
    best = q
    for _ in range(3):
        try:
            out = llm_call(LENGTHEN_SYS, q, temperature=0.7, max_tokens=80, retries=2)
        except Exception:  # noqa: BLE001
            continue
        out = re.sub(r"[「」\"'\n]", "", out).strip()
        if 21 <= len(out) <= 26 and out != q:
            return out
        if len(out) > len(best) and len(out) <= 30:
            best = out
    return best


SHORTEN_SYS = (
    "你是中文文案编辑。把用户给的塔罗提问压缩：保持原意、第一人称和问号结尾，"
    "删掉修饰状语只留核心提问，结果必须 12~16 字、口语化。"
    "只输出压缩后的一句话，不要任何解释。"
)


def shorten_question(q: str) -> str:
    """把长句压缩成 12~16 字短句（LLM 微调小调用）。失败兜底返回最短可用结果。"""
    best = q
    for _ in range(3):
        try:
            out = llm_call(SHORTEN_SYS, q, temperature=0.7, max_tokens=80, retries=2)
        except Exception:  # noqa: BLE001
            continue
        out = re.sub(r"[「」\"'\n]", "", out).strip()
        if 12 <= len(out) <= 16 and out != q:
            return out
        if 8 <= len(out) < len(best):
            best = out
    return best


def ensure_group_longs(groups: list[dict]) -> list[dict]:
    """逐组平衡长短比例（定点微调，不重跑整份清单；实测 LLM 一次生成满足不了逐组配额）：
    - 不足：组 ≥6 条须 ≥2 条长句（3~5 条须 ≥1 条），把最长的短句扩写补足
    - 超配：长句 ≤ max(2, 组条数×30%)（大部分问题须一行展示完），把超出的最长句压缩"""
    fixed = 0
    for g in groups:
        qs = g["questions"]
        need = 2 if len(qs) >= 6 else (1 if len(qs) >= 3 else 0)
        cap = max(need, round(len(qs) * 0.3))
        longs = [i for i, q in enumerate(qs) if len(q) >= LONG_MIN]
        while len(longs) < need:
            # 候选按长度降序逐个试（网络抖动/扩写不达标时换下一个，不轻易放弃整组）
            cands = sorted(((len(q), i) for i, q in enumerate(qs)
                            if len(q) < LONG_MIN), reverse=True)
            if not cands:
                break
            done = False
            for _, i in cands:
                new_q = lengthen_question(qs[i])
                if len(new_q) >= LONG_MIN:
                    qs[i] = new_q
                    longs.append(i)
                    fixed += 1
                    done = True
                    break
            if not done:
                break
        while len(longs) > cap:
            i = max(longs, key=lambda k: len(qs[k]))  # 压最长的长句
            new_q = shorten_question(qs[i])
            if len(new_q) >= LONG_MIN:  # 压缩失败，避免死循环
                break
            qs[i] = new_q
            longs.remove(i)
            fixed += 1
    if fixed:
        print(f"  定点微调 {fixed} 条平衡组内长短比例")
    return groups


def generate_list(theme: str, count: int) -> list[dict]:
    sys_p, user_p = load_prompt("question_list.md")
    user = user_p.replace("{{theme}}", theme).replace("{{count}}", str(count))
    last_err: Exception | None = None
    for attempt in range(3):  # llm_call 自身已带网络重试，这里重试的是解析/数量不达标
        try:
            raw = llm_call(sys_p, user, temperature=0.9, max_tokens=6000, retries=2)
            groups = clean_groups(extract_json(raw).get("groups") or [])
            if not groups:
                raise ValueError("无有效分组")
            total = sum(len(g["questions"]) for g in groups)
            if total < count * (1 - COUNT_TOLERANCE):
                raise ValueError(f"总数 {total} 低于目标 {count} 的 80%")
            if total > count:
                groups = trim_to_count(groups, count)  # 超量确定性裁剪，不再重试
            groups = ensure_group_longs(groups)  # 逐组长句配额：定点扩写兜底
            shortage = group_long_shortage(groups)
            if shortage:
                raise ValueError(f"组长句不足(扩写后仍缺): {'; '.join(shortage)}")
            return groups
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < 2:
                print(f"  ⚠ 清单不达标({attempt + 1}/2): {e}，重新生成...")
    raise RuntimeError(f"清单生成最终失败: {last_err}")


def main() -> None:
    ap = argparse.ArgumentParser(description="塔罗问题清单帖 · 清单生成")
    ap.add_argument("args", nargs="+", help="[主题] <数据目录>（主题可省略，默认综合）")
    ap.add_argument("--count", type=int, default=100)
    ap.add_argument("--title", default="")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    positional = args.args
    data_dir = pathlib.Path(positional[-1])
    theme = positional[0] if len(positional) > 1 else DEFAULT_THEME
    if args.seed is not None:
        random.seed(args.seed)

    data_dir.mkdir(parents=True, exist_ok=True)

    print(f"主题: {theme} / 目标 {args.count} 条")
    groups = generate_list(theme, args.count)
    total = sum(len(g["questions"]) for g in groups)
    # 标题默认跟实际条数走（LLM 计数不精确，±20% 内都算达标），--title 可手动定死
    # 主题词进标题：感情 → 98个塔罗感情问题清单；默认综合 → 98个塔罗牌问题清单
    if args.title:
        title = args.title
    elif theme == DEFAULT_THEME:
        title = f"{total}个塔罗牌问题清单"
    else:
        core = re.sub(r"[（(].*$", "", theme).strip()
        title = f"{total}个塔罗{core}问题清单"
    content = {
        "type": "question_list",
        "title": title,
        "theme": theme,
        "total": total,
        "groups": groups,
    }
    (data_dir / "content.json").write_text(
        json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"分组 {len(groups)} 组 / 共 {total} 条：")
    for i, g in enumerate(groups, 1):
        print(f"  {i}. {g['name']}（{len(g['questions'])} 条）")
    print(f"-> {data_dir}/content.json")


if __name__ == "__main__":
    main()

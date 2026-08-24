#!/usr/bin/env python3
"""大众占卜情绪画像脚本：读 content.json → 逐选项 LLM 抽情绪关键词 → 查 emotion_color_map → 写回 options[].mood。

幂等：已有 mood 的选项跳过（--force 全部重抽）。可离线补跑、可手工改。
用法：
    python3 generate_emotion_profile.py <数据目录> [--force]
环境：DEEPSEEK_API_KEY（回退 LLM_API_KEY）、LLM_API_BASE、LLM_MODEL（复用 generate_mass_divination.llm_call）。
"""
import argparse
import json
import pathlib
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor

from generate_mass_divination import extract_json, llm_call, load_prompt

SKILL = pathlib.Path(__file__).resolve().parent.parent
MOOD_MAP_PATH = SKILL / "data" / "emotion_color_map.json"


def load_mood_map() -> dict:
    return json.loads(MOOD_MAP_PATH.read_text(encoding="utf-8"))


def match_archetype(mood_map: dict, label: str, keywords: list[str], interpretation: str) -> dict:
    """关键词子串命中 + label 命中加权，取最高分原型；score=0 回退 fallback。"""
    text = (interpretation or "") + " " + " ".join(keywords or [])
    label = (label or "").strip()
    best, best_score = None, 0
    for a in mood_map["archetypes"]:
        score = sum(1 for kw in a["keywords"] if kw and kw in text)
        if label and (label == a["mood"] or label in a["mood"] or a["mood"] in label):
            score += 3
        if score > best_score:
            best, best_score = a, score
    return best or mood_map["fallback"]


def parse_short_keywords(interpretation: str) -> list[str]:
    """短图文快路径：解读开头 **关键词** 组（4~8 个顿号分隔词）就是情绪关键词，直接解析省一次 LLM 调用。
    返回 [] = 非短图文/解析失败，回退 LLM 抽取。"""
    m = re.search(r"\*\*关键词\*\*[：:]?\s*(.*)", interpretation or "")
    if not m:
        return []
    line = m.group(1).strip()
    if not line:  # 标题独占一行 → 取下一非空行
        line = next((l.strip() for l in interpretation[m.end():].splitlines() if l.strip()), "")
    kws = [k.strip() for k in re.split(r"[、，,\s]+", line) if 1 <= len(k.strip()) <= 6]
    return kws[:8] if 2 <= len(kws) else []


def extract_one_mood(question: str, option: dict) -> tuple[str, list[str]]:
    """单选项情绪抽取：LLM 输出 {label, keywords}。"""
    sys_p, usr = load_prompt("extract_emotion.md")
    cards = [c["name"] for c in option.get("cards", [])]
    ctx = {
        "question": question,
        "optionLabel": option.get("id", ""),
        "cardsNames": "、".join(cards),
        "interpretation": option.get("interpretation", ""),
    }
    for k, v in ctx.items():
        usr = usr.replace("{{" + k + "}}", str(v))
    raw = llm_call(sys_p, usr, temperature=0.3, max_tokens=300)
    res = extract_json(raw)
    label = str(res.get("label", "")).strip()
    kws = [str(k).strip() for k in res.get("keywords", []) if str(k).strip()]
    return label, kws


def enrich(content: dict, force: bool = False) -> dict:
    q = content.get("question", "")
    mmap = load_mood_map()
    opts = [o for o in content.get("options", []) if force or not o.get("mood")]

    def _extract(opt: dict) -> tuple[str, list[str]]:
        kws = parse_short_keywords(opt.get("interpretation", ""))
        if kws:
            return "", kws  # 快路径：label 置空 → match_archetype 用原型 mood 名
        try:
            return extract_one_mood(q, opt)
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠ 选项{opt.get('id')} 情绪抽取失败: {e}，用 fallback")
            return "", []

    # 并发抽取（每选项一次 LLM 调用，纯 I/O 等待）
    with ThreadPoolExecutor(max_workers=max(1, len(opts))) as ex:
        results = list(ex.map(_extract, opts))
    used_motifs: set[str] = set()
    for opt, (label, kws) in zip(opts, results):
        arch = match_archetype(mmap, label, kws, opt.get("interpretation", ""))
        # 每格画面主体（motif）：从原型物象库挑一个，跨选项去重防封面各格雷同
        pool = [mo for mo in arch.get("motifs", []) if mo not in used_motifs] or arch.get("motifs", [])
        motif = random.choice(pool) if pool else ""
        used_motifs.add(motif)
        opt["mood"] = {
            "label": label or arch["mood"],
            "keywords": kws,
            "primary_color": arch["primary_color"],
            "color_name": arch["color_name"],
            "atmosphere": arch["atmosphere"],
            "motif": motif,
        }
        print(f"  选项{opt.get('id')} 情绪「{opt['mood']['label']}」主色 {arch['color_name']}({arch['primary_color']}) 主体「{motif}」")
    return content


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir", help="含 content.json 的数据目录")
    ap.add_argument("--force", action="store_true", help="已有 mood 也重新抽取")
    args = ap.parse_args()
    d = pathlib.Path(args.data_dir)
    cj = d / "content.json"
    content = json.loads(cj.read_text(encoding="utf-8"))
    content = enrich(content, force=args.force)
    cj.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 已写回 {cj}")


if __name__ == "__main__":
    main()

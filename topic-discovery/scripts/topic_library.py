#!/usr/bin/env python3
"""选题库管理：跨平台选题探索的统一 Excel 库。

库文件：<项目根>/topic-library/选题库.xlsx，sheet「选题库」，12 列：
  platform/scraped_at/keyword/title/author/metric/metric_num/link/
  breakout_score/evidence/status/note

去重规则（双保险，跨平台同样适用）：
  1. 链接精确去重（同一链接不再入库）
  2. 规范化标题去重（去 emoji/标点/空白后比对，同选题不同链接也不重复）

状态：status ∈ {未用, 已用, 已废弃}，默认 未用。推荐时只推 未用。

子命令：
  add <json...> [--keyword 大众占卜] [--platform X] [--llm-filter]
      json 可为文件路径或 -（stdin）。兼容：
        - browser-act eval 抓取格式（title/author/likes/link）
        - viral-topic 各平台脚本 stdout（{platform,...,results:[...]}）
        - 红狐 xhs-hotnotes 格式（title/authorNickname/interactiveCount/noteLink）
  list [--keyword] [--platform] [--status] [--limit] [--format]
  mark --match <标题片段或链接> --status {已用,已废弃} [--platform]
  recommend [--keyword] [--platform] [-n] [--sort metric|breakout] [--random]
  migrate [--jsonl topic-library/xhs-topics.jsonl]    # 存量 jsonl 一次性迁入
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import random
import re
import sys
import unicodedata
import urllib.request
from datetime import datetime
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

SKILL = pathlib.Path(__file__).resolve().parent.parent  # skill 目录
STORE_DIR = SKILL / "data"
STORE = STORE_DIR / "选题库.xlsx"
SHEET = "选题库"
REJECTS = STORE_DIR / "xhs-topics-rejected.jsonl"  # LLM 剔除记录，避免每轮重复送审

HEADERS = [
    "platform", "scraped_at", "keyword", "title", "author",
    "metric", "metric_num", "link", "breakout_score", "evidence",
    "status", "note",
]
COL_WIDTHS = [12, 20, 12, 52, 16, 14, 12, 46, 12, 42, 8, 20]

PLATFORM_CN = {
    "xiaohongshu": "小红书", "xhs": "小红书", "red": "小红书",
    "bilibili": "B站", "bili": "B站", "b站": "B站",
    "wechat": "公众号", "weixin": "公众号", "微信": "公众号",
    "x": "X", "twitter": "X", "推特": "X",
    "youtube": "YouTube", "油管": "YouTube", "yt": "YouTube",
    "douyin": "抖音", "dy": "抖音", "抖音": "抖音",
}

_STRIP = re.compile(r"[\s#＃@，。！？!?、,.\-—_~～|｜【】\[\]()（）:：\"'“”‘’·…]+")
_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️‍️]+")


def norm_title(t: str) -> str:
    """标题规范化：去 emoji/标点/空白后小写，用于选题级去重。"""
    t = unicodedata.normalize("NFKC", t or "")
    return _EMOJI.sub("", _STRIP.sub("", t)).lower()


def pick(a: dict, *keys: str) -> str:
    for k in keys:
        if a.get(k):
            return str(a[k]).strip()
    return ""


def as_int(v: Any, default: int = 0) -> int:
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except (TypeError, ValueError):
        return default


def parse_num(s: Any) -> int:
    """'8593'→8593；'1.1万'→11000；'2w+'→20000；'12.3万播放'→123000；'8.4k'→8400。"""
    if s is None:
        return 0
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([万wWkK])?", str(s))
    if not m:
        return 0
    mult = {"万": 10000, "w": 10000, "k": 1000}.get((m.group(2) or "").lower(), 1)
    return int(float(m.group(1)) * mult)


def norm_platform(s: str) -> str:
    if not s:
        return ""
    return PLATFORM_CN.get(str(s).strip().lower(), str(s).strip())


# ---------- 输入解析 ----------

def read_payload(path: str) -> Any:
    """读 JSON 文件（或 stdin '-'），支持带日志头尾的红狐输出。"""
    raw = sys.stdin.read() if path == "-" else pathlib.Path(path).read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\n\}", raw, re.S)
        if not m:
            return None
        return json.loads(m.group(0))


def extract_items(data: Any) -> list[dict]:
    """兼容纯数组 / {results|items|articles|data|result:[...]}。"""
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    if not isinstance(data, dict):
        return []
    for key in ("results", "items", "articles", "data", "result"):
        v = data.get(key)
        if isinstance(v, list):
            return [d for d in v if isinstance(d, dict)]
    return []


def resolve_platform(override: str, data: Any, items: list[dict]) -> str:
    """平台解析：--platform > 文件顶层 platform > 首条 item platform > 默认小红书。"""
    if override:
        return norm_platform(override)
    if isinstance(data, dict) and data.get("platform"):
        return norm_platform(str(data["platform"]))
    for item in items:
        if item.get("platform"):
            return norm_platform(str(item["platform"]))
    print("⚠ 未指定平台且输入无 platform 字段，默认按小红书处理", file=sys.stderr)
    return "小红书"


def build_candidate(item: dict, platform: str, keyword: str, now: str) -> dict | None:
    """把一条原始采集项归一化为 12 列候选行。"""
    title = pick(item, "title")
    if not title:
        return None
    link = pick(item, "url", "link", "noteLink").split("?")[0].split("#")[0]
    author = pick(item, "author_name", "author", "authorNickname")
    try:
        bscore = float(item.get("breakout_score") or item.get("viral_score") or 0)
    except (TypeError, ValueError):
        bscore = 0.0
    evidence = " | ".join(str(e) for e in (item.get("evidence") or []) if e)
    content_id = str(item.get("content_id") or "")
    note = f"id={content_id}" if content_id else ""

    if platform == "小红书":
        likes = pick(item, "likes", "interactiveCount", "likedCount")
        metric = f"{likes}赞" if likes else ""
        metric_num = parse_num(likes)
    elif platform in ("B站", "YouTube"):
        v = as_int(item.get("view_count"))
        metric = f"{v}播放" if v else ""
        metric_num = v
    elif platform == "公众号":
        v = as_int(item.get("view_count"))
        metric = f"{v}阅读" if v else ""
        metric_num = v
    elif platform == "X":
        v = as_int(item.get("view_count"))
        metric = f"{v}浏览" if v else ""
        metric_num = v
    elif platform == "抖音":
        p = pick(item, "plays")
        metric = f"{p}播放" if p else ""
        metric_num = parse_num(p)
    else:
        v = as_int(item.get("view_count"))
        metric = f"{v}" if v else ""
        metric_num = v

    return {
        "platform": platform, "scraped_at": now, "keyword": keyword,
        "title": title, "author": author, "metric": metric, "metric_num": metric_num,
        "link": link, "breakout_score": bscore, "evidence": evidence,
        "status": "未用", "note": note,
    }


# ---------- Excel 读写 ----------

def style_header(ws) -> None:
    fill = PatternFill("solid", fgColor="FFF2CC")
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = fill


def set_widths(ws) -> None:
    for col, w in zip("ABCDEFGHIJKL", COL_WIDTHS):
        ws.column_dimensions[col].width = w


def load_wb():
    """取工作簿（不存在则建表头），返回 (wb, ws)。"""
    if not STORE.exists():
        STORE_DIR.mkdir(parents=True, exist_ok=True)
        wb = Workbook()
        ws = wb.active
        ws.title = SHEET
        ws.append(HEADERS)
        style_header(ws)
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(len(HEADERS))}1"
        set_widths(ws)
        wb.save(STORE)
    else:
        wb = load_workbook(STORE)
        ws = wb[SHEET] if SHEET in wb.sheetnames else wb.active
    return wb, ws


def read_rows(ws) -> list[dict]:
    """读有效行：只认 title 非空的行（跳过 delete_rows 留下的孤立 link 幽灵行）。"""
    rows: list[dict] = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if r and (r[HEADERS.index("title")] or "").strip():
            rows.append(dict(zip(HEADERS, r)))
    return rows


def append_new_row(ws, c: dict) -> None:
    ws.append([c.get(h, "") for h in HEADERS])
    link = str(c.get("link") or "")
    if link:
        cell = ws.cell(row=ws.max_row, column=HEADERS.index("link") + 1)
        cell.hyperlink = link


def load_rejects() -> set[str]:
    """LLM 剔除标题集合（只对小红书行生效）。"""
    out: set[str] = set()
    if REJECTS.exists():
        for line in REJECTS.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    out.add(norm_title(json.loads(line).get("title", "")))
                except (json.JSONDecodeError, TypeError):
                    continue
    return out


def insert_rows(candidates: list[dict]) -> tuple[list[dict], int, int]:
    """去重后追加。返回 (added, skipped, total)。同一调用内多文件也互相去重。"""
    wb, ws = load_wb()
    existing = read_rows(ws)
    seen_links = {str(r.get("link") or "") for r in existing if r.get("link")}
    seen_titles = {norm_title(str(r.get("title") or "")) for r in existing if r.get("title")}
    seen_rejects = load_rejects()

    added: list[dict] = []
    skipped = 0
    for c in candidates:
        title = str(c.get("title") or "").strip()
        if not title:
            skipped += 1
            continue
        link = str(c.get("link") or "")
        nt = norm_title(title)
        if nt in seen_rejects and c.get("platform") == "小红书":
            skipped += 1
            continue
        if (link and link in seen_links) or (nt and nt in seen_titles):
            skipped += 1
            continue
        seen_links.add(link)
        seen_titles.add(nt)
        added.append(c)

    if added:
        for c in added:
            append_new_row(ws, c)
        wb.save(STORE)
    return added, skipped, len(existing) + len(added)


# ---------- LLM 过滤（小红书行，可选） ----------

FILTER_PROMPT = """你是小红书内容分类器。判断下面每个标题是否属于「{keyword}」类帖子选题。

算{keyword}（保留）：与 {keyword} 主题相关的面向大众的解读/测试/占卜帖。
不算（剔除）：品牌广告、明星/影视剧周边、晒牌/开箱、AI 工具/技术教程、招聘、与 {keyword} 无关的内容、纯运势无占卜形式。

只输出 JSON：{{"keep": [序号...]}}，序号为保留项（从 1 开始），不要输出其他文字。

标题列表：
{titles}"""


def llm_filter(candidates: list[dict], keyword: str) -> list[dict]:
    """调 DeepSeek 过滤非 keyword 选题。无 Key 时原样返回并告警。"""
    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY")
    if not key:
        print("⚠ 无 DEEPSEEK_API_KEY，跳过 LLM 过滤", file=sys.stderr)
        return candidates
    base = os.environ.get("LLM_API_BASE", "https://api.deepseek.com").rstrip("/")
    model = os.environ.get("LLM_MODEL", "deepseek-chat")
    kept: list[dict] = []
    rejected: list[dict] = []
    for off in range(0, len(candidates), 60):
        batch = candidates[off : off + 60]
        titles = "\n".join(f"{i + 1}. {e['title']}" for i, e in enumerate(batch))
        content = FILTER_PROMPT.format(keyword=keyword, titles=titles)
        body = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0,
            "max_tokens": 2000,
            "stream": False,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{base}/chat/completions", data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            text = json.loads(resp.read())["choices"][0]["message"]["content"].strip()
        m = re.search(r"\{.*\}", text, re.S)
        keep_idx = set(json.loads(m.group(0)).get("keep", [])) if m else set()
        for i, e in enumerate(batch):
            if i + 1 in keep_idx:
                kept.append(e)
            else:
                rejected.append(e)
                print(f"  ✗ 剔除: {e['title']}")
    if rejected:
        STORE_DIR.mkdir(parents=True, exist_ok=True)
        with REJECTS.open("a", encoding="utf-8") as fp:
            for e in rejected:
                fp.write(json.dumps({"scraped_at": e.get("scraped_at", ""), "title": e["title"]}, ensure_ascii=False) + "\n")
    return kept


MASS_DIVINATION_PROMPT = """你是大众占卜选题筛选器。判断下面每个小红书标题是否适合作为「大众占卜问题」，并清洗成标准问题。

【适合大众占卜（is_valid=true）】：
- 是问句（含？或疑问词），或可占卜的泛化主题（你的XX、今年XX、近X月XX、Ta的XX、正缘、桃花、财富、事业、复合等）
- 泛化，针对大众，不针对具体某个对象
- 「你」的视角

【不适合（is_valid=false）】：
- 陈述句（不是问题，如「他不在试探，直接提出复合」）
- 传讯/密语类（有缘人传讯、宇宙传讯、高我密语、传讯、密语等）
- 非占卜内容（网站、教程、星座、股票、心理测试、晒牌开箱）
- 针对具体对象的具体叙述
- 多问题混杂（一个标题含多个问号或多个并列问题）
- 过长（清洗后超过 25 字）
- 含操作说明/引导文字（如「男女性别可对调」「关注我看更多」）

【清洗规则（仅对 is_valid=true 的）】：
- 去作者名、去 #标签、去前缀词（大众占卜、合集、Timeless 等）
- 保留 emoji 符号（🔮✨❤️ 等）
- 提取真正的占卜问题（不含前缀/标签/作者）

只输出 JSON：{{"results": [{{"index": 1, "is_valid": true, "question": "清洗后问题"}}, ...]}}，index 从 1 开始。

标题列表：
{titles}"""


def llm_clean_mass_divination(titles: list[str]) -> list[dict]:
    """批量判断+清洗选题：哪些是合适的大众占卜问题，并清洗成标准问题（去作者/去标签/保留emoji）。
    返回 [{"index": N, "is_valid": bool, "question": str}, ...]，无 Key 时原样返回（全部判 valid）。"""
    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY")
    if not key:
        print("⚠ 无 DEEPSEEK_API_KEY，跳过 LLM 清洗判断", file=sys.stderr)
        return [{"index": i + 1, "is_valid": True, "question": t} for i, t in enumerate(titles)]
    base = os.environ.get("LLM_API_BASE", "https://api.deepseek.com").rstrip("/")
    model = os.environ.get("LLM_MODEL", "deepseek-chat")
    results: list[dict] = []
    for off in range(0, len(titles), 50):
        batch = titles[off:off + 50]
        numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(batch))
        content = MASS_DIVINATION_PROMPT.format(titles=numbered)
        body = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0,
            "max_tokens": 4000,
            "stream": False,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{base}/chat/completions", data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            text = json.loads(resp.read())["choices"][0]["message"]["content"].strip()
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                parsed = json.loads(m.group(0))
                for r in parsed.get("results", []):
                    idx = int(r.get("index", 0)) - 1
                    if 0 <= idx < len(batch):
                        results.append({
                            "index": off + idx + 1,
                            "is_valid": bool(r.get("is_valid", True)),
                            "question": r.get("question", batch[idx]),
                        })
            except json.JSONDecodeError:
                for i, t in enumerate(batch):
                    results.append({"index": off + i + 1, "is_valid": True, "question": t})
    return results


# ---------- 子命令 ----------

def cmd_add(args: argparse.Namespace) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    candidates: list[dict] = []
    for path in args.json_files:
        data = read_payload(path)
        if data is None:
            print(f"⚠ 无法解析 {path}", file=sys.stderr)
            continue
        items = extract_items(data)
        if not items:
            print(f"⚠ {path} 内无 results/items", file=sys.stderr)
            continue
        platform = resolve_platform(args.platform, data, items)
        for item in items:
            cand = build_candidate(item, platform, args.keyword, now)
            if cand:
                candidates.append(cand)

    if args.llm_filter:
        xhs = [c for c in candidates if c["platform"] == "小红书"]
        others = [c for c in candidates if c["platform"] != "小红书"]
        if xhs:
            candidates = llm_filter(xhs, args.keyword) + others

    if args.min_likes > 0:
        kept: list[dict] = []
        dropped = 0
        for c in candidates:
            if c["platform"] == "小红书" and int(c.get("metric_num") or 0) < args.min_likes:
                dropped += 1
                continue
            kept.append(c)
        if dropped:
            print(f"小红书低赞过滤 {dropped} 条（<{args.min_likes}赞）")
        candidates = kept

    added, skipped, total = insert_rows(candidates)
    print(f"新增 {len(added)} 条，去重跳过 {skipped} 条，库内共 {total} 条 → {STORE}")
    for c in added:
        print(f"  + [{c['metric']}] {c['title']}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    _, ws = load_wb()
    rows = read_rows(ws)
    out: list[dict] = []
    for r in rows:
        if args.keyword and args.keyword not in str(r.get("keyword") or ""):
            continue
        if args.platform and norm_platform(args.platform) != r.get("platform"):
            continue
        if args.status and r.get("status") != args.status:
            continue
        out.append(r)
    if args.limit:
        out = out[: args.limit]
    if args.format == "json":
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    for i, r in enumerate(out, 1):
        print(f"[{i}] [{r.get('platform')}] {r.get('metric')} | {r.get('title')} | 作者:{r.get('author')} | {r.get('link')}")
    print(f"\n共 {len(out)} 条")
    return 0


def cmd_mark(args: argparse.Namespace) -> int:
    wb, ws = load_wb()
    rows = read_rows(ws)
    match = args.match
    nm = norm_title(match)
    hits: list[tuple[int, dict]] = []
    for idx, r in enumerate(rows):
        if args.platform and norm_platform(args.platform) != r.get("platform"):
            continue
        title = str(r.get("title") or "")
        link = str(r.get("link") or "")
        if match in link or match in title or (nm and nm == norm_title(title)):
            hits.append((idx, r))
    if not hits:
        print(f"✗ 未匹配到任何选题（match={match}）", file=sys.stderr)
        return 1
    for idx, r in hits:
        print(f"[行{idx + 2}] [{r.get('platform')}] {r.get('metric')} | {r.get('title')} | {r.get('link')}")
    print(f"\n将 {len(hits)} 条标记为「{args.status}」...")
    status_col = HEADERS.index("status") + 1
    for idx, _ in hits:
        ws.cell(row=idx + 2, column=status_col, value=args.status)
    wb.save(STORE)
    print("已保存")
    return 0


def cmd_recommend(args: argparse.Namespace) -> int:
    _, ws = load_wb()
    rows = read_rows(ws)
    cands: list[dict] = []
    for r in rows:
        if r.get("status") != "未用":
            continue
        if args.keyword and args.keyword not in str(r.get("keyword") or ""):
            continue
        if args.platform and norm_platform(args.platform) != r.get("platform"):
            continue
        cands.append(r)
    # LLM 过滤 + 清洗：只留适合大众占卜的选题，并清洗成标准问题（去作者/标签、保留 emoji）
    if cands and not getattr(args, "no_filter", False):
        print(f"LLM 过滤清洗 {len(cands)} 条候选...", file=sys.stderr)
        results = llm_clean_mass_divination([r["title"] for r in cands])
        kept: list[dict] = []
        dropped = 0
        for r, res in zip(cands, results):
            if res.get("is_valid", True):
                r["question"] = res.get("question", r["title"])
                kept.append(r)
            else:
                dropped += 1
        cands = kept
        if dropped:
            print(f"  过滤掉 {dropped} 条不适合大众占卜的选题", file=sys.stderr)
    if args.random:
        random.shuffle(cands)
    elif args.sort == "breakout":
        cands.sort(key=lambda r: float(r.get("breakout_score") or 0), reverse=True)
    else:
        cands.sort(key=lambda r: int(r.get("metric_num") or 0), reverse=True)
    shown = cands[: args.limit]
    for i, r in enumerate(shown, 1):
        display = r.get("question") or r.get("title")
        print(f"[{i}] [{r.get('platform')}] {r.get('metric')} | {display}")
        if r.get("author"):
            print(f"    作者: {r.get('author')}")
        print(f"    链接: {r.get('link')}")
    print(f"\n共 {len(cands)} 条候选（未用，已过滤），已展示 {len(shown)} 条")
    if not cands:
        print("（暂无符合条件的大众占卜选题，先去采集入库）")
    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    p = pathlib.Path(args.jsonl)
    if not p.exists():
        print(f"✗ 找不到 {p}", file=sys.stderr)
        return 1
    candidates: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        title = pick(r, "title")
        if not title:
            continue
        likes = pick(r, "likes")
        sort = pick(r, "sort")
        candidates.append({
            "platform": "小红书",
            "scraped_at": pick(r, "scraped_at"),
            "keyword": pick(r, "keyword") or "大众占卜",
            "title": title,
            "author": pick(r, "author"),
            "metric": f"{likes}赞" if likes else "",
            "metric_num": parse_num(likes),
            "link": pick(r, "link").split("?")[0],
            "breakout_score": 0,
            "evidence": "",
            "status": "未用",
            "note": f"排序:{sort}" if sort else "",
        })
    added, skipped, total = insert_rows(candidates)
    print(f"迁移完成：新增 {len(added)} 条，去重跳过 {skipped} 条，库内共 {total} 条 → {STORE}")
    for c in added:
        print(f"  + [{c['metric']}] {c['title']}")
    return 0


def cmd_prune(args: argparse.Namespace) -> int:
    """删除低赞选题（默认只删未用，--include-used 连已用/已废弃一起删）。

    用重建工作簿方式实现（不 delete_rows：openpyxl 删行会留孤立 link 幽灵行）。
    """
    load_wb()  # 确保文件存在
    _, ws = load_wb()
    rows = read_rows(ws)
    kept: list[dict] = []
    to_delete: list[dict] = []
    for r in rows:
        hit = (not args.platform or norm_platform(args.platform) == r.get("platform")) and (
            r.get("status") == "未用" or args.include_used
        ) and int(r.get("metric_num") or 0) < args.min_likes
        (to_delete if hit else kept).append(r)
    for r in to_delete[:50]:
        print(f"  - [{r.get('platform')}] {r.get('metric')} | {r.get('title')}")
    if len(to_delete) > 50:
        print(f"  ... 等，共 {len(to_delete)} 条")

    # 重建工作簿（顺带清掉 delete_rows 遗留的幽灵行；即使 0 删除也重建，保持文件规范）
    new_wb = Workbook()
    new_ws = new_wb.active
    new_ws.title = SHEET
    new_ws.append(HEADERS)
    style_header(new_ws)
    new_ws.freeze_panes = "A2"
    new_ws.auto_filter.ref = f"A1:{get_column_letter(len(HEADERS))}1"
    set_widths(new_ws)
    for r in kept:
        append_new_row(new_ws, r)
    new_wb.save(STORE)
    if to_delete:
        print(f"已删除 {len(to_delete)} 条低赞选题 → {STORE}（现 {len(kept)} 条）")
    else:
        print(f"无低赞选题需删，已重建工作簿（现 {len(kept)} 条）")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="选题库管理：跨平台选题探索的 Excel 库")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="把各平台采集 JSON 入库（文件或 stdin -）")
    p_add.add_argument("json_files", nargs="+")
    p_add.add_argument("--keyword", default="大众占卜")
    p_add.add_argument("--platform", default="", help="平台覆盖，browser-act 轮次无 platform 字段时用")
    p_add.add_argument("--llm-filter", action="store_true", help="对小红书行做 DeepSeek 选题过滤")
    p_add.add_argument("--min-likes", type=int, default=200, help="小红书低赞过滤：低于该赞数不入库（默认200，设0关闭）")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="查看库内选题")
    p_list.add_argument("--keyword", default="")
    p_list.add_argument("--platform", default="")
    p_list.add_argument("--status", default="")
    p_list.add_argument("--limit", type=int, default=50)
    p_list.add_argument("--format", choices=["table", "json"], default="table")
    p_list.set_defaults(func=cmd_list)

    p_mark = sub.add_parser("mark", help="标记选题状态（已用/已废弃）")
    p_mark.add_argument("--match", required=True, help="标题片段或链接")
    p_mark.add_argument("--status", choices=["已用", "已废弃"], default="已用")
    p_mark.add_argument("--platform", default="")
    p_mark.set_defaults(func=cmd_mark)

    p_rec = sub.add_parser("recommend", help="推荐未用选题（赛道+热度）")
    p_rec.add_argument("--keyword", default="")
    p_rec.add_argument("--platform", default="")
    p_rec.add_argument("-n", "--limit", type=int, default=20)
    p_rec.add_argument("--sort", choices=["metric", "breakout"], default="metric")
    p_rec.add_argument("--random", action="store_true")
    p_rec.add_argument("--no-filter", action="store_true", help="跳过 LLM 过滤清洗（默认过滤掉不适合大众占卜的选题）")
    p_rec.set_defaults(func=cmd_recommend)

    p_mig = sub.add_parser("migrate", help="迁移存量 jsonl 进 Excel")
    p_mig.add_argument("--jsonl", default=str(STORE_DIR / "xhs-topics.jsonl"))
    p_mig.set_defaults(func=cmd_migrate)

    p_prune = sub.add_parser("prune", help="删除低赞选题（默认只删未用）")
    p_prune.add_argument("--min-likes", type=int, default=200)
    p_prune.add_argument("--platform", default="")
    p_prune.add_argument("--include-used", action="store_true", help="连已用/已废弃的低赞行一起删")
    p_prune.set_defaults(func=cmd_prune)

    args = ap.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()

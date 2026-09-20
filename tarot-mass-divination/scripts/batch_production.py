#!/usr/bin/env python3
"""批量生产驱动（2026-08-25）：20 题 → 20 张四宫格封面 + 16 长图文 + 15 短图文（10 羊皮纸 + 5 memo 备忘录）。

分发方案（用户确认）：
  - 20 题全做 4 宫格封面，每题一张（分格图 --ref 随机参考 5 张单图风格之一，版式由 render_cover HTML 保证）
  - 11 个热度最高题做「长图文 + 短图文」双版本，5 题只做长图文，4 题只做短图文
  - 15 套短图文中 10 套羊皮纸（parchment）+ 5 套备忘录（memo）
  - 目录：长图文 → <out>/<问题>/；短图文 → <out>/<问题>短图/；双版本共用同一张封面
  - 交付只留 封面.png + 选项图（清 content.json/cards/out/cover.html）

用法:
  python3 batch_production.py --dry-run          # 打印 20 题分发清单
  python3 batch_production.py [--workers 3] [--out 8.25素材] [--start N] [--end M]
"""
import argparse
import pathlib
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

BASE = pathlib.Path(__file__).resolve().parent.parent.parent.parent.parent  # ip-pipeline 根
SCRIPTS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import pipeline as P  # noqa: E402  复用 generate/gen_cover_verified/render_cover

GRID = 4

# (question, formats, short_theme)。formats 顺序：long 先（封面以长图文 content 的情绪画像为准）。
# 短图文 memo/parchment 分配：热度最高 5 套短图文 → memo，其余 10 套 → parchment。
PLAN = [
    # --- 双版本（长+短），Q1-Q5 短=memo，Q6-Q11 短=羊皮纸 ---
    ("你会遇到一个很狂热的年上恋人",             ["long", "short"], "memo"),
    ("有一个人正在考虑和你复合的事情",           ["long", "short"], "memo"),
    ("金桃花降临！真诚且温柔",                   ["long", "short"], "memo"),
    ("你觉得不可能但会发生的事",                 ["long", "short"], "memo"),
    ("你马上就不缺💰了",                        ["long", "short"], "memo"),
    ("你会收到一个意想不到的消息",               ["long", "short"], "parchment"),
    ("好事将至：一定会在你身上显化的好消息是什么！", ["long", "short"], "parchment"),
    ("你要开始过有钱人的生活了",                 ["long", "short"], "parchment"),
    ("身边对你有好感的人是谁，数量多吗？",        ["long", "short"], "parchment"),
    ("任何人都无法取代你的位置",                 ["long", "short"], "parchment"),
    ("心动生理性的喜欢",                         ["long", "short"], "parchment"),
    # --- 只做长图文 ---
    ("未来会后悔追自担吗",                       ["long"], None),
    ("正缘和你谁先动心，谁跟偏爱对方",           ["long"], None),
    ("窥探一下你未来的某个场景",                 ["long"], None),
    ("你这一生·获得·规避",                      ["long"], None),
    ("下一个关于你始料未及的变化",               ["long"], None),
    # --- 只做短图文（羊皮纸） ---
    ("解开彼此心里的误会",                       ["short"], "parchment"),
    ("小时候的你怎么看待现在的自己",             ["short"], "parchment"),
    ("未来你不相信但一定会发生的事！",           ["short"], "parchment"),
    ("你的婚后生活·现实版",                      ["short"], "parchment"),
]


def short_dir(question: str) -> pathlib.Path:
    return OUT / f"{question}短图"


def render_short(qdir: pathlib.Path, theme: str) -> None:
    r = subprocess.run(["python3", str(P.RENDER_SHORT), str(qdir), "--theme", theme],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"render_short({theme}) 失败: {r.stderr[-300:]}")


def cleanup(qdir: pathlib.Path, keep: list[str]) -> None:
    """交付清理：只留封面+选项图，删 content.json/cards/out/cover.html/.cells。"""
    for p in [qdir / "content.json", qdir / "cards", qdir / "out", qdir / "cover.html", qdir / ".cells"]:
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.exists():
            p.unlink()
    # 只保留 keep 里的文件（其余多余 PNG 一并清）
    for p in qdir.glob("*.png"):
        if p.name not in keep:
            p.unlink()


def process(idx: int, question: str, formats: list[str], theme: str | None) -> str:
    ts = f"jm-prod-{idx}"
    long_dir = OUT / question
    short_qdir = short_dir(question)
    summary = []

    def _gen(dir_: pathlib.Path, fmt: str):
        P.generate(question, GRID, dir_, fmt)
        summary.append(f"{fmt}生成✓")

    try:
        # ① 解读 → content.json（长图文优先，封面情绪画像以此为准）
        if "long" in formats:
            _gen(long_dir, "long")
        if "short" in formats:
            _gen(short_qdir, "short")

        # ② 情绪画像（长图文走 LLM，短图文走关键词快路径）
        cover_src = long_dir if "long" in formats else short_qdir
        r = subprocess.run(["python3", str(P.EMO_PROFILE), str(cover_src)],
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            print(f"  ⚠ 情绪画像失败（{r.stderr[-200:]}），封面回退通用 prompt", flush=True)

        # ③ 封面（每题一次，分格图 --ref 随机单图风格）
        cover = P.gen_cover_verified(question, GRID, ts, cover_src)
        if cover:
            summary.append("封面✓")
            if "short" in formats and "long" in formats:
                shutil.copy2(cover, short_qdir / "封面.png")
        else:
            summary.append("封面✗")

        # ④ 渲染选项图
        if "long" in formats:
            P.render(long_dir, "long")
            summary.append("长图渲染✓")
        if "short" in formats:
            render_short(short_qdir, theme)
            summary.append(f"短图渲染({theme})✓")

        # ⑤ 清理中间件
        if "long" in formats:
            cleanup(long_dir, ["封面.png"] + [f"选项{c}.png" for c in "ABCD"[:GRID]])
        if "short" in formats:
            keep = ["封面.png"] + [f"选项{c}-备忘录.png" if theme == "memo" else f"选项{c}.png"
                                   for c in "ABCD"[:GRID]]
            cleanup(short_qdir, keep)

        mark = "" if cover else "（缺封面，需人工补）"
        return f"[{idx}] {question} {formats} 短={theme} → {' + '.join(summary)}{mark}"
    except Exception as e:
        return f"[{idx}] {question}: 异常 {e}"


def main() -> None:
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default="8.25素材")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--start", type=int, default=1, help="从第 N 题开始（1 起）")
    ap.add_argument("--end", type=int, default=0, help="到第 N 题（含），0=全部")
    ap.add_argument("--only", default="", help="只重跑指定题号，逗号分隔（如 4,5,7），覆盖 start/end")
    args = ap.parse_args()
    OUT = BASE / args.out

    plan = PLAN
    if args.only:
        idxs = [int(x) for x in args.only.split(",") if x.strip()]
        plan = [p for n, p in enumerate(plan, 1) if n in idxs]
        args.start = idxs[0] if idxs else 1
    else:
        lo, hi = max(0, args.start - 1), len(plan) if args.end == 0 else args.end
        plan = plan[lo:hi]

    long_n = sum("long" in f for _, f, _ in plan)
    short_n = sum("short" in f for _, f, _ in plan)
    memo_n = sum(1 for _, _, t in plan if t == "memo")
    print(f"计划 {len(plan)} 题 → 长图文 {long_n} 套 + 短图文 {short_n} 套（其中 memo {memo_n} 套）→ {OUT}")
    if args.dry_run:
        for i, (q, fmts, t) in enumerate(plan, args.start):
            dirs = " + ".join(f"{OUT / q}" if f == "long" else str(short_dir(q)) for f in fmts)
            print(f"  [{i}] {q}  [{'/'.join(fmts)}] 短主题={t or '-'}  →  {dirs}")
        return

    OUT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(process, i, q, fmts, t) for i, (q, fmts, t) in enumerate(plan, args.start)]
        for f in futs:
            print(f.result(), flush=True)
    print("=== 批量生产完成 ===")


if __name__ == "__main__":
    main()

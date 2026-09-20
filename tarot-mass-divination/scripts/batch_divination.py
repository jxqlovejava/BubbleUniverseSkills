#!/usr/bin/env python3
"""并行批量生成大众占卜解读（长图文/短图文）。

对 <out>/ 下多个选题目录，每个选题在独立线程里串行跑
generate_*（荐阵→抽牌→LLM解读→content.json）+ render（→选项A/B/C.png）。

用法:
  # 长图文（默认）
  python3 batch_divination.py --out 8.15素材 [--n-options 3] [--workers 3] [--questions q1 q2 ...]
  # 短图文（3:4 定高，羊皮纸/纯黑主题）
  python3 batch_divination.py --out 8.16素材 --format short [--theme parchment|black]
  # --questions 留空 = 跑 out/ 下所有含 封面.png 的目录
  # 默认交付后清理 content.json/cards/out/.cells（只留选项图）；--keep 保留中间件

多套/双格式（同题换 seed，各套独立子目录 + 独立 seed）:
  # 每题同时跑长+短，各 3 套（长图文组1..3 / 短图文组1..3），不要封面，只留选项图
  python3 batch_divination.py --out 9.2素材-3x3 --questions q1 q2 q3 \
      --both --sets 3 --no-cover
  # 只长图文、每套 3 个选项
  python3 batch_divination.py --out x --format long --sets 3 --no-cover --questions q...
"""
import argparse
import pathlib
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

BASE = pathlib.Path(__file__).resolve().parent.parent.parent.parent.parent
SCRIPTS = pathlib.Path(__file__).resolve().parent
GEN_SCRIPTS = {
    "long": "generate_mass_divination.py",
    "short": "generate_short_divination.py",
}
RENDER_SCRIPTS = {
    "long": "render_mass_divination.py",
    "short": "render_short_divination.py",
}
# 中文目录标签：格式 → 「长图文/短图文」组名
FMT_CN = {"long": "长图文", "short": "短图文"}
# 短图文各主题选项图文件后缀（对齐 render_short_divination.SUFFIX）
SHORT_SUFFIX = {"parchment": "", "black": "-纯黑", "memo": "-备忘录"}
# 长图文高度告警线：高于用户认可批次上限（2026.8.12 ≈15.8k）才提示，勿按旧 12k 误报
LONG_HIGH_PX = 17000


def height_summary(files: list[pathlib.Path]) -> str:
    """长图文选项图高度报告（A=9268px 形式），有超 17k 追加 ⚠ 提示。"""
    from PIL import Image
    parts, high = [], False
    for p in sorted(files):
        letter = p.stem[len("选项"):]
        try:
            h = Image.open(p).size[1]
            high = high or h > LONG_HIGH_PX
        except Exception:  # noqa: BLE001
            h = None
        parts.append(f"{letter}={h}px" if h else f"{letter}=?")
    tail = f" ⚠超高(>{LONG_HIGH_PX})" if high else ""
    return " 高度 " + " ".join(parts) + tail


def gen_one(question: str, data_dir: pathlib.Path, n_options: int,
            fmt: str, theme: str, keep: bool, no_cover: bool,
            label: str = "", seed: int | None = None) -> str:
    """单个变体：generate + render（+清理）。label 非空 → 建 <问题>/<label>/ 子目录。"""
    qdir = data_dir / question
    if label:
        qdir = qdir / label
    qdir.mkdir(parents=True, exist_ok=True)
    who = question if not label else f"{question}/{label}"
    try:
        gen_cmd = [sys.executable, str(SCRIPTS / GEN_SCRIPTS[fmt]), question,
                   str(qdir), "--n-options", str(n_options)]
        if seed is not None:
            gen_cmd += ["--seed", str(seed)]
        # 短图文：非 memo 主题跳过 LLM 高亮摘录（省 1 次调用/选项，parchment/black 不消费 highlights）
        if fmt == "short" and theme != "memo":
            gen_cmd.append("--no-highlights")
        r1 = subprocess.run(gen_cmd, capture_output=True, text=True, timeout=600)
        if r1.returncode != 0:
            return f"✗ {who}: generate失败 {r1.stderr[-200:] or r1.stdout[-200:]}"
        render_cmd = [sys.executable, str(SCRIPTS / RENDER_SCRIPTS[fmt]), str(qdir)]
        if fmt == "short":
            render_cmd += ["--theme", theme]
        r2 = subprocess.run(render_cmd, capture_output=True, text=True, timeout=300)
        if r2.returncode != 0:
            return f"✗ {who}: render失败 {r2.stderr[-200:] or r2.stdout[-200:]}"
        # 长图文/短图文选项图都在目录根（01_封面.png + 选项X.png；黑版带 -纯黑 后缀）
        if no_cover:
            (qdir / "01_封面.png").unlink(missing_ok=True)   # 长图 render 会产默认封面，--no-cover 删
        base_dir = qdir
        suffix = SHORT_SUFFIX.get(theme, "") if fmt == "short" else ""
        opts = [base_dir / f"选项{chr(65+i)}{suffix}.png" for i in range(n_options)]
        missing = [o.name for o in opts if not o.exists()]
        if missing:
            return f"⚠ {who}: render成功但缺 {missing}"
        summary = height_summary(opts) if fmt == "long" else ""
        if not keep:
            for p in ["content.json", "cover.html", ".cells"]:
                (qdir / p).unlink(missing_ok=True)
            for d in ["cards", "out"]:
                shutil.rmtree(qdir / d, ignore_errors=True)
        return f"✅ {who}: {len(opts)} 张选项图{summary}"
    except Exception as e:
        return f"✗ {who}: 异常 {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(BASE / "8.15素材"), help="输出根目录")
    ap.add_argument("--n-options", type=int, default=3)
    ap.add_argument("--workers", type=int, default=3, help="并行度")
    ap.add_argument("--format", choices=["long", "short"], default="long",
                    help="长图文/短图文（--both 时忽略）")
    ap.add_argument("--both", action="store_true",
                    help="每题同时跑长图文+短图文（多套时各自建子目录）")
    ap.add_argument("--sets", type=int, default=1,
                    help="每题每个格式跑 N 套（同题换 seed，各套独立子目录）。默认 1")
    ap.add_argument("--seed-base", type=int, default=100,
                    help="多套 seed 起点；seed = seed_base + 题序*100 + 格式偏移 + 套序")
    ap.add_argument("--no-cover", action="store_true",
                    help="渲染后删除长图默认封面 01_封面.png（交付只要选项图时用）")
    ap.add_argument("--theme", choices=["parchment", "black", "memo"], default="parchment",
                    help="短图文主题（仅 --format short）")
    ap.add_argument("--keep", action="store_true",
                    help="保留 content.json/cards/out/.cells（默认交付后清理）")
    ap.add_argument("--questions", nargs="*", default=None,
                    help="指定选题（留空=out/下所有含封面.png的目录，按目录名排序）")
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out)
    if args.questions:
        questions = args.questions
    else:
        questions = sorted(d.name for d in out_dir.iterdir()
                           if d.is_dir() and (d / "封面.png").exists())

    # 展开变体任务：(question, label, seed)
    fmts = ["long", "short"] if args.both else [args.format]
    variants = []
    for qi, q in enumerate(questions):
        for f in fmts:
            for s in range(1, args.sets + 1):
                fmt_off = {"long": 0, "short": 1000}[f]
                seed = args.seed_base + qi * 100 + fmt_off + s if args.sets > 1 or args.both else None
                # 多套/双格式才建子目录（否则保持旧版：直接放 <问题>/ 根）
                label = f"{FMT_CN[f]}组{s}" if (args.sets > 1 or args.both) else ""
                variants.append((q, f, label, seed))

    multi = args.both or args.sets > 1
    print(f"批量生成 {len(questions)} 题 × {len(variants) // max(len(questions),1)} 变体"
          f"（format={'+'.join(fmts)}, n-options={args.n_options}, "
          f"workers={args.workers}{', no-cover' if args.no_cover else ''}）")
    if multi:
        print("  同题多套 → 各自独立子目录，seed 递增")
    for q, _fmt, label, seed in variants:
        print(f"  {q}" + (f"/{label}" if label else "") + (f"  seed={seed}" if seed else ""))

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(gen_one, q, out_dir, args.n_options, fmt,
                             args.theme, args.keep, args.no_cover,
                             label, seed): (q, label)
                   for q, fmt, label, seed in variants}
        # 每个 future 依提交顺序取结果即可（label 已含在 gen_one 返回串里）
        for fut in futures:
            r = fut.result()
            print(r, flush=True)
            results.append(r)
    print("=== 批量完成 ===")
    fails = [r for r in results if r.startswith("✗") or r.startswith("⚠")]
    if fails:
        print(f"需重跑 {len(fails)} 条：")
        for f in fails:
            print("  " + f)


if __name__ == "__main__":
    main()

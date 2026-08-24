#!/usr/bin/env python3
"""并行批量生成大众占卜解读长图文。

对 <out>/ 下多个选题目录，每个选题在独立线程里串行跑
generate_mass_divination（荐阵→抽牌→DeepSeek解读→content.json）+ render（→out/选项A/B/C.png）。

用法:
  python3 batch_divination.py --out 8.15素材 [--n-options 3] [--workers 3] [--questions q1 q2 ...]
  # --questions 留空 = 跑 out/ 下所有含 封面.png 的目录
"""
import argparse
import pathlib
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

BASE = pathlib.Path(__file__).resolve().parent.parent.parent.parent.parent
SCRIPTS = pathlib.Path(__file__).resolve().parent
GEN = SCRIPTS / "generate_mass_divination.py"
RENDER = SCRIPTS / "render_mass_divination.py"


def gen_one(question: str, data_dir: pathlib.Path, n_options: int) -> str:
    """单个选题：generate + render，返回结果描述。"""
    qdir = data_dir / question
    qdir.mkdir(parents=True, exist_ok=True)
    try:
        r1 = subprocess.run([sys.executable, str(GEN), question, str(qdir), "--n-options", str(n_options)],
                            capture_output=True, text=True, timeout=600)
        if r1.returncode != 0:
            return f"✗ {question}: generate失败 {r1.stderr[-200:] or r1.stdout[-200:]}"
        r2 = subprocess.run([sys.executable, str(RENDER), str(qdir)],
                            capture_output=True, text=True, timeout=300)
        if r2.returncode != 0:
            return f"✗ {question}: render失败 {r2.stderr[-200:] or r2.stdout[-200:]}"
        out = qdir / "out"
        opts = [f"选项{chr(65+i)}.png" for i in range(n_options)]
        missing = [o for o in opts if not (out / o).exists()]
        if missing:
            return f"⚠ {question}: render成功但缺 {missing}"
        return f"✅ {question}: {len(opts)} 张选项图"
    except Exception as e:
        return f"✗ {question}: 异常 {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(BASE / "8.15素材"), help="输出根目录")
    ap.add_argument("--n-options", type=int, default=3)
    ap.add_argument("--workers", type=int, default=3, help="并行度")
    ap.add_argument("--questions", nargs="*", default=None,
                    help="指定选题（留空=out/下所有含封面.png的目录，按目录名排序）")
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out)
    if args.questions:
        questions = args.questions
    else:
        questions = sorted(d.name for d in out_dir.iterdir()
                           if d.is_dir() and (d / "封面.png").exists())
    print(f"批量生成 {len(questions)} 篇（n-options={args.n_options}, workers={args.workers}）")
    for i, q in enumerate(questions, 1):
        print(f"  {i}. {q}")

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(gen_one, q, out_dir, args.n_options): q for q in questions}
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

#!/usr/bin/env python3
"""批量生成大众占卜封面图（3 宫格，即梦 Agent 参考图生图）。

对指定的固定选题列表逐个生成封面（不复用 pipeline.recommend_topics，
因为那些选题已标记「已用」且只出封面、不出长图文）。
输出：<out>/<问题>/封面.png

用法:
  python3 generate_covers.py [--limit 1] [--workers 3] [--out 8.15素材] [--questions "q1" "q2" ...]
"""
import argparse
import pathlib
import random
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

BASE = pathlib.Path(__file__).resolve().parent.parent.parent.parent.parent  # ip-pipeline 根
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # 找 pipeline.py
sys.path.insert(0, str(BASE / ".claude" / "skills" / "tarot-mass-divination" / "scripts"))
from pipeline import pick_ref_cover, gen_cover, clean_title, OUT_DEFAULT, REF_COVERS_DIR  # noqa: E402


def list_ref_covers() -> list[pathlib.Path]:
    """收集参考图并按文件名排序（保证分配顺序稳定）。"""
    covers = []
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        covers.extend(REF_COVERS_DIR.glob(ext))
    return sorted(set(covers))

# 25 个已选选题（清洗后的标准问题名）
DEFAULT_QUESTIONS = [
    "你吸引异性的魔力在哪里？",
    "你在吸引什么",
    "暗恋你的人多吗？质量怎么样？",
    "单身之拐点",
    "你正在吸引的正缘，藏在这4组磁场里",
    "你隐藏最深的 xp 是什么？",
    "你以为他对你的看法 VS 实际他对你的看法",
    "什么状态下 他觉得你最可爱",
    "你的正缘，偏偏爱上你这一点",
    "你结婚对象的过人之处",
    "你的天赋使命是什么（含职业方向）",
    "你今生的财富量级？",
    "下一步的人生进程是？",
    "你觉得不可能但会发生的事情",
    "被你低估的潜力和优点",
    "你身上哪一点，让别人不敢惹？",
    "摆脱人类身份，你会成为什么？",
    "你身上巨迷人的高级感？",
    "在发生什么你还不知道的事",
    "近一个月的好消息",
    "你即将迎来的转变",
    "最近将迎来什么好消息？",
    "老天爷提醒但你却忽略的事情",
    "你的贵人是谁？",
    "一年后的你在做什么？",
]

GRID = 3

# 感情/关系向选题 → 用影视人物参考图（欧美情侣形象）；非感情类用刺绣风景/水果油画
LOVE_MARKERS = ["吸引异性", "你在吸引什么", "暗恋", "单身", "正缘", "xp", "他对你的看法",
                "他觉得你", "结婚对象"]


def is_love_question(q: str) -> bool:
    return any(m in q for m in LOVE_MARKERS)


# 影视人物参考图特判：强制锁定欧美影视人物形象，防止即梦 Agent 偷懒换成默认 AI 脸
PERSON_LOCK = (
    "人物必须严格沿用参考图中那对欧美复古电影情侣的形象与面孔："
    "卷发女生、穿马甲白衬衫打领带的男生，保持欧美面孔特征、复古8mm胶片质感、自然光影与神情。"
    "严禁使用通用AI脸、网红脸或卡通脸，人物造型与参考图一致，只换互动场景和动作，绝不换人物本身。"
)


def gen_one(idx: int, question: str, ref: pathlib.Path, out_dir: pathlib.Path) -> str:
    """单个选题生成封面，输出 <out>/<问题>/封面.png，返回结果描述。ref 为指定参考图。"""
    qdir = out_dir / question
    qdir.mkdir(parents=True, exist_ok=True)
    # 唯一 task-space：避免复用之前失败轮次残留的同名 ego space（会继承坏 tab）
    ts = f"jm-cover-{idx}-{random.randint(1000, 9999)}"
    tmp = out_dir / f".tmp_cover_{idx}"
    try:
        # 覆盖 pipeline.gen_cover 的随机 pick，改用传入的 ref
        import subprocess as _sp
        from pipeline import AGENT_GEN
        prompt = (f"这是大众占卜封面图，{GRID}宫格，每个宫格一张图，每张图左下角一个选项。"
                  f"主题：{question}。请完全复刻参考图的版式和插画风格，生成一张全新的封面图，图片不要雷同。")
        if ref and "影视人物" in ref.name:
            prompt += " " + PERSON_LOCK
        cmd = ["python3", str(AGENT_GEN), prompt, "--out", str(tmp), "--task-space", ts]
        if ref:
            cmd += ["--ref", str(ref)]
        r = _sp.run(cmd, capture_output=True, text=True, timeout=520)
        import json
        cover = ""
        for line in (r.stdout + r.stderr).splitlines():
            if '"status": "ok"' in line and '"images"' in line:
                d = json.loads(line)
                imgs = d.get("images", [])
                if imgs:
                    cover = imgs[0]
                    break
        if not cover:
            err_tail = (r.stderr or r.stdout or "").strip()[-300:]
            return (f"[{idx}] {question}: ✗ 生成失败（无图片返回） ref={ref.name if ref else 'none'} "
                    f"| agent: {err_tail}")
        dst = qdir / "封面.png"
        shutil.copy2(cover, dst)
        return f"[{idx}] {question} ✅ ref={ref.name if ref else 'none'} ({dst.stat().st_size // 1024}KB)"
    except Exception as e:
        return f"[{idx}] {question}: 异常 {e} ref={ref.name if ref else 'none'}"
    finally:
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 个（验证用）")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--out", default=str(OUT_DEFAULT), help="输出目录（默认 8.14素材）")
    ap.add_argument("--questions", nargs="*", default=None, help="自定义选题列表（覆盖默认）")
    ap.add_argument("--ref-filter", default="", help="只跑参考图文件名含该子串的选题（保持原序号 round-robin 分配）")
    ap.add_argument("--only", type=int, nargs="*", default=None, help="只跑这些原序号（1-based，保持原语义分配）")
    args = ap.parse_args()

    questions = [clean_title(q) or q for q in (args.questions or DEFAULT_QUESTIONS)]
    if args.limit:
        questions = questions[: args.limit]

    # 参考图分配：感情类选题 → 影视人物（欧美情侣）；非感情类 → 刺绣/水果轮流
    # 保证：非感情类绝不用影视人像参考
    refs = list_ref_covers()
    film_refs = [r for r in refs if "影视人物" in r.name]
    non_film_refs = [r for r in refs if "影视人物" not in r.name]
    if not refs:
        print("⚠ 无参考图，将用纯文生图")
        film_refs = [None]
        non_film_refs = [None] * 2

    assignments: list[pathlib.Path | None] = []
    non_film_idx = 0
    for q in questions:
        if is_love_question(q):
            assignments.append(film_refs[0] if film_refs else None)
        else:
            assignments.append(non_film_refs[non_film_idx % len(non_film_refs)] if non_film_refs else None)
            non_film_idx += 1

    # ref-filter：只保留指定参考图的选题（保持原序号 → 对应原 ref 不变）
    if args.ref_filter:
        keep = [(i, q) for i, q in enumerate(questions, 1)
                if assignments[i - 1] and args.ref_filter in assignments[i - 1].name]
        questions = [q for _, q in keep]
        assignments = [assignments[i - 1] for i, _ in keep]
        print(f"--ref-filter {args.ref_filter}：保留 {len(questions)} 张")
    # --only：只跑指定原序号（保持原语义分配）
    if args.only is not None:
        keep = [(i, q) for i, q in enumerate(questions, 1) if i in args.only]
        questions = [q for _, q in keep]
        assignments = [assignments[i - 1] for i, _ in keep]
        print(f"--only {args.only}：保留 {len(questions)} 张")
    for i, (q, r) in enumerate(zip(questions, assignments), 1):
        print(f"  {i}. {q} → ref={r.name if r else 'none'}")

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    from collections import Counter
    print("参考图分配：", {f"{r}": c for r, c in Counter(a.name for a in assignments).items()})

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for r in ex.map(lambda t: gen_one(*t),
                        [(i, q, assignments[i - 1], out_dir)
                         for i, q in enumerate(questions, 1)]):
            print(r, flush=True)
            results.append(r)
    print("=== 封面生成完成 ===")
    fails = [r for r in results if "✗" in r or "异常" in r]
    if fails:
        print(f"失败 {len(fails)} 条：")
        for f in fails:
            print("  " + f)


if __name__ == "__main__":
    main()

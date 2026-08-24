#!/usr/bin/env python3
"""大众占卜端到端 pipeline：选题推荐 → 生成封面 → 生成占卜长图文 → 组织目录。

一条命令串起完整生产流程：
  1. 从选题库(topic-library/选题库.xlsx)随机推荐 N 个「未用」选题（清洗标题前缀）
  2. 参考「大众占卜参考封面图」用 jimeng-image Agent 模式生成每题的封面图（3/4 宫格）
  3. 用 tarot-mass-divination 生成每题的大众占卜长图文（--n-options = 宫格数）
  4. 每题建一个目录（8.14素材/<问题>/），放封面.png + 选项A/B/C(.D).png

用法:
  python3 pipeline.py --count 3 [--grid 3|4|random] [--out 8.14素材] [--dry-run]
"""
import argparse
import json
import pathlib
import random
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import openpyxl

BASE = pathlib.Path(__file__).resolve().parent.parent.parent.parent.parent  # ip-pipeline 根
TOPIC_XLSX = BASE / "topic-library" / "选题库.xlsx"
REF_COVERS_DIR = BASE / "大众占卜参考封面图"
JIMENG_SKILL = BASE / ".claude" / "skills" / "jimeng-image" / "scripts"
TAROT_SCRIPTS = pathlib.Path(__file__).resolve().parent
OUT_DEFAULT = BASE / "8.14素材"

AGENT_GEN = JIMENG_SKILL / "agent_generate.py"
GEN_MASS = TAROT_SCRIPTS / "generate_mass_divination.py"
RENDER_MASS = TAROT_SCRIPTS / "render_mass_divination.py"
GEN_SHORT = TAROT_SCRIPTS / "generate_short_divination.py"
RENDER_SHORT = TAROT_SCRIPTS / "render_short_divination.py"
EMO_PROFILE = TAROT_SCRIPTS / "generate_emotion_profile.py"
COVER_VERIFY = TAROT_SCRIPTS / "cover_verify.py"


def clean_title(title: str) -> str:
    """清洗选题标题：去 #标签、【】、括号备注、前缀词、作者账号名；保留 emoji。

    规则（用户明确）：去作者、去标签、保留 emoji 符号（抓流量的标题 emoji 要留）。
    """
    t = (title or "").strip()
    # 1. 去 # 标签（#xxx 到空白/行尾），正文和 emoji 保留
    t = re.sub(r'#\S+', ' ', t).strip()
    # 2. 【xxx】删；《xxx》提取内容（书引号里常是真占卜问题）；（）备注删；末尾不闭合括号删
    t = re.sub(r'【[^】]*】', '', t)
    t = re.sub(r'《([^》]*)》', r'\1', t)
    t = re.sub(r'[（(][^）)]*[）)]', '', t)
    t = re.sub(r'[（(][^）)]*$', '', t)
    # 3. 去前缀词（现占/大众/众占/Timeless/合集/答案/测试/暗恋专场/日期 等）
    t = re.sub(r'^(?:合集|Timeless|现占|众占|大众|答案|测试|DD塔罗|心理测试|有缘人传讯|暗恋专场|系列篇\d*|\d+\.\d+|月日)\s*[｜|:：]?\s*', '', t)
    # 4. 去重复的账号名片段（如「月亮塔罗师 月亮塔罗师」）
    t = re.sub(r'(.{2,12})\s+\1', r'\1', t)
    # 5. 去开头作者账号名：账号名含数字/字母/*，后跟空格/分隔，接长内容（避免误伤纯中文问题）
    m = re.match(r'^([^\s，。？?！!｜|：:]{1,10})\s+[｜|]?\s*(.{4,})$', t)
    if m and re.search(r'[0-9*A-Za-z]', m.group(1)):
        t = m.group(2).strip()
    # 6. 去前导分隔符，保留 emoji
    t = re.sub(r'^[｜|:：]+\s*', '', t)
    t = t.strip(' ｜|:：·').strip()
    return t


def is_valid_question(t: str) -> bool:
    """过滤：只留 4~25 字的真问题，剔除推广/教程/星座预测等非占卜内容。"""
    if not (4 <= len(t) <= 25):
        return False
    black = ('网站', '股票', '教程', '学习', '粉丝', '上热门', '创作者', '观看指南',
             '星座', '处女座', '狮子座', '水瓶座', '土象', '合集', '系列篇',
             '塔罗牌娱乐推演', '啰里八嗦', '讲个故事')
    return not any(k in t for k in black)


def recommend_topics(n: int) -> list[str]:
    """从选题库随机抽 n 个「未用」选题，用 LLM 判断+清洗成标准大众占卜问题。"""
    # 复用 topic-discovery 的 LLM 清洗判断（去作者/标签、保留 emoji、过滤非大众占卜问题）
    sys.path.insert(0, str(BASE / ".claude" / "skills" / "topic-discovery" / "scripts"))
    from topic_library import llm_clean_mass_divination

    wb = openpyxl.load_workbook(TOPIC_XLSX)
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    raw_titles = [r[3] for r in rows if r[10] == "未用" and r[3]]
    random.shuffle(raw_titles)
    # LLM 判断+清洗（取 n*4 候选，足够筛出 n 个有效问题）
    pool = raw_titles[: n * 4]
    results = llm_clean_mass_divination(pool)
    valid = []
    for res in results:
        q = res.get("question", "")
        if not res.get("is_valid", True) or not q:
            continue
        # 后过滤：单问题（≤1个问号）、长度 4~25 字
        if q.count("？") + q.count("?") > 1:
            continue
        if not (4 <= len(q) <= 25):
            continue
        valid.append(q)
    return valid[:n]


def pick_ref_cover() -> pathlib.Path:
    covers = []
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        covers.extend(REF_COVERS_DIR.glob(ext))
    covers = sorted(set(covers))
    return random.choice(covers) if covers else None


def gen_cover(question: str, grid: int, task_space: str, out_dir: pathlib.Path) -> str:
    """Agent 模式生成封面图，返回封面文件路径。"""
    ref = pick_ref_cover()
    prompt = (f"这是大众占卜封面图，{grid}宫格，每个宫格一张图，每张图左下角一个选项。"
              f"主题：{question}。请完全复刻参考图的版式和插画风格，生成一张全新的封面图，图片不要雷同。")
    cmd = ["python3", str(AGENT_GEN), prompt, "--count", "1", "--out", str(out_dir), "--task-space", task_space]
    if ref:
        cmd += ["--ref", str(ref), "--describe"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=400)
    import json
    for line in (r.stdout + r.stderr).splitlines():
        if '"status": "ok"' in line and '"images"' in line:
            d = json.loads(line)
            imgs = d.get("images", [])
            if imgs:
                return imgs[0]
    return ""


def build_emotion_cover_prompt(question: str, grid: int, moods: list[dict]) -> str:
    """按 mood 组情绪定向封面 prompt。每格只给情绪/主色/氛围抽象约束，绝不列物象（防即梦版式漂移）。"""
    lines = [
        f"第{i + 1}格：情绪 {m['label']}，主色调 {m['color_name']}（{m['primary_color']}），氛围 {m['atmosphere']}"
        for i, m in enumerate(moods)
    ]
    return (
        f"这是大众占卜封面图，{grid}宫格，每个宫格一张图，每张图左下角一个选项，每个宫格不要画其他文字。\n"
        f"主题：{question}\n"
        f"{grid}个宫格按顺序对应{grid}种不同心境，请严格按宫格顺序用各格的情绪与主色渲染，不要串格、不要改变宫格数量：\n"
        + "\n".join(lines) + "\n"
        f"请完全复刻参考图的版式和插画风格，保持{grid}宫格版式稳定不变（不要变多不要变少），每格用其情绪与主色渲染，"
        f"生成一张全新的封面图，图片不要雷同。"
    )


def build_cell_prompt(question: str, mood: dict, idx: int) -> str:
    """单格情绪图 prompt：情绪/主色/氛围 + 具体画面主体（motif，防各格雷同——路线 B 每格独立生成无串格风险，
    路线 A 时代「绝不列物象」约束已松绑为「主体由 motif 库给定」）。标签由 HTML/CSS 确定性叠字，AI 图必须无字。
    """
    motif = (mood.get("motif") or "").strip()
    motif_line = (f"画面主体：{motif}。必须画这个主体场景，不要画成只有颜色和氛围的抽象画面。\n"
                  if motif else "")
    return (f"这是大众占卜封面图的第{idx + 1}个宫格画面，情绪 {mood['label']}，"
            f"主色调 {mood['color_name']}（{mood['primary_color']}），氛围 {mood['atmosphere']}。\n"
            f"{motif_line}"
            f"请参考参考图的插画风格，画一张干净、留白充足的情绪图，只表现这种情绪氛围。\n"
            f"构图硬约束：画面必须是一个单一、完整、连续的场景，"
            f"禁止分屏、禁止左右/上下拼接、禁止多格/条带式构图、禁止任何形式的画面分割。\n"
            f"画面中禁止出现任何文字、字母、数字、标点、Logo。")


def load_moods(qdir: pathlib.Path, grid: int) -> list[dict]:
    """读 qdir/content.json 的 options[].mood；数量不足或缺 mood 返回 []。"""
    cj = qdir / "content.json"
    if not cj.exists():
        return []
    try:
        content = json.loads(cj.read_text(encoding="utf-8"))
        opts = content.get("options", [])
        if len(opts) < grid:
            return []
        moods = [o.get("mood") for o in opts[:grid]]
        return moods if all(moods) else []
    except Exception:  # noqa: BLE001
        return []


def gen_cover_emotion(question: str, grid: int, task_space: str, qdir: pathlib.Path) -> str:
    """路线 B：N 个选项 → N 次单图（--ratio 16:9 3格横格 / 3:4 4格）→ HTML/CSS 合成 → 返回封面路径。
    无 mood → 回退旧整图 gen_cover（无解读批量）。分格图失败的空底格占位、标签照叠。
    返回封面源文件路径（qdir/封面.png）。
    """
    moods = load_moods(qdir, grid)
    if not moods:
        return gen_cover(question, grid, task_space, qdir.parent)   # 旧整图路径（无解读批量）
    ref = pick_ref_cover()
    tmp = qdir / ".cells"
    tmp.mkdir(exist_ok=True)

    def _gen_cell(arg: tuple[int, dict]) -> tuple[int, str]:
        """单格即梦生图（独立 task-space，可并发——批量 --workers 3 跨题并发即梦已验证同模式）。"""
        i, m = arg
        prompt = build_cell_prompt(question, m, i)
        cmd = ["python3", str(AGENT_GEN), prompt, "--count", "1", "--out", str(tmp),
               "--task-space", f"{task_space}-cell-{i}", "--ratio", "16:9" if grid == 3 else "3:4"]
        if ref:
            # 不带 --describe：识图描述会把参考图的三横幅结构喂给 AI，加剧条带模仿；只留 --ref 锚风格
            cmd += ["--ref", str(ref)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        for line in (r.stdout + r.stderr).splitlines():
            if '"status": "ok"' in line and '"images"' in line:
                imgs = json.loads(line).get("images", [])
                if imgs:
                    return i, imgs[0]
        return i, ""

    try:
        # 并发：N 格即梦生图纯 I/O 等待，串行 N 格 ≈ N 倍耗时
        with ThreadPoolExecutor(max_workers=len(moods)) as ex:
            imgs = dict(ex.map(_gen_cell, enumerate(moods)))
        cells = []
        for i in range(len(moods)):
            img = imgs.get(i, "")
            if not img:
                print(f"  ⚠ 第{i + 1}格分格图生成失败，该格用空底占位")
            cells.append({"img": img, "label": "壹贰叁肆"[i]})
        # 合成
        from render_cover import render
        out = render(qdir, question, cells, grid)
    finally:
        import shutil as _sh
        _sh.rmtree(tmp, ignore_errors=True)
    return str(out)


def gen_cover_verified(question: str, grid: int, task_space: str, qdir: pathlib.Path) -> str:
    from cover_verify import verify_cover_grid
    last: dict = {"ok": False, "warn": True, "reason": "未生成"}
    cover = ""
    for attempt in range(2):
        c = gen_cover_emotion(question, grid, f"{task_space}-{attempt}", qdir)
        if not c:
            print(f"  ⚠ 封面生成无图片返回（第 {attempt + 1} 次）")
            continue
        cover = c
        v = verify_cover_grid(cover, grid, top_ignore=0.09)
        print(f"  校验: {v['reason']}")
        last = v
        if v["ok"] or v["warn"] or attempt == 1:
            break
        print(f"  ⚠ 宫格数不符，重试第 {attempt + 2} 次...")
    if cover and not last["ok"] and not last["warn"]:
        print(f"  ⚠⚠ 封面宫格数不符（OCR {last['count']}≠{grid}），已交付但需人工复核")
    return cover


def generate(question: str, grid: int, qdir: pathlib.Path, format_: str = "short", spread: str = "") -> None:
    """生成解读 + content.json。short → generate_short_divination；long → generate_mass_divination。"""
    script = GEN_SHORT if format_ == "short" else GEN_MASS
    cmd = ["python3", str(script), question, str(qdir), "--n-options", str(grid)]
    if spread:
        cmd += ["--spread", spread]   # 手动牌阵：跳过 LLM 荐阵，省 ~15s
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"generate({format_}) 失败: {r.stderr[-200:]}")


def render(qdir: pathlib.Path, format_: str = "short") -> None:
    """渲染选项图（short → render_short；long → render_mass）。输出在 <qdir>/ 根。"""
    script = RENDER_SHORT if format_ == "short" else RENDER_MASS
    r = subprocess.run(["python3", str(script), str(qdir)], capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"render({format_}) 失败: {r.stderr[-200:]}")


def organize(question: str, grid: int, cover_path: str, qdir: pathlib.Path):
    """组织目录：封面.png + 选项图，清理中间文件。"""
    qdir.mkdir(parents=True, exist_ok=True)
    if cover_path:
        # 路线 B：render_cover.render 已把封面写进 qdir/封面.png（cover_path==目标），
        # shutil.copy2 对同文件抛 SameFileError，需跳过。
        dst = qdir / "封面.png"
        if pathlib.Path(cover_path).resolve() != dst.resolve():
            shutil_copy(cover_path, dst)
    out = qdir / "out"
    for i in range(grid):
        src = out / f"选项{chr(65+i)}.png"
        if src.exists():
            shutil_copy(src, qdir / src.name)
    for p in [qdir / "content.json", qdir / "cards", qdir / "cover.html", out]:
        if p.is_dir():
            shutil_rmtree(p)
        elif p.exists():
            p.unlink()


def shutil_copy(src, dst):
    import shutil
    shutil.copy2(str(src), str(dst))


def shutil_rmtree(p):
    import shutil
    shutil.rmtree(p, ignore_errors=True)


def process(idx, question, grid, format_, out_dir, spread=""):
    qdir = out_dir / question
    ts = f"jm-pipe-{idx}"
    try:
        generate(question, grid, qdir, format_, spread)             # ① 解读 → content.json
        r = subprocess.run(["python3", str(EMO_PROFILE), str(qdir)],
                           capture_output=True, text=True, timeout=300)  # ② 情绪画像（失败不阻塞，封面回退通用）
        if r.returncode != 0:
            print(f"  ⚠ 情绪画像失败（{r.stderr[-300:]}），封面将回退通用 prompt", flush=True)
        # ③④ 封面与选项图渲染互不依赖（都只读 content.json），并行
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_cover = ex.submit(gen_cover_verified, question, grid, ts, qdir)
            f_render = ex.submit(render, qdir, format_)
            cover = f_cover.result()
            f_render.result()   # 渲染失败抛异常进 except；封面失败只警告
        if not cover:
            print(f"  ⚠⚠ 封面生成失败（无图片返回），已交付选项图但缺封面，需人工补封面", flush=True)
        organize(question, grid, cover, qdir)                        # ⑤ 目录
        mark = "" if cover else "（封面需人工复核）"
        print(f"[{idx}] {question}（{grid}宫格 {format_}）✅{mark}", flush=True)
    except Exception as e:
        print(f"[{idx}] {question}: 异常 {e}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, required=True, help="推荐选题数")
    ap.add_argument("--grid", default="random", help="宫格数：3/4/random（默认 random）")
    ap.add_argument("--format", default="short", choices=["short", "long"],
                    help="解读/渲染格式：short（3:4 短图文，默认）/ long（自适应高度长图文）")
    ap.add_argument("--spread", default="", help="手动指定牌阵（跳过 LLM 荐阵，每题省 ~15s）")
    ap.add_argument("--out", default=str(OUT_DEFAULT), help="输出目录")
    ap.add_argument("--workers", type=int, default=3, help="并行度")
    ap.add_argument("--dry-run", action="store_true", help="只推荐选题，不生成")
    args = ap.parse_args()

    topics = recommend_topics(args.count)
    print(f"推荐 {len(topics)} 个选题：")
    for i, t in enumerate(topics, 1):
        print(f"  {i}. {t}")
    if args.dry_run:
        return

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    tasks = []
    for i, t in enumerate(topics, 1):
        grid = int(args.grid) if args.grid in ("3", "4") else random.choice([3, 4])
        tasks.append((i, t, grid, args.format, out_dir, args.spread))

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(lambda t: process(*t), tasks))
    print("=== pipeline 完成 ===")


if __name__ == "__main__":
    main()

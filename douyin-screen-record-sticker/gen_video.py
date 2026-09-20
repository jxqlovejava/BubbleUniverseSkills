#!/usr/bin/env python3
"""录屏 + 贴纸合成 9:16 抖音成片。

用法：
  python3 gen_video.py raw/xxx.mov                      # 默认文案贴纸
  python3 gen_video.py raw/xxx.mov --copy sahuang       # 换贴纸文案（自动重渲染贴纸）
  python3 gen_video.py raw/xxx.mov --ss 2 --to 38       # 掐头去尾（秒）
  python3 gen_video.py raw/xxx.mov --speed 2            # 2 倍速（短视频节奏）
  python3 gen_video.py raw/xxx.mov --x 600 --y 700 --sticker-width 440 --opacity 0.82
输出：out/<输入名>-<copy>.mp4（1080×1920，h264 + yuv420p）

画幅适配（--fit）：
  bleed 裁上下铺满 9:16，零侧边（默认顶裁 280 设备像素 = 状态栏+App 页眉）
  bars  保留整屏，两侧用画面自身边缘色横向延展，不再有黑边（不裁内容）
  pad   老方案：整屏居中等比缩放 + 纯色侧边
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys

BASE = pathlib.Path(__file__).parent
OUT_W, OUT_H = 1080, 1920

def run(cmd: list[str]) -> None:
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)


def build_fit(src: str, fit: str, in_w: int, in_h: int, args) -> str:
    """把（已 trim/变速的）录屏链补成 1080×1920 的画幅链，输出 pad 标签 [bg]。
    src 是形如 [0:v]trim=…,setpts=…, 的链（末尾带逗号），boost 时是 concat 链。"""
    if fit == "bleed":
        # 设备屏比 9:16 更长（1320×2868 → 2.17:1），必须裁掉 521px 才能铺满。裁在哪：
        # 顶 315 = 状态栏 + 「无限畅享占卜」页眉（解读页标题 y=375 保住）；
        # 底 206 = 牌堆下缘，且「结束洗牌」按钮（y=2596-2652）整颗仍在画面里。
        # 代价：解读正文往下流到 y>2662 的行会被切，需要一字不落就改 --fit bars。
        crop_h = round(in_w * OUT_H / OUT_W / 2) * 2
        top = args.crop_top
        bottom = in_h - crop_h - top if args.crop_bottom is None else args.crop_bottom
        if bottom < 0:
            sys.exit(f"[err] --crop-top {top} 太大：9:16 只需裁 {in_h - crop_h}px（顶+底）")
        return f"{src}crop={in_w}:{crop_h}:0:{top},scale={OUT_W}:{OUT_H}[bg]"
    if fit == "bars":
        # 整屏不裁：先等比缩到高 1920，两侧缺口用画面自身的最外两列像素横向拉伸补齐
        # （按行取色，跟该页背景/明暗自动一致，比固定深色侧边自然，也没有模糊背景的重影）
        fg_w = round(in_w * OUT_H / in_h / 2) * 2
        left = (OUT_W - fg_w) // 2
        right = OUT_W - fg_w - left
        return (
            f"{src}scale=-2:{OUT_H}[fg];"
            f"[fg]split=3[v0][vl][vr];"
            f"[vl]crop=2:ih:0:0,scale={left}:{OUT_H}:flags=bilinear[L];"
            f"[vr]crop=2:ih:iw-2:0,scale={right}:{OUT_H}:flags=bilinear[R];"
            f"[v0]pad={OUT_W}:{OUT_H}:{left}:0:color={args.side_color}[pg];"
            f"[pg][L]overlay=0:0[x];[x][R]overlay={OUT_W - right}:0[bg]"
        )
    return (f"{src}scale=-2:{OUT_H},"
            f"pad={OUT_W}:{OUT_H}:(ow-iw)/2:0:color={args.side_color}[bg]")


def find_blank_spans(video: pathlib.Path, lo: float, hi: float, fps: float = 1.0,
                     min_std: float = 42.0, min_mean: float = 228.0,
                     min_len: float = 1.0) -> list[tuple[float, float]]:
    """找「近乎空白」的区间（浅底纯色、页面上没有任何内容）。

    App 在抽牌之间会连续 2-4 秒显示一个几乎全白的页面（全帧只有状态栏时间，
    偶尔一个卡名），录屏里就是死时间——必须剪掉，否则成片里卡与卡之间会闪空白。
    判据用内容区亮度：白屏页均值高（>228）、标准差低（<42）；正常页面标准差普遍 >45
    （解读页 69、翻牌页 100、结果页 47）。std 放到 42 是因为 App 白屏那段有的帧上还残留
    一点内容（实测 233/39），用 26 会漏 —— 但放宽后开头「洗牌页淡入」（228/40）也会命中，
    所以**扫描范围必须限定在抽牌段到解读页之间**（见 --drop-range），别对整片扫。
    """
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        print("[warn] 缺 numpy/Pillow，跳过空白段检测")
        return []
    tmp = BASE / "out" / ".blank"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(video),
                        "-vf", f"trim=start={lo:.2f}:end={hi:.2f},setpts=PTS-STARTPTS,fps={fps}",
                        "-y", str(tmp / "%05d.png")], check=False)
        ocr_bin = pathlib.Path.home() / ".cache/tarot-ocr/ocr_boxes"
        hits = []
        for i, png in enumerate(sorted(tmp.glob("*.png"))):
            im = np.array(Image.open(png).convert("L")).astype(float)
            body = im[int(im.shape[0] * 0.07):int(im.shape[0] * 0.88)]  # 去状态栏/底边
            if not (body.mean() > min_mean and body.std() < min_std):
                continue
            # 亮度只是初筛：变帧率录屏上同一段两次扫描能对不上，光靠亮度会漏。
            # 用 App 白屏的硬特征二次确认——**整页没有任何文字**（正常页面都有标题/按钮）。
            # OCR 只花在初筛命中的帧上，开销可控。
            if ocr_bin.exists():
                r = subprocess.run([str(ocr_bin), str(png)], capture_output=True, text=True)
                boxes = [json.loads(x) for x in r.stdout.splitlines() if x.startswith("{")]
                # 必须排除状态栏：那里的时钟（"17:44"）每个页面都有，不排掉会全判成有文字
                body_texts = [b["text"] for b in boxes
                              if b["y"] > 140 and len(b["text"].strip()) > 2]
                if body_texts:
                    continue
            hits.append(lo + i / fps)
        spans: list[list[float]] = []
        for t in hits:
            if spans and t - spans[-1][1] <= 1.5 / fps:
                spans[-1][1] = t
            else:
                spans.append([t, t])
        out = [(s, e + 1.0 / fps) for s, e in spans if e - s + 1.0 / fps >= min_len]
        if out:
            print("[info] 空白段（死时间）: " + ", ".join(f"{s:.1f}-{e:.1f}s" for s, e in out))
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def plan_segments(a: float, b: float, base_speed: float, boosts: list, tail_start,
                  drops: list) -> list[list]:
    """把 [a,b] 切成 [[起, 止, 倍速], ...]：先按加速区间分速度档，再挖掉空白段。
    相邻段不合并（合并省不了多少滤镜，反而容易写错）。"""
    bounds = {a, b}
    for s0, s1, _ in boosts:
        bounds |= {s0, s1}
    if tail_start is not None:
        bounds.add(tail_start)
    pts = sorted(x for x in bounds if a <= x <= b)
    segs = []
    for i, s0 in enumerate(pts[:-1]):
        s1 = pts[i + 1]
        fac = next((f for r0, r1, f in boosts if r0 <= s0 and s1 <= r1), 1.0)
        segs.append([s0, s1, base_speed * fac])
    out = []
    for s0, s1, f in segs:
        cur = s0
        for d0, d1 in sorted(drops):
            if d1 <= cur or d0 >= s1:
                continue
            if d0 > cur:
                out.append([cur, d0, f])
            cur = max(cur, d1)
        if cur < s1:
            out.append([cur, s1, f])
    return [s for s in out if s[1] - s[0] > 0.05]


def output_to_raw(segs: list, o: float) -> float:
    """成片时间 → 原片时间：按分段计划逐段累加（每段时长 = (止-起)/倍速）。"""
    pos = 0.0
    for s0, s1, f in segs:
        dur = (s1 - s0) / f
        if o <= pos + dur + 1e-6:
            return s0 + (o - pos) * f
        pos += dur
    s0, s1, f = segs[-1]
    return s0 + (o - pos) * f


def probe_last_frame_time(path: pathlib.Path) -> float:
    """最后一帧的 pts（秒）。recordVideo 是变帧率，末尾还可能没有可解码帧，
    容器 duration 会比实际最后一帧长——所以尾部裁剪必须按这个值倒推，不能信 duration。"""
    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True).stdout.strip())
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-read_intervals", f"{max(0.0, dur - 30):.0f}%",  # 只读末尾 30s，全片扫要 30s+
         "-show_entries", "packet=pts_time", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True)
    ts = [float(x.strip().rstrip(",")) for x in r.stdout.split()
          if x.strip().rstrip(",") not in ("", "N/A")]
    return max(ts) if ts else 0.0


def probe_size(path: pathlib.Path) -> tuple[int, int]:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True)
    w, h = (int(x) for x in r.stdout.strip().split(",")[:2])
    return w, h


def render_fits(fits: list[str], src: str, inp: pathlib.Path, out_dir: pathlib.Path,
                key: str, args, in_w: int, in_h: int, alpha: str) -> list[pathlib.Path]:
    """按画幅打标 → 生成文件名 → 建滤镜链 → 编码。返回产出的文件列表。"""
    made: list[pathlib.Path] = []
    for fit in fits:
        tags = [fit] if args.fit == "both" else []
        suffix = ("-" + "-".join(tags) + ".mp4") if tags else ".mp4"
        target = out_dir / (f"{inp.stem}-{key}{suffix}")
        fit_chain = build_fit(src, fit, in_w, in_h, args)
        if args.cover:
            # 首图拼片头：封面也叠贴纸（钩子文案是信息流点击理由），位置与录屏段一致
            # （cover_sticker_x/y 默认跟随 --x/--y），0.8s 过渡时贴纸不跳变；split 一路给录屏段用
            fc = (f"{fit_chain};[1:v]scale={args.sticker_width}:-1{alpha},split[st][stc];"
                  f"[bg][st]overlay={args.x}:{args.y}[vo];"
                  f"[2:v]scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,"
                  f"crop={OUT_W}:{OUT_H},fps=30,format=yuv420p,setsar=1[cv];"
                  f"[cv][stc]overlay={args.cover_sticker_x}:{args.cover_sticker_y}[cvo];"
                  f"[cvo][vo]concat=n=2:v=1:a=0")
        else:
            fc = (f"{fit_chain};[1:v]scale={args.sticker_width}:-1{alpha}[st];"
                  f"[bg][st]overlay={args.x}:{args.y}")
        cmd = (["ffmpeg", "-y", "-i", str(inp), "-i", str(sticker_path(key))]
               + (["-loop", "1", "-t", str(args.cover_dur), "-i", args.cover] if args.cover else [])
               + ["-filter_complex", fc, "-c:v", "libx264", "-preset", "medium",
                  "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac",
                  "-movflags", "+faststart"] + [str(target)])
        run(cmd)
        print(f"[done] {target}")
        made.append(target)
    return made


def sticker_path(key: str) -> pathlib.Path:
    return BASE / "out" / f"sticker-{key}.png"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="录屏文件（mov/mp4）")
    ap.add_argument("--copy", default=None, help="贴纸文案 key（content.json）")
    ap.add_argument("--ss", type=float, default=None, help="起始秒")
    ap.add_argument("--to", type=float, default=None, help="结束秒")
    ap.add_argument("--x", type=int, default=60, help="贴纸左边距（输出画幅像素，默认 60 左侧，与首图段同一位置）")
    ap.add_argument("--y", type=int, default=200, help="贴纸顶边距（输出画幅像素，默认 200 = 头顶上方留白区，7 张封面人脸实测最顶上沿 500，不压脸）")
    ap.add_argument("--sticker-width", type=int, default=440, help="贴纸宽度（输出画幅像素）")
    ap.add_argument("--opacity", type=float, default=0.82, help="贴纸不透明度（<1 可透出下层内容）")
    ap.add_argument("--speed", type=float, default=1.0, help="变速倍率（>1 加速）")
    ap.add_argument("--boost", default=None,
                    help="raw 秒区间额外加速，格式 SS:TO:FACTOR（如 80:125:2 = 该段再快 2 倍，用于抽牌等待段）")
    ap.add_argument("--fit", choices=["bleed", "bars", "both", "pad"], default="bleed",
                    help="画幅适配（默认 bleed）：bleed=裁上下铺满 9:16（零侧边）；"
                         "bars=整屏+边缘色延展侧边（备用，不再默认出）；both=两种各出一版")
    ap.add_argument("--crop-top", type=int, default=315,
                    help="bleed：顶部裁多少设备像素（默认 315 = 状态栏 + App 页眉，解读页标题 y=375 仍在画面内）")
    ap.add_argument("--crop-bottom", type=int, default=None,
                    help="bleed：底部裁多少设备像素（默认按 9:16 反推，牌堆下缘那一截）")
    ap.add_argument("--side-color", default="0x14101A", help="pad/bars 两侧兜底色")
    ap.add_argument("--cover", default=None, help="首图 PNG：拼到片头（封面也叠贴纸，位置默认与录屏段一致）")
    ap.add_argument("--cover-dur", type=float, default=0.8, help="首图在片头的秒数（默认 0.8）")
    ap.add_argument("--cover-sticker-x", dest="cover_sticker_x", type=int, default=None,
                    help="封面上贴纸左边距（默认跟随 --x：首图与正文贴纸同一位置，不跳变）")
    ap.add_argument("--cover-sticker-y", dest="cover_sticker_y", type=int, default=None,
                    help="封面上贴纸顶边距（默认跟随 --y）")
    ap.add_argument("--tail-hold", type=float, default=0.0,
                    help="成片尾部保持常速的秒数（解读段用）：从视频真实结尾倒推，前面的加速段自动截到它之前")
    ap.add_argument("--drop-range", default=None,
                    help="空白段扫描范围 SS:TO（默认整段）。App 白屏只出现在抽牌到解读之间，"
                         "限定范围能避免误剪开头的洗牌页淡入")
    ap.add_argument("--drop-blank", dest="drop_blank", action="store_true", default=True,
                    help="剪掉录屏里的空白页死时间（App 抽牌之间会白屏数秒），默认开")
    ap.add_argument("--keep-blank", dest="drop_blank", action="store_false",
                    help="保留空白段（调试用）")
    args = ap.parse_args()
    # 首图贴纸默认跟正文同一位置：0.8s 封面过渡到录屏时贴纸不跳变（要分开调才显式传）
    if args.cover_sticker_x is None:
        args.cover_sticker_x = args.x
    if args.cover_sticker_y is None:
        args.cover_sticker_y = args.y

    cfg = json.loads((BASE / "content.json").read_text(encoding="utf-8"))
    key = args.copy or cfg["default"]
    sticker = BASE / "out" / f"sticker-{key}.png"
    if not sticker.exists():
        # 贴纸没渲染过就先渲染（等价于手动 python3 gen_sticker.py --copy key）
        run([sys.executable, str(BASE / "gen_sticker.py"), "--copy", key])

    inp = pathlib.Path(args.input)
    if not inp.exists():
        sys.exit(f"[err] 录屏不存在: {inp}")
    in_w, in_h = probe_size(inp)
    out_dir = BASE / "out"
    out_dir.mkdir(exist_ok=True)

    # 起止/加速/剔除全靠 trim 滤镜实现（帧精确）：-ss 输入搜寻在 simctl 录屏上关键帧稀疏不准，
    # 输出搜寻又会把贴纸 PNG 输入流截空。trim 只作用于录屏流，无此问题。
    opacity = min(max(args.opacity, 0.0), 1.0)
    alpha = f",format=rgba,colorchannelmixer=aa={opacity}" if opacity < 1.0 else ""

    a = args.ss if args.ss is not None else 0.0
    last = probe_last_frame_time(inp)
    b = args.to if args.to is not None else last + 1.0  # 到片尾（多给 1s，避免截掉最后一帧）
    # 尾部常速段（解读）起点：从视频真实结尾倒推 tail_hold * speed 秒
    tail_start = max(a, last - args.tail_hold * args.speed) if args.tail_hold else None

    boosts = []
    if args.boost:
        # 支持多段：SS:TO:F,SS:TO:F,…（抽牌等待段 2x、解读 loading 段 6x）
        for item in args.boost.split(","):
            s0, s1, factor = (float(x) for x in item.split(":"))
            s0, s1 = max(s0, a), min(s1, b)
            if tail_start is not None:
                s1 = min(s1, tail_start)  # 不吞掉尾部常速段
            if s0 < s1:
                boosts.append((s0, s1, factor))
            else:
                print(f"[warn] --boost 区间 {item} 与成片范围无交集，忽略")

    if args.drop_blank:
        d0, d1 = (float(x) for x in args.drop_range.split(":")) if args.drop_range else (a, b)
        # fps=2：1fps 在变帧率录屏上会漏掉白屏中段的帧（同段两套扫描结果都对不上），
        # 采样密一倍才抓得全；代价只是多算几十帧的均值
        drops = find_blank_spans(inp, max(d0, a), min(d1, b), fps=2.0)
    else:
        drops = []
    fits = ["bleed", "bars"] if args.fit == "both" else [args.fit]

    def build_src(segs: list) -> str:
        return (";".join(f"[0:v]trim=start={s0:.2f}:end={s1:.2f},"
                         f"setpts=(PTS-STARTPTS)/{f:.3f}[v{i}]"
                         for i, (s0, s1, f) in enumerate(segs))
                + ";" + "".join(f"[v{i}]" for i in range(len(segs)))
                + f"concat=n={len(segs)}:v=1:a=0,")

    # 闭环：变帧率录屏上用 fps 采样找空白段不稳（同一段两套扫描结果能对不上），
    # 所以先剪一版，再扫**成片**（成片恒定帧率，扫描可靠），还有空白就映射回原片追加剔除重剪。
    made: list[pathlib.Path] = []
    for attempt in range(3):
        segs = plan_segments(a, b, args.speed, boosts, tail_start, drops)
        if not segs:
            sys.exit("[err] 分段计划为空（--ss/--to 区间被裁光了？）")
        src = build_src(segs)
        made = render_fits(fits, src, inp, out_dir, key, args, in_w, in_h, alpha)
        if not args.drop_blank or attempt == 2:
            break
        leftover = []
        for t in made:
            dur = float(subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", str(t)], capture_output=True, text=True).stdout or 0)
            leftover += find_blank_spans(t, 0, dur, fps=2.0)
        if not leftover:
            break
        # 成片扫出的残留只是「线索」，必须映射回原片**密扫确认**才真剪：
        # 成片上的判据区不含底部牌堆，抽牌页会被误报成空白——不确认就直接剪，
        # 会把正常画面当空白剪掉（21.3s 被剪成 14.5s 那次就是）。
        # 成片时间轴 = 首图 cover_dur + 录屏段，映射回原片前先减掉首图偏移
        off = args.cover_dur if args.cover else 0.0
        confirmed = []
        for lo, hi in leftover:
            lo, hi = lo - off, hi - off
            if hi <= 0:
                continue  # 整段落在首图里
            c0, c1 = output_to_raw(segs, max(0.0, lo)), output_to_raw(segs, hi)
            confirmed += find_blank_spans(inp, max(a, c0 - 1.0), min(b, c1 + 1.0), fps=4.0)
        if not confirmed:
            print("[info] 成片扫出的空白在原片密扫中未确认（误报），保留画面")
            break
        drops = sorted(drops + confirmed)
        print(f"[warn] 成片残留空白 {[(round(x,1), round(y,1)) for x, y in leftover]}"
              f" → 原片确认 {[(round(x,1), round(y,1)) for x, y in confirmed]}，重剪（第 {attempt + 2} 次）")



if __name__ == "__main__":
    main()

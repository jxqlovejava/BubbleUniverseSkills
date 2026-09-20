#!/usr/bin/env python3
"""即梦 Agent 模式生图：让即梦 Agent 端到端理解参考图再生成，还原度高于手动 i2i。

默认不拆解参考图，直接基于提示词生成（Agent 模式 / 图片 5.0 Lite / 3:4 / 2K / 默认 3 张）。
默认 --enhance 自动润色：简单提示词（纯文字或参考图+文字）自动追加对应风格质感块 + 负向块，
让"丢个简单 prompt 就出不错效果"；已含硬约束（必须/禁止）或复刻版式时自动跳过；--no-enhance 关闭。
需要精确还原参考图关键质感（油画颗粒感/暖调主色/皮肤红润等）时，显式 --describe
先调 describe_reference.py 识图拿关键维度描述，作为硬约束拼进 prompt 再生成
（实测暖色 16%→44%，还原度显著提升）。

用法:
  python3 agent_generate.py "换成新的不同人物" --ref 参考图.png [--describe] [--out ./jimeng_output]
  python3 agent_generate.py "一个女孩在咖啡店" [--out ./jimeng_output]   # 简单提示词，--enhance 自动润色

输出: stdout 逐行 JSON。成功: {"status":"ok","count":N,"images":[...]}
"""
import argparse
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

EGO = str(Path.home() / ".local" / "bin" / "ego-browser")
JS = Path(__file__).parent / "agent_generate.js"


def describe(ref_path: str) -> str:
    """调 describe_reference.py 拿识图描述（关键维度文字）。"""
    desc_script = Path(__file__).parent / "describe_reference.py"
    proc = subprocess.run([sys.executable, str(desc_script), ref_path],
                          capture_output=True, text=True, timeout=220)
    try:
        d = json.loads(proc.stdout)
        return d.get("description", "")
    except Exception:
        return ""


# ---- 自动润色（--enhance 默认开，2026-08-20 加）：简单提示词自动追加质感块 + 负向块 ----
STYLE_RULES = [
    (("漫画", "动漫", "卡通"), "漫画"),
    (("治愈", "插画", "可爱", "温馨"), "治愈"),
    (("油画", "古典", "静物", "莫奈"), "油画"),
    (("风景", "场景", "城市", "森林", "山", "海"), "风景"),
    (("日系", "胶片", "清新"), "日系"),
    (("影视", "人物", "人像", "写真", "女孩", "女子", "少女", "男人", "女人"), "影视人物"),
]
ENHANCE_BLOCKS = {
    "影视人物": "影视质感实拍：人物保留自然毛孔、细微肌理和自然瑕疵雀斑，未经美颜修饰，不做过度磨皮，真实皮肤反光，自然柔光，35mm 胶片色调，电影感构图，真实细腻皮肤纹理，无塑料感皮肤、无美颜滤镜感；表情自然有生活感，眼神平和有内容，非摆拍抓拍感，避免AI感、CG感、完美对称五官。",
    "油画": "古典油画质感：厚涂笔触清晰可见，画布纹理，深色背景与主体高光对比（伦勃朗式明暗），哑光油画光泽。",
    "漫画": "漫画质感：干净利落的线条，鲜明配色，漫画成片质感，画面干净。",
    "治愈": "治愈系插画质感：柔和线条，暖色调，温馨氛围，画面干净留白。",
    "风景": "写实摄影质感：前景/中景/远景层次分明，自然色彩过渡，空气透视感，高清细节。",
    "日系": "日系胶片质感：自然光，柔和通透，真实胶片颗粒，清新氛围。",
}
ENHANCE_UNIVERSAL = "高质量成片质感：真实细腻的光影层次，自然色彩过渡，画面干净通透，构图完整清晰，无AI塑料感。"
NEGATIVE_BLOCK = "负向：AI感，CG感，网红脸，整容脸，完美对称五官，呆滞眼神，空洞眼神，多余的手指，变形的手，扭曲的脸，模糊的脸，塑料感皮肤，过度磨皮，美颜滤镜感，低分辨率，干净棚拍背景，生硬伪影，人物手中或身上出现照片、小票、卡片、手机等多余物品，多余文字、水印、Logo。"


def enhance_prompt(prompt: str, ref_mode: bool, count: int = 1) -> str:
    """简单提示词自动润色：已有硬约束（必须/禁止/严格）则不动；参考图模式只补负向块；count>1 且未声明张数时补张数。
    注：Agent 模式的实际出图张数由 prompt 决定（不写"生成N张"可能只出 1 张），故这里补上。"""
    if any(k in prompt for k in ("必须严格保持", "禁止", "严格保持", "除外")):
        return prompt
    if ref_mode:
        suffix = NEGATIVE_BLOCK
    else:
        suffix = ""
        for kws, name in STYLE_RULES:
            if any(k in prompt for k in kws):
                suffix = ENHANCE_BLOCKS[name] + NEGATIVE_BLOCK
                break
        if not suffix:
            suffix = ENHANCE_UNIVERSAL + NEGATIVE_BLOCK
    if count > 1 and not re.search(r"\d+\s*张", prompt):
        suffix += f"生成{count}张不同的画面。"
    return prompt + suffix


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt", help="生成要求（如「换成新的不同人物」「保持风格版式换内容」）")
    ap.add_argument("--ref", action="append", default=[],
                    help="参考图路径（可多次传，一张或多张；不传则纯文案文生图）。"
                         "多张按传入顺序对应 prompt 里的「图1/图2/图3」")
    ap.add_argument("--describe", action="store_true",
                    help="对 --ref 参考图先自动识图拿关键维度约束再生成（默认不拆解，直接基于提示词生成）")
    ap.add_argument("--no-enhance", action="store_true",
                    help="关闭自动润色（默认开：简单提示词自动追加对应风格质感块+负向块；已有硬约束或复刻版式自动跳过）")
    ap.add_argument("--count", type=int, default=3,
                    help="生成张数，默认 3")
    ap.add_argument("--ratio", default="", choices=["1:1", "3:4", "4:3", "16:9", "9:16", ""],
                    help="分格图比例（默认空=沿用 intelligent_ratio 自动）")
    ap.add_argument("--model", default="5.0",
                    help="图片模型：4.0/4.1/4.5/4.6/4.7/5.0(=图片5.0 Lite)/5.0 Pro；默认 5.0(Lite)。"
                         "Agent 端点无模型参数，这里通过改页面 localStorage 选中模型 + 请求体带 model_req_key 实现（实测有效才保留）")
    ap.add_argument("--task-space", default="jimeng image generation",
                    help="ego task space 名（并行时每个进程用不同名，独立 tab 互不干扰）")
    ap.add_argument("--out", default="./jimeng_output")
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()

    ref_paths = []
    for r in args.ref:
        p = Path(r).resolve()
        if not p.exists():
            print(json.dumps({"status": "error", "errmsg": f"参考图不存在: {p}"}, ensure_ascii=False))
            sys.exit(1)
        ref_paths.append(str(p))

    # 可选识图 → 把关键维度描述拼进 prompt 作为硬约束（默认不拆解，直接基于提示词生成）
    prompt = args.prompt
    if ref_paths and args.describe:
        desc = "\n".join(d for d in (describe(p) for p in ref_paths) if d)
        if desc:
            prompt = (f"参考这张图生成一张全新的图。必须严格保留参考图的以下所有关键视觉特征"
                      f"（主体内容、构图逻辑、元素密度、色彩配色、对比度、材质笔触、皮肤质感、光照、镜头景深、视角景别、透视、线条风格、艺术风格、文字排版、氛围）：\n{desc}\n"
                      f"以上关键特征必须完整保留。现在请：{args.prompt}，"
                      f"只换主体内容，其余特征保持参考图不变。")

    # 自动润色（默认开）：简单提示词追加质感块+负向块+张数提示；已有硬约束 / 复刻版式自动跳过
    if not args.no_enhance:
        prompt = enhance_prompt(prompt, bool(ref_paths), args.count)

    model_key = ""
    if args.model:
        from jimeng_generate import MODEL_MAP
        if args.model not in MODEL_MAP:
            print(json.dumps({"status": "error",
                              "errmsg": f"未知模型 {args.model}，可选：{'、'.join(MODEL_MAP)}"}, ensure_ascii=False))
            sys.exit(1)
        # 2026-08-19 抓包实测：模型经 content_parts 的 generate_args.image_args.model_key 下发
        model_key = MODEL_MAP[args.model]

    js_code = (JS.read_text()
               .replace("__REF_PATHS__", json.dumps(ref_paths))
               .replace("__PROMPT__", json.dumps(prompt, ensure_ascii=False))
               .replace("__MODEL_REQ_KEY__", json.dumps(model_key))
               .replace("__MODEL_NAME__", json.dumps("", ensure_ascii=False))
               .replace("__COUNT__", str(args.count))
               .replace("__RATIO__", json.dumps(args.ratio))
               .replace("__TASK_SPACE__", json.dumps(args.task_space, ensure_ascii=False)))

    proc = subprocess.run([EGO, "nodejs"], input=js_code, capture_output=True,
                          text=True, timeout=args.timeout + 120)
    out = proc.stdout + proc.stderr

    m = re.search(r"^RESULT_JSON:(.*)$", out, re.M)
    if not m:
        print(json.dumps({"status": "error", "stage": "runtime",
                          "errmsg": out[-500:]}, ensure_ascii=False))
        sys.exit(1)
    result = json.loads(m.group(1))
    if result.get("status") != "ok":
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    # 下载图片
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^\w一-鿿]+", "_", args.prompt)[:30].strip("_")
    ts = time.strftime("%Y%m%d_%H%M%S")
    paths = []
    for i, u in enumerate(result["urls"]):
        fp = out_dir / f"{ts}_{slug}_{i+1}.png"
        urllib.request.urlretrieve(u, fp)
        paths.append(str(fp.resolve()))

    print(json.dumps({"status": "ok", "count": len(paths), "images": paths,
                      "submit_id": result.get("submit_id"),
                      "model_used": (re.search(r"^MODEL_USED:(.*)$", out, re.M) or [None, "unknown"])[1]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()

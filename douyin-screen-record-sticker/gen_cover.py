#!/usr/bin/env python3
"""抖音录屏贴纸模板 · 首图（封面）生成：温暖治愈带淡淡忧郁的电影感女性人像，人物形象每次随机变化。

技法来源：jimeng-image prompt-examples 示例13（分段编号式）+ 预设G（肤质/负向块）。
变化靠槽位池随机采样（脸型/发型/妆容/服饰），风格帧（暖金逆光 + 暖棕背景 + 治愈忧郁）保持不变——
每次运行换一张脸，账号内容不同质化；一批内人物一致，只变发丝动态与角度。

用法：
  python3 gen_cover.py                    # 随机一个人物形象，出 3 张（挑一张当封面）
  python3 gen_cover.py --count 1          # 只出 1 张
  python3 gen_cover.py --seed 42          # 固定形象配方（可复现）
  python3 gen_cover.py --dry-run          # 只打印提示词不生图（不耗积分）
  python3 gen_cover.py --out <目录>       # 输出目录（默认 out/）
输出：out/cover-<形象key>-*.png（9:16）
"""
import argparse
import json
import pathlib
import random
import subprocess
import sys

BASE = pathlib.Path(__file__).parent
AGENT = BASE.parent / ".claude" / "skills" / "jimeng-image" / "scripts" / "agent_generate.py"

# 人物形象槽位池（温暖治愈家族内变化；风格帧不动，只换人）
FACES = {
    "luyan": "柔和小圆脸，鹿眼湿润温柔，眼神安静带一点淡淡的忧郁",
    "xingyan": "心形小脸，杏眼清澈弯成浅浅月牙，温柔里藏着一点心事",
    "yuanyan": "鹅蛋脸，圆眼干净无辜，眉眼低垂带一点倦感",
    "chanyue": "鹅蛋脸，细长丹凤眼，眼神柔和平静，像刚哭过又笑了一下",
    "guazi": "瓜子脸，内双眼，眼尾有淡淡红晕，眼神温柔克制",
}
HAIRS = {
    "mizong": "蜜茶棕长卷发，松弛大波浪",
    "nuanzong": "暖棕长发，蓬松微卷",
    "heicha": "黑茶色长直发，发尾微乱",
    "lise": "深栗色长发，空气感碎发多",
    "wufa": "乌黑长发，几缕碎发贴在颈侧",
}
MAKEUPS = {
    "naicha": "奶杏色眼影与微红眼周，奶茶色唇",
    "suyan": "几乎素颜，仅眼周淡淡红晕，裸粉唇",
    "mitao": "淡蜜桃色眼影，蜜桃色唇，脸颊有自然血色",
    "dousha": "暖棕眼影，豆沙色唇",
    "meigui": "大地色眼影，唇色偏干枯玫瑰",
}
OUTFITS = {
    "yamai": "燕麦色细肩带针织裙，外罩下滑的米色薄纱",
    "mibai": "米白细吊带上衣，松垮奶咖色针织外搭滑落一边肩",
    "kaqi": "浅卡其吊带裙，肩上奶油色薄纱半透",
    "naika": "奶咖色丝绒吊带裙，质感细腻哑光",
    "moxiong": "米色抹胸上衣，外搭半透明暖纱",
}

PROMPT_TMPL = """温暖治愈系电影感人像摄影，柔暖金光，梦幻柔雾，胶片质感。9:16 竖版构图。

一、主体与动作
1 人物：年轻东亚女性，{face}，半身近景，身体侧向右侧，回眸直视镜头
2 表情：眼神温柔安静，带一点淡淡的忧郁与故事感，眼周微微泛红，嘴角放松似有浅浅笑意，眼中有自然眼神光
3 头发：{hair}，暖风吹拂，发丝轻轻飘起掠过脸颊，根根分明有束感
4 妆容：{makeup}，睫毛清晰，肤质通透有血色
5 服饰：{outfit}，肩颈与锁骨露出，薄纱或外搭下滑形成柔和包裹，织物褶皱与垂坠感真实

二、构图与镜头
1 景别：胸口以上的半身近景，三分之二侧脸
2 位置：人物偏画面中右，高度约占画面三分之二，头顶留少量空间，左侧留出光源与雾化留白区域
3 视角：平视或略微仰视，85mm 人像镜头，镜头距离较近但不夸张变形
4 对焦：焦点落在眼睛与面部，背景强虚化，整体带轻微柔化与朦胧感

三、光线与氛围
1 主光：左后方暖金色逆光（黄昏光感），形成发丝与肩部的明亮轮廓光，发丝边缘呈半透明辉光，这是画面核心高光
2 补光：正面柔和暖调补光，轻轻提亮面部细节，阴影保留且柔和
3 光质：散射柔光，明显雾化光晕，带空气感与轻微眩光
4 氛围：温暖、治愈、安静、电影感，带一点淡淡的忧郁

四、色彩与质感
1 色调：暖棕奶金主色调，肤色温暖有血色，整体低饱和偏暖
2 明暗：明暗过渡柔和，暗部不压死，高光柔亮不过曝
3 肤质：真实细腻的皮肤纹理和微小毛孔，保留自然瑕疵和轻微雀斑，不做过度磨皮，无塑料感，轻微颗粒与雾面感，边缘高光带光晕

五、背景
暖棕到深咖的渐变空间，无明确场景信息；背景与发梢周围有零散暖金色点状光斑与闪烁颗粒，类似尘埃反光，风带动发丝轻舞，光点呈漂浮散落的层次感

请按以上设定生成 {count} 张，发丝动态与头部角度可有细微差别，人物形象保持一致。
必须严格保持：9:16 竖版构图；画面中只有这一个人；人物位于画面中右，左侧留出雾化留白区；画面中禁止出现任何文字、字母、数字、水印、Logo、边框。
禁止：脸部畸变、五官错位、双脸、多余肢体、手指异常、塑料感皮肤、网红脸、完美对称五官、呆滞空洞眼神、过度磨皮、过度锐化、正面硬光、强烈死白高光、背景过亮抢主体、卡通化、漫画厚涂感、夸张霓虹色、蓝色紫色冷色调、黄色调滤镜。"""


def sample_persona(rng: random.Random) -> dict[str, str]:
    return {
        "face": rng.choice(list(FACES.values())),
        "hair": rng.choice(list(HAIRS.values())),
        "makeup": rng.choice(list(MAKEUPS.values())),
        "outfit": rng.choice(list(OUTFITS.values())),
    }


def persona_key(p: dict[str, str]) -> str:
    rev = [{v: k for k, v in pool.items()} for pool in (FACES, HAIRS, MAKEUPS, OUTFITS)]
    return "-".join(m[p[k]] for m, k in zip(rev, ("face", "hair", "makeup", "outfit")))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=3, help="出图张数（默认 3，挑一张当封面）")
    ap.add_argument("--seed", type=int, default=None, help="固定形象配方（可复现）")
    ap.add_argument("--out", default=str(BASE / "out"), help="输出目录（默认 out/）")
    ap.add_argument("--dry-run", action="store_true", help="只打印提示词不生图")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    persona = sample_persona(rng)
    key = persona_key(persona)
    prompt = PROMPT_TMPL.format(count=args.count, **persona)
    print(f"[info] 形象配方: {key}")
    if args.dry_run:
        print(prompt)
        return

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    before = {p.name for p in out_dir.glob("*.png")}
    r = subprocess.run(
        [sys.executable, str(AGENT), prompt, "--count", str(args.count),
         "--ratio", "9:16", "--out", str(out_dir)],
        capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.startswith("{"):
            print(line)
    if r.returncode != 0:
        sys.exit(f"[err] 生图失败: {r.stdout[-500:]} {r.stderr[-500:]}")
    # 重命名带上形象配方 key，方便回溯（同名不覆盖，加序号）
    for i, p in enumerate(
            sorted(p for p in out_dir.glob("*.png") if p.name not in before), 1):
        dest = out_dir / f"cover-{key}-{i}.png"
        n = 1
        while dest.exists():
            n += 1
            dest = out_dir / f"cover-{key}-{i}-{n}.png"
        p.rename(dest)
        print(f"[done] {dest}")


if __name__ == "__main__":
    main()

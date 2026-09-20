# 自然感实拍照片 + 塔罗气泡解读卡片 · 抖音图文模板

复刻抖音爆款结构（参考「自然感美女/情侣实拍照片 + 产品界面截图」帖）：**满版自然感实拍照片垫底 + 左约 43% 半透明白底「塔罗气泡App 解读卡」浮层**。
与「塔罗解读截图模板」的区别：那是整屏 App 截图（1170×2532，无照片），这是**照片 + 悬浮解读卡**——照片是主角，解读卡是产品截图浮层。

## 快速复用

```bash
# 一条命令：主题 → 照片文案 → 即梦生照片 → 抽牌 → 真实解读 → 渲染 → OCR
python3 gen_photo.py "缘分回溯到相遇那天"
python3 gen_photo.py "为何总遇到慢热的人" --seed 7 --card-position right

# 只生成 content.json 不渲染（先看文案/解读）
python3 gen_photo.py "主题" --skip-render

# 改了解读/划线/卡片位置后单独重渲染（不重新抽牌解读）
python3 render_photo_share.py [content.json]
```

输出：`out/自然照片产品截图.png`（1728×2304，432×576 @ DPR4，即梦 2K 同尺寸）+ `out/发布文案.txt`。

## 内容铁律

1. **解读禁止手写** — cards/interpretation 走 `gen_photo.py`（interpret.md 真实管线）；手写会被覆盖。
2. **截图不求完整** — 解读 8 块左右，截图靠卡 max-height 自然截断（真实截图感），不用凑整。
3. **划线词选可见开头** — `underlines[]` 命中任何位置都划红手绘线，但卡片只露前几块，选靠后的短语等于白划。gen 后看控制台回显解读再定。
4. **卡片位置与照片留白互补** — `--card-position left/right/center`，默认 `left`（对齐参考帖）。生成的 photo_prompt 会让主体偏卡片对侧、对侧留白，避免卡片盖脸。
5. 牌阵固定 **我-对方-我们牌阵**（3 张），牌图自动从 tarot-mass-divination 拷到 `assets/cards/`。
6. **发布文案开头必带品牌软植入句**（用户 2026-09-16 拍板）— 结构：软植入句（单独一行）→ 正文 → 话题标签。由 `gen_photo.py` 按主题用 `tarot-mass-divination/scripts/opener.py` 生成（AI，失败回退固定池），存 content.json 的 `opener`，完整文案存 `caption_full`；**`render_photo_share.py` 直接写 `caption_full`**（旧版它只写 `caption`，会把标签和软植入句冲掉）。

## content.json 字段

| 字段 | 说明 |
|---|---|
| `theme` / `card_position` | 主题 / 卡位置（default left） |
| `photo` | 背景照片路径（默认 `assets/photo_bg.png`，可由 gen 生图或手动覆盖） |
| `card_title` / `remaining_text` / `ai_label` | 品牌铭牌文案 / 顶部 chip / AI 标签 |
| `question` | 占卜问题（≤20 字，居中两行内最佳） |
| `cards` / `interpretation` | **勿手写**，gen_photo.py 回填 |
| `underlines` | 划线短语列表，全局子串匹配；未命中打 `[warn]` |
| `caption` / `hashtags` | LLM 写的抖音正文 / 话题标签，渲染时写 `out/发布文案.txt` |
| `opener` / `caption_full` | **勿手写**，gen_photo.py 回填：软植入句 / 组装好的完整发布文案（渲染直接写这个） |

## 依赖（拿到就能跑清单）

- **macOS**（正文用苹方 PingFang SC 系统字体；OCR 校验走 Vision 框架）
- `python3` + Playwright：`pip3 install playwright && python3 -m playwright install chromium`
- **仅渲染**（render_photo_share.py）：零外部依赖，assets 全在模板目录内
- **gen_photo.py**（抽牌+真实解读+生图）：需环境变量 `LLM_API_KEY`（或 `DEEPSEEK_API_KEY`）、同级的 **tarot-mass-divination**（提供 interpret.md 提示词、牌阵、牌图；ip-pipeline 的 `.claude/skills/` 布局和 vira 平铺布局都自动识别）、**jimeng-image skill**（ego-lite 浏览器已登录即梦；生图失败自动回退 `assets/photo_bg.png`）
- 想换 LLM 生成解读不换牌：重跑 `gen_photo.py --seed <固定值>`

## 版面规范（复刻来源）

- UI 底座取自 TarotBubble Flutter 源码（`tarot_chat_history_screen.dart`），同 tarot 解读截图模板：品牌铭牌白底圆角胶囊（logo+塔罗气泡）、`无限畅享占卜` 虚线 chip、白色半透问题卡、牌 46×82 圆角 5（reversed 转 180°）+ 牌名 9px + 位置 8px、Luna 头像 26px + 名 13px、解读卡白 70% 紫边 `rgba(91,77,188,.15)` 圆角 12、**12px/1.7**（与 App MarkdownInterpretationView 对齐）；`**粗体**` w600、`\n` 换行。
- 划线：`#FF3B30` 5px 红手绘线 + 淡副笔（马克笔效果），`text-underline-offset` 7px。
- 卡片：`rgba(255,255,255,.88)` 半透白底、圆角 18、投影 `0 12px 40px`，`max-height` 裁剪；位置由 `--card-position` 控制。
- 照片：`<img class="photo" object-fit:cover>` 满版垫底，是画面主角。

## 验证

```bash
bash ../tarot-mass-divination/scripts/ocr_text.sh out/自然照片产品截图.png   # vira 布局
# ip-pipeline 布局：bash .claude/skills/tarot-mass-divination/scripts/ocr_text.sh 自然照片产品截图模板/out/自然照片产品截图.png
```

（gen_photo.py 渲染后自动跑 OCR。已验证：铭牌/问题/牌名/位置/解读开头逐字准确。）

---
name: tarot-mass-divination
description: 大众占卜小红书长图文工作流。真实占卜逻辑：问题→LLM荐阵（≤5张牌硬过滤）→78张无放回抽牌→DeepSeek按牌阵逐选项解读→结构正则修复→Playwright渲染。输出 = 封面(3:4) + 每选项一张自适应高度长图（浅色分享风，复刻 TarotBubble App 分享长图文）。触发词：大众占卜、占卜长图文、三选一/四选一大众占卜、选项图。
---

# 大众占卜长图文 Skill

为「塔罗气泡」小红书笔记产出大众占卜素材：**1 问题 + N 选项（默认 3）→ 封面 3:4 + 每选项一张解读长图**。

## 一键 pipeline（端到端）

一条命令串起完整生产流程：**选题推荐 → 生成封面 → 生成占卜长图文 → 组织目录**：

```bash
cd ip-pipeline
# 随机推荐 N 个选题并端到端生成（先 dry-run 看选题再实跑）
python3 .claude/skills/tarot-mass-divination/scripts/pipeline.py --count 5 --dry-run
python3 .claude/skills/tarot-mass-divination/scripts/pipeline.py --count 5 --out 8.14素材 --workers 3
```

- `--count N`：随机推荐 N 个「未用」选题（从 `topic-library/选题库.xlsx`，自动清洗标题前缀/#标签/括号）
- `--grid 3|4|random`：宫格数（默认 random，决定选项数）
- `--out`：输出目录，每题建 `<问题>/` 子目录放 `封面.png + 选项A/B/C(.D).png`
- **封面生成**：参考 `大众占卜参考封面图/` 目录（用户会不定期更换，脚本动态读取所有 jpg/png/webp），jimeng-image Agent 模式生成
- **占卜长图文**：tarot-mass-divination 按宫格数生成选项
- **并发加速（2026-08-24 起）**：选项解读 LLM、情绪画像、封面分格即梦生图三处均 N 路并发（ThreadPoolExecutor，纯 I/O 等待无状态冲突；分格并发与批量 `--workers 3` 跨题并发即梦同模式）；封面生成与选项图渲染也并行（都只读 content.json）。第二轮优化：短图文情绪画像走 `**关键词**` 组解析快路径（`parse_short_keywords`，省每题 3 次 LLM 调用，长图文仍走 LLM）；`--spread` 手动牌阵可跳过 LLM 荐阵。单题全程 6min → ~2.4min（指定牌阵时 ~2.2min）

> 选题库 title 脏格式较多（#标签/作者名/正文/推广），`clean_title` + `is_valid_question` 已做基本清洗过滤，但仍有半脏选题（如「谨慎思考」）会漏过，建议 dry-run 先看选题再实跑。

### 情绪定向封面（组合管线核心）

`pipeline.py` 顺序已翻转：**选题 → 解读 → 情绪画像 → 封面 → 渲染 → 目录**。封面为 N 宫格整图（jimeng Agent 参考图生图），**每格按顺序反映对应选项解读的情绪/心理**：
- **路线 B（2026-08-21 起）**：封面改为**每格单独 AI 情绪图 + HTML/CSS 拼格**（`render_cover.py`，3:4，标签壹贰叁确定性叠字）。宫格数 100% 确定，不再依赖 AI 整图（路线 A 实测 100% 宫格漂移已弃用）。分格图经 jimeng `--ratio` 按格子比例生成（3 格横格 16:9 / 4 格 2×2 用 3:4）。**版式为满版杂志风（2026-08-24 起，对齐参考封面图）**：图片顶满画布、无缝隙/圆角/描边/标题，每格底部渐变暗条 + 左下统一白字大标签（暗条兼作 OCR 可读底，曾用深色胶囊被否——卡片感太重、与参考图差距大）。
- **情绪画像**：`generate_emotion_profile.py` 读 content.json → 逐选项抽情绪关键词（短图文走 `**关键词**` 组解析快路径，长图文 LLM `data/prompts/extract_emotion.md`，不碰 interpret 提示词）→ 查 `data/emotion_color_map.json`（色彩心理学映射库，12 原型 + fallback，每原型含 `motifs` 画面主体库）→ 写回 `options[].mood`（含 `motif`，跨选项去重；幂等，`--force` 重抽）
- **封面 prompt 物象规则（2026-08-24 修订）**：每格给「情绪 + 主色 + 氛围 + **画面主体 motif**」。路线 A 时代「绝不列物象」防串格约束已随路线 B（每格独立生成，无格可串）松绑——实测只给抽象约束会导致各格画面雷同（同款构图只换色）。motif 由原型物象库给定（不临时编造），仍保留构图硬约束（禁分屏/拼接/多格）与禁文字
- **校验**：`cover_verify.py` 宫格数硬校验（OCR 选项标签计数，ocrmac）+ PIL 主色软校验；宫格数不符自动重试 1 次
- 无 mood（旧 content.json / 无解读）→ 自动回退通用封面 prompt
- `--format short|long` 用户指定；`--grid 3|4|random` 决定选项数与宫格数

## 管线（分步，pipeline 内部调用）

```bash
cd ip-pipeline
# ① 生成（荐阵→抽牌→解读→content.json）
python3 .claude/skills/tarot-mass-divination/scripts/generate_mass_divination.py "<问题>" <数据目录> [--n-options 3] [--spread 牌阵名] [--seed N]
# ② 渲染（content.json → out/ PNG）
python3 .claude/skills/tarot-mass-divination/scripts/render_mass_divination.py <数据目录>
```

环境：`DEEPSEEK_API_KEY`（回退 `LLM_API_KEY`）、`LLM_API_BASE`、`LLM_MODEL`。

> **⚠️ 问题名保留问号**：`question` 参数和目录名都要**原样保留问号**（如 `"你的生命天赋是什么？"`、目录 `8.14素材/你的生命天赋是什么？/`）。**严禁**为了目录名简洁而去掉问号——否则长图文标题和目录名都会缺问号（用户明确纠正过）。脚本本身不会 strip 问号，问题出在调用时手写问题名漏了问号。

**generate 内部流程**：
1. LLM 荐阵（`data/prompts/spread_recommend.md`）→ 脚本级 `SPREADS_LE5` 硬过滤（**只许 ≤5 张牌的牌阵**，越界回退时间流牌阵；`--spread` 手动指定同样校验）
2. 抽牌：N 选项 × 牌阵卡数，78 张无放回（跨组不重复），正逆位各 50%
3. 每选项 LLM 解读（`data/prompts/interpret.md`）。**综合解读有篇幅红线**：第1段直球回答 ≤150 字、第2段整体感受与串牌 ≤280 字（提示词 `【篇幅红线】` 约束 + 生成端 `_cap_para` 安全网，超长截到最近句号）。其余板块篇幅仍按 LLM 默认（历史上用户否决过"500~800字上限"和"写足3~4句"，故不对整体再设硬上限）
4. 文本处理链：`postprocess`（截「你还可以追问」尾巴）→ `normalize`（**结构正则修复**，见下）→ `is_complete`（结构校验，不过重试 3 次）→ `finalize`（综合解读两段拆两个 `---` 块）
5. 写 content.json + 拷贝牌图到 `cards/`

## 结构规则（is_complete 校验 + normalize 修复）

渲染要求解读是「每 `---` 块一张白卡」，所以结构必须统一。LLM 输出常见问题靠 **normalize 正则修复，不重新生成**（用户明确）：

| 问题 | normalize 修复 |
|---|---|
| 单牌/行动/启示标题并块（标题在 `\n\n` 后出现） | 标题处切开，各自独立成块 |
| 行动指引/心灵启示没写标题 | 标题补到最后两个无标题块上 |
| 综合解读 1 段 / >2 段 | 1 段→中点句号切开；>2 段→第 1 段独立、其余并入第 2 段；**直接输出两段两块（`---` 分隔）** |

**只有内容缺失**（整张单牌没写、残留 `**隐形流转板块**` 这类结构标签）才重跑 LLM——normalize 修不了，is_complete 会判失败。

is_complete（只验结构不管篇幅）：含行动指引/心灵启示；`**N.` 标题必须是**块首行**且 ≥ 牌数；综合解读恰好两段 = **开头两个块均为无标题文本块**；第三块必须紧跟 `**1.`（防单牌前插过渡段）；`---` 块数 ≥ 牌数+4。校验在 finalize 之前。

> ⚠ normalize 已改为直接输出两段两块，`finalize` 幂等（无需再拆卡）。注意：合并第二段时**不要**再 `"\n\n".join(paras)` 二次 join（会把压成两段的文本展开回 3 段，导致 finalize 不拆卡、is_complete 失败）。

**单选项补跑**（不重抽牌）：import generate 模块，按牌名从 `data/tarot_cards.json` 找回 cardNumber、按位置名从 `data/spreads.json` 找回 positionMeaning，只调 `generate_interpretation` 覆盖该选项。normalize 对存量 content.json 幂等，可离线修复。

## 渲染视觉规则（用户逐条定下的，违反=返工）

- **解读页 = 自适应高度长图**（宽 1560，高 6000~12000px 随内容），**不再固定 3:4**、无 overflow 裁切、无 JS 缩字（曾遮蔽心灵启示）
- **每个 `---` 块独立一张白卡**（复刻 Flutter MarkdownInterpretationView：白 70% 半透明、16px 圆角、0.5px 紫 15% 描边、块间距 12px、正文 16px/1.7）；块间**不加横线**
- 综合解读固定两段 → **两张独立卡片**（第一张单牌卡之前恰好两张卡）
- 解读页**无**顶部「解读来自塔罗气泡」条、**无**底部 AI 提示、**无**引流 CTA（封面仍保留 `cover_ai_tip`）
- 牌卡行：逆位牌图旋转 180°，**牌名纯名不带「逆位」**（对齐 TarotBubble tarot_cards_share_widget.dart），牌名下小字显示**真实牌阵位置名**（过去/现在/未来；是否判断牌阵就是「卡牌1/2/3」）
- 输出文件名：`01_封面.png` + `选项A.png`（**无序号前缀、不带牌名**）
- 封面（3:4 浅色可爱风）：无页头、奶白→柔粉渐变 + ✦✧♡ + 圆润 CSS 卡背 + 卡下糖果色标签 A/B/C… + 底部 `cover_ai_tip` 居中。参数 `theme_color`（默认 `#E8788A`）/`title_style`

## 输出结构

```
<数据目录>/
  content.json     # question/spread/options[](cards+interpretation+cta)
  cards/           # 韦特牌图 + ic_launcher.png
  01_封面.png      # 封面/选项 PNG 直接输出到问题目录根（不进 out/，方便拷贝交付）
  选项A.png…
  out/             # 仅 <问题>.html 中间件
```

**交付时只保留封面 + 选项图**（`01_封面.png` + `选项A/B/C.png`，已在问题目录根），清掉 content.json、cards/、out/（含 html），对齐 `2026.8.12长图文/<问题>/`（10 题 × 3 选项批量产物）。封面按需留/删。

## 批量

```bash
for q in "问题1" "问题2"; do
  python3 .../generate_mass_divination.py "$q" "$q" --n-options 3 && python3 .../render_mass_divination.py "$q"
done
```

牌阵注意：爱情/财运/桃花类问题 LLM 常荐 >4 张的主题牌阵（未来恋人/财富树/桃花运）被回退时间流，属预期。

## 短图文（3:4 定高，解读散文）

与长图文同一套「荐阵→抽牌→DeepSeek 解读→Playwright 渲染」逻辑，但：
- **解读**用 `data/prompts/interpret_short.md`（**状态翻译型** + **开头两组**：先输出 `**关键词**` 和 `**星座与四元素**`（粉色标题，元素→人设翻译），再写状态翻译散文——命名用户说不清的状态、对号入座微场景、重框定；**460-540 字**（统一 10.5px 字号能放下），单段自然流动，无 `---` 分块、无「」/破折号，**每张抽到的牌都必须在散文里点到**（只在关键词/四元素组点名不算，防止全文点牌名、散文不提牌）——生成端按散文部分校验牌名 + 开头两组校验，超长 `_cap_total(535)` 兜底截句号）
- **牌阵只用 3 或 4 张**：荐阵/手动指定都限 `SPREADS_3_4` 集合（生成端硬过滤 + LLM 约束），不用单张/两张牌阵
- **选项页固定 3:4**（1560×2080），**羊皮纸底 `#E8D4B4` 统一配色**（即梦识图爆款参考，带**古朴程序化羊皮纸纹理**——`_make_parchment_uri`：深暖褐底 + ~1.5× 块状细颗粒（介于逐像素与2×2之间） + 低频正弦斑驳（暗处偏棕、亮处偏暖的包浆）+ 随机纤维细线/细点（偶有几根）+ 老化渍斑；`::before` 叠加**边缘泛黄老化晕染**，像旧纸中间亮、四边泛黄）：顶部**组号 + 问题**（不显示牌阵名）+ **牌面小图行**（每张牌小图 + 图下牌名更小更淡，逆位旋转 180°）+ **关键词/星座与四元素 两组**（深玫瑰 `#C4677E` 加粗标题；**关键词标题+关键词同一行粉粗**，换行祝福句；星座与四元素标题独占一行、正文换行）+ 状态翻译散文（**无底部引流 CTA**），**字体楷体 `Kaiti SC`**（古朴感，宋体 `Songti SC` 回退；区别于长图文的苹方/Noto Sans）
- **全篇只有 2 种字号**：标题（组号/关键词/星座与四元素）**固定 13px** 加粗粉色（三组一致）+ 其余（问题/牌面名/两组正文/散文）**1em = 10.5px 统一**（`.s-scale` 缩放容器 base 10.5px，全局统一字号——取最长组所需，三组一致不因内容长短错位）
- 排版为容纳 540 字：牌面小图 24×42、内边距 16/10；**块间距拉开**（关键词组→星座与四元素→散文各 14px），关键词组内部（标题+关键词+祝福）紧凑成一组
- 正文超限 JS 按 0.5px 缩字号（下限 9.0px，**必须 IIFE 立即执行**，普通箭头函数字符串不会求值导致末行被裁），保证定高不溢出不截断

```bash
python3 scripts/generate_short_divination.py "<问题>" <数据目录> [--n-options 3] [--seed N]
python3 scripts/render_short_divination.py <数据目录> [--theme parchment|black]
```

- **双主题**（仅换皮，结构/字号/缩字逻辑完全一致；`parchment` 默认）：`black` = 抖音爆款纯黑风（参考抖音大众占卜爆款帖）——纯黑 `#000000` 底（**必须 `background-image:none` 压掉 `.sheet` 基类紫色渐变**）、标题沿用深玫瑰 `#C4677E` 带 emoji（🔮组号 / 💫关键词 / ✨星座与四元素）、正文白 92% 半粗 600、苹方（不用楷体）、关键词块上边距 12px（`gmt` 主题变量）；封面不变。**黑版与羊皮纸版同目录共存**：black 主题选项图输出为 `选项A-纯黑.png`（羊皮纸 `选项A.png` 不动），封面两主题相同共用 `01_封面.png`

- content.json 多一个 `format:"short"`；输出文件名与长图文一致（`01_封面.png` + `选项A/B/C.png`，**全部 3:4**）——**PNG 直接输出到问题目录根**（不进 `out/`，方便直接拷贝交付）；`out/` 仅留 `<问题>.html` 中间件
- 篇幅校验 460-540 字（统一 10.5px 字号能放下）；LLM 常写超长，脚本内置「重试 3 次 + 超长压缩 + `_cap_total(535)` 截句号兜底」
- 短图文视觉规范见 `data/短图文配图设计规范.md`（现行定稿：羊皮纸底 `#E8D4B4` + 深玫瑰 `#C4677E` 标题 + 关键词/星座与四元素两组 + 状态翻译散文 + 2 种字号 + 块间距）
- 爆款文案拆解见 `data/爆款文案拆解.md`（抖音/B站三篇爆款：万能骨架 7 步 + 底盘四铁律 + 封神/疗愈/圈层点名三路线；6 条借鉴已落地 `interpret_short.md`：答题留活口/人群点名/短板焊高贵出处/微场景反差/拟物化金句/条件化希望结尾）

## 铁律（项目 CLAUDE.md）

1. **禁止「」引号**（标题/正文/图片/解读）。
2. **AI 生图绝不作文字排版**：文字全归 HTML/CSS 模板。本工作流不需要 AI 生图（纯渐变底复刻原设计）。
3. 字体 PingFang SC，不用宋体衬线。
4. 解读由 DeepSeek 按 `interpret.md` 生成（真实牌意，不手写、不编造牌意）。
5. **选项图底部不加引流 CTA**（已去掉「Luna 在塔罗气泡App等你来聊聊」）。

## 验证

- 结构：content.json 每选项 `---` 分块后 = 段段 + `**N.`×牌数 + （联动段） + **行动指引 + **心灵启示
- 视觉：渲染后抽查 PNG 顶部（牌名+位置）与底部（心灵启示完整）；可用 macOS Vision OCR 逐字核对
- 长图高度 6000~12000px 属正常

## 数据文件（skill `data/`）

| 文件 | 来源 | 用途 |
|---|---|---|
| `tarot_cards.json` | TarotBubble `tarot_cards_data.dart` + backend `TarotCards.java` | 78 张牌 |
| `spreads.json` | backend `sql/init_db.sql`（56 牌阵） | 牌阵位置名+含义 |
| `prompts/spread_recommend.md` | 用户提供 | LLM 荐阵 |
| `prompts/interpret.md` | 用户提供 | LLM 解读（自带全部文案规范，**不要改动、不要追加篇幅约束**） |

## 参考

- 复刻来源：`TarotBubble/lib/features/tarot/presentation/screens/long_text_share_tab.dart`、`shared/widgets/markdown_interpretation_view.dart`、`shared/widgets/tarot_cards_share_widget.dart`
- 本工作流为浅色分享风；深色漫画风走 `tarot-x-psy-material`
- **短图文**（封面 + 每选项一张 3:4 解读图）配图设计规范见 `data/短图文配图设计规范.md`（现行定稿：羊皮纸爆款风，即梦识图拆解沉淀 + 多轮反馈打磨）

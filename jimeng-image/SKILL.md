---
name: jimeng-image
description: 即梦(jimeng.jianying.com) AI 生图。当用户要求"即梦生图""jimeng 生成图片""用即梦画"或指定即梦出图时使用。复用 ego-lite 浏览器的登录态（不占用用户主浏览器）。默认走 Agent 模式（agent_generate.py），默认模型图片 5.0 Lite、默认 3:4 @ 2K、默认生成 3 张、默认不拆解参考图直接基于提示词生成（要精确还原参考图质感加 --describe 自动识图）；需要精确控制模型/strength/多参考图时用 jimeng_generate.py。
---

# 即梦 AI 生图

> **⚠️ 写提示词前必读（两个文件都要翻，缺一不可，任何生图请求都不例外）**：
> - **`prompt-presets.md`** = 怎么写：大师心法（七层结构/空间关系显式化/位置三件套）、**跨示例元知识**（专名点名锁风格/情绪用可见证据/光三件套/负向块+可信瑕疵/风格帧不混搭等 8 条，适用一切生图）、常识纠错对照表（照片朝向反、人物位置漂移、手部畸形等翻车修正句式）、大众占卜封面六大风格预设库（影视人物/静物油画/风景/情绪特写/治愈插画/日系写真）+ 预设G自然感美女/情侣实拍（逆光发丝/第一人称情侣POV/照片叠产品卡背景）、封面通用硬约束块、生成后复检清单。
> - **`prompt-examples.md`** = 好样例长什么样：30 条示例 + 六块通用件（胶片/主角配方/肤质/发丝/织物/负向）+ 27 条共性规律 + 技法笔记（前景失焦光斑遮挡、叙事性布光）+ GPT 结构化模板。**同款场景/光线先查示例抄骨架**。
> 拼装顺序（真人像/氛围图必按此序）：**场景定调词（开头）→ 主角配方块 → 姿态 → 服装/织物 → 光的三件套 → 肤质/发丝细节 → 风格帧 → 负向块**。
> 用户反馈（2026-08-20）：只翻 presets 漏 examples 会导致真人像缺肤质/负向/风格帧料、AI 味重。两个文件是本 skill 的共享资产，供所有人使用。

通过 ego-lite 浏览器（`ego-browser nodejs`）在即梦页面上下文内发 XHR 调内部 API，`msToken`/`a_bogus` 签名由页面 SDK 自动注入，登录态复用 ego 的用户 profile，不干扰用户日常浏览器。

## 用法

**默认走 Agent 模式**（文生图 + 参考图生图都用这个，还原度最高）：

```bash
# ★ 文生图（Agent 模式，默认：图片5.0 Lite / 3:4 / 2K / 3张）
python3 .claude/skills/jimeng-image/scripts/agent_generate.py "提示词" [--out ./jimeng_output]

# ★ 参考图 + 文案（Agent 模式，默认不拆解，直接基于提示词 + --ref 生成）
python3 .claude/skills/jimeng-image/scripts/agent_generate.py "换成新的不同人物" --ref ./ref.png

#   需要精确还原参考图关键质感时 → 显式 --describe（先识图→关键约束→生成）
python3 .claude/skills/jimeng-image/scripts/agent_generate.py "参考这张图生成新图，必须严格保留[识图的关键特征]，只换主体内容" --ref ./ref.png --describe

# 需要精确控制（模型/strength/多参考图/2K分辨率）时才用 i2i
python3 .claude/skills/jimeng-image/scripts/jimeng_generate.py "提示词" [--ref ./ref.png] [--count 1] [--model 5.0 Pro] [--strength 0.5] [--out ./jimeng_output]
```

**⚠️ 参考图生图的核心经验（实测踩坑）**：Agent 直接生成会**漏掉参考图的关键质感**——油画颗粒感、皮肤红润通透、暖调主色、光影方向这些细节会被"偷懒"丢成冷灰发灰。**默认已改为不拆解、直接基于提示词生成；需要精确还原参考图质感时显式加 `--describe`**，把识图描述的「材质/笔触/光影/皮肤/主色/氛围」提炼成 prompt 的**硬约束**，再让 Agent 生成。实测：识图约束后暖色占比 16%→44%（参考 40%）、平均色从冷灰 [60,65,64] 回到暖棕 [91,87,77]（参考 [98,89,84]），还原度显著提升。识图描述也比 OCR 更准（能识别书法字"壹贰叁"，OCR 会误读成"第一组"）。

**脚本选型**：

| 场景 | 用哪个 | 说明 |
|---|---|---|
| **默认（文生图 + 参考图生图）** | **`agent_generate.py`** ★ | Agent 端到端理解，prompt 自动精细化（含质感/景深/色彩调性），还原最"传神" |
| 精确控制（模型/strength/多参考图/2K） | `jimeng_generate.py --ref` | byte_edit/i2i，可控参数多 |
| 参考图风格分析 | `describe_reference.py` | 即梦识图，输出构图/光照/视角描述 |

- `prompt`：必填，图片提示词（中文即可）
- `--count`：生成张数，**默认 3**
- `--model`：图片模型，**默认 5.0**（图片5.0 Lite，`high_aes_general_v50`），额度不足自动降级到 4.7。支持 `4.0 / 4.1 / 4.5 / 4.6 / 4.7 / 5.0`（图片5.0 Lite）/ `5.0 Pro` 或直接传 model_req_key。模型 key 清单可查页面 `window.__image_generate_model_config__`
- `--describe`：对 `--ref` 参考图先自动识图拿关键维度约束再生成（**默认不拆解，直接基于提示词生成**）
- `--no-enhance`：关闭自动润色（**默认开**：简单提示词自动追加对应风格质感块 + 负向块 + 张数提示，纯文字/参考图+文字都能"丢个简单 prompt 出不错效果"；已含硬约束【必须/禁止/严格】或复刻版式时自动跳过）。**注意**：Agent 模式实际出图张数由 prompt 决定，简单 prompt 未写"生成N张"时 enhance 会自动补上（否则 `--count 3` 可能只出 1 张）
- `--ref`：参考图路径，可传多次（一张或多张）。参考图 + 文案 → 保留参考图的构图/配色/主体生成新图。
- `--strength`：参考图强度（byte_edit，jimeng_generate.py），默认 0.5（与网页端一致）。要更贴参考图风格/构图/配色调高到 `0.7-0.8`；要高自由创作调低到 `0.3-0.4`

固定参数（agent_generate.py，2026-08-04 ego 抓包实测）：默认模型 `high_aes_general_v50`（图片 5.0 Lite），额度不足自动降级 `high_aes_general_v43`（图片 4.7）；3:4 @ 2K（1728×2304，文生图与参考图同）。改参数改脚本顶部常量。jimeng_generate.py（i2i）默认 5.0 Pro、参考图分辨率 1.5K。
注意：`gen_option` 必须是 `abilities` 下 `generate` 的同级字段（抓包实测）。放进 `generate` 内部会被后端忽略、按 workspace 默认张数出图（实测 4 张）。请求始终带 `gen_option.gen_count=N`。

### 参考图模式（--ref）

参考图生成走即梦"图生图/i2i"经典端点 `aigc_draft/generate`（2026-08-13 抓包实测，网页 UI 已切 Agent 模式但经典端点仍可用）：

- **上传**：脚本把参考文件以 **drop 事件注入**上传容器 `[class^="reference-upload-"]`（`DragEvent('drop')` + `DataTransfer` 带 File，见 2026-09-09 修复），页面自身 SDK 完成 `get_upload_token → ApplyImageUpload → TOS 分片/整传 → CommitImageUpload → submit_audit_job`；脚本拦截 `submit_audit_job` 请求体 `uri_list` 拿 store_uri，**无需复制 TOS 签名逻辑**。大图（>2MB）自动用 PIL 压缩到最长边 2048 再传。
- **生成结构**：`image_base_component.generate_type="blend"` + `abilities.blend`，每个参考图一个 `ability_list` 条目（`name="byte_edit"`、`image_uri_list=[uri]`、`image_list=[{image_uri:uri, source_from:"upload", platform_type:1}]`、`strength:0.5`）；prompt 自动加 `"##"×N` 前缀；`babi_param.feature_key="to_image_referenceimage"`、`extra_param.generate_type="i2i"`。
- **分辨率**：参考图模式固定 1296×1728 @ 1.5K（5.0 Pro i2i 默认，抓包实测），与文生图的 2K 不同。
- **文字**：prompt 原样传给即梦（只加 `##`×N 前缀），**不自动加「禁止文字」**——AI 会像网页端一样复刻参考图的文案/手绘字体。要无字背景就在 prompt 里自己写「禁止任何文字」。
- 实测：单张参考图、多张参考图（每个 byte_edit 条目）均验证可用；带文字复刻参考图风格已实测（OCR 16 处文字）。
- **宫格版式复刻（2026-08-20 修正，用户偏好）**：
  - **一次 `--count N` 出 N 张**（**不要逐张 `--count 1`**——太慢）。用 prompt 控制张数与版式：`生成N张，严格保持 N 宫格版式不变（不要变多不要变少），每张换新画面和选项文字，图片不要雷同`。
  - 注：i2i byte_edit（jimeng_generate.py）实测多张版式会漂移（4 宫格→6/8/9），但 **Agent 模式（agent_generate.py）用 prompt 控制张数版式稳定**（用户实测，`--count 3` 一次出 3 张）。
  - **不要列具体物象**（如「金币/财神/聚宝盆」），列物象会触发版式漂移。只说「换新画面 + 换选项文字」。
  - 注意：投影法检测宫格数会被弱分隔线误导（误判 2 宫格），用 **OCR 选项坐标**判断（N 个选项分布 = N 宫格）才准。

### 参考图反向解析工作流（避翻车核心）

`--ref` 前**先拆参考图**，把风格约束写进 prompt，避免「元素堆砌 / AI味 / 不干净」。四步：

**① 程序化拆解（自动，先跑这个）**
```bash
python3 .claude/skills/jimeng-image/scripts/analyze_reference.py <参考图> [--cells 2x2] [--json]
```
输出风格矩阵：版式（宫格）、色调（暗/中/明）、饱和度（muted/鲜艳）、主色中文名、留白占比、细节密度、参考图比例。

**② 语义确认 —— 优先用「即梦识图」自动提取（程序化测不到的语义）**
```bash
python3 .claude/skills/jimeng-image/scripts/describe_reference.py <参考图>
```
调即梦 Agent 模式（`creation_agent/v2/conversation`），让即梦自己描述参考图的 5 个语义维度：
- 构图逻辑（主体位置、布局、留白、分隔线）
- 元素密度（简洁/丰富、有无堆砌）
- 光照（方向、明暗、光线质感、色温）
- 视角景别（平视/俯仰、特写/全景）
- 画面氛围

返回 `description` 字段，直接拼进 prompt（见③）。这是还原「构图/光照/视角」的关键——程序化和人眼都测不准，但即梦识图能精确描述（实测：识图描述让元素密度对齐度明显提升）。

> 无即梦识图时（或想补充），再问用户：线条质感 / 光线 / 构图 / 文字 / 氛围。

**③ 写 prompt（先判断场景，别一上来就写详细约束）**

**场景A：复刻样式（最常见 = 用户网页端用法）→ 极简 prompt**
```
这是[类型]封面图，[N]宫格，每个宫格一张图，每张图左下角有一个选项。
请你完全复刻这个样式为我生成[N]张图，图片不要雷同。
```
一句话、参考图主导。**绝不要写每格详细内容**——写详细内容会把即梦从「照着参考图改」带偏成「按文字自由发挥」，导致元素堆砌、AI 味重（实测：详细 prompt 留白 12.8% vs 极简 prompt 25%+，干净度差距明显）。

**场景B：风格迁移 / 自由创作 → 才写风格约束**
```
[版式] 2×2宫格，每格单一主体，大片留白/负空间
[配色] 暗调、低饱和（墨蓝/灰蓝/暖褐），无高饱和鲜艳色
[线条] 手绘柔线、干净利落
[光线] 柔和自然光
[氛围] 静谧治愈
[内容] 每格仅一物 A / B / C / D
```
**铁律：每格只给 1 个主体**。`一条桃花枝` 而非 `樱花树下浪漫邂逅的男女剪影`——元素一多就脏、就 AI 味。

**④ 生成 + 复检**
- 默认 `--strength 0.5`；要更贴参考图风格 → `0.7-0.8`
- 生成后 macOS Vision OCR 复核文字、比对配色/留白是否符合风格矩阵

## 输出

stdout 逐行 JSON：
1. `{"stage": "ref_uploaded", "index": N, "uri": "tos-..."}`（仅参考图模式，每张图一条）
2. `{"stage": "submitted", "submit_id": ..., "history_id": ...}`
3. 成功：`{"status": "ok", "count": N, "images": ["绝对路径", ...]}`
4. 失败：`{"status": "error", "stage": ..., "errmsg": ...}`（exit code 1）

把最终的 `images` 路径告诉用户。

## 前提与故障处理

- 依赖：ego-lite 已安装并在首次引导后完成即梦登录（登录态持久保存在 ego profile）；`~/.local/bin/ego-browser` 可用；python3 无需额外依赖（大图参考图压缩需 `Pillow`，一般环境已有；没有时会报 ImportError）。
- `no_webid` 错误：ego 里即梦登录失效 —— 让用户在 ego lite 中重新登录 jimeng.jianying.com。
- generate 阶段 `ret: "3018"`：签名/权限问题，通常是登录失效或即梦更新了参数结构（重新抓包比对）。
- 参考图上传超时：脚本注入后 40s 内没等到 `submit_audit_job`。**2026-09-09 已修复（即梦前端改版打断）**：即梦把参考图上传从「常驻 file input」改为「点击加号→原生文件选择器」，agentic 页 `fileInputCount=0`、点加号后 MutationObserver 3.5s 内无任何 input 创建（改用 `showOpenFilePicker` 类 API），旧 `input.files=DataTransfer` 的 DOM 注入必然超时。**新注入通道 = drop 事件**：往上传容器 `[class^="reference-upload-"]` 派发 `dragenter/dragover/drop`（`DragEvent` + `DataTransfer` 带 File），SDK 自行走 `submit_audit_job` 拿 store_uri（实测成功拿到 `tos-...`）。agent_generate.js 已改为「等容器出现 → drop 派发」；jimeng_generate.py 仍走 `.reference-upload-eWIGta input[type=file]`，若同样超时也要改成 drop 注入。
- 上传端点现为 `mweb/v1/imagex/submit_audit_job`（请求体仍顶层 `uri_list`）。
- **Agent 生成阶段瞬时错误 `ret: "7057" err stream receive`**（`creation_agent` SSE 流偶发中断）：服务端瞬时抖动，非请求参数问题。**2026-08-20 已内建自动重试**：脚本会自动重新发起会话（最多 3 次）再报错，通常无需手动干预。
- 积分不足：脚本检测到 credit 相关错误会自动降级到图片 4.7 重试一次；若 4.7 仍不足，才报错提示用户充值或降数量。agent_generate.py 默认 5.0 Lite，单张积分消耗低（约 2-3 积分/张）；jimeng_generate.py i2i 默认 5.0 Pro，单张消耗更高（约 8-11 积分/张）。
- 超时：高峰期排队，调大 `--timeout`。

## 注意

- 每次生成消耗即梦积分（5.0 Lite 2K 每张约 2-3 积分；i2i 5.0 Pro 更高），**默认一次 3 张**，调用前确认张数。
- 图片 URL 是 byteimg 签名链接（约 2 小时过期），脚本已即时下载到本地。
- 旧的 Chrome CDP 方案抓包存档在 `jimeng/captures/key_requests.json`，调参时可对照。

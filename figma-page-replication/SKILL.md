---
name: figma-page-replication
description: |
  Figma 设计稿 → 应用页面完整复刻工作流。支持 Flutter / React Native / Compose 等任意 UI 框架。
  核心流程 P→A→I→E→V→B：准备 Figma 上下文 → 模块分析与策略判定 → 资源收集 → 逐模块构建
  → 多维度验证 → 边界陷阱参考。内置三轨策略引擎（整图导出 / 原生 Widget / 复用项目组件）、
  设计标记自动映射、底部 CTA 滚动自适应阴影模式、常见陷阱自动规避。
  适用于活动落地页、招募页、推广页、功能引导页等任何 Figma → Code 场景。
tags: [figma, landing-page, design-to-code, flutter, react-native, compose, page-replication, manifest, image-to-code]
---

# Figma 页面复刻工作流

> **适用范围**：Claude Code / Codex / Cursor / Copilot / Windsurf / Cline 等任何 AI Coding Agent。
> 可以作为 Skill、自定义指令、Rules、System Prompt 或项目约定加载。核心方法论 P→A→I→E→V→B 与具体工具无关。

将 Figma 设计稿精准复刻为应用页面。基于多个实战项目迭代提炼，覆盖从设计分析到代码落地的完整链路。

**流程**: P → A → I → E → V → B（Preparation → Analyze → Identify → Execute → Verify → Boundary）

## 前置条件

使用者需要确保其 AI Coding Agent 能访问 **Figma MCP**（Model Context Protocol），提供以下工具：
- `get_design_context(nodeId, fileKey)` — 获取设计节点完整规格
- `get_screenshot(nodeId, fileKey)` — 获取设计节点截图
- `get_metadata(nodeId, fileKey)` — 获取节点结构树（context 过大/截断时用）

配置方式参见 [README.md](./README.md)。

## Skill 边界

**交付物是仓库里的页面代码** 时使用本 skill。以下情况不要走完整 P→A→I→E→V→B：

| 场景 | 处理 |
|------|------|
| 在 Figma 画布内创建/编辑/删除节点 | **不用本 skill**；改用 Figma 画布类 skill（如 `figma-use`） |
| 仅实现单个组件/设计系统变体（Button、Chip、空态） | **轻量路径**（见下），不必整页分析表 |
| 纯逻辑页、无视觉稿、无 Figma 链接 | **不触发** |
| 仅要 Code Connect / 设计 token 文档 | **不触发** |
| 活动/招募/落地/推广等整页复刻 | **完整流程** |

### 轻量路径（单组件 / 局部区块）

满足任一即可走轻量路径：

- 用户明确只要一个组件或一小块 UI
- 分析后模块数 ≤ 2，且无策略 A 整图资源

轻量步骤：

1. P：解析 URL → `get_design_context` + `get_screenshot`（过大则 metadata 分层）
2. A：口头判定策略 B 或 C（可跳过完整分析表、manifest 与 A6 确认，除非用户要求）
3. I：仅当有策略 A 时收集资源
4. E：实现并 **优先策略 C 复用**；有偏离写注释
5. V：对照截图做 layout/type/color 快速验收

---

## When to Activate

触发条件（满足任一）：
- 用户提供 Figma 链接并要求「复刻」「实现」「做活动页」「做落地页」
- 用户说「参考 figma 设计稿」「按设计稿做」
- 关键词：`figma.com` + 落地页/活动页/招募页/推广页

---

## P: Preparation — 准备阶段

1. 从 Figma URL 提取 `fileKey` 和 `nodeId`
2. 调用 `get_design_context(nodeId, fileKey)` 获取完整设计规格
3. 调用 `get_screenshot(nodeId, fileKey)` 获取视觉参考截图
4. **确认项目的资源目录路径**：检查 `pubspec.yaml` / 项目配置中的 assets 路径
5. **确认项目设计系统入口**：组件库路径、主题/token 文件（供策略 C 检索）

### P2 补充：Context 过大 / 截断时的分层拉取（必须）

`get_design_context` 返回过大、截断、或明显缺层时，**禁止瞎猜补全**，按序：

```
1. get_metadata(nodeId, fileKey)     → 高层次节点树 / 子节点 ID 列表
2. 按从上到下识别主要 section 的 childNodeId
3. 对每个 section 分别：
     get_design_context(fileKey, childNodeId)
     （可选）get_screenshot(fileKey, childNodeId)
4. 合并各 section 规格后再进入 A 阶段
```

规则：
- 优先对 **页面主 frame 的直接子节点** 分批拉取
- 某 section 仍过大 → 对该 section 再 `get_metadata` → 继续下钻
- 整页 `get_screenshot` 仍建议保留一张，作 V2 全局对照

---

## A: Analyze — 模块分析（关键步骤）

**目的**：在写任何代码之前，完整解析设计稿中每个模块的类型和策略。

### A1: 获取设计树

```
get_design_context(nodeId, fileKey) → 解析所有子节点
```

若 context 截断/过大 → **先走 P2 分层拉取**，再解析模块。不要在半截 JSON 上做完整分析表。

### A2: 输出模块分析表

按从上到下顺序，逐个模块记录。以下为示例格式（括弧内为 Figma 提取值，实际项目会不同）：

| # | 模块描述 | Figma top | 设计尺寸 | 复杂度 | 策略 | 说明 |
|---|---------|-----------|---------|--------|------|------|
| 0 | `<badge>` | 53 | 292×27 | 简单 | **A** | 导出3x整图 |
| 1 | `<hero_banner>` | 76 | 343×112 | 简单 | **A** | 导出3x整图 |
| 2 | `<subtitle_text>` | 195 | 359×28 | 简单 | **B** | Text.rich（1 agent） |
| 3 | `<description_text>` | 235 | 356×51 | 简单 | **B** | Text（1 agent） |
| 4 | `<tag_row>` | 305 | 345×25 | 简单 | **A** | 导出3x整图 |
| 5 | `<feature_cards>` | 341 | 334×226 | **复杂** | **A** | 导出3x整图（≥3张独立卡片） |
| 6 | `<expect_section>` | 569 | 355×159 | 简单 | **A** | 导出3x整图 |
| 7 | `<cta_button>` | 814 | 343×48 | 简单 | **C** | 复用 XxxButton + 文案/渐变变体（1 agent） |
| 8 | `<bottom_hint>` | 875 | 342×17 | 简单 | **B** | Text（1 agent） |
| 9 | `<back_button>` | — | — | 简单 | **C** | 复用项目返回控件（1 agent） |

每个模块还记录与上一模块的间距（`下一模块.top - (上一模块.top + 上一模块.height)`），用于后续 `SizedBox` 取值。

### A2b: 复杂度判定与拆分规则

**复杂度定义**（影响 E 阶段并行分派粒度）：

| 级别 | 条件 | Builder 策略 |
|------|------|-------------|
| 简单 | 单组件无子结构（1 个 Text / 1 个 Button / 1 张图） | **1 个 agent** |
| 中等 | 1-2 个子组件，结构明确 | **1 个 agent**，spec 内容 ≤ ~150 行 |
| 复杂 | ≥3 个独立子组件，各有独特样式/状态 | **拆分为 N 个 agent**：每个子组件独立 builder + 1 个 wrapper builder |

**拆分示例**：`<feature_cards>` 包含 3 种卡片变体（每种有独特 hover 态和布局）→ 拆为：
- `feature_cards/card_variant_a` — builder agent 1
- `feature_cards/card_variant_b` — builder agent 2  
- `feature_cards/card_variant_c` — builder agent 3
- `feature_cards/wrapper` — builder agent 4（import 前 3 个 + 组装布局）

**判定原则**：When in doubt, make it smaller。宁可多拆，不要让一个 agent 处理过于复杂的模块。

### A3: 策略判定规则

**判定顺序：先 C，再 A，最后 B。** 能复用项目组件时不要新建平行实现。

| 条件 | 策略 |
|------|------|
| 模块与项目已有组件**同构**（主按钮、次按钮、返回、Tag、空态、列表项、Nav 等） | **C**：复用项目组件 + 样式/文案变体 |
| 模块内**同时有底图 + 叠加文字**（文字已嵌入底图不可分离） | **A**：整图导出3x |
| 模块包含**复杂不规则装饰物**（SVG路径多且非规则形状） | **A**：整图导出3x |
| 模块包含**照片级细节或复杂纹理** | **A**：整图导出3x |
| 模块仅有**纯色/渐变底色 + 独立文字** | **B**：Widget渲染 |
| 模块仅为**纯文本**（无论是否有富文本样式） | **B**：Widget渲染 |
| 模块为**简单按钮**但项目中无对等组件 | **B**：Widget渲染 |
| 模块为**简单按钮**且项目已有对等组件 | **C**：复用 |

**策略 C 检索方法（写代码前做）：**
1. 在项目中搜索同类 UI：Button / AppBar 返回 / Tag / Chip / Card 等
2. 找到则记录：文件路径、构造参数、主题 token
3. 分析表「说明」列写清复用哪个组件、要改哪些参数
4. 找不到对等物 → 降级为 B（或视觉极复杂则 A）

### A4: 输出 manifest

将分析表转换为 `layers.manifest.json`，作为后续 E 阶段（构建）和 V 阶段（验证）的单一数据源。

```json
{
  "version": "1.0.0",
  "source": {
    "type": "figma",
    "source_width": 390,
    "source_height": 844,
    "target_width": 390,
    "target_height": 844,
    "scale": 1.0
  },
  "layers": [
    {
      "id": "hero_banner",
      "type": "bitmap",
      "strategy": "A",
      "source_bbox": { "x": 16, "y": 76, "width": 358, "height": 112 },
      "scaled_bbox": { "x": 16, "y": 76, "width": 358, "height": 112 },
      "z_index": 10,
      "asset": "assets/hero_banner_3x.png",
      "figma_node_id": "123:456",
      "gap_to_next": 12
    },
    {
      "id": "subtitle_text",
      "type": "text",
      "strategy": "B",
      "source_bbox": { "x": 16, "y": 195, "width": 359, "height": 28 },
      "scaled_bbox": { "x": 16, "y": 195, "width": 359, "height": 28 },
      "z_index": 5,
      "spec_file": "docs/research/modules/subtitle_text.spec.md",
      "figma_node_id": "123:567",
      "gap_to_next": 7
    },
    {
      "id": "cta_button",
      "type": "component",
      "strategy": "C",
      "source_bbox": { "x": 24, "y": 814, "width": 343, "height": 48 },
      "scaled_bbox": { "x": 24, "y": 814, "width": 343, "height": 48 },
      "z_index": 20,
      "reuse": "XxxPrimaryButton",
      "spec_file": "docs/research/modules/cta_button.spec.md",
      "figma_node_id": "123:789",
      "gap_to_next": 8
    }
  ]
}
```

**规则**：
- `figma_node_id` 记录对应 Figma 节点，便于追溯
- `gap_to_next` 记录与下一模块的垂直间距
- `strategy` 必须通过 A3 判定规则分配（`A` | `B` | `C`）
- 策略 C 建议写 `reuse` 字段标明复用组件名/路径
- 策略 B / C 的模块**必须**在 E2 阶段写 `spec_file` 并在 manifest 中记录路径
- 统一使用本 skill 内置 [manifest 规范](references/manifest-spec.md)（已随本 skill 内嵌完整内容）

### A5: 预览模块边界

在 Figma 截图上用脚本标注各模块边界，验证分析表的模块划分是否准确：

```bash
scripts/preview_modules.py figma-screenshot.png layers.manifest.json qa/module-preview.png
```

- 红色框 = Strategy A（整图导出）
- 蓝色框 = Strategy B（原生渲染）
- 绿色框 = Strategy C（复用项目组件；脚本未区分时可与 B 同色，以 manifest `strategy` 为准）
- 青色线 = gap_to_next 间距指示

检查框选区域是否完整覆盖每个模块，不框到相邻元素。边界不准时，先改 manifest，再重新预览。

### A6: 用户确认

展示分析表 + 模块边界预览图，等待用户确认策略分配。确认后进入资源收集阶段。

轻量路径可跳过本步；整页流程默认**不可跳过**。

---

## I: Identify — 资源收集

根据分析表收集策略 A 的资源：

1. 列出所有标记为 **策略 A** 的模块（从 `layers.manifest.json` 筛选 `strategy="A"`）
2. 请用户从 Figma 桌面端逐个导出 3x PNG → 本地目录（如 `~/Downloads/`）
3. 复制到项目资源目录下（路径从 P4 确认）
4. 优先检查用户本地是否有已有高清版本（避免 Figma API 1x 模糊）
5. **运行资源审计**：

```bash
scripts/audit_assets.py assets/ \
  --manifest layers.manifest.json \
  --no-black-bg \
  --min-dimension 200
```

检查项：
- 资源尺寸是否匹配 manifest 预期（检测 1x 误导出）
- 是否有黑色背景（Figma 导出常见问题）
- 文件大小是否正常（检测空白导出）

**注意**：Figma API 的 `get_screenshot` 只能输出 1x 设计分辨率 → **永远不要用作策略 A 的最终资源**。

策略 B / C 不需要整图导出；C 仅复用代码与 token，不新增平行图片资源。

---

## E: Execution — 构建阶段（Extract → Spec → Dispatch → Merge → Assemble）

**核心原则**：不是一次性写完全部代码，而是 **逐模块提取 → 写 Spec → 并行分派 Builder → Merge → 组装**。提取和构建可以并行进行——你在提取下一个模块的同时，builder agent 已经在 worktree 中构建上一个模块。

### Guiding Principles（E 阶段专用）

这些原则区分成功的复刻和「差不多」的半成品：

**1. 完整性优先于速度**：每个 builder 必须收到完成工作所需的所有信息——截图、精确 Figma 值、资源路径、真实文本内容、组件结构。如果 builder 需要猜测任何值（颜色/字号/间距），提取就不完整。

**2. 小任务，精结果**：让一个 agent「构建整个 features 区域」→ 它会敷衍间距、猜测字号。给它一个聚焦的单组件 + 完整 CSS 规格 → 每次都精准。复杂模块应拆分。

**3. Spec 文件是唯一真相源**：每个策略 B/C 模块必须在分派 builder 之前写 spec 文件。Spec 是提取工作与 builder 之间的契约。builder 收到 spec 内容内联在 prompt 中——不是「去看 DESIGN_TOKENS.md」，而是零外部引用。

**4. 先提取外观，再提取行为**：组件不只是静态截图——它有 variant（hover/pressed/disabled/selected）、有 transition、有响应式变化。从 Figma `get_design_context` 中提取所有 variant 的样式差异。

**5. 构建必须始终可编译**：每个 builder 完成后验证 typecheck/lint。每次 merge 后验证完整 build。不允许任何时刻构建是坏的，即使是临时性的。

### E0: 创建 Spec 目录

```bash
mkdir -p docs/research/modules
```

---

### E1: 逐模块提取 + 写 Spec（Extract & Spec）

这是核心循环的一部分。对分析表中每个策略 **B** / **C** 模块（策略 A 不需要 spec——整图导出已在 I 阶段完成）：

#### Step 1: 提取完整 Figma 样式

从 `get_design_context` 返回的设计数据中，为该模块提取所有视觉属性：

```javascript
// 对目标 Figma 节点运行 get_design_context，提取以下信息：
// - 字体：fontFamily, fontSize, fontWeight, lineHeight, letterSpacing
// - 颜色：fills/strokes 中的色值（含透明度）
// - 布局：padding, gap, alignment, constraints
// - 装饰：borderRadius, boxShadow, backdropFilter, gradient
// - Variant：所有交互状态的样式差异（hover/pressed/disabled/selected）
// - 内容：所有文本节点的实际文字
// - 资源：该模块引用的图片/SVG 节点
```

**规则**：
- 每个值必须从 Figma context 中精确提取，不用「看起来像 16px」这种近似
- 如果有 variant（组件变体），提取所有 variant 的完整样式
- 截图保存到 `docs/design-references/<module-id>.png`，供 builder 视觉对照

#### Step 2: 写模块 Spec 文件

**文件路径**：`docs/research/modules/<module-id>.spec.md`

**模板**：

```markdown
# <ModuleName> 模块规格

## 基本信息
- **目标文件**: `src/components/<ModuleName>.tsx`（或项目对应路径）
- **策略**: B（原生渲染）| C（复用 `<ComponentName>`）
- **Figma 节点**: `123:456`
- **截图**: `docs/design-references/<module-id>.png`
- **复杂度**: 简单 | 中等 | 复杂（≥3 子组件）

## 层级结构
<!-- 描述 DOM / Widget 层级：什么包含什么 -->
- Container (maxWidth: 343, padding: 16)
  - Text (标题)
  - Row (标签组)
    - Chip × 3

## Figma 精确样式（来自 get_design_context）

### Container
- backgroundColor: #FFFFFF
- borderRadius: 12px
- padding: 16px 20px
- boxShadow: 0px 2px 8px rgba(0,0,0,0.08)

### 标题 Text
- fontFamily: "PingFang SC"
- fontSize: 18px
- fontWeight: 600
- color: #1A1A1A
- lineHeight: 1.4 (25.2px)
- letterSpacing: 0

### 标签 Chip（×3）
- backgroundColor: #F5F0FF
- borderRadius: 20px
- padding: 4px 12px
- fontSize: 12px
- color: #7C5CFC

### 间距
- 标题 → 标签组：12px gap
- 标签之间：8px gap

## Variant / 交互状态

### 标签 Chip — hover 态（如有）
- backgroundColor: #F5F0FF → #EDE3FF
- transition: 200ms ease

### 标签 Chip — selected 态（如有）
- backgroundColor: #7C5CFC, color: #FFFFFF

## 文本内容（逐字）
- 标题: "立即加入，开启你的专属体验"
- 标签1: "免费试用"
- 标签2: "随时退出"
- 标签3: "专业指导"

## 响应式行为
- **Desktop**: 水平排列，maxWidth 600px 居中
- **Mobile**: 同上（该模块尺寸小，不需换行）

## 资源引用
- 图标: 无（纯文本+背景）
- 图片: 无

## 复用组件（仅策略 C）
- **复用**: `XxxPrimaryButton`（路径: `src/components/buttons/`）
- **覆盖参数**: label=稿面文案, gradient=稿面渐变色
- **无需覆盖**: borderRadius 用主题默认, onPressed 连现有客服跳转
```

**填写要求**：
- 每个字段必须填。不适用则写「N/A」而非跳过
- Variant 部分如果 Figma 组件确有 variant，必须逐个写全
- 文本内容必须从 Figma 逐字复制，不要意译

#### Step 3: 更新 Manifest

在 `layers.manifest.json` 对应层中填写 `spec_file` 路径：

```json
{ "id": "tag_row", "strategy": "B", "spec_file": "docs/research/modules/tag_row.spec.md" }
```

---

### E2: 预分派检查清单（Pre-Dispatch Checklist）

每分派一个 builder agent 之前，必须逐项确认。**有一条不满足就不能分派**：

- [ ] Spec 文件已写入 `docs/research/modules/<name>.spec.md`，所有字段已填
- [ ] 每个 CSS 值来自 Figma `get_design_context`，非目测估算
- [ ] 策略 C 模块的复用组件已在项目中确认存在（grep 验证）
- [ ] 交互状态（variant）已提取（如 Figma 组件有 variant）
- [ ] 截图已保存到 `docs/design-references/` 供 builder 对照
- [ ] Builder prompt 内容控制在合理规模（spec 内容 ≤ ~150 行；超过则表明需拆分模块）
- [ ] 文本内容逐字来自 Figma，非意译
- [ ] 模块间依赖已明确（如 wrapper 需等子组件先完成）

---

### E3: 并行分派 Builder（Dispatch）

#### 分派策略

按 A2b 复杂度判定：

| 复杂度 | 做法 |
|--------|------|
| 简单 | 1 个 agent 构建整个模块 |
| 中等 | 1 个 agent，spec 内联 |
| 复杂 | **拆分**：N 个子组件各 1 个 agent + 1 个 wrapper agent |

**并行原则**：所有独立模块的 builder agent 可以同时分派（使用 git worktree 隔离）。O orchestrator 分派后继续提取下一个模块，不等待 builder 完成。

**依赖排序**：wrapper 必须等其子组件 builder 全部完成后再分派。独立的兄弟模块无此限制。

#### Builder Agent Prompt 模板

每个 builder agent 收到以下内容的 prompt：

```
## 任务：构建 <ModuleName>

## Spec 文件
[在此内联 docs/research/modules/<module-id>.spec.md 的完整内容]

## 设计截图
截图路径：docs/design-references/<module-id>.png
（请参考截图进行视觉对照）

## 共享资源
- 主题/Token 文件：<项目主题文件路径>
- 复用组件：<列表，含文件路径和构造参数>
- 工具函数：<cn() / 项目 utils 路径>

## 目标文件
src/components/<ModuleName>.tsx（或项目对应路径+扩展名）

## 要求
1. **严格按 Spec 中的 Figma 值实现**——不要近似，不要「看起来差不多」
2. **策略 C 优先复用**：如果 Spec 标记了 reuse 组件，import 它而非新建平行实现
3. **偏离必须注释**：因设计系统/无障碍等原因故意偏离 Figma 时，必须加注释：
   // 偏离 Figma: <改了什么>；原因: <为什么>；稿面值: <原值>
4. **完成后验证**：运行项目 typecheck/lint 确保无错误
5. 在独立 worktree 中工作，完成后通知 merge
```

#### Worktree 隔离

```bash
# Orchestrator 为每个 builder agent 创建独立 worktree
git worktree add .claude/worktrees/<module-name> -b build/<module-name>
# Builder agent 在该 worktree 中工作
# 完成后 Orchestrator merge 回主分支
```

---

### E4: Merge + 验证（Merge & Verify）

Builder agent 完成构建后：

1. **Merge worktree**：
   ```bash
   git merge build/<module-name> --no-ff -m "feat: add <ModuleName> component"
   git worktree remove .claude/worktrees/<module-name>
   ```
2. **验证构建**：
   ```bash
   flutter analyze   # 或项目对应的 typecheck/lint 命令
   ```
3. **冲突处理**：O orchestrator 有所有模块的完整上下文，智能解决冲突
4. **不等待全部完成**：Merge 一个 builder 的结果后，立即继续当前提取循环。Builder 间并行工作

**规则**：一次 merge 后构建是坏的 → 立即修复 → 再继续。不要积累多个未验证的 merge。

---

### E5: 页面组装（Page Assembly）

所有模块 builder 完成 + merge 后，在页面入口文件中统一接入：

1. **导入所有 section 组件**
2. **按分析表从上到下排列**，间距使用 manifest 中的 `gap_to_next` 值
3. **策略 A 模块**：直接引用已导入的图片资源（I 阶段完成）
4. **实现页面级行为**：scroll controller、sticky 元素、z-index 层级
5. **CTA / 交互按钮**（参照 E6）
6. **验证**：完整 build 通过

```dart
// 页面组装示例（Flutter，其他框架同理）
Scaffold(
  backgroundColor: /* Figma 页面背景色 */,
  body: Column(children: [
    Expanded(child: Stack(children: [
      SingleChildScrollView(
        controller: _scrollController,
        child: Column(children: [
          // 策略 A: 图片
          _buildImageSection('assets/badge_3x.png', 0),
          SizedBox(height: 12),   // gap_to_next 来自 manifest
          _buildImageSection('assets/hero_banner_3x.png', 12),
          SizedBox(height: 7),
          // 策略 B: Widget（builder agent 产出）
          SubtitleText(),         // 来自 build/subtitle_text worktree
          SizedBox(height: 7),
          DescriptionText(),
          SizedBox(height: 13),
          // 策略 C: 复用组件（builder agent 产出）
          TagRow(),
          // ...
        ]),
      ),
      Positioned(top: 48, left: 16, child: _buildBackButton()),
    ])),
    BottomBar(...),  // 参照 E6
  ]),
);
```

---

### E6: 底部常驻 CTA（滚动自适应阴影）

**适用场景**：活动页底部 CTA 按钮需要始终可见，滑到底部时自然融入。

**默认实现模式**（Flutter 示例，其他框架同理）：

```dart
class _XxxLandingPageState extends State<XxxLandingPage> {
  final ScrollController _scrollController = ScrollController();
  bool _isNearBottom = false;

  @override
  void initState() { super.initState(); _scrollController.addListener(_onScroll); }
  @override
  void dispose() { _scrollController.dispose(); super.dispose(); }

  void _onScroll() {
    if (!_scrollController.hasClients) return;
    final maxScroll = _scrollController.position.maxScrollExtent;
    final currentScroll = _scrollController.position.pixels;
    final nearBottom = maxScroll - currentScroll < 16;
    if (nearBottom != _isNearBottom) setState(() => _isNearBottom = nearBottom);
  }

  Widget _buildBottomBar(BuildContext context) {
    final bottomPadding = MediaQuery.of(context).padding.bottom;
    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      decoration: BoxDecoration(
        color: /* 页面背景色 */,
        boxShadow: _isNearBottom
            ? []
            : [BoxShadow(color: Color(0x1A000000), blurRadius: 8, offset: Offset(0, -2))],
      ),
      padding: EdgeInsets.only(bottom: bottomPadding),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        const SizedBox(height: 16),
        // CTA 按钮...
        const SizedBox(height: 8),
        // 底部提示文字...
        const SizedBox(height: 16),
      ]),
    );
  }
}
```

**状态说明**：
- `_isNearBottom = false` → 阴影可见（常驻态）
- `_isNearBottom = true` → 阴影消失（融入态）
- `AnimatedContainer` 200ms 过渡

---

### E7: 设计标记映射

| Figma 属性 | 代码映射 |
|-----------|---------|
| `color: #967ED6` | `Color(0xFF967ED6)` 或项目 token（策略 C 优先 token） |
| `border-radius: 20px` | `BorderRadius.circular(20)` 或主题 radius |
| `gradient: #START → #END` | `LinearGradient(colors: [Color(0xFFSTART), Color(0xFFEND)])` |
| `padding: 16px` | `EdgeInsets.all(16)` |
| `gap: 12px` | `SizedBox(height: 12)` |
| `line-height / font-size` | `height: <比值>` |

> 字体、具体色值均从 `get_design_context` 返回的 Figma 声明中提取。**策略 C**：稿面值与项目 token 冲突时，优先 token；若必须贴稿，按 E7b 写偏离注释。

### E7b: 偏离文档化（必须）

因设计系统、无障碍、安全区、SDK 限制等**故意偏离 Figma** 时，必须在代码旁注释：

```dart
// 偏离 Figma: <改了什么>；原因: <为什么>；稿面值: <原值>
// 偏离 Figma: fontSize 12→14；原因: 最小可读/触控；稿面值: 12
// 偏离 Figma: 圆角 10→12；原因: 使用主题 radiusMd；稿面值: 10
```

- 注释写在偏离发生的那一行或紧邻上方
- 禁止静默偏离：改了却不写，后续验收会被当成 bug

### E8: CTA / 交互按钮

**复用项目中已有的模式**（策略 C），不要凭空实现：
1. 搜索项目中「联系我们」「客服」「分享」「跳转」等功能的实现
2. 找到对应的 Service/Manager 或页面跳转逻辑
3. 直接引用，保持行为一致

### E9: 构建与部署

- 资源文件新增/替换 → 完整 rebuild
- 仅代码变更 → 热重载即可

---

## V: Verify — 复刻检查

### V0: REST API 导出完整性检查（关键）

**Figma REST API 导出单个节点时，不会包含其子节点的叠加内容。** 如果模块结构是：
- 背景图片节点
- 标题/文字节点（独立定位叠加在上面）

→ REST API 对背景图片节点单独导出 **会丢失所有叠加文字**。

**识别方法**：在 `get_design_context` 返回中，检查目标节点是否有兄弟文字节点在相同坐标区域：
```html
<div style="position:absolute; top:xxx; left:xxx">  <!-- 背景图片 -->
<div style="position:absolute; top:xxx; left:xxx">  <!-- 叠加文字 -->
```

**修复**：
- 优先使用**父级容器节点**导出（包含所有子节点）
- 或使用用户提供的**组合截图**（如图层合并后的 PNG）
- 或将文字拆为 Flutter Widget 叠加在背景图上

### V1: 模块对照

拿出 **A2 分析表** / `layers.manifest.json` / **各模块 spec 文件**，在设备上逐模块对照：位置、尺寸、清晰度、样式是否与设计一致。  
策略 C 模块额外确认：是否真的复用了声明的组件（无平行复制实现）。

### V2: 视觉对比（量化）

重新调用 `get_screenshot(nodeId, fileKey)` 获取原始设计截图，与设备显示对比。

**使用脚本做像素级量化对比**：

```bash
scripts/compare_images.py figma-reference.png device-screenshot.png --json --output-diff qa/diff-heatmap.png
```

输出指标：
- `changed_pixel_ratio`: 变化像素比例（目标 < 0.05）
- `mae`: 平均绝对误差（目标 < 5）
- `rmse`: 均方根误差（目标 < 10）
- `max_rgb_diff`: 最大 RGB 差异（目标 < 30）

`--output-diff` 生成差异热力图，红色区域 = 差异最大，便于定位问题模块。

### V2.5: 模块边界复核

如 V2 发现差异，重新运行模块边界预览，确认差异来自哪个模块：

```bash
scripts/preview_modules.py device-screenshot.png layers.manifest.json qa/device-modules.png
```

逐模块对照 manifest 中的 bbox 和 gap 值，定位错位/遗漏模块。

### V3: 交互检查

- [ ] 返回按钮可点击且有振动/触摸反馈
- [ ] CTA 按钮功能正常
- [ ] 页面可正常滚动，无溢出
- [ ] 无闪烁、无布局跳动

### V4: 高频遗漏项

- [ ] 所有文本用原生 Widget（策略 B）或项目排版组件（策略 C），清晰无模糊
- [ ] 所有图片来自 3x 导出（策略 A），清晰无模糊
- [ ] 策略 C 模块未新建平行 Button/返回等实现
- [ ] 按钮渐变起止色与 Figma 一致（或已按 E7b 注明偏离）
- [ ] Section 间距与分析表 / manifest gap 值对齐
- [ ] 策略 B/C 模块实现与 spec 文件中的 Figma 精确值一致
- [ ] 故意偏离均有 `// 偏离 Figma:` 注释

### V5: 偏离清单复核

扫描本页新增代码中的 `偏离 Figma` 注释：
- [ ] 每条均有：改了什么 / 原因 / 稿面值
- [ ] 无「改了但没注释」的静默偏离
- [ ] 可向用户口头摘要关键偏离（如字号、圆角、安全区）

---

## B: Boundary — 常见陷阱

| # | 陷阱 | 现象 | 修复 |
|---|------|------|------|
| 1 | **Figma API 1x 限制** | 图模糊 | Figma 桌面端 3x 导出，或用户提供高清文件 |
| 2 | **语法兼容** | 新语法编译报错 | 确认项目 SDK/language 版本，回退兼容写法 |
| 3 | **图片黑底** | 图标有黑色背景 | `get_screenshot(contentsOnly: true)` |
| 4 | **键盘透黑**（iOS） | 键盘圆角处黑色 | 设置窗口/根视图背景色为白色 |
| 5 | **调试器超时** | 连不上 | 停掉旧进程后重试 |
| 6 | **模块遗漏** | 某个设计元素未实现 | 严格按 A2 分析表逐项对照 V1 |
| 7 | **图片拉伸变形** | `BoxFit.fill` 改变比例 | 用 `BoxFit.fitWidth` + `ClipRRect` |
| 8 | **Manifest 缺失** | 代码位置与 Figma 设计值不一致 | 所有模块必须先入 `layers.manifest.json` |
| 9 | **1x 资源误用** | 策略 A 模块模糊 | 运行 `audit_assets.py --min-dimension` 检测 |
| 10 | **模块边界不准** | 截图叠图时发现模块裁切/偏移 | 用 `preview_modules.py` 提前校验 bbox |
| 11 | **Context 截断仍硬写** | 模块结构不全、间距乱 | P2：metadata → 分 section 再 get_design_context |
| 12 | **忽略设计系统硬抄稿** | 平行 Button/色值泛滥 | 策略先 C 后 B；token 冲突用 E7b 注释 |

---

## 统一 Manifest 规范

本 skill 使用 BubbleUniverseSkills 统一的 `layers.manifest.json` 格式作为所有模块的唯一数据源。

- **规范位置**：`references/manifest-spec.md`（**完整内容已内嵌本 skill**，单目录拷贝即可独立使用，无外部依赖）
- **核心原则**：`source_bbox` 来自 Figma 提取 → `scaled_bbox` 由 scale 计算 → 代码实现必须追溯到 manifest
- **策略字段**：`strategy` 支持 `A` | `B` | `C`；`C` 建议附 `reuse` 组件标识
- **与 image-to-code skill 共享**：相同的 manifest 格式，不同的 `source.type`（`figma` vs `image`）；需要时双方各自使用随目录内嵌的同一份规范

当用户同时提供 Figma 链接和图片参考时，两个 skill 可以基于同一 manifest 协作：
- `figma-page-replication` 负责从 Figma 提取结构化数据和初始 manifest
- `image-to-code` 负责从图片提取额外资源和补充切图

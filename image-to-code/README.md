# Image To Code

`image-to-code` 是一个图片转代码与切图 skill，目标是把选中的 UI 图片或设计截图按 750px 画板宽度进行像素级还原，并导出独立透明 PNG 切图资源。

适用于 **Claude Code / Codex / Cursor / Copilot / Windsurf / Cline** 等任何 AI Coding Agent。

## 这是什么

一套方法论和工具链，引导 AI Coding Agent 将 UI 截图/设计图自动还原为代码。核心流程 **S→M→E→C→V→D**：

| 阶段 | 说明 |
|------|------|
| **S**ource | 源图分析，确认框架和需求 |
| **M**anifest | 建立图层清单，750px 归一化 |
| **E**xtract | 按 bbox 导出透明 PNG 切图 |
| **C**ode | 按 manifest 坐标实现代码 |
| **V**erify | 截图对比、分模块验收 |
| **D**eliver | 交付代码、资源和报告 |

## 适用场景

- 将移动端 UI 截图还原为 Flutter / React Native / Web 代码
- 将设计图按 750px 宽度等比还原
- 从源图中提取头像、图标、插画、装饰图、导航图标等透明 PNG 资源
- 保留文本为可编辑文本层
- 将简单矩形、圆角卡片、按钮、分割线等转为原生 CSS/矢量形状
- 对切图位置、尺寸、透明背景和整页还原效果做验收

## 核心原则

- 原图是唯一视觉源，不允许凭感觉重绘或重新设计
- 画板宽度必须精确为 `750px`
- 所有元素按同一比例缩放
- 禁止自动排版、优化间距、重排布局
- 禁止用相似图标库、相似插画、AI 生成图或占位素材替代原图资源
- 切图必须来自当前源图对应区域
- 切图必须是透明背景 PNG
- 切图区域必须先通过 bbox 预览确认
- 不允许自动 trim、智能裁边、内容自适应缩边
- 交付前必须进行 bbox、PNG 透明度、贴边和整页叠图校验

## 前置条件

```bash
pip install Pillow numpy
```

## 安装 & 加载方式

### Claude Code

本 skill 是**自包含目录**（`references/`、`scripts/` 均随目录内嵌），安装只需把整个目录拷贝到 skills 目录：

```bash
# 1) 拉取 BubbleUniverseSkills 仓库（整仓包含多个 skill，本 skill 只是其中之一）
git clone --depth 1 https://github.com/jxqlovejava/BubbleUniverseSkills.git ~/BubbleUniverseSkills

# 2) 拷贝本 skill 目录（含 SKILL.md / README.md / references / scripts）
cp -R ~/BubbleUniverseSkills/image-to-code ~/.claude/skills/
```

使用：在对话中说「用 image-to-code 还原这张截图」或「按 750px 还原这张 UI 图」。

### Codex / OpenAI Codex CLI

将 `SKILL.md` 内容作为**自定义指令（Custom Instructions）**加载，或在对话开头粘贴核心流程。

也可以将 SKILL.md 作为项目根目录的 `CODEX.md` 或 `AGENTS.md` 的一部分。

### Cursor

**方式 A**：将 SKILL.md 放入项目 `.cursor/rules/` 目录作为 rule 文件。

**方式 B**：在 Cursor Settings → Rules 中添加自定义规则，粘贴 SKILL.md 内容。

### Copilot / Copilot Chat

将 SKILL.md 作为 `.github/copilot-instructions.md` 或项目自定义指令使用。

### Windsurf

将 SKILL.md 内容作为 **Cascade 自定义规则** 或在 `.windsurfrules` 中添加。

### 通用方式（任意平台）

直接在当前对话中引用 SKILL.md：

```
请严格按照 ~/.claude/skills/image-to-code/SKILL.md 中的
S→M→E→C→V→D 流程，将这张 UI 截图还原为代码。
```

## 目录结构

```text
image-to-code/
├── SKILL.md
├── README.md
├── references/
│   ├── manifest-spec.md
│   └── slicing.md
└── scripts/
    ├── preview_bboxes.py
    ├── extract_png_asset.py
    ├── audit_png_assets.py
    └── compare_images.py
```

## 脚本说明

### 1. 预览 bbox

在源图上画出 manifest 中记录的 bbox，用于检查切图区域是否准确。

```bash
scripts/preview_bboxes.py source.png layers.manifest.json qa/bbox-preview.png --only-type bitmap
```

### 2. 按 bbox 导出 PNG

从源图按精确 bbox 导出 PNG。脚本不会自动 trim，输出画布固定等于 bbox。

```bash
scripts/extract_png_asset.py source.png assets/icons/icon-user.png \
  --x 120 --y 980 --width 72 --height 72 \
  --remove-bg floodfill \
  --manifest layers.manifest.json \
  --id icon-user
```

### 3. 审计 PNG 切图

检查 PNG 是否贴边、尺寸是否匹配，以及透明背景是否合格。

```bash
scripts/audit_png_assets.py assets/icons assets/images \
  --require-transparent-bg \
  --manifest layers.manifest.json
```

### 4. 图片差异对比

对比 750px 原图和最终渲染截图。

```bash
scripts/compare_images.py reference-750.png render-750.png --json
```

## 验收标准

- 最终画板宽度为 `750px`
- 页面布局和原图同位置、同尺寸、同层级
- 文本为可编辑文本，不 rasterize 到整页图中
- 简单图形用 CSS/原生矢量实现
- 头像、图标、插画、装饰图等从当前源图提取
- PNG 切图有 alpha 通道，背景透明
- PNG 不贴边、不缺失、不带白色或灰色矩形背景
- bbox 预览图中框选区域准确
- 最终页面截图和 750px 原图叠图无明显偏移、缺图、裁切或替代素材

## 平台兼容性

| 平台 | 加载方式 | 自动触发 | 依赖 |
|------|---------|---------|------|
| Claude Code | Skill 目录 | 关键词自动激活 | Pillow, numpy |
| Codex | Custom Instructions | 需手动引用 | Pillow, numpy |
| Cursor | Rules / .cursorrules | glob 匹配触发 | Pillow, numpy |
| Copilot | copilot-instructions.md | 项目级自动 | Pillow, numpy |
| Windsurf | .windsurfrules / Cascade Rules | 项目级自动 | Pillow, numpy |
| Cline | .clinerules | 项目级自动 | Pillow, numpy |

## 适配的框架

| 框架 | 支持度 |
|------|--------|
| Flutter | 完整支持 |
| React / React Native | 完整支持 |
| Web (HTML/CSS/JS) | 完整支持 |
| Vue / Svelte | 完整支持 |
| Compose / SwiftUI | 支持（需告知目标框架） |

## 统一 Manifest 规范

本 skill 使用 BubbleUniverseSkills 统一的 `layers.manifest.json` 格式。规范完整内容已内嵌于本 skill，详见 [references/manifest-spec.md](references/manifest-spec.md)。

## License

MIT

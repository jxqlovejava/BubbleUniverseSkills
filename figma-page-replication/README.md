# Figma Page Replication

Figma 设计稿 → 应用页面完整复刻工作流。适用于 **Claude Code / Codex / Cursor / Copilot / Windsurf / Cline** 等任何 AI Coding Agent。

## 这是什么

一套方法论和提示词模板，引导 AI Coding Agent 将 Figma 设计稿自动复刻为应用页面。核心流程 **P→A→I→E→V→B**：

| 阶段 | 说明 |
|------|------|
| **P**reparation | 从 Figma 链接提取设计上下文；过大时 metadata 分层拉取 |
| **A**nalyze | 逐模块分析，三轨策略（A 整图 / B 原生 / C 复用组件）+ manifest |
| **I**dentify | 收集策略 A 模块所需的高清资源 |
| **E**xecute | 按分析表逐模块构建；优先复用项目组件；偏离须注释 |
| **V**erify | 模块对照、视觉对比、交互检查、偏离清单复核 |
| **B**oundary | 常见陷阱自动规避（含截断硬写、忽略设计系统） |

### 三轨策略（A / B / C）

| 策略 | 何时用 |
|------|--------|
| **A** 整图导出 3x | 合成图、复杂装饰、照片级纹理 |
| **B** 原生 Widget | 纯文、简单控件，且项目无对等组件 |
| **C** 复用项目组件 | 与现有 Button/返回/Tag 等**同构**（判定优先于 B） |

另有 **Skill 边界** 与 **轻量路径**（单组件/≤2 模块）见 `SKILL.md` 文首。

## 前置条件

### 校验脚本依赖（所有平台通用）

`scripts/` 下的校验脚本需要 Python 图像库：

```bash
pip install Pillow numpy
```

### Figma MCP 配置（所有平台通用）

工作流依赖 Figma MCP 工具获取设计数据。在任何 Agent 中使用前，需要先配置 Figma MCP 服务器。

**Step 1**：获取 Figma Personal Access Token
1. 登录 [Figma](https://www.figma.com)
2. 头像 → Settings → Personal Access Tokens
3. 生成一个新 token，复制保存

**Step 2**：配置 MCP 服务器

根据你的 Agent 平台配置 MCP：

| 平台 | 配置文件 | 示例 |
|------|---------|------|
| **Claude Code** | `~/.claude/.mcp.json` 或项目 `.mcp.json` | 见下方 |
| **Codex** | Settings → MCP Servers | 添加 Figma 服务器 |
| **Cursor** | `~/.cursor/mcp.json` | 同 Claude Code 格式 |
| **Windsurf** | Settings → MCP | Web UI 中添加 |
| **其他 MCP 兼容** | 各平台 MCP 配置文件 | JSON 格式通用 |

通用 MCP 配置 JSON：

```json
{
  "mcpServers": {
    "figma": {
      "command": "npx",
      "args": [
        "-y",
        "@anthropic-ai/mcp-figma",
        "--figma-token",
        "<你的Figma-Token>"
      ]
    }
  }
}
```

## 安装 & 加载方式

根据你使用的 Agent 平台选择对应的加载方式：

### Claude Code

本 skill 是**自包含目录**（`references/`、`scripts/` 均随目录内嵌），安装只需把整个目录拷贝到 skills 目录：

```bash
# 1) 拉取 BubbleUniverseSkills 仓库（整仓包含多个 skill，本 skill 只是其中之一）
git clone --depth 1 https://github.com/jxqlovejava/BubbleUniverseSkills.git ~/BubbleUniverseSkills

# 2) 拷贝本 skill 目录（含 SKILL.md / README.md / references / scripts）
cp -R ~/BubbleUniverseSkills/figma-page-replication ~/.claude/skills/
```

自动激活。也可以手动调用：在对话中输入 `figma-page-replication` 或直接说「复刻 Figma 页面」。

### Codex / OpenAI Codex CLI

将 `SKILL.md` 内容作为**自定义指令（Custom Instructions）**加载，或在对话开头粘贴核心流程：

```
请按照以下工作流将 Figma 设计稿复刻为页面：
[粘贴 SKILL.md 中 P→A→I→E→V→B 章节内容]
```

也可以将 SKILL.md 作为项目根目录的 `CODEX.md` 或 `AGENTS.md` 的一部分。

### Cursor

**方式 A**：将 SKILL.md 放入项目 `.cursor/rules/` 目录作为 rule 文件。

**方式 B**：在 Cursor Settings → Rules 中添加自定义规则，粘贴 SKILL.md 内容。推荐添加触发条件：`globs: **/*` 或 Figma 相关关键词。

### Copilot / Copilot Chat

将 SKILL.md 作为 `.github/copilot-instructions.md` 或项目自定义指令使用。

### Windsurf

将 SKILL.md 内容作为 **Cascade 自定义规则** 或在 `.windsurfrules` 中添加。

### 通用方式（任意平台）

直接在当前对话中引用 SKILL.md：

```
请严格按照 ~/.claude/skills/figma-page-replication/SKILL.md 中的
P→A→I→E→V→B 流程，复刻这个 Figma 页面：
https://www.figma.com/design/XXXX/YYY?node-id=1-2
```

或者将 SKILL.md 打印出来作为 System Prompt 的一部分。

## 使用方式

在任何 Agent 对话中，提供 Figma 设计稿链接并说：

```
帮我复刻这个 Figma 页面：
https://www.figma.com/design/XXXX/YYY?node-id=1-2
```

Agent 将按 P→A→I→E→V→B 流程引导你完成复刻。

### 你需要做什么

1. **确认模块分析表**：Agent 会展示设计稿的模块拆解和策略分配，你核对确认
2. **导出 3x 图片**：策略 A 的模块需要你从 Figma 桌面端手动导出 3x PNG（右键 → Export → 3x），放到项目 assets 目录
3. **验证效果**：构建后在真机上对照设计稿验证

### Agent 自动处理什么

- 分析设计稿结构，判定每个模块用图片还是代码实现
- 提取颜色、字号、间距等设计标记并映射为代码
- 生成完整的页面框架代码（含底部 CTA 常驻、滚动自适应阴影等模式）
- 7 类常见陷阱（1x 模糊、图片拉伸、模块遗漏等）的自动识别和规避

## 平台兼容性

| 平台 | 加载方式 | 自动触发 | MCP 支持 |
|------|---------|---------|----------|
| Claude Code | Skill 目录 | 关键词自动激活 | 原生 |
| Codex | Custom Instructions | 需手动引用 | 支持 |
| Cursor | Rules / .cursorrules | glob 匹配触发 | 支持 |
| Copilot | copilot-instructions.md | 项目级自动 | 有限 |
| Windsurf | .windsurfrules / Cascade Rules | 项目级自动 | 支持 |
| Cline | .clinerules | 项目级自动 | 支持 |
| 其他 MCP Agent | System Prompt | 需手动引用 | 支持 |

## 适配的页面类型

| 类型 | 是否支持 |
|------|---------|
| 活动落地页 / Landing Page | 完整支持 |
| 招募页 / 推广页 | 完整支持 |
| 功能引导页 | 支持 |
| 复杂列表/表格页 | 部分支持（需人工介入） |
| 数据仪表盘 | 不适用 |

## 文件结构

```
figma-page-replication/          # 自包含：整个目录可单独拷贝/克隆使用
├── README.md                    # 本文件（安装指南 + 平台适配 + FAQ）
├── SKILL.md                     # 工作流定义（P→A→I→E→V→B 核心流程 + 代码模板）
├── references/
│   └── manifest-spec.md         # layers.manifest.json 统一规范（完整内容内嵌）
└── scripts/
    ├── compare_images.py        # 像素级图片对比（V2）
    ├── preview_modules.py       # 模块边界预览（A5 / V2.5）
    └── audit_assets.py          # 资源审计（I 阶段）
```

## 常见问题

**Q: 我的 Agent 没有 MCP 支持怎么办？**
A: 可以手动提供 Figma 设计数据——从 Figma Dev Mode 复制 CSS/属性信息，粘贴到对话中，Agent 仍可按照 P→A→I→E→V→B 流程工作。MCP 只是自动化获取设计规格，不是必须的。

**Q: Figma API 导出的图很模糊？**
A: Figma API 的 `get_screenshot` 只能输出 1x 分辨率。策略 A 模块必须从 Figma 桌面端手动导出 3x。

**Q: 支持哪些框架？**
A: SKILL.md 中的代码示例以 Flutter 为主，但 P→A→I→V→B 流程框架无关，React Native / Compose / SwiftUI 等都可以套用相同方法论。只需告诉 Agent 你的目标框架即可。

**Q: Token 安全吗？**
A: Figma Token 存放在你的本地 MCP 配置中，不会被提交或分享。工作流文件不包含任何密钥。

## License

MIT

# 气泡宇宙 BubbleUniverse Skills

气泡宇宙团队公共 AI Coding Agent Skill 库。收录团队在实战项目中提炼的方法论与提示词模板，适用于 **Claude Code / Codex / Cursor / Copilot / Windsurf / Cline** 等任何 AI Coding Agent。

---

## 📦 Skill 列表

| Skill | 简介 | 适用场景 |
|-------|------|---------|
| [figma-page-replication](./figma-page-replication/README.md) | Figma 设计稿 → 应用页面完整复刻工作流 | 活动页、落地页、招募页等任意 Figma → Code 场景 |

---

## 🚀 快速开始

每个 Skill 目录下都有：

- **`README.md`** — 安装指南、平台适配说明、FAQ
- **`SKILL.md`** — 核心工作流定义，可直接作为 System Prompt / Custom Instructions 使用

选择你使用的 Agent 平台，参照对应 Skill 的 `README.md` 完成配置即可。

---

## 🗂 目录结构

```
BubbleUniverseSkills/
├── README.md                        # 本文件
└── figma-page-replication/
    ├── README.md                    # 安装指南 + 平台适配 + FAQ
    └── SKILL.md                     # P→A→I→E→V→B 核心流程 + 代码模板
```

---

## 🤝 贡献指南

欢迎团队成员提交新 Skill：

1. 在根目录新建以 Skill 名称命名的文件夹（使用 kebab-case，如 `my-new-skill`）
2. 在文件夹内添加 `SKILL.md`（核心工作流）和 `README.md`（使用说明）
3. 更新本文件的 Skill 列表
4. 提交 PR，描述该 Skill 解决的问题和适用场景

---

## License

MIT

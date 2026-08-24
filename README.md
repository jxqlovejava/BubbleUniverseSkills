# 气泡宇宙 BubbleUniverse Skills

气泡宇宙团队公共 AI Coding Agent Skill 库。收录团队在实战项目中提炼的方法论与提示词模板，适用于 **Claude Code / Codex / Cursor / Copilot / Windsurf / Cline** 等任何 AI Coding Agent。

---

## 📦 Skill 列表

| Skill | 简介 | 适用场景 |
|-------|------|---------|
| [gcp](./gcp/SKILL.md) | Git Commit & Push 智能分组提交 + 自动同步推送 | 多文件变更自动分组 commit、工作区干净时自动 pull/push 同步 |
| [figma-page-replication](./figma-page-replication/README.md) | Figma 设计稿 → 应用页面完整复刻工作流 | 活动页、落地页、招募页等任意 Figma → Code 场景 |
| [image-to-code](./image-to-code/README.md) | UI 截图/设计图 → 代码 + 透明 PNG 切图资源 | 移动端截图还原、750px 像素级复刻、图标/插画提取 |
| [tarot-mass-divination](./tarot-mass-divination/SKILL.md) | 大众占卜小红书长图文一键管线：选题 -> LLM 荐阵 -> 78 张无放回抽牌 -> DeepSeek 逐选项解读 -> 情绪画像封面 -> Playwright 渲染 | 大众占卜三选一/四选一长图文批量生产、短图文配图 |
| [topic-discovery](./topic-discovery/SKILL.md) | 跨平台选题采集 -> Excel 选题库（12 列，链接+标题去重，未用/已用状态标记）-> LLM 推荐未用选题 | 小红书/抖音/B站/X/YouTube/公众号等选题沉淀与复用 |

---

## 🚀 快速开始

每个 Skill 目录下都有：

- **`README.md`** — 安装指南、平台适配说明、FAQ
- **`SKILL.md`** — 核心工作流定义，可直接作为 System Prompt / Custom Instructions 使用

选择你使用的 Agent 平台，参照对应 Skill 的 `README.md` 完成配置即可。

---

## 🔗 统一规范

### `layers.manifest.json` — 跨 Skill 的单一数据源

所有 design-to-code Skill 共用统一的 manifest 格式：

- **位置**：`references/manifest-spec.md`
- **作用**：连接分析 → 资源导出 → 代码实现 → 验收验证 的全流程数据契约
- **兼容**：`figma-page-replication`（`source.type = "figma"`）和 `image-to-code`（`source.type = "image"`）

## 🗂 目录结构

```
BubbleUniverseSkills/
├── README.md                        # 本文件
├── references/
│   └── manifest-spec.md             # 统一 manifest 规范
├── gcp/
│   └── SKILL.md                     # Git Commit & Push 智能分组工作流
├── figma-page-replication/
│   ├── README.md                    # 安装指南 + 平台适配 + FAQ
│   ├── SKILL.md                     # P→A→I→E→V→B 核心流程 + 代码模板
│   ├── references/
│   │   └── manifest-spec.md         # 引用统一规范
│   └── scripts/
│       ├── compare_images.py        # 像素级图片对比
│       ├── preview_modules.py       # 模块边界预览
│       └── audit_assets.py          # 资源审计
├── image-to-code/
    ├── README.md                    # 安装指南 + 平台适配 + FAQ
    ├── SKILL.md                     # S→M→E→C→V→D 核心流程
    ├── references/
    │   ├── manifest-spec.md         # 引用统一规范
    │   └── slicing.md               # 切图与导出规范
    └── scripts/
        ├── preview_bboxes.py        # bbox 预览
        ├── extract_png_asset.py     # 精确 bbox 导出 PNG
        ├── audit_png_assets.py      # PNG 审计
        └── compare_images.py        # 像素级图片对比
├── tarot-mass-divination/
│   ├── SKILL.md                     # 大众占卜长图文一键管线工作流
│   ├── data/                        # 牌阵/78 张韦特牌面/字体/LLM 提示词/情绪色彩库
│   └── scripts/                     # pipeline 端到端 + 生成/渲染/封面校验脚本
└── topic-discovery/
    ├── SKILL.md                     # 跨平台选题采集入库工作流
    └── scripts/
        └── topic_library.py         # Excel 选题库管理（去重/状态标记/推荐）
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

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
| [jimeng-image](./jimeng-image/SKILL.md) | 即梦(jimeng.jianying.com) AI 生图：复用 ego-lite 浏览器登录态，Agent 模式 + 精确控制双脚本，配套大师心法预设库与 30 条示例 | 塔罗封面、自然感人像、情侣实拍、情绪插画等一切生图场景 |
| [wechat-tarot-dual](./wechat-tarot-dual/SKILL.md) | 微信聊天 × 塔罗气泡解读 双拼抖音图文：左半聊天截图（剧本/头像/背景可换）+ 右半 App 解读截图（真实 interpret.md 管线） | 抖音塔罗双拼图文、聊天记录+占卜截图类爆款 |
| [tarot-reading-shot](./tarot-reading-shot/README.md) | 抖音单屏塔罗解读截图：整屏 App 解读界面 + 正文红色关键词划线 + 牌卡区紫色情绪贴纸 | 抖音单屏截图直出图文帖 |
| [natural-photo-product-shot](./natural-photo-product-shot/README.md) | 自然感实拍照片垫底 + 左约 43% 半透明白底「App 解读卡」浮层（照片为主角，解读卡为产品截图） | 抖音「实拍照片 + 产品界面」图文爆款 |
| [couple-tarot-four-grid](./couple-tarot-four-grid/README.md) | 情侣四宫格：上排 2 格产品界面截图（HTML 原色渲染）+ 下排 2 格不露脸情侣场景照片 | 小红书四宫格图文、情感赛道 |
| [douyin-screen-record-sticker](./douyin-screen-record-sticker/README.md) | 抖音录屏贴纸视频：左上角手写便利贴 + 产品洗牌→抽牌→解牌全流程自动走查录屏，输出 9:16 成片 | 抖音视频成片批量生产 |

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

- **权威位置**：仓库根 `references/manifest-spec.md`（修改规范时只改这里）
- **内嵌分发**：`figma-page-replication/references/manifest-spec.md` 与 `image-to-code/references/manifest-spec.md` 各内嵌一份**完整副本**，保证任一 skill 单独拷贝即可自包含使用。修改根目录权威文件后，需同步两份内嵌副本。
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
│   │   └── manifest-spec.md         # 统一规范（完整内容内嵌，单目录自包含）
│   └── scripts/
│       ├── compare_images.py        # 像素级图片对比
│       ├── preview_modules.py       # 模块边界预览
│       └── audit_assets.py          # 资源审计
├── image-to-code/
    ├── README.md                    # 安装指南 + 平台适配 + FAQ
    ├── SKILL.md                     # S→M→E→C→V→D 核心流程
    ├── references/
    │   ├── manifest-spec.md         # 统一规范（完整内容内嵌，单目录自包含）
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
├── topic-discovery/
│   ├── SKILL.md                     # 跨平台选题采集入库工作流
│   └── scripts/
│       └── topic_library.py         # Excel 选题库管理（去重/状态标记/推荐）
├── jimeng-image/
│   ├── SKILL.md                     # 即梦 AI 生图工作流
│   ├── README.md                    # 安装指南 + 平台适配 + FAQ
│   ├── prompt-presets.md            # 提示词大师心法 + 风格预设库
│   ├── prompt-examples.md           # 30 条示例 + 共性规律 + 技法笔记
│   └── scripts/                     # Agent 模式 / 精确控制 / 参考图识图
├── wechat-tarot-dual/
│   ├── SKILL.md                     # 微信聊天 × 塔罗解读 双拼图文工作流
│   ├── README.md                    # 安装指南 + 平台适配 + FAQ
│   ├── assets/                      # 牌面/头像池/角色/表情贴纸/聊天背景
│   └── scripts/
├── tarot-reading-shot/
│   ├── SKILL.md                     # 单屏解读截图核心工作流
│   ├── README.md                    # 安装指南 + 版面规范 + 踩坑记录
│   ├── assets/                      # 牌面/App 图标/Luna 头像
│   └── gen_reading.py, render_reading_shot.py
├── natural-photo-product-shot/
│   ├── SKILL.md                     # 实拍照片 + 解读卡浮层核心工作流
│   ├── README.md                    # 安装指南 + 版面规范 + 踩坑记录
│   ├── assets/                      # 牌面/照片底图/App 图标
│   └── gen_photo.py, render_photo_share.py
├── couple-tarot-four-grid/
│   ├── SKILL.md                     # 情侣四宫格核心工作流
│   ├── README.md                    # 安装指南 + 版面规范 + 踩坑记录
│   ├── assets/                      # 牌面/App 界面截图/卡背
│   └── gen_four_grid.py, render_four_grid.py
└── douyin-screen-record-sticker/
    ├── SKILL.md                     # 录屏贴纸视频核心工作流
    ├── README.md                    # 安装指南 + 故障表 + 踩坑记录
    ├── scripts/                     # OCR 校验 / 权限检查 / 指针控制
    └── auto_record.py, gen_video.py, gen_cover.py
```

---

## 🎨 素材策略（哪些入库、哪些不入库）

模板类 skill 需要素材才能跑通，但**生成出来的产物不入库**。入库判定只看一条：*重新跑一遍能不能再产出*。

**入库**（skill 运行必需的输入资源）

- 78 张韦特牌面 `assets/cards/`、牌阵与牌义 JSON、字体 `data/fonts/`
- 头像池 / 角色 / 表情贴纸 / 聊天背景、App 界面截图、App 图标与 Luna 头像
- 提示词库、`content.json` 示例、各 skill 的 `SKILL.md` / `README.md` / 脚本

**不入库**（`.gitignore` 已固化，重跑即可复现）

| 排除项 | 说明 | 复现方式 |
|--------|------|---------|
| `**/out/` | 渲染产物：成片 PNG / MP4、预览 HTML、发布文案 | 重跑各 skill 的 `gen_*.py` |
| `**/assets/raw/`、`**/assets/photos_{a,b}/` | AI 生图原稿 | 重跑 `jimeng-image` 按提示词出图 |
| `微信聊天塔罗素材/` | 按选题产出的成品素材包（含发布文案） | 重跑 `wechat-tarot-dual` |
| `topic-discovery/data/选题库.xlsx` | 个人选题库数据 | 本地自行积累 |
| `**/__pycache__/`、`*.pyc`、`.DS_Store` | 缓存与系统文件 | — |

> 需补素材时，把本地工作区的对应目录按同名路径拷回本仓库即可；`rsync` 同步脚本用的是同一套排除规则。

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

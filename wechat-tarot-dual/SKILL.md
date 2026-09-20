---
name: wechat-tarot-dual
description: 微信聊天×塔罗气泡解读 双拼抖音图文帖素材模板。用户给主题（如「暧昧期想确认TA心意」「异地恋吵架后」），自动生成：微信聊天截图（剧本/头像/背景可换）+ 塔罗气泡App解读截图（真实 interpret.md 管线出解读）+ 抖音正文文案。当用户要求「微信聊天塔罗双拼」「聊天记录+占卜截图」「抖音塔罗双拼图文」时使用。
---

# wechat-tarot-dual：微信聊天×塔罗气泡 双拼抖音帖

一张图 = 左半微信聊天截图 + 右半塔罗气泡App解读截图（1560×1688，双 390×844 屏 @DPR2）。
爆款公式：**女生在聊天里反复确认的事，正是占卜里问出口的事**，两边互相印证。

## 依赖（拿到手先核对）

| 依赖 | 必须？ | 说明 |
|---|---|---|
| tarot-mass-divination skill（同工作区） | ✅ | LLM 管线 / interpret.md / 牌阵数据，gen_content.py 自动在两种布局里找它 |
| 环境变量 `LLM_API_KEY`（或 `DEEPSEEK_API_KEY`） | ✅ | DeepSeek 调用 |
| Playwright chromium | ✅ | 渲染（`python3 -m playwright install chromium`） |
| jimeng-image skill（同工作区） | 背景生成需要 | 依赖 ego-lite 浏览器已登录即梦；**缺失时自动回退默认石阶背景，管线不中断** |
| macOS Vision OCR | 否 | 渲染后自动校验文字（tarot-mass-divination/scripts/ocr_text.sh） |

双布局兼容：ip-pipeline 在 `.claude/skills/` 下；vira 独立工作区直接在根目录（无 `.claude/skills/` 前缀），脚本自动识别。

## 用法

```bash
# 一条命令出全套（需 LLM_API_KEY / DEEPSEEK_API_KEY）
python3 .claude/skills/wechat-tarot-dual/scripts/gen_content.py "主题"

# 选项
python3 .claude/skills/wechat-tarot-dual/scripts/gen_content.py "异地恋吵架后" --seed 7        # 抽牌可复现
python3 .claude/skills/wechat-tarot-dual/scripts/gen_content.py "主题" --skip-bg               # 不生背景，用默认石阶图
python3 .claude/skills/wechat-tarot-dual/scripts/gen_content.py "主题" --out 我的目录           # 自定义输出
python3 .claude/skills/wechat-tarot-dual/scripts/gen_content.py "主题" --skip-render            # 只生成内容

# 改了 content.json 后单独重渲染
python3 .claude/skills/wechat-tarot-dual/scripts/render_wechat_tarot.py <实例目录>/.src/content.json
```

默认输出到 `微信聊天塔罗素材/<月.日>-<主题>/`：**顶层只有成品** `微信聊天塔罗_双拼.png` + `发布文案.txt`；中间产物（content.json、生成的背景图、备选 raw）收在隐藏目录 `.src/`，重渲染/换素材都操作那里。

## 生成管线（gen_content.py）

1. **池子选型**：昵称从 `assets/nicknames.txt` 随机选本体（拼 A+本体+宝宝+MMDD），头像对从 `assets/avatars/pair_XX_{me,ta}.png` 随机选，`--seed` 可复现
2. **聊天剧本**：DeepSeek + `prompts/chat_script.md`（昵称注入提示词，LLM 照抄且称呼一致）→ 聊天消息/占卜问题/正文金句/话题标签/背景图提示词（JSON，带校验+重试）
3. **聊天背景**：即梦按 bg_prompt 生 9:16 背景图（2 张取 1）→ 实例 `.src/assets/chat_bg.png`；失败/缺提示词/`--skip-bg` 时回退 skill 默认石阶图。**每次生图都要目检生活常识**，备选图在实例 `.src/assets/raw/` 可同名覆盖
4. **抽牌**：时间流牌阵 3 张（过去/现在/未来），复用 tarot-mass-divination 的 `draw_groups`
5. **真实解读**：DeepSeek + tarot-mass-divination 的 `interpret.md` 提示词 → --- 分块长解读（综合解读2段+单牌+行动指引+心灵启示）
6. **渲染+校验**：Playwright HTML→PNG，Vision OCR 自动跑

## 内容铁律（用户纠正沉淀，违反=返工）

1. **解读禁止手写** — 必须走 interpret.md 真实管线（gen_content.py 内置）；**截图不求完整**，长解读在底部追问框后自然截断即真实
2. **占卜问题与聊天记录强关联** — 问题是聊天核心纠结的占卜化表达（chat_script.md 已锁此结构）
3. **对话零引号** — 「」""'' 一律禁止（生成端校验拦截）；每条消息 ≤14 字；节奏 = 女问（emo开场→核心问题→大哭贴纸→追问）→ 男笃定回应（2-3条+开心贴纸）
4. **微信昵称/头像走池子** — 昵称本体从 `assets/nicknames.txt` 随机选（拼 A+本体+宝宝+MMDD），LLM 只许照抄、聊天称呼必须与昵称本体一致；头像对从 `assets/avatars/` 随机选。**禁用参考图原名**（恒恒0312）入池
5. **即梦生背景/头像必须检查生活常识**（路灯不能在台阶中间——位置写进提示词+负向块）；背景图每次按主题自动生成，**成品图发出前目检**，翻车换 assets/raw/ 备选同名覆盖；生图提示词先翻 jimeng-image 的 prompt-presets.md 和 prompt-examples.md
6. **发布文案 = 标题金句行 → 品牌软植入句 → 话题标签**（用户 2026-09-16 拍板）。软植入句由 `tarot-mass-divination/scripts/opener.py` 按主题 AI 生成（失败回退固定池），标题行后单独一行，不用手写、别写进 chat_script.md 的字段里；品牌名「塔罗气泡」是禁词（塔罗/占卜/算命）的唯一豁免

## 换素材（头像/背景/贴纸）

- 默认素材在 `assets/`：sticker_cry.png（大哭猫）、sticker_happy.png（开心狗）、chat_bg.png（深夜石阶，**仅兜底**——gen_content 每次按主题即梦新生成到实例目录）、cards/（84 张 rider_waite）、luna_avatar.png
- **头像池** `assets/avatars/pair_XX_{me,ta}.png`（pair_00=奶油猫×棕狗，另有橘猫×柴犬/灰兔×棕熊/仓鼠×柯基各 3 对）；扩池：即梦按「软萌[颜色][动物]的大头头像，正面居中构图，圆脸大眼睛，粉色腮红，纯色奶油白背景，治愈系插画风。不要文字，不要水印」出图 → 中心裁方 512 → 命名 pair_NN_me/ta.png 入池（新动物组合先目检）
- **昵称池** `assets/nicknames.txt`（一行一个本体，叠字/双字，禁止恒恒）；加昵称直接追加行
- **单实例覆盖**：在实例 `.src/assets/` 放 `xxx.png` 同名文件即可（渲染时实例 .src 优先，skill `assets/` 兜底）
- **全量换默认**：即梦出新图到 `assets/raw/` → 改 `scripts/prep_assets.py` 的 `PICKS` → 重跑（头像裁方、贴纸白底抠透明用 `key_white()`，边缘 BFS 保内容）
- 牌面不用管：content.json 的 `cards[].img` 自动指到 `assets/cards/`，`reversed:true` 渲染时旋转 180°

## 版面规范（复刻来源）

- 微信侧：绿气泡 #95EC69、白气泡、头像 40px 圆角 6px、浅灰导航+灰色未读徽标、底部输入栏 #F7F7F7
- 塔罗气泡侧（取自 TarotBubble Flutter 源码 tarot_chat_history_screen.dart）：爱情题渐变底 #FAF3FF→#FFF；**品牌铭牌在状态栏内居中**（参考 Quin/解读截图单屏模板 .brand：白底圆角 10 框住 app_icon 18px + 塔罗气泡 15px，位于时间/信号图标一行、无限畅享占卜 chip 上方，**勿放进 appbar 与 chip 同行**）；白色半透问题卡（底圆角 20，问题 20px 居中）；牌 74×130 圆角 5 + 牌名 13px + 位置 11px；Luna 头像 35px + 名 17px；解读卡白 70%、紫边框 rgba(91,77,188,.15)、圆角 16、15px/1.7；底部追问框白 78% 圆角 25

## 参考实例

`微信聊天塔罗模板/`（首个实例，主题=想确认TA是不是想和自己一直走下去）。

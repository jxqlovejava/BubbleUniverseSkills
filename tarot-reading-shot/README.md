# 塔罗解读截图 + 关键词划线 + 贴纸 · 抖音单屏图文模板

复刻抖音爆款结构（参考 quin 单屏帖）：**一整屏塔罗气泡App解读界面 + 解读正文红色关键词划线 + 牌卡区紫色情绪贴纸**。
与「微信聊天塔罗双拼」的区别：那是左右双屏讲故事，这是单屏截图直出，贴纸和划线是唯二的二创元素。

## 快速复用

```bash
# 1. content.json 手写：question / sticker / underlines / caption（cards、interpretation、opener 不用写）
# 2. 一条命令：抽牌（我-对方-我们牌阵）→ interpret.md 真实解读 → 回填 JSON → 渲染 → OCR
python3 gen_reading.py                 # 读 content.json
python3 gen_reading.py 别的.json --seed 7   # 换内容 / 抽牌可复现

# 改了 sticker/underlines/caption 后单独重渲染（不重新抽牌解读）
python3 render_reading_shot.py [content.json]
```

输出：`out/塔罗解读截图.png`（1170×2532，390×844 @ DPR3，真机截图分辨率）+ `out/发布文案.txt`。

## 依赖（拿到就能跑清单）

- **macOS**（正文用苹方 PingFang SC 系统字体；OCR 校验走 Vision 框架）
- `python3` + Playwright：`pip3 install playwright && python3 -m playwright install chromium`
- **仅渲染**（render_reading_shot.py）：除 Playwright 外无依赖，assets 全在模板目录内；只有组装发布文案时会去读 `opener.py`（读不到就原样输出 caption，不影响出图）
- **gen_reading.py**（抽牌+真实解读）：需要环境变量 `LLM_API_KEY`（或 `DEEPSEEK_API_KEY`，可选 `LLM_API_BASE`/`LLM_MODEL`），以及**同级的 tarot-mass-divination 目录**（提供 interpret.md 提示词、牌阵、牌图；ip-pipeline 的 `.claude/skills/` 布局和 vira 平铺布局都自动识别）
- 想换 LLM 生成的解读但不换牌：重跑 `gen_reading.py --seed <固定值>`

## 内容铁律

1. **解读禁止手写** — cards/interpretation 必须走 `gen_reading.py`（interpret.md 真实管线）；手写的会被覆盖。
2. **截图不求完整** — 真实解读很长（8 块左右），截图只展示开头、底部自然截断即真实，不用凑整。
3. **划线词要选在可见开头** — `underlines[]` 命中任何位置都划线，但截图只露前两块，选靠后的短语等于白划。gen 完先看控制台回显的解读再定划线词。
4. 牌阵固定 **我-对方-我们牌阵**（3 张，对齐参考帖版式）；牌图自动从 tarot-mass-divination 拷到 `assets/cards/`。
5. **发布文案开头必带品牌软植入句**（用户 2026-09-16 拍板）— 结构：正文标题行 → 软植入句（单独一行）→ 正文 → 话题标签。软植入句由 `gen_reading.py` 按 question 用 `tarot-mass-divination/scripts/opener.py` 生成（AI，失败回退固定池），存 `content.json` 的 `opener` 字段，渲染时组装进 `out/发布文案.txt`。**别手写 `opener`**，也别把它塞进 `caption`（会重复）。

## content.json 字段

| 字段 | 说明 |
|---|---|
| `question` | 占卜问题（20px 居中，两行内最佳） |
| `sticker.text` | 贴纸文案，`\n` 分行，3 行内最佳；可选 `top`/`right`/`rotate` 微调 |
| `underlines` | 划线短语列表，全局子串匹配所有出现；未命中打 `[warn]` |
| `caption` | 抖音正文（首行可为钩子标题行；末行话题标签），渲染时自动写 `out/发布文案.txt` |
| `time` / `remaining_text` | 状态栏时间 / 顶部 chip（默认「无限畅享占卜」，gen 会强制写入） |
| `cards` / `interpretation` / `opener` | **勿手写**，gen_reading.py 回填（`opener` = 正文开头软植入句） |

## 版面规范（复刻来源）

- UI 底座取自 TarotBubble Flutter 源码（`tarot_chat_history_screen.dart` 等），同 wechat-tarot-dual 的塔罗侧面板：爱情题渐变底 `#FAF3FF→#FFF`；**状态栏居中品牌铭牌**（白底圆角矩形 + app logo + 塔罗气泡，参考 quin 状态栏胶囊，logo 在 `assets/app_icon.png`）；白色半透问题卡（底圆角 20）；牌 74×130 圆角 5（`reversed` 转 180°）+ 牌名 13px + 位置 11px；Luna 头像 35px + 名 17px；解读卡白 70%、紫边框 `rgba(91,77,188,.15)`、圆角 16、padding 13px 15px、间距 10px、**15px/1.7**（与 App 的 MarkdownInterpretationView 对齐，同 wechat-tarot-dual 现行设置）；`**粗体**` 渲染 w600 粗体、`\n` 正常换行；**无底部追问框**（用户拍板去除，解读自然铺到底部截断）。
- 划线：`#FF3B30` 4px 红线、`text-underline-offset:4px`，跨行短语每行都有线（马克笔效果）。
- 贴纸：品牌紫 `#5B4DBC` 底、白字 19px/600、圆角 14、投影、`rotate(-3deg)`。

## 验证

```bash
bash ../tarot-mass-divination/scripts/ocr_text.sh out/塔罗解读截图.png   # vira 布局
# ip-pipeline 布局：bash .claude/skills/tarot-mass-divination/scripts/ocr_text.sh 塔罗解读截图模板/out/塔罗解读截图.png
```

（gen_reading.py 渲染后自动跑 OCR。已验证：问题/牌名/位置/贴纸/解读开头全部逐字准确；`…` 被 OCR 读成 `..` 属识别误差。）

---
name: tarot-reading-shot
description: 抖音单屏塔罗解读截图图文模板。一整屏塔罗气泡App解读界面 + 解读正文红色关键词划线 + 牌卡区紫色情绪贴纸，1170×2532 真机分辨率直出。当用户要求「塔罗解读截图」「单屏解读图文」「抖音塔罗截图帖」时使用。
---

# tarot-reading-shot：单屏解读截图 + 划线 + 贴纸

复刻抖音爆款结构：**一整屏塔罗气泡App解读界面 + 解读正文红色关键词划线 + 牌卡区紫色情绪贴纸**。
与微信聊天双拼的区别：那是左右双屏讲故事，这是单屏截图直出，贴纸和划线是唯二的二创元素。

## 工作流

```bash
# 1. content.json 手写：question / sticker / underlines / caption（cards、interpretation、opener 不用写）
# 2. 一条命令：抽牌（我-对方-我们牌阵）→ interpret.md 真实解读 → 回填 JSON → 渲染 → OCR
python3 gen_reading.py                 # 读 content.json
python3 gen_reading.py 别的.json --seed 7   # 换内容 / 抽牌可复现

# 改了 sticker/underlines/caption 后单独重渲染（不重新抽牌解读）
python3 render_reading_shot.py [content.json]
```

输出：`out/塔罗解读截图.png`（1170×2532，390×844 @ DPR3）+ `out/发布文案.txt`。

## 内容铁律（违反=返工）

1. **解读禁止手写** — cards/interpretation 必须走 `gen_reading.py`（interpret.md 真实管线）；手写的会被覆盖。
2. **截图不求完整** — 真实解读很长（8 块左右），截图只展示开头、底部自然截断即真实，不用凑整。
3. **划线词要选在可见开头** — `underlines[]` 命中任何位置都划线，但截图只露前两块，选靠后的短语等于白划。gen 完先看控制台回显的解读再定划线词。
4. 牌阵固定 **我-对方-我们牌阵**（3 张，对齐参考帖版式）；牌图自动从 tarot-mass-divination 拷到 `assets/cards/`。
5. **发布文案开头必带品牌软植入句** — 结构：正文标题行 → 软植入句（单独一行）→ 正文 → 话题标签。软植入句由 `gen_reading.py` 按 question 用 `tarot-mass-divination/scripts/opener.py` 生成（全项目唯一实现），存 `content.json` 的 `opener` 字段。**别手写 `opener`**，也别把它塞进 `caption`（会重复）。

## content.json 字段

| 字段 | 说明 |
|---|---|
| `question` | 占卜问题（20px 居中，两行内最佳） |
| `sticker.text` | 贴纸文案，`\n` 分行，3 行内最佳；可选 `top`/`right`/`rotate` 微调 |
| `underlines` | 划线短语列表，全局子串匹配所有出现；未命中打 `[warn]` |
| `caption` | 抖音正文（首行可为钩子标题行；末行话题标签） |
| `time` / `remaining_text` | 状态栏时间 / 顶部 chip（默认「无限畅享占卜」，gen 强制写入） |
| `cards` / `interpretation` / `opener` | **勿手写**，gen_reading.py 回填 |

## 依赖

- **macOS**（正文用苹方 PingFang SC；OCR 走 Vision）
- `python3` + Playwright：`pip3 install playwright && python3 -m playwright install chromium`
- **仅渲染**（render_reading_shot.py）：除 Playwright 外无依赖，assets 全在模板目录内
- **gen_reading.py**：需 `LLM_API_KEY`（或 `DEEPSEEK_API_KEY`）+ 同级 tarot-mass-divination（提示词/牌阵/牌图）
- 想换 LLM 解读但不换牌：重跑 `gen_reading.py --seed <固定值>`

## 验证

gen 渲染后自动跑 OCR；手动：`bash ../tarot-mass-divination/scripts/ocr_text.sh out/塔罗解读截图.png`

版面规范（复刻来源、像素级参数）与已验证结论见 [README.md](./README.md)。

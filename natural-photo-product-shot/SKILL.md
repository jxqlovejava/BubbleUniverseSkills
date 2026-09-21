---
name: natural-photo-product-shot
description: 抖音「自然感实拍照片 + 产品解读卡」图文模板。满版自然感实拍照片垫底 + 左约 43% 半透明白底塔罗气泡App解读卡浮层，1728×2304 直出。当用户要求「自然照片产品截图」「实拍照片+解读卡」「照片垫底图文」时使用。
---

# natural-photo-product-shot：自然感实拍照片 + 解读卡浮层

复刻抖音爆款结构：**满版自然感实拍照片垫底 + 左约 43% 半透明白底「塔罗气泡App 解读卡」浮层**。
与单屏解读截图的区别：那是整屏 App 截图（无照片），这是**照片 + 悬浮解读卡**——照片是主角，解读卡是产品截图浮层。

## 工作流

```bash
# 一条命令：主题 → 照片文案 → 即梦生照片 → 抽牌 → 真实解读 → 渲染 → OCR
python3 gen_photo.py "缘分回溯到相遇那天"
python3 gen_photo.py "为何总遇到慢热的人" --seed 7 --card-position right

# 只生成 content.json 不渲染（先看文案/解读）
python3 gen_photo.py "主题" --skip-render

# 改了解读/划线/卡片位置后单独重渲染（不重新抽牌解读）
python3 render_photo_share.py [content.json]
```

输出：`out/自然照片产品截图.png`（1728×2304，即梦 2K 同尺寸）+ `out/发布文案.txt`。

## 内容铁律（违反=返工）

1. **解读禁止手写** — cards/interpretation 走 `gen_photo.py`（interpret.md 真实管线）；手写会被覆盖。
2. **截图不求完整** — 解读 8 块左右，截图靠卡 max-height 自然截断（真实截图感），不用凑整。
3. **划线词选可见开头** — `underlines[]` 命中任何位置都划红手绘线，但卡片只露前几块，选靠后的短语等于白划。gen 后看控制台回显解读再定。
4. **卡片位置与照片留白互补** — `--card-position left/right/center`（默认 left）；photo_prompt 会让主体偏卡片对侧留白，避免卡片盖脸。
5. 牌阵固定 **我-对方-我们牌阵**（3 张），牌图自动从 tarot-mass-divination 拷到 `assets/cards/`。
6. **发布文案开头必带品牌软植入句** — 结构：软植入句（单独一行）→ 正文 → 话题标签。由 `gen_photo.py` 按主题用 `tarot-mass-divination/scripts/opener.py` 生成，存 `opener`，完整文案存 `caption_full`；**渲染直接写 `caption_full`**（旧版只写 `caption` 会冲掉标签和软植入句）。

## content.json 字段

| 字段 | 说明 |
|---|---|
| `theme` / `card_position` | 主题 / 卡位置（default left） |
| `photo` | 背景照片路径（默认 `assets/photo_bg.png`，可由 gen 生图或手动覆盖） |
| `question` | 占卜问题（≤20 字，居中两行内最佳） |
| `cards` / `interpretation` | **勿手写**，gen_photo.py 回填 |
| `underlines` | 划线短语列表，全局子串匹配；未命中打 `[warn]` |
| `caption` / `hashtags` | LLM 写的抖音正文 / 话题标签 |
| `opener` / `caption_full` | **勿手写**，gen_photo.py 回填：软植入句 / 组装好的完整发布文案 |

## 依赖

- **macOS**（苹方字体；OCR 走 Vision）
- `python3` + Playwright：`pip3 install playwright && python3 -m playwright install chromium`
- **仅渲染**（render_photo_share.py）：零外部依赖，assets 全在模板目录内
- **gen_photo.py**：需 `LLM_API_KEY`（或 `DEEPSEEK_API_KEY`）+ 同级 tarot-mass-divination + **jimeng-image skill**（ego-lite 已登录即梦；生图失败自动回退 `assets/photo_bg.png`）
- 想换 LLM 解读不换牌：重跑 `gen_photo.py --seed <固定值>`

## 验证

gen 渲染后自动跑 OCR；手动：`bash ../tarot-mass-divination/scripts/ocr_text.sh out/自然照片产品截图.png`

版面规范（复刻来源、像素级参数）与已验证结论见 [README.md](./README.md)。

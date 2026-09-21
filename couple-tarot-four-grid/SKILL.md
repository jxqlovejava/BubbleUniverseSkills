---
name: couple-tarot-four-grid
description: 小红书情侣四宫格图文模板。上排 2 格塔罗气泡App真实界面截图（HTML 原色渲染，6 个产品页可选）+ 下排 2 格不露脸情侣场景照片（即梦生图），1080×1620 直出。当用户要求「情侣四宫格」「四宫格图文」「小红书情感四格」时使用。
---

# couple-tarot-four-grid：情侣四宫格（产品截图 + 情侣照片）

复刻小红书爆款结构：**上排 2 格=真实产品界面截图（源码样式 HTML 渲染，原色），下排 2 格=真实感情侣场景照片（不露脸，牵手/逛街局部）**。
与单屏解读截图、自然照片产品截图的区别：那两个是单屏/照片+悬浮卡，这个是 **2×2 四宫格**。

## 工作流

```bash
# 任意情侣主题 → LLM 出问题/文案/推荐语/照片提示词 → 真实抽牌+解读（禁手写）→ 即梦出照片 → 渲染+OCR
python3 gen_four_grid.py "异地恋该不该为Ta换城市"
python3 gen_four_grid.py "暗恋的同事要不要主动表白" --pages spread_result shuffle   # 上排换页
python3 gen_four_grid.py "复合" --seed 42 --skip-photos   # 复现抽牌 / 复用已有照片
```

- `--pages`：上排 2 格从 6 个真实产品页里选 2 个（默认 `reading shuffle`）：
  `reading` 解读页 / `shuffle` 洗牌页 / `draw` 抽牌页 / `spread` 牌阵选择页 /
  `spread_result` 牌阵结果页 / `history` 历史记录页
- 其他：`--count N` 每格照片即梦出 N 张（默认 3 选最新 1，可手动换 content.json 的 photo_bl/photo_br）；`--skip-render` 只回填不渲染
- 黑白化可选：content.json 里 `"bw": true` 开启（默认关=原色）

输出：`out/情侣四宫格.png`（1080×1620，2:3）+ `out/发布文案.txt`。

## 内容铁律（违反=返工）

1. **解读禁止手写** — 走塔罗解读截图模板的真实管线（gen_reading.py 同源逻辑），手动复用分步流程见 README。
2. **发布文案结构**（用户 2026-09-16 拍板）：标题短句（钩子行）→ 品牌软植入句（单独一行）→ 话题标签。软植入句走 `tarot-mass-divination/scripts/opener.py`（全项目唯一实现），`gen_four_grid.py` 组装好整段写进 content.json 的 `caption`，**不用手写**。
3. **照片不下牌不叠字**，保持「随手拍」感；手部是高危项，提示词写「五指完整清晰」+ 挑图复检。
4. **即梦并行生图必串** — 两个 agent_generate.py 并行、task-space 同名时会拿到同一批结果；并行必须 `--task-space` 各起不同名。

## 依赖

- **macOS** + `python3` + Playwright（chromium）+ PIL
- 解读管线：同级 `塔罗解读截图模板/gen_reading.py`（需 `LLM_API_KEY` 或 `DEEPSEEK_API_KEY`）
- 照片：`jimeng-image` skill（ego-lite 浏览器已登录即梦；没有先 `--skip-photos`，照片手动放进 `assets/photos_a|b/` 再改 content.json）

## 验证

`bash ../tarot-mass-divination/scripts/ocr_text.sh out/情侣四宫格.png`（已验证状态栏/铭牌/chip/问题/牌名/位置/解读开头逐字准确）

版面规范（各产品页像素级复刻参数）、手动分步流程与踩坑记录见 [README.md](./README.md)。

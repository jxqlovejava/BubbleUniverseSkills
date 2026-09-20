# 情侣四宫格图文模板（塔罗解读+情侣照片 · 小红书）

复刻小红书爆款结构：**上排 2 格=真实产品界面截图（源码样式 HTML 渲染，原色），下排 2 格=真实感情侣场景照片（不露脸，牵手/逛街局部）**。

与「塔罗解读截图模板」「自然照片产品截图模板」的区别：那两个是单屏/照片+悬浮卡；这个是 **2×2 四宫格**。

## 一条命令（推荐）

```bash
# 任意情侣主题 → LLM 出问题/文案/推荐语/照片提示词 → 真实抽牌+解读（禁手写）→ 即梦出照片 → 渲染+OCR
python3 gen_four_grid.py "异地恋该不该为Ta换城市"
python3 gen_four_grid.py "暗恋的同事要不要主动表白" --pages spread_result shuffle   # 上排换页
python3 gen_four_grid.py "复合" --seed 42 --skip-photos   # 复现抽牌 / 复用已有照片
```

- `--pages`：上排 2 格从 6 个真实产品页里选 2 个（默认 `reading shuffle`）：
  `reading` 解读页 / `shuffle` 洗牌页 / `draw` 抽牌页 / `spread` 牌阵选择页（浅色流程页）/
  `spread_result` 牌阵选择结果页（深色沉浸页）/ `history` 历史记录页
- 其他开关：`--count N` 每格照片即梦出 N 张（默认 3，自动选最新 1 张，可手动换 content.json 的 photo_bl/photo_br）；`--skip-render` 只回填不渲染
- 黑白化已改为**可选**：content.json 里 `"bw": true` 开启（默认关=原色）

## 手动复用（分步）

```bash
# 1. 换主题：先走真实管线生成解读（禁手写，铁律同解读截图模板）
cd ../塔罗解读截图模板
# 新建 xxx-content.json（只写 theme/time/question/caption，cards/interpretation 留空）
python3 gen_reading.py xxx-content.json --skip-render

# 2. 拷回内容 + 牌图
cp assets/cards/*.webp ../情侣四宫格图文模板/assets/cards/
# 把 gen 回填的 cards/interpretation 合入本模板 content.json（img 路径保持 assets/cards/...）

# 3. 换情侣照片：即梦各出 3 张挑 1（并行必须各自 --task-space 不同名，否则串结果！）
python3 ../jimeng-image/scripts/agent_generate.py "提示词" --out assets/photos_a --task-space "起名A"
# content.json 里 photo_bl / photo_br 指向选中照片

# 4. 渲染
python3 render_four_grid.py
```

输出：`out/情侣四宫格.png`（1080×1620，2:3 同参考帖 898×1352 比例）+ `out/发布文案.txt`。

## 发布文案结构（用户 2026-09-16 拍板）

```
标题短句（钩子行）
品牌软植入句（单独一行，AI 按主题生成，失败回退固定池）
#塔罗气泡 #塔罗牌 #情侣 …
```

软植入句走 `tarot-mass-divination/scripts/opener.py`（全项目唯一实现，同微信聊天双拼 / 解读截图 / 自然照片 / 录屏贴纸四个模板），
`gen_four_grid.py` 组装好整段写进 content.json 的 `caption`（另存 `opener` 便于回溯），`render_four_grid.py` 原样写 `out/发布文案.txt`。
**不用手写**；改了池子或校验规则改 opener.py，不要在各模板里各写一份。

## 版面规范（复刻来源）

- **解读页（左上）**：同塔罗解读截图模板（tarot_chat_history_screen.dart 系）：品牌铭牌、`无限畅享占卜` chip、白透问题卡 + 3 牌（逆位转 180°）、Luna 头像 + 解读卡，整屏 390×844 渲染后**顶部对齐裁 2:3**，解读自然截断。
- **洗牌页（右上）**：divination_shuffling_view.dart：爱情题渐变 `#FAF3FF→#FFF`、标题「正在洗牌」26px `rgba(0,0,0,.8)` w500、副标题 16px `rgba(0,0,0,.6)`、牌堆=App 牌背（默认 tarot_bg_1 深蓝，**本模板用 tarot_bg_10 浅色金线圈**，黑白化后更像参考帖的白牌堆；18 款牌背在 `TarotBubble/assets/torot/cardBg/` 可换）、核心 22+边缘 8 高斯散牌 ±65°、按钮 `#B0A5E1` 圆角 20「结束洗牌」。2:3（390×585）直出不裁切。
- **黑白化**（可选，`"bw": true`）：`L 模式 + autocontrast(cutoff=2) + Contrast×1.18`——参考帖的黑白不是纯灰，对比更狠。
- **照片（下排）**：即梦 3:4 出图，中心裁 2:3。**不下牌不叠字**，保持「随手拍」感；提示词参考参考帖：夜景背影+玩偶 / 俯拍牵手（手部高危，写「五指完整清晰」+挑图复检）。
- **单格 540×810**，整图 1080×1620。

## 依赖

- macOS + `python3` + Playwright（chromium）+ PIL
- 解读管线：同级 `塔罗解读截图模板/gen_reading.py`（需 `LLM_API_KEY` 或 `DEEPSEEK_API_KEY`）
- 照片：`jimeng-image` skill（ego-lite 浏览器已登录即梦）

## 拷给朋友部署（整个 vira-topic-and-tarot-readings 工作区）

工作区**自含**的部分（拷贝即带走）：84 张 Rider-Waite 牌面图（`tarot-mass-divination/data/tarot-card/rider_waite/`，不依赖 TarotBubble）、牌背/Luna 头像/App 图标、解读 LLM 管线与提示词、即梦生图脚本、6 个页面渲染器。

朋友还需补 4 样（都是一次性）：

```bash
# 1. Python 依赖 + chromium 内核（截图用）
pip3 install playwright pillow && python3 -m playwright install chromium

# 2. LLM key（解读 + 主题内容生成，DeepSeek 或任意兼容 OpenAI 接口）
export DEEPSEEK_API_KEY=sk-...        # 或 LLM_API_KEY，配 LLM_API_BASE / LLM_MODEL

# 3. 即梦出图：装 ego-browser 到 ~/.local/bin/ 并用它登录一次即梦（cookies 在本地 profile）
#    没有的话先用 --skip-photos，照片手动放进 assets/photos_a|b 再改 content.json

# 4.（可选）OCR 验证：xcode-select --install（ocr_text.sh 用 macOS Vision，缺了只是跳过校验）
```

然后 `cd 情侣四宫格图文模板 && python3 gen_four_grid.py "主题"` 即可。非 macOS 不能跑（状态栏字体 PingFang SC、OCR、ego-lite 都是 Mac 栈）。

## 验证

```bash
bash ../tarot-mass-divination/scripts/ocr_text.sh out/情侣四宫格.png
```

已验证：状态栏/铭牌/chip/问题/牌名/位置/解读开头/洗牌页文案逐字准确。

## 踩坑记录

- **即梦并行生图必串**：两个 agent_generate.py 并行跑、task-space 同名（默认值）时，两边会拿到同一批下载结果。并行必须 `--task-space` 各起不同名。
- 牌背用 App 默认 tarot_bg_1（经典深蓝星空，原色模式下最耐看）；只有开 `"bw": true` 黑白化时才建议换浅色 tarot_bg_10（深蓝黑白化是一坨黑方块）。18 款牌背在 `TarotBubble/assets/torot/cardBg/` 可换，替换 `assets/card_back.webp` 即可。
- **抽牌页扇形别凭感觉摆**：源码 `card_draw_page.dart` 的真实几何是 78 张 120×210 牌、以**左下角**为旋转枢轴（`Transform alignment: bottomLeft + rotateZ`）、枢轴落在圆心 (屏宽/2, 屏高+220) 半径 250 的圆上、角度 ±135°（`_maxFanAngle=1.5π`）；可见的只有中间 ±35° 一段，两侧自然旋出屏外——按这个写一次就对，别手调圆弧参数。注意 App 的 +220 偏移对应 844 高真机屏，本模板 2:3 画布只有 585 高，圆心要再下移 ~110px（`fan_cards(drop=110)`），否则弧顶压到抽到的牌、牌名和提示语。

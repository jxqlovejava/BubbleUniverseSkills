---
name: douyin-screen-record-sticker
description: 抖音录屏贴纸视频模板。左上角固定手写便利贴贴纸 + 塔罗气泡App洗牌→抽牌→解牌全流程自动走查录屏，OCR 定位 + CGEvent 真实操作，ffmpeg 合成 9:16 成片（自动变速剪辑/白屏剪除/首图拼接）。当用户要求「录屏贴纸视频」「产品录屏成片」「抖音录屏帖」时使用。
---

# douyin-screen-record-sticker：录屏贴纸视频

复刻竞品爆款形态：**左上角固定手写便利贴贴纸 + 产品洗牌→抽牌→解牌全流程录屏**，输出 9:16 抖音成片。
分工：贴纸讲故事立人设，录屏证明产品真实存在。

## 工作流

**自动录屏（推荐，主题参数化）：**

```bash
python3 auto_record.py "他对我是不是真心的"              # 全流程自动走查+录屏+合成
python3 auto_record.py "主题" --copy sahuang            # 换贴纸文案
python3 auto_record.py "主题" --no-compose              # 只录屏不合成
python3 auto_record.py "主题" --cover                    # 顺手出一张首图并拼到片头（耗即梦积分）
```

**首图/封面（gen_cover.py，可独立）：**

```bash
python3 gen_cover.py                  # 治愈系女性人像 9:16，出 3 张挑一张 → out/
python3 gen_video.py raw/xxx.mov --cover out/cover-xxx.png   # 已有首图手动拼片头
```

**手动录屏：** `gen_sticker.py --copy <key>` 出贴纸 → `./record_sim.sh` 录屏 → `gen_video.py raw/<时间戳>.mov` 合成。

## 核心机制（自动录制为什么能跑通）

- 零依赖原生方案：`simctl screenshot` + macOS Vision OCR 带框定位 → CGEvent 真实点击；**中文输入走 `simctl pbcopy` 写设备剪贴板 + 点「粘贴」**（模拟器丢 CGEvent 的 Unicode 载荷，直输中文只会打出 `aaaa…`，别再试）
- **主题上屏判据**：发送按钮有字才由灰转紫——脚本按颜色定位圆心，既判断已上屏又用来点发送（固定比例会因输入行漂移落空）
- **前置**：模拟器已 boot、App 已装、已手动登录（预检查 `flutter.isLoggedIn`）、账号有剩余解读次数；唯一依赖 = 终端授予「辅助功能」权限
- **成片剪辑**：洗牌页首帧用整片解码 + fps 取样定位（不能用 `-ss` 探针，关键帧稀疏会漂十几秒）；变速打点校准成视频时间轴（recordVideo 变帧率，比挂钟慢）；白屏死时间按「亮度初筛 + OCR 确认整页无文字」两步判据剪除；尾部常速段按**视频真实末帧**倒推
- **画幅**：默认 `--fit bleed` 裁上下铺满零侧边（设备屏 1320×2868 比 9:16 长 521px）

## 内容铁律（违反=返工）

1. **贴纸文案公式**：上句立冲突（挑衅/炫耀）+ 下句归因产品，第一人称口语，7+7 字；不用「」引号。文案库在 `content.json`（key 即 `--copy` 参数）
2. **发布文案禁词**：`塔罗`/`占卜`/`算命`/`卜卦` 一律不出现，话题标签换情感向；唯一豁免是品牌名 `塔罗气泡App`
3. **发布文案结构**（2026-09-16 拍板）：标题行 → 品牌软植入句（单独一行）→ 过程行 → 标签行；软植入句走 `tarot-mass-divination/scripts/opener.py`
4. **首图形象每次随机**（脸型/发型/妆容/服饰四槽位池采样，风格帧不变），账号内容不同质化；封面贴纸与录屏段**同一位置**（默认左上 60,200 头顶留白区），0.8s 过渡不跳变

## 依赖

- **macOS** + xcode 工具链（simctl、Vision OCR）、ffmpeg、Pillow（`pip install pillow`）、Playwright（贴纸渲染）
- App：TarotBubble 跑在 iPhone 模拟器（需 Rosetta + x86_64 构建），首次手动短信验证码登录
- 首图：jimeng-image skill（ego-lite 已登录即梦）

## 验证

`auto_record.py --selftest` 断言发布文案与全部贴纸文案无禁词；OCR 走 `scripts/ocr_boxes.swift`。

故障表、App 侧白屏根因、`gen_video.py` 全参数与分步说明见 [README.md](./README.md)。

---
name: image-to-code
description: |
  像素级图片转代码与切图工作流。将 UI 截图、App/Web 设计稿、Figma 图片导出稿或设计长图
  转换为代码，并输出独立透明 PNG 切图资源。支持严格 1:1 等比例还原、画板宽度精确 750px、
  禁止自动排版优化、文本可编辑、简单图形原生矢量/代码化、图标和位图独立透明 PNG 提取。
  适用于 Flutter / React Native / Web 等任意 UI 框架。
tags: [image-to-code, design-to-code, slicing, png-export, pixel-perfect, flutter, react-native, web]
---

# Image To Code 工作流

> **适用范围**：Claude Code / Codex / Cursor / Copilot / Windsurf / Cline 等任何 AI Coding Agent。
> 可以作为 Skill、自定义指令、Rules、System Prompt 或项目约定加载。

将 UI 图片/截图还原为代码并导出必要切图资源。基于 yueban-image-to-code 实战项目迭代提炼，覆盖从图片分析到代码落地的完整链路。

**流程**: S → M → E → C → V → D（Source → Manifest → Extract → Code → Verify → Deliver）

## 前置条件

- Python 3.8+，Pillow (`pip install Pillow`)，numpy (`pip install numpy`)
- 当前工作目录可读写

## When to Activate

触发条件（满足任一）：
- 用户提供 UI 截图并要求「还原」「转代码」「复刻」「按这个做页面」
- 用户提供设计长图、App 截图、网页截图
- 关键词：「图片转代码」「截图还原」「切图」「导出 PNG」「750px 还原」

---

## S: Source — 源图分析

1. 读取当前源图，记录原始尺寸 `source_width × source_height`
2. 确认目标框架：Flutter / React Native / Web / 其他
3. 确认输出要求：只输出代码 / 只输出切图 / 代码加切图
4. 确认哪些文字必须变成可编辑文本
5. 确认哪些复杂图形需要保留为透明 PNG

---

## M: Manifest — 建立图层清单（关键步骤）

**任何图片转代码 + 切图任务都必须先创建 `layers.manifest.json`。Manifest 是布局和切图的唯一数据源，不允许在代码里重新估算位置。**

### M1: 计算缩放比例

假设原图尺寸为 `source_width × source_height`：

```text
scale = 750 / source_width
final_width = 750
final_height = round(source_height * scale)
scaled_x = original_x * scale
scaled_y = original_y * scale
scaled_width = original_width * scale
scaled_height = original_height * scale
```

同一个 `scale` 必须应用到所有坐标、宽高、圆角、描边、阴影偏移和模糊、渐变位置、图标外框、文字字号、行高和字间距。

### M2: 图层分类与策略判定

实现前把每个可见元素归类，按策略判定表分配实现方式：

| 条件 | 策略 | 说明 |
|------|------|------|
| 照片级细节、复杂纹理、不规则插画、手绘元素 | **A** | 透明 PNG 切图 |
| 头像、产品图、截图、照片 | **A** | 透明 PNG 切图 |
| 图标（无论简单复杂）、logo、品牌标识 | **A** | 透明 PNG 切图 |
| 模块内同时有底图 + 叠加文字（不可分离） | **A** | 透明 PNG 切图 |
| 纯文本（无论是否有富文本样式） | **B** | 可编辑文本代码 |
| 简单几何形状（矩形、圆形、线条、边框） | **B** | CSS/矢量代码 |
| 简单按钮（纯色/渐变、无纹理） | **B** | CSS/矢量代码 |
| 简单分割线、标签、输入框 | **B** | CSS/矢量代码 |

### M3: 填写 manifest

每个图层至少记录：

```json
{
  "version": "1.0.0",
  "source": {
    "type": "image",
    "source_width": 1125,
    "source_height": 2436,
    "target_width": 750,
    "target_height": 1624,
    "scale": 0.6667
  },
  "layers": [
    {
      "id": "avatar",
      "type": "bitmap",
      "strategy": "A",
      "source_bbox": { "x": 86, "y": 112, "width": 120, "height": 120 },
      "scaled_bbox": { "x": 57, "y": 75, "width": 80, "height": 80 },
      "z_index": 10,
      "asset": "assets/images/avatar.png",
      "transparent_required": true,
      "gap_to_next": 16
    },
    {
      "id": "username",
      "type": "text",
      "strategy": "B",
      "source_bbox": { "x": 252, "y": 134, "width": 140, "height": 40 },
      "scaled_bbox": { "x": 168, "y": 89, "width": 93, "height": 27 },
      "z_index": 20,
      "style": {
        "text": "橘子果酱",
        "font_size": 21,
        "font_weight": 700,
        "color": "#07162A"
      },
      "gap_to_next": 12
    }
  ]
}
```

**规则**：
- `source_bbox` 必须来自当前源图测量，不得凭布局推算
- `scaled_bbox` 必须由同一个 `scale` 计算得到
- 代码中的每个图层必须能追溯到 manifest
- 如果实现截图和原图不一致，先修 manifest 坐标，再修代码
- 没有 manifest 的交付视为未完成

---

## E: Extract — 切图导出

### E1: Bbox 预览校验

切图区域不能凭感觉。每个需要导出的资源必须先完成 bbox 预览校验，再导出 PNG。

```bash
scripts/preview_bboxes.py source.png layers.manifest.json qa/bbox-preview.png --only-type bitmap
```

流程：
1. 在原图原始尺寸上测量 `source_bbox`，不要在浏览器缩放预览图上估算
2. bbox 必须覆盖完整元素外框，包括透明留白、浅色底形、阴影、半透明边缘
3. 对边界不确定的资源，建立 2-3 个候选 bbox，选择能完整覆盖且不多带相邻元素的最大安全框
4. 使用 `preview_bboxes.py` 把 manifest 中的 bbox 画到源图上生成预览图
5. 只有当预览框与原图元素完整外框对齐后，才允许切图
6. 如果预览框框到了相邻文字、相邻图标、卡片背景大块区域，必须修 bbox
7. 如果导出后发现缺失、贴边、白底、灰底，必须回到 bbox 预览步骤重测

### E2: 按 bbox 导出 PNG

```bash
scripts/extract_png_asset.py source.png assets/icons/icon-user.png \
  --x 120 --y 980 --width 72 --height 72 \
  --remove-bg floodfill \
  --manifest layers.manifest.json \
  --id icon-user
```

- 脚本不会自动 trim，输出画布固定等于 bbox
- `--remove-bg floodfill`：移除纯色背景并保留 alpha
- `--remove-bg corners`：按角点采样颜色移除背景
- 导出后自动更新 manifest

### E3: 审计 PNG 切图

```bash
scripts/audit_png_assets.py assets/icons assets/images \
  --require-transparent-bg \
  --manifest layers.manifest.json
```

检查：
- PNG 是否贴边（非透明像素触碰画布边缘）
- 尺寸是否匹配 manifest
- 透明背景是否合格（`--require-transparent-bg`）
- 是否有 alpha 通道

---

## C: Code — 代码实现

### C1: 框架选择

- 仓库已有框架 → 遵循现有框架
- 无项目 → 静态页面优先 HTML/CSS/JS；组件结构或交互需要时才用 React/Vite/Flutter

### C2: 750px 画板锁定

```css
/* Web 示例 */
.canvas {
  width: 750px;
  height: var(--final-height); /* = source_height * scale */
  position: relative;
  margin: 0 auto;
}
```

- 根画板必须是 `width: 750px`，高度等于归一化高度
- 画板内所有关键层必须使用 manifest 坐标定位
- 可以使用绝对定位实现锁定画板
- 禁止使用 flex/grid 的自动分布结果替代原图坐标

### C3: 图层实现对照

**Strategy A (bitmap) → 图片组件：**

```dart
// Flutter
Positioned(
  left: scaled_bbox.x,
  top: scaled_bbox.y,
  width: scaled_bbox.width,
  height: scaled_bbox.height,
  child: Image.asset(asset, fit: BoxFit.fill),
)
```

```tsx
{/* React */}
<img
  src={asset}
  style={{
    position: 'absolute',
    left: scaled_bbox.x,
    top: scaled_bbox.y,
    width: scaled_bbox.width,
    height: scaled_bbox.height,
  }}
/>
```

**Strategy B (text) → 可编辑文本：**

```dart
// Flutter
Positioned(
  left: scaled_bbox.x,
  top: scaled_bbox.y,
  child: Text(
    style.text,
    style: TextStyle(
      fontSize: style.font_size,
      fontWeight: FontWeight.w700,
      color: Color(int.parse(style.color.replaceFirst('#', '0xFF'))),
      height: style.line_height,
    ),
  ),
)
```

**Strategy B (vector) → CSS/原生形状：**

```css
.vector-layer {
  position: absolute;
  left: var(--x);
  top: var(--y);
  width: var(--width);
  height: var(--height);
  background: linear-gradient(...);
  border-radius: var(--radius);
  box-shadow: ...;
}
```

### C4: 布局锁定规则

- 页面预览时可以整体缩放画板，但不能对子元素重新排版
- 顶部头像区、数据区、会员条、四宫格卡片、更多服务、底部导航必须分别和原图同 x/y/width/height
- 如果截图里出现内容整体上移、下移、卡片变宽、间距变大、头像被裁、底部导航位置变化，直接判定布局失败
- 响应式适配是第二阶段任务，不能改变 750px 定稿

---

## V: Verify — 验收与复核

### V1: 启动本地页面

```bash
# Flutter
flutter run

# Web
python -m http.server 8080
# 或
npm run dev
```

### V2: 截取 750px 画板截图

确保浏览器/模拟器窗口宽度为 750px，截取完整页面。

### V3: 图片差异对比

```bash
scripts/compare_images.py reference-750.png render-750.png --json
```

输出量化指标：
- `changed_pixel_ratio`: 变化像素比例（目标 < 0.05）
- `mae`: 平均绝对误差（目标 < 5）
- `rmse`: 均方根误差（目标 < 10）
- `max_rgb_diff`: 最大 RGB 差异（目标 < 30）

### V4: 分模块验收

**矢量图层模块：**
- [ ] x/y 坐标、宽高、圆角、描边、颜色、渐变、阴影、透明度对齐

**文本图层模块：**
- [ ] 文字内容、坐标、字号、字重、行高、字间距、颜色、对齐方式

**位图/图标切图模块：**
- [ ] PNG 宽高与 manifest 一致
- [ ] 叠放到最终坐标位置，无边缘缺漏
- [ ] 四边无非透明像素贴边
- [ ] 来源一致性：形状、颜色、比例、角度与原图一致

### V5: 叠图复核

- 最终页面截图与 750px 原图叠图比对
- 确认无缺图、无裁切、无错位、无层级错误
- 保留 QA 对照方式（半透明 overlay 或差异图）

---

## D: Deliver — 交付

完成后只需要简短说明：

- 修改或新增的代码文件
- 切图资源目录
- 750px 画板尺寸
- `layers.manifest.json`
- bbox 预览图或等效框选复核说明
- 截图和模块校验记录
- `audit_png_assets.py` 审计结果
- 已知限制（缺少原字体、源图像素不足、部分元素被遮挡等）

不要写冗长解释。真正的交付证明是代码、切图资源和复核截图。

---

## 禁止行为清单

以下行为全部视为失败：

- [ ] 把原图的小图标换成 lucide、Material Icons、SF Symbols 或其他相似图标
- [ ] 把原图卡片里的钱包、礼盒、徽章、星星、人物头像重新画成另一套风格
- [ ] 把原图中靠左/靠右/局部露出的插画改成居中、放大、缩小或重新裁切
- [ ] 把四宫格、服务宫格、会员条、底部导航重新排版成更均匀的布局
- [ ] 为了适配代码组件，把原图卡片高度、圆角、间距、文字位置、图片比例改掉
- [ ] 用渐变、阴影或 CSS 图形模拟复杂位图，导致形状和原图不一致
- [ ] 先凭感觉写代码再补切图（必须先有 manifest 再切图再写代码）

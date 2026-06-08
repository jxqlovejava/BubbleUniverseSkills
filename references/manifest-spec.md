# Unified Manifest Specification

`layers.manifest.json` 是 BubbleUniverseSkills 下所有 design-to-code skill 的**单一数据源**。

任何图片转代码、Figma 复刻、设计稿还原任务都必须先创建 manifest，再导出资源或写代码。

## 文件约定

- **文件名**：`layers.manifest.json`
- **位置**：项目工作目录下，与代码和资源同级
- **格式**：JSON，UTF-8 编码

## Schema

```json
{
  "version": "1.0.0",
  "source": {
    "type": "image | figma",
    "source_width": 750,
    "source_height": 1624,
    "target_width": 750,
    "target_height": 1624,
    "scale": 1.0
  },
  "layers": [
    {
      "id": "hero_banner",
      "type": "bitmap | text | vector | container",
      "strategy": "A | B",
      "source_bbox": { "x": 0, "y": 76, "width": 750, "height": 280 },
      "scaled_bbox": { "x": 0, "y": 76, "width": 750, "height": 280 },
      "z_index": 10,
      "asset": "assets/images/hero_banner_3x.png",
      "transparent_required": false,
      "gap_to_next": 16,
      "figma_node_id": "123:456",
      "style": {
        "color": "#FFFFFF",
        "font_size": 32,
        "font_weight": 700,
        "line_height": 1.4,
        "text_align": "center"
      },
      "notes": "从 Figma 桌面端导出 3x PNG"
    }
  ]
}
```

## 字段说明

### 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `version` | string | 是 | Manifest 版本号，当前 `1.0.0` |
| `source` | object | 是 | 源信息 |
| `layers` | array | 是 | 图层列表，按 z-index 从小到大排序 |

### source 对象

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 源类型：`image` 或 `figma` |
| `source_width` | number | 是 | 原始源宽度（像素） |
| `source_height` | number | 是 | 原始源高度（像素） |
| `target_width` | number | 是 | 目标画板宽度 |
| `target_height` | number | 是 | 目标画板高度 |
| `scale` | number | 是 | 全局缩放比例：`target_width / source_width` |

### layer 对象

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 图层唯一标识，kebab-case |
| `type` | string | 是 | `bitmap` / `text` / `vector` / `container` |
| `strategy` | string | 条件 | 实现策略：`A`（导出整图）/ `B`（原生代码渲染）。`type=bitmap` 时必填 |
| `source_bbox` | object | 是 | 源图中的边界框 `{x, y, width, height}` |
| `scaled_bbox` | object | 是 | 缩放后的边界框，所有值 = source_bbox * scale |
| `z_index` | number | 是 | 堆叠顺序，数值越大越在上层 |
| `asset` | string | 条件 | 资源文件路径。`strategy=A` 或 `type=bitmap` 时必填 |
| `transparent_required` | boolean | 否 | 是否需要透明背景，默认 `false` |
| `gap_to_next` | number | 否 | 与下一个图层的垂直间距（像素） |
| `figma_node_id` | string | 否 | Figma 节点 ID，如 `123:456`。Figma 源时推荐填写 |
| `style` | object | 否 | 样式属性，视 type 而定 |
| `notes` | string | 否 | 人工备注 |

### bbox 对象

```json
{ "x": 120, "y": 80, "width": 200, "height": 100 }
```

- 所有值为整数像素
- `x, y` 为左上角坐标
- `width, height` 必须 > 0

### style 对象（按 type 扩展）

**type=text 时：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | string | 文本内容 |
| `color` | string | 文字颜色，hex 格式 |
| `font_size` | number | 字号（px） |
| `font_weight` | number | 字重 |
| `font_family` | string | 字体 |
| `line_height` | number | 行高倍数 |
| `letter_spacing` | number | 字间距 |
| `text_align` | string | `left` / `center` / `right` |

**type=vector 时：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `background_color` | string | 填充色 |
| `border_radius` | number | 圆角（px） |
| `border_width` | number | 描边宽度 |
| `border_color` | string | 描边颜色 |
| `gradient` | object | 渐变 `{start, end, angle}` |
| `shadow` | object | 阴影 `{color, blur, offset_x, offset_y}` |
| `opacity` | number | 不透明度 0-1 |

## 规则

1. **`source_bbox` 必须来自当前源图测量**，不得凭布局推算。
2. **`scaled_bbox` 必须由同一个 `scale` 计算得到**，不得单独估算。
3. **代码中的每个图层必须能追溯到 manifest**，不得出现 manifest 外的隐形图层。
4. **如果实现截图和原图不一致，先修 manifest 坐标，再修代码。**
5. **没有 manifest 的交付视为未完成。**

## 两种 Skill 的差异

### image-to-code 使用方式

- `source.type = "image"`
- `source_bbox` 从截图/设计图测量
- `scale = 750 / source_width`（固定 750px 归一化）
- `strategy` 通过规则判定表分配
- `asset` 指向从源图提取的透明 PNG

### figma-page-replication 使用方式

- `source.type = "figma"`
- `source_bbox` 从 Figma `get_design_context` 提取
- `scale` 通常为 1.0（使用 Figma 原始设计值）或按目标平台缩放
- `strategy` 通过 A3 策略判定规则分配
- `figma_node_id` 记录对应节点，便于追溯
- `asset` 指向从 Figma 桌面端导出的 3x PNG

## 校验清单

- [ ] `version` 为 `1.0.0`
- [ ] `source` 包含完整的宽高和 scale
- [ ] 每个 layer 有唯一 `id`
- [ ] `type` 为 `bitmap` / `text` / `vector` / `container` 之一
- [ ] `source_bbox` 和 `scaled_bbox` 的宽高为正整数
- [ ] `z_index` 无重复（除非明确需要同层）
- [ ] `strategy=A` 的 layer 有 `asset` 路径
- [ ] `transparent_required=true` 的 layer 有对应的审计计划
---
name: figma-page-replication
description: |
  Figma 设计稿 → 应用页面完整复刻工作流。支持 Flutter / React Native / Compose 等任意 UI 框架。
  核心流程 P→A→I→E→V→B：准备 Figma 上下文 → 模块分析与策略判定 → 资源收集 → 逐模块构建
  → 多维度验证 → 边界陷阱参考。内置双轨策略引擎（整图导出 vs 原生 Widget 渲染）、
  设计标记自动映射、底部 CTA 滚动自适应阴影模式、7 类常见陷阱自动规避。
  适用于活动落地页、招募页、推广页、功能引导页等任何 Figma → Code 场景。
tags: [figma, landing-page, design-to-code, flutter, react-native, compose, page-replication]
---

# Figma 页面复刻工作流

> **适用范围**：Claude Code / Codex / Cursor / Copilot / Windsurf / Cline 等任何 AI Coding Agent。
> 可以作为 Skill、自定义指令、Rules、System Prompt 或项目约定加载。核心方法论 P→A→I→E→V→B 与具体工具无关。

将 Figma 设计稿精准复刻为应用页面。基于多个实战项目迭代提炼，覆盖从设计分析到代码落地的完整链路。

**流程**: P → A → I → E → V → B（Preparation → Analyze → Identify → Execute → Verify → Boundary）

## 前置条件

使用者需要确保其 AI Coding Agent 能访问 **Figma MCP**（Model Context Protocol），提供以下工具：
- `get_design_context(nodeId, fileKey)` — 获取设计节点完整规格
- `get_screenshot(nodeId, fileKey)` — 获取设计节点截图

配置方式参见 [README.md](./README.md)。

## When to Activate

触发条件（满足任一）：
- 用户提供 Figma 链接并要求「复刻」「实现」「做活动页」「做落地页」
- 用户说「参考 figma 设计稿」「按设计稿做」
- 关键词：`figma.com` + 落地页/活动页/招募页/推广页

---

## P: Preparation — 准备阶段

1. 从 Figma URL 提取 `fileKey` 和 `nodeId`
2. 调用 `get_design_context(nodeId, fileKey)` 获取完整设计规格
3. 调用 `get_screenshot(nodeId, fileKey)` 获取视觉参考截图
4. **确认项目的资源目录路径**：检查 `pubspec.yaml` / 项目配置中的 assets 路径

---

## A: Analyze — 模块分析（关键步骤）

**目的**：在写任何代码之前，完整解析设计稿中每个模块的类型和策略。

### A1: 获取设计树

```
get_design_context(nodeId, fileKey) → 解析所有子节点
```

### A2: 输出模块分析表

按从上到下顺序，逐个模块记录。以下为示例格式（括弧内为 Figma 提取值，实际项目会不同）：

| # | 模块描述 | Figma top | 设计尺寸 | 内容类型 | 策略 | 说明 |
|---|---------|-----------|---------|---------|------|------|
| 0 | `<badge>` | 53 | 292×27 | 复杂SVG装饰+文字 | **A** | 导出3x整图 |
| 1 | `<hero_banner>` | 76 | 343×112 | 合成图(底图+叠加文字) | **A** | 导出3x整图 |
| 2 | `<subtitle_text>` | 195 | 359×28 | 纯文字 | **B** | Text.rich |
| 3 | `<description_text>` | 235 | 356×51 | 纯文字 | **B** | Text |
| 4 | `<tag_row>` | 305 | 345×25 | 图标+文字标签 | **A** | 导出3x整图 |
| 5 | `<feature_cards>` | 341 | 334×226 | 复杂卡片组 | **A** | 导出3x整图 |
| 6 | `<expect_section>` | 569 | 355×159 | 底图+内置文字 | **A** | 导出3x整图 |
| 7 | `<cta_button>` | 814 | 343×48 | 渐变按钮 | **B** | 项目 Button/GestureDetector |
| 8 | `<bottom_hint>` | 875 | 342×17 | 纯文字 | **B** | Text |

每个模块还记录与上一模块的间距（`下一模块.top - (上一模块.top + 上一模块.height)`），用于后续 `SizedBox` 取值。

### A3: 策略判定规则

| 条件 | 策略 |
|------|------|
| 模块内**同时有底图 + 叠加文字**（文字已嵌入底图不可分离） | **A**：整图导出3x |
| 模块包含**复杂不规则装饰物**（SVG路径多且非规则形状） | **A**：整图导出3x |
| 模块包含**照片级细节或复杂纹理** | **A**：整图导出3x |
| 模块仅有**纯色/渐变底色 + 独立文字** | **B**：Widget渲染 |
| 模块仅为**纯文本**（无论是否有富文本样式） | **B**：Widget渲染 |
| 模块为**简单按钮**（渐变纯色、无纹理） | **B**：Widget渲染 |

### A4: 用户确认

展示分析表，等待用户确认策略分配。确认后进入资源收集阶段。

---

## I: Identify — 资源收集

根据分析表收集策略 A 的资源：

1. 列出所有标记为 **策略 A** 的模块
2. 请用户从 Figma 桌面端逐个导出 3x PNG → 本地目录（如 `~/Downloads/`）
3. 复制到项目资源目录下（路径从 P4 确认）
4. 优先检查用户本地是否有已有高清版本（避免 Figma API 1x 模糊）

**注意**：Figma API 的 `get_screenshot` 只能输出 1x 设计分辨率 → **永远不要用作策略 A 的最终资源**。

---

## E: Execution — 页面构建

### E1: 搭建页面框架

按项目框架创建页面组件。通用结构（StatefulWidget + Column + Expanded，以 Flutter 为例，其他框架同理）：

```dart
// 1. 从 Figma get_design_context 提取页面背景色
// 2. 按分析表从上到下排列各 section（CTA 按钮除外）
// 3. 间距使用分析表中计算出的 gap 值
// 4. 底部 CTA 参照 E6 默认模式实现（常驻 + 滚动自适应阴影）
// 5. 返回按钮浮动在 ScrollView 之上
class XxxLandingPage extends StatefulWidget {
  static void navigate(BuildContext context) { /* push route */ }
  @override
  State<XxxLandingPage> createState() => _XxxLandingPageState();
}

class _XxxLandingPageState extends State<XxxLandingPage> {
  final ScrollController _scrollController = ScrollController();
  bool _isNearBottom = false;

  @override
  void initState() { super.initState(); _scrollController.addListener(_onScroll); }
  @override
  void dispose() { _scrollController.dispose(); super.dispose(); }

  void _onScroll() { /* 参照 E6 */ }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: /* Figma 页面背景色 */,
      body: Column(children: [
        Expanded(child: Stack(children: [
          SingleChildScrollView(
            controller: _scrollController,
            child: Column(children: [
              _section0(), SizedBox(height: _gap0_1),  // 按分析表
              _section1(), SizedBox(height: _gap1_2),
              // ...
            ]),
          ),
          _buildBackButton(context),
        ])),
        _buildBottomBar(context),  // 参照 E6
      ]),
    );
  }
}
```

### E2: 策略 A 模块 → 图片组件

```dart
Widget _buildImageSection(String assetPath, double borderRadius) {
  return Padding(
    padding: const EdgeInsets.symmetric(horizontal: /* Figma 边距 */),
    child: ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: Image.asset(assetPath, width: double.infinity, fit: BoxFit.fitWidth),
    ),
  );
}
```

### E3: 策略 B 模块 → 原生 Widget

字体、颜色、字号、字重均从 `get_design_context` 返回的 Figma 规格中提取：

```dart
// 纯文本示例
Text(
  /* Figma 文本内容 */,
  style: TextStyle(
    fontFamily: /* 从 Figma font-family 提取 */,
    fontSize: /* Figma font-size */,
    fontWeight: /* Figma font-weight */,
    color: /* Figma color */,
    height: /* Figma line-height / font-size */,
  ),
  textAlign: TextAlign.center,
);

// 渐变按钮示例
Container(
  decoration: BoxDecoration(
    gradient: LinearGradient(
      colors: [/* Figma gradient start */, /* Figma gradient end */],
    ),
    borderRadius: BorderRadius.circular(/* Figma border-radius */),
  ),
  child: Text(/* Figma 按钮文字 */),
);
```

### E4: 设计标记映射

| Figma 属性 | 代码映射 |
|-----------|---------|
| `color: #967ED6` | `Color(0xFF967ED6)` |
| `border-radius: 20px` | `BorderRadius.circular(20)` |
| `gradient: #START → #END` | `LinearGradient(colors: [Color(0xFFSTART), Color(0xFFEND)])` |
| `padding: 16px` | `EdgeInsets.all(16)` |
| `gap: 12px` | `SizedBox(height: 12)` |
| `line-height / font-size` | `height: <比值>` |

> 字体、具体色值均从 `get_design_context` 返回的 Figma 声明中提取，不同项目不同设计稿都会变化。

### E5: CTA / 交互按钮

**复用项目中已有的模式**，不要凭空实现。查找方法：
1. 搜索项目代码中现有的「联系我们」「客服」「分享」「跳转」等功能的实现
2. 找到对应的 Service/Manager 或页面跳转逻辑
3. 直接引用，保持行为一致

### E6: 底部常驻CTA（滚动自适应阴影）

**适用场景**：活动页底部 CTA 按钮（如「立即加入」「立即参与」）需要始终可见，且滑到底部时自然融入。

**默认实现模式**：

```dart
class XxxLandingPage extends StatefulWidget {                    // 必须是 StatefulWidget
  const XxxLandingPage({Key? key}) : super(key: key);

  @override
  State<XxxLandingPage> createState() => _XxxLandingPageState();
}

class _XxxLandingPageState extends State<XxxLandingPage> {
  final ScrollController _scrollController = ScrollController();
  bool _isNearBottom = false;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (!_scrollController.hasClients) return;
    final maxScroll = _scrollController.position.maxScrollExtent;
    final currentScroll = _scrollController.position.pixels;
    final nearBottom = maxScroll - currentScroll < 16;          // 距底部 16px 触发
    if (nearBottom != _isNearBottom) {
      setState(() => _isNearBottom = nearBottom);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: /* 页面背景色 */,
      body: Column(                                               // Column + Expanded 布局
        children: [
          Expanded(
            child: Stack(
              children: [
                SingleChildScrollView(
                  controller: _scrollController,                  // 传入 controller
                  child: Column(children: [
                    // ... 所有内容模块（不含底部CTA）...
                    const SizedBox(height: 24),
                  ]),
                ),
                _buildBackButton(context),                        // Positioned 返回按钮
              ],
            ),
          ),
          _buildBottomBar(context),                               // 底部栏在 Column 最下
        ],
      ),
    );
  }
}
```

**`_buildBottomBar` 实现**（带 `AnimatedContainer` 平滑过渡阴影）：

```dart
Widget _buildBottomBar(BuildContext context) {
  final bottomPadding = MediaQuery.of(context).padding.bottom;
  return AnimatedContainer(                                       // 200ms 平滑过渡
    duration: const Duration(milliseconds: 200),
    decoration: BoxDecoration(
      color: /* 页面背景色 */,
      boxShadow: _isNearBottom                                    // 距底部 16px 内无阴影
          ? []
          : [BoxShadow(color: Color(0x1A000000), blurRadius: 8, offset: Offset(0, -2))],
    ),
    padding: EdgeInsets.only(bottom: bottomPadding),              // 适配安全区
    child: Column(mainAxisSize: MainAxisSize.min, children: [
      const SizedBox(height: 16),
      // CTA 按钮...
      const SizedBox(height: 8),
      // 底部提示文字...
      const SizedBox(height: 16),
    ]),
  );
}
```

**状态说明**：
- `_isNearBottom = false` → 阴影可见，按钮与内容区视觉分离（常驻态）
- `_isNearBottom = true` → 阴影消失，按钮自然融入页面（融入态）
- `AnimatedContainer` 保证两种状态间的 200ms 过渡丝滑流畅
- 阈值 `16px` 适用于大部分页面内容高度，可根据实际微调

### E7: 构建与部署

根据项目类型选择构建命令，原则：
- 资源文件新增/替换 → 需要完整 rebuild
- 仅代码变更 → 热重载即可

---

## V: Verify — 复刻检查

### V0: REST API 导出完整性检查（关键）

**Figma REST API 导出单个节点时，不会包含其子节点的叠加内容。** 如果模块结构是：
- 背景图片节点
- 标题/文字节点（独立定位叠加在上面）

→ REST API 对背景图片节点单独导出 **会丢失所有叠加文字**。

**识别方法**：在 `get_design_context` 返回中，检查目标节点是否有兄弟文字节点在相同坐标区域：
```html
<div style="position:absolute; top:xxx; left:xxx">  <!-- 背景图片 -->
<div style="position:absolute; top:xxx; left:xxx">  <!-- 叠加文字 -->
```

**修复**：
- 优先使用**父级容器节点**导出（包含所有子节点）
- 或使用用户提供的**组合截图**（如图层合并后的 PNG）
- 或将文字拆为 Flutter Widget 叠加在背景图上

### V1: 模块对照

拿出 **A2 分析表**，在设备上逐模块对照：位置、尺寸、清晰度、样式是否与设计一致。

### V2: 视觉对比

重新调用 `get_screenshot(nodeId, fileKey)` 获取原始设计截图，与设备显示对比。

### V3: 交互检查

- [ ] 返回按钮可点击且有振动/触摸反馈
- [ ] CTA 按钮功能正常
- [ ] 页面可正常滚动，无溢出
- [ ] 无闪烁、无布局跳动

### V4: 高频遗漏项

- [ ] 所有文本用原生 Widget（策略 B），清晰无模糊
- [ ] 所有图片来自 3x 导出（策略 A），清晰无模糊
- [ ] 按钮渐变起止色与 Figma 一致
- [ ] Section 间距与分析表 gap 值对齐

---

## B: Boundary — 常见陷阱

| # | 陷阱 | 现象 | 修复 |
|---|------|------|------|
| 1 | **Figma API 1x 限制** | 图模糊 | Figma 桌面端 3x 导出，或用户提供高清文件 |
| 2 | **语法兼容** | 新语法编译报错 | 确认项目 SDK/language 版本，回退兼容写法 |
| 3 | **图片黑底** | 图标有黑色背景 | `get_screenshot(contentsOnly: true)` |
| 4 | **键盘透黑**（iOS） | 键盘圆角处黑色 | 设置窗口/根视图背景色为白色 |
| 5 | **调试器超时** | 连不上 | 停掉旧进程后重试 |
| 6 | **模块遗漏** | 某个设计元素未实现 | 严格按 A2 分析表逐项对照 V1 |
| 7 | **图片拉伸变形** | `BoxFit.fill` 改变比例 | 用 `BoxFit.fitWidth` + `ClipRRect` |

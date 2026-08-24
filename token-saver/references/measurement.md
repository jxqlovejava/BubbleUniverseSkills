# 度量方法 — 优化前后节省幅度量化

核心原则：**不许愿式优化**。每次改动前采基线，改动后同路径复测，数字写进 commit 和 learnings。

## 1. 基线三件套（改前必采）

| 指标 | 采集方法 | 为什么 |
|------|---------|--------|
| 轮次数 | 数一次完整任务的工具往返轮数 | 弱缓存后端每轮全价，轮次是第一杠杆 |
| 单轮上下文体量 | 读入文件：行数 × ~29 token（420 行 ≈12k）；或 `wc -c` 字节 ÷ 4（英文）/÷ 1.5（中文）粗估 | 推理耗时 ∝ 上下文体量 |
| 静态注入体量 | `wc -c CLAUDE.md`；skill 描述注入 = 各 SKILL.md frontmatter description 合计 token | L0 裁剪的直接收益指标（实证：17.5k→1.4k） |
| 耗时分解 | 脚本/命令自带耗时日志 vs 任务总耗时，差值 = 模型推理+往返 | 定位大头在脚本侧还是模型侧 |

实证案例：
- 4m47s 任务，pipeline 仅 7.0s → 4 轮推理 × 大上下文是大头
- 3m59s 分析，scan 本体 50s → 截断补数据 + 重复搜索占 3/4
- 2m11s 中 scan 33.7s → 97s 浪费在 6 个静态文件全量 Read

## 2. 工具盘点

| 工具 | 测什么 | 用法 |
|------|--------|------|
| `rtk gain` | 命令输出过滤节省的 token | `rtk gain --history` 看逐命令节省 |
| ccusage / 会话统计 | 会话级 token 总量、cache 命中 | `npx ccusage` 按会话/按天看 input/output/cache read |
| 日志时间戳分段 | 慢在哪一段 | 相邻日志时间差 >5s 的段即嫌疑段（实证：一眼定位 scan 6.9s vs DDG 186s） |
| Claude Code statusline | 当前上下文占用 | 观察静态瘦身前后变化（需新会话生效） |
| openwolf-rtk skill | Read/Write 工具 token 浪费追踪 | hook 自动跑，定期看报告 |
| 跨项目使用审计 | 全局层裁剪前的使用证据 | python 扫 `~/.claude/projects/*/*.jsonl` 聚合 skill/MCP/插件调用次数（方法见 static-context.md §9） |

## 3. Prompt cache 专项

- **固定前缀**（system prompt + CLAUDE.md + 工具 schema + 插件注入）有 cache 命中折价，TTL ~5min。
- 首轮 prefill 全价；缓存过期后的第一轮全价；静态上下文越大，这两轮越贵。
- 弱缓存后端（无 cache 或命中率低）：视同每轮全价，**轮次数 × 单轮体量** 是唯一优化目标。
- 静态瘦身对 cache 场景的收益：降首轮 prefill + 降过期轮 + 降每轮注意力开销（实证预估 -15~20k token/轮）。
- 验证 cache 是否生效：ccusage 看 `cache_read` vs `input` 比例；或直接查会话 transcript——
  ```bash
  grep -o '"cache_read_input_tokens":[0-9]*' ~/.claude/projects/<project-slug>/<session>.jsonl | tail -3
  ```
  cache_read 稳定 >0 即命中（实证：kimi-k3 实测 cache_read ~74-79k/轮、新 input 仅 0.3-3.4k，"弱缓存"的旧记忆被实测推翻——**别凭传闻假设缓存不生效，先查 transcript**）。

## 4. 前后对比模板

commit message / learnings 里写死：

```
<动作> — <指标>: <改前>→<改后> (<幅度>)
根因: <一句话>
```

实证样例（全部来自真实 commit）：
- `fact_checker 13.3s→2.3s, scan总耗时-45% — 新闻交叉验证并行化+30min缓存`
- `scan 提速 35s→26s (Step2 20.9→4.5s) — ETF并行+磁盘缓存`
- `8主题串行重试白耗~186s→仅首主题~14s — DDG进程级熔断`
- `金价分析 19min→≤1min — 只跑一次scan+落盘一次+cat直出`
- `每轮 -15~20k token — 禁28插件+归档265技能+agents 94→44`
- `skill描述注入 17.5k→1.4k token(-92%) — 白名单制 skills 305→28`
- `CLAUDE.md 23.3k→10.9k字符(309→136行) — 大表外置docs+删重复覆盖`

## 5. 防虚报检查

- 时间收益/token 收益分开报，不混为一谈。
- **生效时机分两类**：skill/agents/rules 归档本会话实时生效（系统注入重扫，可即测）；插件/MCP 禁用**下次会话才生效**——本会话测不出就说"预期值"，新会话实测后回填。
- 复用类优化（mtime <3h 复用）只在重复执行场景生效，注明适用条件。
- 对比必须同路径：冷启动 vs 冷启动，复用 vs 复用。
- **展示类优化必须验证用户实际可见性**——省下的 token 若以"用户看不见内容"为代价（工具输出折叠），是负收益不是优化（P7 cat 直出当日废除事故）。

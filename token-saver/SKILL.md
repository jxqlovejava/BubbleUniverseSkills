---
name: token-saver
description: Claude Code 项目级 token 成本诊断、优化与度量。触发词：省 token / token 优化 / token 太贵 / 上下文瘦身 / 会话变慢 / 降本 / prompt cache / 分析太慢 / token saver / context slimming。用于：诊断会话 token 消耗结构、裁剪项目级静态上下文（插件/agents/skills/rules/MCP/CLAUDE.md）、优化运行时行为（轮次/读入/输出/思考预算）、度量优化前后节省幅度。
---

# Token Saver — 项目级 token 成本优化

实战沉淀自 ai-gold-miner 2026-06→08 的 20+ 次提速迭代（金价分析 19min→≤1min，单轮上下文 -15~20k token）+ ip-pipeline 2026-08-24 二验（skills 81→15、项目级禁插件 19、全局层审计裁剪插件 16/MCP 4/agents 41→3）。

## 成本心智模型

```
单轮成本 = prefill(全量上下文) + output 生成 + 工具往返
总成本   = 轮次数 × 单轮上下文 + 输出 token 总量
```

- **有 prompt cache**：固定前缀（system prompt + CLAUDE.md + 工具 schema）命中折价，但首轮 prefill 全价、缓存 ~5min 过期轮全价、注意力开销随总长涨。
- **弱缓存/无缓存后端**（如部分国产模型）：每轮全价重算 → **轮次数 × 单轮体量是唯一可控杠杆**，减轮次和减体量等效。
- **output 生成是硬耗时**：把盘上已有内容重新生成一遍 = 同内容付两遍钱（实测复述 5k 字报告 ≈10k token ≈60-90s）。
- **瓶颈定位先归因**：脚本硬耗时 vs 模型推理耗时分开算。案例：4m47s 中 pipeline 仅 7s；3m26s 中 scan 仅 18s——大头全在模型侧。

## 四层杠杆速查

| 层 | 对象 | 特点 | 详见 |
|----|------|------|------|
| L0 静态上下文 | 插件/agents/skills/rules/MCP/CLAUDE.md | 每轮必付，裁剪一次永久受益 | references/static-context.md |
| L1 会话行为 | 轮次数 / 读入量 / 输出量 | 工作流纪律，零配置成本 | references/runtime.md |
| L2 工具层 | rtk 过滤/熔断/缓存复用/落盘直读 | 一次性代码改动 | references/runtime.md |
| L3 思考预算 | MAX_THINKING_TOKENS / 分档思考 | 项目级 env 硬顶 | references/static-context.md |

## 铁律（每条都有事故实证）

1. **先归因再动手**——改前记录：轮次数、单轮上下文体量、脚本 vs 推理耗时分解。不许愿式优化。
2. **L0 优先，白名单制**——静态上下文每轮都付费，裁 1k 静态 = 每轮省 1k × 全部轮次。裁剪用**白名单**（只留用到的，其余全归档）不用黑名单（逐挑不用的）——实证 skills 305→28，描述注入 17.5k→1.4k token；二验 ip-pipeline 81→15，25.8k→6.4k 字节（-75%，≈省 10~13k token/轮）。
3. **轮次数最小化**——启动批单条消息并行发齐（取数后台 + 读配置 + grep 小文件），禁串行探索、禁单独读 1 行输出文件。
4. **全文禁读，摘要优先**——420 行报告 ≈12k token/轮；骨架+摘要双文件 ≈5k token 覆盖推理所需。
5. **产物复用**——当日已跑过的扫描/报告（mtime <3h）直接复用补 delta，不盲目重跑。
6. **禁重复校验**——pipeline 内置的校验不单独重跑（省的是工具轮 + 推理轮）。
7. **可见性优先于输出 token**——Bash/Read 工具输出在终端会折叠收起，用户不可见 = 变相摘要。面向用户的内容必须模型文本直发；「cat 直出禁复述」仅限纯存档/机器消费场景。任何"工具输出替代模型文本"的优化，先验证终端实际渲染再推广（P7→P9 当日废除事故）。
8. **执行已文档化脚本不读源码**——用法以 skill 文档为准；读源码仅限改代码/排错/新脚本。
9. **工具产出即终点**——scan/报告已给的结论直接引用，不追源码、不重跑、零深挖。
10. **串行网络重试必配熔断**——第一个失败已含"网络不可达"全部信息（8 主题×2 重试白耗 186s→熔断后 14s）。
11. **全局层裁剪审计先行**——`~/.claude` 砍一处 = 所有项目一起没。先扫全部项目 transcript 聚合使用次数，零使用证据充分才砍；**项目级覆盖优先**（项目 settings.json 的 enabledPlugins:false 不动全局 = 零跨项目副作用）。方法见 references/static-context.md §9。

## 度量（优化前后对比）

每次优化必须留数字证据，方法见 **references/measurement.md**：

- 基线三件套：轮次数、单轮上下文（行数×~29 token 或 `wc -c`/4）、耗时分解（脚本 vs 推理）
- 工具：`rtk gain`（命令输出过滤节省）、ccusage/会话统计（总量）、日志时间戳分段（归因）
- 证据落点：commit message 写死数字（`13.3s→2.3s, -45%`），错题本/learnings 归档根因

## 使用流程

1. **诊断**：跑 references/measurement.md 的基线采集 → 定位大头在哪层（静态？轮次？读入？输出？）
2. **开方**：按上表选杠杆，L0 → L1 → L2 → L3 顺序动
3. **验证**：同路径重跑，对比前后数字，写入 commit/learnings
4. **防回潮**：能程序化的不靠记忆（hook 校验、settings.json env、熔断代码）

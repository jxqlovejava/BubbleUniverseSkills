# L0 静态上下文裁剪 — 操作手册

静态上下文 = 每轮 prefill 都付费的部分。裁剪一次，永久受益。以下全部有实战数字。

## 1. 项目级插件禁用（收益最大，最先做）

`.claude/settings.json`（项目级，可不入库）：

```json
{
  "enabledPlugins": {
    "superpowers@claude-plugins-official": false,
    "pm-toolkit@pm-skills": false,
    "...每个不用的插件都显式置 false": false
  }
}
```

- 实证：禁用 28 个插件（pm 全家桶/gsd/superpowers/context-mode 等），只留 1 个高频的。插件的 SessionStart 注入随之消失。二验：ip-pipeline 项目级禁 19 个（pm×9、superpowers、agent-skills、example-skills 等），预期 ~10k token/轮。
- **项目级覆盖优先于全局修改**：项目 settings.json 的 enabledPlugins:false 只影响本项目，全局配置不动 → 零跨项目副作用。要砍全局层先做使用审计（见 §9）。
- **下次会话才生效**，本会话无感——验证要开新会话。
- 判据：当前项目工作流用不到的整套域（如纯数据项目里的 pm/frontend/sales 域）全禁。

## 2. 全局技能归档（白名单制 + 归档安全）

**方法论：白名单 > 黑名单。** 第一轮挑"不用的"归档（265 个，黑名单思路）；第三轮翻转为白名单——只留当前工作流用到的（实证 28 个：项目 pipeline/搜索/提交/hook 依赖/OMC 核心），其余全归档。**skills 305→28，描述注入 17.5k→1.4k token**（-92%）。黑名单永远挑不干净，白名单一次到位。

```bash
mkdir -p ~/.claude/skills-backup/roundN-$(date +%F)
# 白名单外归档（安全版，见下方三规则）
```

**归档安全三规则（踩坑实证，2026-08-24）：**

1. **symlink 分开处理**：`for d in */` 循环变量带尾斜杠，BSD `mv "symlink/"` 会**解引用**——把链接指向的外部实体目录整体搬走，留下悬空链接（事故：89 个 symlink 的实体被从 .orchestra/semantica/gstack/ego 应用包搬空）。正确写法：
   ```bash
   for d in *; do
     [ -L "$d" ] && { mv "$d" backup/_symlinks/; continue; }  # 链接单独归档
     [ -d "$d" ] && mv "$d" backup/
   done
   ```
2. **归档前查 hooks**：带 `hooks/hooks.json` 或 `.claude-plugin/plugin.json` 的插件型 skill 被归档后，**已启动的存量会话内存中残留 hook 注册**，每次工具调用报错。归档前扫描豁免，或归档后立即重启会话：
   ```bash
   for l in 待归档/*; do t=$(readlink "$l" 2>/dev/null || echo "$l");
     [ -f "$t/hooks/hooks.json" -o -f "$t/.claude-plugin/plugin.json" ] && echo "HAS-HOOKS: $l"; done
   ```
3. **禁开 `2>/dev/null`**：批量移动失败必须可见，吞错误 = 第一轮发现不了搬空。
4. **zsh 不做变量分词**（2026-08-24 ip-pipeline 事故）：`for k in $keep` 把整串白名单当一个词 → 白名单全失效，81 个 skill 全被归档。**批量操作改用 python 脚本（推荐）**，或 zsh 数组/`${=var}`；且一律用**绝对路径**——会话 cwd 可能被 hook 重置，相对路径 mv 全失败。

- 可逆优先：`mv` 不归档删除，backup 目录放 README 写恢复命令。

## 3. Agents 裁剪

```bash
mv ~/.claude/agents/<name>.md ~/.claude/agents-backup/
```

- 实证：94→44（gsd-* ×30 / gan-* ×3 / 语言域 java/react/typescript / sales 域归档）。
- 注意 symlink：归档前检查 `ls -la` 是否符号链接，链接指向的实体要一起处理。

## 4. Rules 目录裁剪

- `~/.claude/rules/` 是**目录扫描加载**——移出即不进上下文，无需改任何配置。
- 实证：rules/common 裁到 3 个高频（coding-style/git-workflow/security），余归档 rules-backup。

## 5. CLAUDE.md / SKILL.md 瘦身

实证三轮：CLAUDE.md →256 行（-54%）→ **309→136 行（23.3k→10.9k 字符）**；SKILL.md 774→151 行（~10k token 参考材料移 `references/*.md`）。

四个手法（按收益排序）：

1. **大表/长协议外置**：完整枚举表（如 29 个思维模型）、长协议（信息验证协议）移到 `docs/*.md`，主文件只留指针 + 一句话核心（「模型库见 docs/x.md」）。
2. **删重复覆盖**：其他文件已覆盖的内容直接删（例：SKILL.md 已写的操作细则，CLAUDE.md 里的 12 步使用方式整节删除）——双份维护必漂移。
3. **压缩为结论**：多条细述规则压成一行核心 + 指向详文的链接（5 条铁律全文 → 一句核心 + 链接）。
4. **按需读取模式**：主文件写「调 X 前必读 references/x.md」，细节不进默认上下文。

配套：
- 消除双文件漂移：全局 skill 与仓库 skill 用 symlink 合一，单文件真相源。
- **stale 规则同步**：改过的决策要 grep 所有引用处同步（实证：HTML 渲染默认关闭 8/22 已决，CLAUDE.md/SKILL.md 两处残留旧表述，第三轮才修）。瘦身时顺带做一次全文一致性扫描。

## 6. MCP 工具 schema

- MCP server 的工具 schema 进每轮上下文，server 越多 schema 越厚。
- 判据：高价值留（如 codegraph 一次调用替代多次 grep+read，净省）；低频/付费的默认禁或按需开（实证：wind-mcp 仅 full-mode 才调）。
- 项目级 `.claude/settings.json` 可对保留的 MCP 配 `permissions.allow` 免确认，省交互轮。

## 7. 思考预算硬顶（L3）

```json
{ "env": { "MAX_THINKING_TOKENS": "3000" } }
```

- 项目级 settings.json 设 env，所有会话思考预算硬顶。
- 配套**分档思考纪律**：常规任务低档（复用已有结论直接组装），重大决策/不可逆操作全量推理。重大场景会话内临时放开。

## 8. Hook 注入审计

- SessionStart hook 的 stdout 进每轮上下文——检查 `~/.claude/settings.json` 和项目级 hooks，删掉不看的启动问候/统计输出。
- 保留的 hook（如格式校验 PostToolUse）本身是省 token 的：程序化强制替代模型记忆，防返工轮。

## 9. 全局层裁剪（~/.claude，影响所有项目）

全局砍一处 = 所有项目一起没 → **审计先行，零使用证据充分才砍**。

**跨项目使用审计**（2026-08-24 实证，369 个会话 / 近 30 天窗口）：python 扫 `~/.claude/projects/*/*.jsonl`，聚合 skill 调用、MCP 调用、插件触发次数，只输出聚合结论。

- **有使用 = 不可动**：superpowers 16×、code-review 11×、agentmemory MCP 37×/6 项目、codegraph 180×。
- **零使用砍掉**：全局插件 16 个、MCP 4 个（vox/figma/pencil/xiaohongshu-mcp）、agents 41→3。
- **行为注入类零调用 ≠ 未使用**：ponytail 这类模式 hook 是每轮行为注入不是 skill 调用，审计时单独标注，别误砍。

**备份纪律**（全部可逆）：

- 改前 `cp ~/.claude/settings.json{,.bak-$(date +%F)}`
- MCP 移除项导出 `~/.claude/mcp-disabled-$(date +%F).json`（恢复 = 合并回 mcpServers）
- agents/skills 一律 mv 到 backup 目录 + README 写恢复命令，禁删

**激进裁剪知情确认**：agents 只留 explore/tracer/writer 这类方案会断 OMC 等编排层的委派能力——明确告知后果、用户确认后再执行。

## 防回潮

- **生效时机分两类，别一刀切**：skill/agents/rules 归档**本会话实时生效**（系统注入实时重扫，可立即对比验证）；插件/MCP 禁用**下次会话才生效**（报预期值，新会话实测回填）。带 hooks 的 skill 恢复后需重启会话。
- 每季度复查一次：插件/agents/skills 会随安装重新膨胀。

---
name: topic-discovery
description: 跨平台选题探索/发现：采集小红书、B站、抖音、公众号、X、YouTube 的爆款与低粉破圈选题，统一入库 topic-library/选题库.xlsx（Excel，非 JSON），按 链接+规范化标题 去重，标注 未用/已用/已废弃 状态，并按 赛道+热度 推荐未用选题。触发词：选题探索、找选题、选题发现、推荐选题、选题入库、爆款选题、低粉爆款、跨平台选题、起号选题。
---

# 选题探索 / 发现（topic-discovery）

融合 `xhs-topic-scraper`（小红书采集入库）+ `viral-topic`（多平台路由）的跨平台选题库。

- 采集 → 统一入库 Excel（`topic-library/选题库.xlsx`，sheet「选题库」）
- 去重：链接精确去重 + 规范化标题去重（跨平台重复也只留一条）
- 状态：每条有 `status`（未用/已用/已废弃），默认未用；用掉的选题打「已用」，推荐自动排除
- 推荐：`赛道+热度`（过滤未用 + keyword + 按主指标/爆款分数排序）

库管理脚本：`.claude/skills/topic-discovery/scripts/topic_library.py`
各平台采集脚本：复用 `viral-topic` 的 `search_*_viral_topic.py` + 小红书 browser-act。

## 流程

### Step 1 · 归一化赛道

用户给一个赛道 → 拆成 3–8 个搜索关键词。默认「大众占卜」→ `塔罗,占卜,宇宙传讯,有缘人传讯,选一组,能量测试`。

### Step 2 · 小红书（推荐 ego-browser，不抢 Chrome）

**主路径（推荐）**：ego-browser（ego-lite）独立浏览器采集，agent 在自己 task space 操作，你正常用 Chrome/电脑不受影响。需 ego-lite 已装并登录过小红书（未登录则先在 ego-lite 里登录一次，之后复用）。关键词 URL 编码后填入。

```bash
# 边滚边采 6 屏，按 link 去重合并，输出 JSON
# ⚠ ego-browser 的 cliLog 走 stderr：输出文件用 2>，stdout 用 1>/dev/null 丢弃
ego-browser nodejs <<'EOF' 1>/dev/null 2>/tmp/xhs_ego.json
const task = await useOrCreateTaskSpace('xhs-collect')
await openOrReuseTab('https://www.xiaohongshu.com/search_result?keyword=<URL编码关键词>&source=web_search_result_notes', { wait: true, timeout: 30 })
const sleep = ms => new Promise(r => setTimeout(r, ms))
const all = []
const seen = new Set()
for (let i = 0; i < 6; i++) {
  const rows = await js(String.raw`(() => {
    const out=[]
    document.querySelectorAll('section.note-item').forEach(el => {
      const t=el.querySelector('.title')
      const au=el.querySelector('.author .name, .name')
      const like=el.querySelector('.like-wrapper .count, .count')
      const a=el.querySelector('a[href*="/explore/"]')
      out.push({title:t?t.innerText.trim():'', author:au?au.innerText.trim():'', likes:like?like.innerText.trim():'', link:a?a.href.split('?')[0]:''})
    })
    return out
  })()`)
  for (const r of rows) { if (!r.link || seen.has(r.link)) continue; seen.add(r.link); all.push(r) }
  await scrollBy(1800)
  await sleep(1500)
}
cliLog(JSON.stringify(all))
EOF
```

**备选（会抢 Chrome）**：browser-act chrome-direct 直接控制你正在用的 Chrome，会打断前台操作，仅当不介意时用（完整命令见原 `xhs-topic-scraper` skill：open → wait stable → 边滚边采 6 屏落 `/tmp/xhs_round_$i.json` → close）。

入库（`--llm-filter` 有 `DEEPSEEK_API_KEY` 时开，剔非赛道帖；**小红书默认自动过滤 <200 赞**，`--min-likes 0` 关闭或改阈值）：

```bash
python3 .claude/skills/topic-discovery/scripts/topic_library.py add /tmp/xhs_ego.json --keyword 大众占卜 --platform 小红书 [--llm-filter] [--min-likes 200]
```

### Step 3 · B站（免费，无需 key，必跑）

```bash
python3 .claude/skills/viral-topic/bilibili-viral-topic/scripts/search_bilibili_viral_topic.py \
  --topic "塔罗,占卜,宇宙传讯" --days 30 --max-followers 100000 --min-play 10000 --limit 50 --format json \
  | python3 .claude/skills/topic-discovery/scripts/topic_library.py add - --keyword 大众占卜
```

### Step 3.5 · 抖音（browser-act chrome-direct，需用户 Chrome 抖音已登录）

抖音 web 对 ego 纯净环境会降级到「抖音精选」精简版（无登录入口、搜索空），**只能**用 browser-act 控制用户 Chrome 采（采前确认用户 Chrome 空闲，采完 `session close`）。核心：打开 `https://www.douyin.com/search/<URL编码关键词>?type=video` → `wait stable` → **边滚边采** 6 屏，每屏 eval 采 `a[href*="/video/"]` 卡片（title/author/plays/link）→ 合并且 `add --platform 抖音`。

```bash
# 采集模板（eval 内 JS 从 /tmp/dy_round_$i.json 落盘，按需用启发式提取标题/@作者/播放量）
browser-act --session dy browser open direct_local_106477693767254045 "https://www.douyin.com/search/%E5%A1%94%E7%BD%97?type=video"
browser-act --session dy wait stable
browser-act --session dy eval "window.scrollTo(0,0)"
for i in 0 1 2 3 4 5; do
  browser-act --session dy eval "<提取 a[href*='/video/'] 卡片的 JS>" > /tmp/dy_round_$i.json
  browser-act --session dy scroll down --amount 2000; sleep 1.5
done
browser-act session close dy
# 合并去重 + 清理标题残渣（周前/天前/  # 等）后入库
python3 .claude/skills/topic-discovery/scripts/topic_library.py add /tmp/dy_round_*.json --keyword 大众占卜 --platform 抖音
```

### Step 4 · 公众号 / X / YouTube（仅当有 key，否则跳过并注明）

| 平台 | 所需环境变量 | 命令 |
|------|------------|------|
| 公众号 | `WECHAT_HOT_API_BASE`+`WECHAT_HOT_APP_ID`+`WECHAT_HOT_APP_SECRET`（或 `WECHAT_HOT_ACCESS_TOKEN`） | `python3 .claude/skills/viral-topic/wechat-viral-topic/scripts/search_wechat_viral_topic.py --category <类别> --days 7 --min-read 10000 --min-read-month-avg-ratio 2 --format json \| add -` |
| X | `TWITTERAPI_IO_KEY` 或 `TWITTER_API_KEY` | `python3 .claude/skills/viral-topic/x-viral-topic/scripts/search_x_viral_topic.py --topic "塔罗 OR 占卜" --days 7 --max-followers 50000 --min-engagement 100 --format json \| add -` |
| YouTube | `YOUTUBE_API_KEY` | `python3 .claude/skills/viral-topic/youtube-viral-topic/scripts/search_youtube_viral_topic.py --topic "tarot,manifestation,channelled message" --days 30 --min-views 10000 --format json \| add -` |

公众号先查 `viral-topic/wechat-viral-topic/references/categories.md` 有无匹配类别；无则跳过并注明。

### Step 5 · 推荐（赛道+热度，排除已用）

```bash
python3 .claude/skills/topic-discovery/scripts/topic_library.py recommend --keyword 大众占卜 -n 20
# 跨平台排序更可比：--sort breakout（爆款分数）；或 --random 随机抽
python3 .claude/skills/topic-discovery/scripts/topic_library.py recommend --keyword 大众占卜 -n 10 --sort breakout
```

### Step 6 · 用掉一个选题 → 标记「已用」（推荐自动排除）

```bash
python3 .claude/skills/topic-discovery/scripts/topic_library.py mark --match "<标题片段或链接>" --status 已用
python3 .claude/skills/topic-discovery/scripts/topic_library.py mark --match "<标题片段>" --status 已废弃   # 不合适的
```

### Step 7 · 查看 / 清理库

```bash
python3 .claude/skills/topic-discovery/scripts/topic_library.py list --status 未用 --limit 30
python3 .claude/skills/topic-discovery/scripts/topic_library.py list --keyword 大众占卜 --platform B站
# 删存量低赞选题（默认只删未用；--include-used 连已用/已废弃一起删）
python3 .claude/skills/topic-discovery/scripts/topic_library.py prune --min-likes 200 [--platform 小红书] [--include-used]
```

## 数据模型（选题库.xlsx）

12 列：`platform / scraped_at / keyword / title / author / metric / metric_num / link / breakout_score / evidence / status / note`
- metric = 人类可读（`1.1万赞`/`12.3万播放`/`8593阅读`），metric_num = 排序用数字（`1.1万`→11000）
- metric_num 仅平台内可比；跨平台排序用 breakout_score（`--sort breakout`）
- 小红书新增默认过滤 `<200` 赞（`add --min-likes` 调阈值，0 关闭），可 `--llm-filter` 经 DeepSeek 剔非赛道帖；剔除记录落 `topic-library/xhs-topics-rejected.jsonl`，下次自动跳过

## 坑（实测）

1. **列表虚拟化**：小红书必须每滚一屏采一屏再合并，一次性 querySelectorAll 再滚动会丢已滚走的卡片。
2. **ego-browser 的 cliLog 走 stderr**：采集输出文件用 `2>` 重定向，stdout 丢弃；task space（`xhs-collect`）跨轮复用，重复开页面无害。
3. **登录态**：小红书结果区 0 条 = ego-lite 未登录或被风控，先在 ego-lite 里登录一次小红书；ego 复用登录态不碰用户 Chrome。
4. **chrome-direct 备选抢占**：browser-act chrome-direct 直接控制用户正在用的 Chrome，会打断前台操作——因此主路径用 ego-browser，chrome-direct 仅应急。
5. **点赞格式混杂**（`8593`/`1.1万`/`2w+`）：`parse_num` 自动归一用于排序，入库保留原始串。
6. **B站限速**：脚本已内置 headers + 限速（防 HTTP 412），勿加并发。
7. **抖音只能用 chrome-direct**：抖音 web 对 ego 纯净环境降级「抖音精选」精简版（无登录、搜索空），必须控制用户 Chrome（需 Chrome 抖音已登录）。抖音标题常残留「周前/天前/小时前」和时间数字，采集后用正则清尾部残渣。
8. **Excel 写**：脚本每次 `load_workbook`→追加→`save`，不会覆盖旧数据；文件若被 Excel 打开，写会失败，先关闭。避免用 `delete_rows` 删行（openpyxl 会留孤立 link 幽灵行）——清理统一走 `prune`（重建工作簿）。
9. 原 `xhs-topics.jsonl` 为历史存档，新数据一律走 Excel；`migrate` 已把存量迁入（幂等）。

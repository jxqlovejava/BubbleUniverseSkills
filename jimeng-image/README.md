# jimeng-image 使用说明

即梦(jimeng.jianying.com) AI 生图：复用 ego-lite 浏览器登录态在页面上下文发 XHR 调内部 API，
`msToken`/`a_bogus` 签名由页面 SDK 自动注入，不干扰用户日常浏览器。
核心工作流（提示词心法、参考图反向解析四步、参数细节）见 [SKILL.md](./SKILL.md)，
本文件只讲安装、平台适配与 FAQ。

## 安装

1. **ego-lite 浏览器**：`~/.local/bin/ego-browser` 可用（`ego-browser nodejs` 启动），
   首次引导后在 ego-lite 里登录一次 jimeng.jianying.com（登录态持久保存在 ego profile）
2. **python3**，无额外必装依赖；大图参考图压缩需 `Pillow`（一般环境已有）

## 使用

```bash
# 文生图（默认：图片5.0 Lite / 3:4 / 2K / 3张）
python3 scripts/agent_generate.py "提示词" [--out ./jimeng_output]

# 参考图 + 文案（默认不拆解，直接基于提示词生成）
python3 scripts/agent_generate.py "换成新的不同人物" --ref ./ref.png

# 需要精确还原参考图关键质感时 → 显式 --describe（先识图→硬约束→生成）
python3 scripts/agent_generate.py "参考这张图生成新图，必须严格保留[关键特征]" --ref ./ref.png --describe

# 精确控制（模型/strength/多参考图）才用 i2i
python3 scripts/jimeng_generate.py "提示词" --ref ./ref.png --strength 0.7

# 参考图分析
python3 scripts/analyze_reference.py <参考图> [--cells 2x2] [--json]   # 程序化风格矩阵
python3 scripts/describe_reference.py <参考图>                          # 即梦识图 5 维语义
```

stdout 逐行 JSON：`ref_uploaded` → `submitted` → `{"status":"ok","images":[...]}` 或 `{"status":"error",...}`。

**写提示词前必读** `prompt-presets.md`（怎么写：心法/预设库/纠错表）和 `prompt-examples.md`
（好样例：30 条示例 + 共性规律）——**两个都要翻**，只翻 presets 真人像会缺肤质/负向/风格帧料、AI 味重。

## 平台适配

- **macOS**：生成后复检走 Vision OCR；其他平台脚本本身可跑（python3 + ego-browser），复检需自行替换
- **Agent 布局**：`.claude/skills/jimeng-image/` 与平铺工作区均支持，脚本路径按实际布局取

## FAQ

**Q：`no_webid` 错误？**
ego 里即梦登录失效——在 ego-lite 中重新登录 jimeng.jianying.com。

**Q：generate 阶段 `ret: "3018"`？**
签名/权限问题，通常是登录失效或即梦更新了参数结构（重新抓包比对）。

**Q：Agent 生成报 `ret: "7057" err stream receive`？**
服务端 SSE 流瞬时抖动，脚本已内建自动重试（最多 3 次），仍失败再重跑一次。

**Q：积分不足？**
脚本检测到 credit 错误会自动降级到图片 4.7 重试一次；仍不足才报错。5.0 Lite 约 2-3 积分/张，i2i 5.0 Pro 约 8-11 积分/张，**默认一次 3 张**，调用前确认张数。

**Q：参考图上传超时？**
即梦前端改版后上传走 drop 事件注入（agent_generate.py 已适配）；jimeng_generate.py 若同样超时需同样改造（见 SKILL.md「前提与故障处理」）。

**Q：图片 URL 过期？**
byteimg 签名链接约 2 小时过期，脚本已即时下载到本地，直接用 `images` 返回的本地路径。

**Q：宫格版式复刻要点？**
一次 `--count N` 出 N 张（别逐张出），prompt 控制张数版式（Agent 模式稳定）；**不要列具体物象**，会触发版式漂移。

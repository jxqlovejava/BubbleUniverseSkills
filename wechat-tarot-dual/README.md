# wechat-tarot-dual 使用说明

微信聊天×塔罗气泡解读 双拼抖音图文帖模板：一张图 = 左半微信聊天截图 + 右半塔罗气泡App解读截图（1560×1688）。
核心工作流定义（生成管线、内容铁律、版面规范、换素材）见 [SKILL.md](./SKILL.md)，本文件只讲安装、平台适配与 FAQ。

## 安装

```bash
# 1. Python 渲染依赖
pip3 install playwright && python3 -m playwright install chromium

# 2. LLM key（聊天剧本 + 真实解读，DeepSeek 或任意 OpenAI 兼容接口）
export DEEPSEEK_API_KEY=sk-...        # 或 LLM_API_KEY，配 LLM_API_BASE / LLM_MODEL

# 3.（可选）聊天背景自动生成：装 ego-browser 到 ~/.local/bin/ 并用它登录一次即梦
#    没有也能跑：自动回退 skill 默认石阶背景，管线不中断
```

**同级依赖**：tarot-mass-divination skill 必须在同工作区（LLM 管线 / interpret.md / 牌阵数据 / OCR 校验脚本），
脚本自动识别 `.claude/skills/` 布局和 vira 平铺布局两种目录结构。

**平台**：macOS（渲染后 OCR 校验走 Vision 框架；非 macOS 可出图但无自动校验）。

## 使用

```bash
python3 scripts/gen_content.py "暧昧期想确认TA心意"        # 一条命令出全套
python3 scripts/gen_content.py "主题" --seed 7            # 抽牌可复现
python3 scripts/gen_content.py "主题" --skip-bg            # 不生背景，用默认石阶图
python3 scripts/gen_content.py "主题" --out 我的目录        # 自定义输出目录
python3 scripts/gen_content.py "主题" --skip-render        # 只生成内容不渲染
```

输出到 `微信聊天塔罗素材/<月.日>-<主题>/`：顶层只有成品 `微信聊天塔罗_双拼.png` + `发布文案.txt`；
中间产物（content.json、背景图、备选 raw）收在隐藏目录 `.src/`，重渲染/换素材都操作那里。

改了 content.json 后单独重渲染：`python3 scripts/render_wechat_tarot.py <实例目录>/.src/content.json`

## FAQ

**Q：聊天背景/头像能换吗？**
头像池 `assets/avatars/`（扩池即梦出图后命名 `pair_NN_me/ta.png` 入池）、昵称池 `assets/nicknames.txt`（一行一个）、
贴纸/兜底背景在 `assets/`。单实例覆盖：实例 `.src/assets/` 放同名文件优先。全量换默认见 SKILL.md「换素材」。

**Q：即梦生图失败会挂吗？**
不会。生背景失败/缺提示词/`--skip-bg` 时回退默认石阶图，管线不中断；备选图在实例 `.src/assets/raw/` 可同名覆盖。

**Q：为什么解读/聊天内容不能手改？**
cards/interpretation 走 interpret.md 真实管线回填，手写会被覆盖；聊天剧本由 LLM 按锁定的结构生成
（问题与聊天记录强关联、对话零引号、每条 ≤14 字）。要改就改 `prompts/chat_script.md` 后重跑。

**Q：OCR 校验报错？**
校验脚本在 tarot-mass-divination/scripts/ocr_text.sh，需要 macOS Vision；属提示性检查，出图不受影响，按报错文本比对渲染结果定位。

## 依赖速查

| 依赖 | 必须？ | 说明 |
|---|---|---|
| tarot-mass-divination skill | ✅ | LLM 管线 / interpret.md / 牌阵数据 |
| `LLM_API_KEY` 或 `DEEPSEEK_API_KEY` | ✅ | DeepSeek 调用 |
| Playwright chromium | ✅ | 渲染 |
| jimeng-image skill（ego-lite 登录即梦） | 背景生成需要 | 缺失自动回退默认背景 |
| macOS Vision OCR | 否 | 渲染后自动文字校验 |

#!/usr/bin/env python3
"""正文开头的 AI 软植入句：一句话自然带出塔罗气泡。

2026-09-16 用户拍板，抖音图文/视频的发布文案统一结构：

    标题行（钩子）
    软植入句 ← 正文开头，单独一行，主题相关、不像广告
    正文 / 结尾行
    话题标签

本模块是**全项目唯一实现**（原在 抖音录屏贴纸模板/auto_record.py 内联）。各生成脚本
（情侣四宫格、微信聊天双拼、塔罗解读截图、自然照片产品截图、抖音录屏贴纸）import 它，
不要各写一份——池子/校验规则在某个模板里改了、别的没改，就是下一轮返工。

铁律：
- 第一人称口语，像真实用户随手分享，必须和话题强相关、自然融进去
- 不用「」引号；禁词 塔罗/占卜/算命/卜卦 —— **唯一豁免是品牌名「塔罗气泡」**
- 禁硬广口吻（下载/等你/快来/App），无 CTA
- LLM 不可用或校验不过 → 回退固定池，流水线不断
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Callable

BRAND = "塔罗气泡"
BANNED_WORDS = ("塔罗", "占卜", "算命", "卜卦")  # BRAND 内的“塔罗”不算命中
HARD_AD_WORDS = ("下载", "等你", "快来", "App")
MAX_LEN = 40  # 含标点
SYSTEM_PROMPT = (
    "你是抖音情感号写手。为塔罗气泡App写一篇笔记的开头第一句：软植入。"
    "要求：第一人称口语，像真实用户随手分享；必须和给定话题强相关、自然融进去，"
    "不要泛泛而谈；不超过30字；不要用「」引号；禁止出现 占卜/算命/卜卦；"
    "品牌名只准写 塔罗气泡；禁止硬广口吻（不要出现 下载/等你/快来/App）。"
    "只输出这一句文案，不要任何解释。"
)
# 固定池兜底：无 API key / 调用失败 / 校验不过时用。按话题取模轮换，可复现。
FALLBACK_POOL = (
    "关于{t}，我在塔罗气泡问了个明白。",
    "{t}，这个问题我拿去问了塔罗气泡。",
    "我在塔罗气泡看到了答案：{t}。",
    "憋在心里很久的事，我在塔罗气泡问了出来：{t}。",
)


def clean_topic(topic: str) -> str:
    """话题句尾标点去掉，免得池子拼出「关于他喜欢我吗？，我在…」这种病句。"""
    return topic.strip().rstrip("？?。.！!，,")


def banned_text(text: str) -> str | None:
    """命中平台高敏词就返回该词，否则 None。品牌名内的「塔罗」豁免。"""
    body = text.replace(BRAND, "")
    return next((w for w in BANNED_WORDS if w in body), None)


def is_valid(line: str) -> bool:
    """软植入句质检：必须带品牌名、不超字、无引号、无禁词、无硬广词。"""
    return (
        BRAND in line
        and len(line) <= MAX_LEN
        and "「" not in line
        and "」" not in line
        and banned_text(line) is None
        and not any(w in line for w in HARD_AD_WORDS)
    )


def fallback_opener(topic: str) -> str:
    """固定池兜底（无 LLM 或校验不过）。"""
    t = clean_topic(topic)
    if not t:  # 话题为空时别拼出「关于，我在…」这种病句
        return "憋在心里很久的事，我在塔罗气泡问了出来。"
    return FALLBACK_POOL[sum(map(ord, t)) % len(FALLBACK_POOL)].replace("{t}", t)


def _http_llm_call(system: str, user: str, temperature: float = 1.0, max_tokens: int = 100) -> str:
    """内置 DeepSeek 兼容调用（录屏模板等零依赖场景用）。缺 key 直接抛，由上层回退。"""
    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY")
    if not key:
        raise RuntimeError("缺少 DEEPSEEK_API_KEY / LLM_API_KEY")
    base = os.environ.get("LLM_API_BASE", "https://api.deepseek.com").rstrip("/")
    model = os.environ.get("LLM_MODEL", "deepseek-chat")
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": temperature, "max_tokens": max_tokens, "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/chat/completions", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]


def gen_opener(topic: str, llm_call: Callable[..., str] | None = None) -> str:
    """按话题生成一句正文开头的软植入。

    llm_call(system, user, temperature=, max_tokens=) -> str；不传则用内置 HTTP 调用
    （各模板可传自己的 gmd.llm_call，复用它的重试与缓存日志）。
    校验不过或调用失败一律回退固定池，保证流水线不断。
    """
    user = f"话题：{clean_topic(topic)}"
    try:
        raw = (llm_call or _http_llm_call)(SYSTEM_PROMPT, user, temperature=1.0, max_tokens=100)
        line = raw.strip().strip('"').strip()
    except Exception as e:  # noqa: BLE001 - 任何异常都不能断流水线
        print(f"[opener] AI 软植入失败（{e}），回退固定池")
        return fallback_opener(topic)
    if is_valid(line):
        return line
    print(f"[opener] AI 软植入校验不过（{line}），回退固定池")
    return fallback_opener(topic)


def insert_opener(caption: str, opener_line: str) -> str:
    """把软植入句放到正文开头（用户 2026-09-16 拍板：标题行之后单独一行）。

    caption 首行是钩子标题（短句、不以句末标点收尾）时插在它后面；整段都是正文时
    放最前面。两种情况软植入句都单独成行，不跟正文挤一行。"""
    lines = caption.split("\n")
    first = lines[0].strip()
    is_hook = len(first) <= 30 and not first.endswith(("。", "！", "？", ".", "!", "?"))
    if is_hook:
        return "\n".join([first, opener_line, *lines[1:]])
    return "\n".join([opener_line, *lines])


if __name__ == "__main__":
    import sys

    topic = sys.argv[1] if len(sys.argv) > 1 else "他对我是不是真心的？"
    print("固定池：", fallback_opener(topic))
    line = gen_opener(topic)
    assert is_valid(line), f"软植入句不合格：{line}"
    print("最终：  ", line)

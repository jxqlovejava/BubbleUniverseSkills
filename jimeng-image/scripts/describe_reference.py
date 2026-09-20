#!/usr/bin/env python3
"""即梦识图：调 Agent 模式描述参考图的构图/光照/视角/元素密度/氛围。

用法:
  python3 describe_reference.py <参考图路径>

输出: stdout 单行 JSON。成功: {"status":"ok","description":"分点描述文字"}
description 可直接拼进 jimeng_generate.py 的 prompt，实现「构图/光照/视角对齐但换主体」。
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

EGO = str(Path.home() / ".local" / "bin" / "ego-browser")
JS = Path(__file__).parent / "describe_reference.js"


def extract(sse: str) -> tuple:
    events = re.findall(r"event:(\w+)\ndata:(.*?)(?=\n\n|\nid:)", sse, re.S)
    reasoning = ""
    answer = ""
    for ev, data in events:
        try:
            d = json.loads(data)
        except Exception:
            continue
        if ev == "delta":
            path = d.get("path", "")
            if path == "/message/content/reasoning_content":
                reasoning += d.get("value", "")
            elif path.endswith("content_parts/0/text"):
                answer += d.get("value", "")
        elif ev == "message":
            cp = (d.get("content") or {}).get("content_parts") or []
            for part in cp:
                if part.get("text"):
                    answer += part["text"]
    return reasoning, answer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--task-space", default="jimeng image generation",
                    help="ego task space 名（并行识图时每个进程用不同名）")
    args = ap.parse_args()
    p = Path(args.image).resolve()
    if not p.exists():
        print(json.dumps({"status": "error", "errmsg": f"参考图不存在: {p}"}, ensure_ascii=False))
        sys.exit(1)

    env = dict(os.environ)
    env["REF_PATH"] = str(p)
    js_code = (JS.read_text()
               .replace("__REF_PATH__", json.dumps(str(p)))
               .replace("__TASK_SPACE__", json.dumps(args.task_space, ensure_ascii=False)))
    proc = subprocess.run([EGO, "nodejs"], input=js_code,
                          capture_output=True, text=True, timeout=200, env=env)
    out = proc.stdout + proc.stderr
    m = re.search(r"^SSE_FULL:(.*)$", out, re.M)
    if not m:
        print(json.dumps({"status": "error", "stage": "runtime",
                          "errmsg": out[-500:]}, ensure_ascii=False))
        sys.exit(1)
    reasoning, answer = extract(json.loads(m.group(1)))
    desc = answer or reasoning
    print(json.dumps({"status": "ok", "description": desc, "reasoning": reasoning},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()

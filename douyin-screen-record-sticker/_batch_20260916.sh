#!/bin/bash
# 剩余 9 组带首图录屏帖子 2026-09-16（第 1 组 最近会有人向我表白吗 已验证完成）
cd "$(dirname "$0")"
LOG="out/_batch-20260916.log"
pairs=(
  "我暗恋的人喜欢我吗|xinshi"
  "我该不该主动找TA|caita"
  "今年年底前我能脱单吗|buwen"
  "我的桃花什么时候来|pianbuguo"
  "我什么时候能升职加薪|cangbuzhu"
  "我的副业能做起来吗|zhuangding"
  "最近谁在偷偷关注我|sahuang"
  "我和最好的朋友会疏远吗|zuishang"
  "今年我最大的坎是什么|yingcheng"
)
for p in "${pairs[@]}"; do
  theme="${p%%|*}"; copy="${p##*|}"
  echo "BATCH_START $theme ($copy)" | tee -a "$LOG"
  python3 auto_record.py "$theme" --copy "$copy" --cover 2>&1 | tail -5 | tee -a "$LOG"
  echo "BATCH_EXIT $theme code=${PIPESTATUS[0]}" | tee -a "$LOG"
  sleep 10
done
echo "BATCH_ALL_DONE" | tee -a "$LOG"

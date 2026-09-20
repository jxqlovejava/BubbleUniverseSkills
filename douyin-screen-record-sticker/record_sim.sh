#!/bin/bash
# 模拟器录屏助手：boot 模拟器 → 提示走查清单 → 录制 → 回车停止
# 用法：./record_sim.sh            （默认 iPhone 16 Pro Max）
#       SIM="iPhone 16" ./record_sim.sh
set -euo pipefail

SIM="${SIM:-iPhone 16 Pro Max}"
BASE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$BASE/raw"

xcrun simctl boot "$SIM" 2>/dev/null || true
open -a Simulator
echo ">>> 等待模拟器就绪..."
xcrun simctl bootstatus booted -b

cat <<'EOF'

走查清单（录屏时点稳一点，每屏停 1-2 秒）：
  1. 首页 → 开始占卜
  2. 输入问题（未登录会走短信验证码登录）
  3. 选牌阵 → 开始抽牌
  4. 洗牌页稍停（洗牌动画完整放一遍）→ 结束洗牌
  5. 抽牌页逐张点选
  6. 解读页缓慢滑动展示全文
  ※ 账号需有剩余解读次数，否则解读页弹订阅

EOF

TS=$(date +%Y%m%d-%H%M%S)
RAW="$BASE/raw/$TS.mov"
echo ">>> 开始录制 → $RAW"
echo ">>> 走完流程后回到这里按【回车】停止"
xcrun simctl io booted recordVideo --codec=h264 "$RAW" &
PID=$!
read -r
kill -INT "$PID" 2>/dev/null || true
wait "$PID" 2>/dev/null || true
echo "[done] $RAW"
echo "下一步：python3 gen_video.py $RAW"

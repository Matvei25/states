#!/bin/bash
# tick.sh — ежедневный тик Юсиксландии 🫠 (вызывается из cron 12:30)
# 1) экономика: зарплаты + налоги
# 2) коммит в git мира (~/states)
set -u

STATE_DIR="/home/yusmatvei25/states/юсиксландия"
WORLD_DIR="/home/yusmatvei25/states"
LOG="$STATE_DIR/tick.log"

{
  echo "=== $(date '+%Y-%m-%d %H:%M') ==="
  /usr/bin/python3 "$STATE_DIR/economy.py" tick
} >> "$LOG" 2>&1

cd "$WORLD_DIR" || exit 1
if ! git diff --quiet || ! git diff --cached --quiet; then
  git add -A
  git commit -m "🫠 Юсиксландия: ежедневный тик $(date '+%Y-%m-%d %H:%M') — экономика" >> "$LOG" 2>&1
fi

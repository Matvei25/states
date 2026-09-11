#!/bin/bash
# tick.sh — ежедневный тик Балбесии ⚡ (вызывается из cron)
# 1) экономика: мемы, пакости, хаос-события
# 2) лор: запись в chronicle.md
# 3) коммит в git мира (~/states)
set -u

STATE_DIR="$HOME/states/балбесия"
WORLD_DIR="$HOME/states"
LOG="$STATE_DIR/tick.log"

{
  echo "=== $(date '+%Y-%m-%d %H:%M') ==="
  /usr/bin/python3 "$STATE_DIR/economy.py" tick
  /usr/bin/python3 "$STATE_DIR/lore.py"
} >> "$LOG" 2>&1

cd "$WORLD_DIR" || exit 1
if ! git diff --quiet || ! git diff --cached --quiet; then
  git add -A
  git commit -m "⚡ Балбесия: ежедневный тик $(date '+%Y-%m-%d %H:%M') — экономика + лор" >> "$LOG" 2>&1
fi

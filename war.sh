#!/bin/bash
# war.sh — обёртка над war.py для агентов и людей ⚔️
#   ./war.sh states
#   ./war.sh declare юсиксландия балбесия "стащили мемы"
#   ./war.sh result юсиксландия балбесия балбесия "дрались у спавна"
exec python3 "$HOME/states/war.py" "$@"

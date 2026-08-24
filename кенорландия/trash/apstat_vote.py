#!/usr/bin/env python3
"""Опрос апатридов: к какому государству присоединиться. БЕЗ воздержания."""
import re, sys, json, time, random
import urllib.request, datetime
from pathlib import Path

BASE = Path.home() / "states"
PEOPLE = BASE / "people.json"
POLLS = BASE / "юсиксландия" / "polls.md"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "minicpm-v4.6"

def ask_ollama(system, user, timeout=180):
    prompt = f"{system}\n\nВопрос: {user}\n\nОтвечай строго на русском, одной строкой, в формате: Ответ: <вариант>"
    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0.9, "num_predict": 100}}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode()).get("response", "")
    except Exception as e:
        print(f"    ⚠️  ollama: {e}")
        return None

def parse_vote(text, options):
    if not text:
        return None
    m = re.search(r"Ответ\s*[:：]\s*(.+)", text, re.I | re.DOTALL)
    cand = (m.group(1) if m else text).strip().strip(".,!?»\"")
    for o in options:
        if cand.lower() == o.lower() or o.lower() in cand.lower() or cand.lower() in o.lower():
            return o
    return None

people = json.loads(PEOPLE.read_text(encoding="utf-8"))
apat = [p for p in people if p.get("state") == "none"]
if not apat:
    print("нет апатридов"); sys.exit(1)

question = "Ты никому не принадлежишь. К какому государству присоединишься?"
options = ["Юсиксландия", "Кенорландия", "Балбесия"]
poll_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
print(f"🗳  ОПРОС АПАТРИДОВ: «{question}»")
print(f"    варианты: {', '.join(options)} · апатридов: {len(apat)} (воздержаться НЕЛЬЗЯ)")
results = {o: 0 for o in options}
log = []

for p in apat:
    name = p["name"]
    system = (f"Ты — {name}, {p['age']} лет, работаешь {p['job']}. Характер: {p['personality']}. "
              f"Интересы: {', '.join(p['interests'])}. Ты АПАТРИД — у тебя нет гражданства, и тебе нужно "
              f"выбрать государство. Голосуй исходя из своего характера и интересов. "
              f"Ты ОБЯЗАН выбрать одно из государств — воздержаться НЕЛЬЗЯ.")
    user = f"{question}\nВарианты: {', '.join(options)}"
    vote = None
    for attempt in range(2):
        print(f"  🗳  {name} ({p['job']}) думает...", end=" ", flush=True)
        text = ask_ollama(system, user)
        vote = parse_vote(text, options)
        if vote:
            break
        if attempt == 0:
            print("(неопределённо, переспрашиваю строже)", end=" ", flush=True)
            user += "\nЭто обязательно! Просто напиши «Ответ: <одно из государств>»."
    if not vote:
        # гарантия без воздержания: первый упомянутый вариант или случайный
        text = text or ""
        vote = next((o for o in options if o.lower() in text.lower()), None) or random.choice(options)
        print(f"→ принудительно: {vote} (ответ модели не распознан)")
    else:
        print(f"→ {vote}")
    results[vote] += 1
    p["voted"] = p.get("voted", []) + [poll_id]
    log.append(f"{name}→{vote}")
    time.sleep(0.3)

PEOPLE.write_text(json.dumps(people, ensure_ascii=False, indent=2), encoding="utf-8")

header = f"\n## {datetime.datetime.now():%Y-%m-%d %H:%M} — «{question}» (апатриды, без воздержания)\n"
table = ["| Вариант | Голоса |", "|---|---|"]
for o, c in sorted(results.items(), key=lambda kv: -kv[1]):
    table.append(f"| {o} | {c} {'█'*c} |")
with POLLS.open("a", encoding="utf-8") as f:
    f.write(header + "\n".join(table) + f"\n\nГолосовали: {', '.join(log)}\n\n")

print("\n━━━ РЕЗУЛЬТАТЫ ━━━")
for o, c in sorted(results.items(), key=lambda kv: -kv[1]):
    print(f"  {o}: {c}")
print(f"итог: апатриды идут в «{max(results, key=results.get)}» 🎉")

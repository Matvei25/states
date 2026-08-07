#!/usr/bin/env python3
"""
vote.py — демократия с нейрогражданами 🗳🤖
Граждане из ~/states/people.json. Каждый голосует через локальную Ollama.
Когда модель пишет «Ответ: <кандидат>» — голос засчитывается.

запуск: python3 vote.py <вопрос> <вариант1> [вариант2 ...]
        python3 vote.py results   — результаты последних голосований
        python3 vote.py people    — список граждан

опции:  --model <имя>   — модель Ollama (по умолчанию из POLL_MODEL или minicpm-v4.6)
"""
import re
import sys
import json
import time
import urllib.request
import datetime
from pathlib import Path

BASE = Path(__file__).parent
PEOPLE = BASE.parent / "people.json"
POLLS = BASE / "polls.md"
OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "minicpm-v4.6"


def load_people():
    if PEOPLE.exists():
        return json.loads(PEOPLE.read_text(encoding="utf-8"))
    return []


def save_people(people):
    PEOPLE.write_text(json.dumps(people, ensure_ascii=False, indent=2), encoding="utf-8")


def ask_ollama(model, system, user, timeout=180):
    """Спрашивает Ollama. Возвращает текст ответа или None."""
    prompt = f"{system}\n\nВопрос: {user}\n\nОтвечай строго на русском языке, кратко, одной строкой. Формат: Ответ: <вариант>"
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.9, "num_predict": 150},
    }).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "")
    except Exception as e:
        print(f"    ⚠️  ollama ошибка: {e}")
        return None


def parse_vote(text, options):
    """Ищет «Ответ: X» и сверяет с вариантами. Возвращает вариант или None."""
    if not text:
        return None
    m = re.search(r"Ответ\s*[:：]\s*(.+)", text, re.IGNORECASE | re.DOTALL)
    candidate = (m.group(1) if m else text).strip().strip(".,!?»\"")
    # точное совпадение (без учёта регистра)
    for opt in options:
        if candidate.lower() == opt.lower():
            return opt
    # вариант входит в ответ
    for opt in options:
        if opt.lower() in candidate.lower():
            return opt
    # кандидат входит в вариант (напр. «Партия Мемов» vs «за Партию Мемов»)
    for opt in options:
        if candidate.lower() in opt.lower():
            return opt
    return None


def cmd_vote(model, question, options):
    people = load_people()
    if not people:
        print("❌ население пусто. сначала: python3 gen.py people <n>")
        return
    poll_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"🗳  РЕФЕРЕНДУМ: «{question}»")
    print(f"    варианты: {', '.join(options)} · электорат: {len(people)}")
    results = {opt: 0 for opt in options}
    results["воздержались"] = 0
    votes_log = []

    for p in people:
        if poll_id in p.get("voted", []):
            continue
        name = p["name"]
        system = (f"Ты — {name}, {p['age']} лет, работаешь {p['job']}. "
                  f"Характер: {p['personality']}. Интересы: {', '.join(p['interests'])}. "
                  f"Ты гражданин Юсиксландии-на-Морозовке, у тебя есть право голоса. "
                  f"Голосуй ИСХОДЯ ИЗ СВОЕГО ХАРАКТЕРА и интересов, не как все. "
                  f"Твоё мнение может отличаться от других — это нормально.")
        user = f"{question}\nВарианты: {', '.join(options)}\nКого/что выбираешь?"
        print(f"  🗳  {name} ({p['job']}) думает...", end=" ", flush=True)
        text = ask_ollama(model, system, user)
        vote = parse_vote(text, options)
        if vote:
            results[vote] += 1
            p.setdefault("voted", []).append(poll_id)
            print(f"→ {vote}")
        else:
            results["воздержались"] += 1
            print(f"→ воздержался ({text[:60]!r})" if text else "→ воздержался (нет ответа)")
        votes_log.append((name, vote or "воздержался"))
        time.sleep(0.3)  # не дёргать ollama очередью

    save_people(people)

    # таблица в polls.md
    header = f"\n## {datetime.datetime.now():%Y-%m-%d %H:%M} — «{question}»\n"
    table = ["| Вариант | Голоса |", "|---|---|"]
    for opt, cnt in sorted(results.items(), key=lambda kv: -kv[1]):
        bar = "█" * cnt
        table.append(f"| {opt} | {cnt} {bar} |")
    with POLLS.open("a", encoding="utf-8") as f:
        f.write(header + "\n".join(table) + "\n")
        f.write("\nГолосовали: " + ", ".join(f"{n}→{v}" for n, v in votes_log) + "\n\n")

    print("\n━━━ РЕЗУЛЬТАТЫ ━━━")
    winner = max(results, key=results.get)
    for opt, cnt in sorted(results.items(), key=lambda kv: -kv[1]):
        print(f"  {opt}: {cnt}  {'👑' if cnt == results[winner] and cnt > 0 else ''}")
    print(f"итог: побеждает «{winner}» 🎉")


def cmd_results():
    if POLLS.exists():
        print(POLLS.read_text(encoding="utf-8"))
    else:
        print("(голосований ещё не было)")


def cmd_people_list():
    people = load_people()
    if not people:
        print("(население пусто — python3 gen.py people <n>)")
        return
    print(f"👥 НАСЕЛЕНИЕ МИРА: {len(people)}")
    for p in people:
        print(f"  • {p['name']} ({p['age']}, {p['job']}): {p['personality']} — {p['party']}")


def main():
    args = sys.argv[1:]
    model = DEFAULT_MODEL
    if "--model" in args:
        i = args.index("--model")
        model = args[i + 1]
        del args[i:i + 2]
    if not args:
        print(__doc__)
    elif args[0] == "results":
        cmd_results()
    elif args[0] == "people":
        cmd_people_list()
    elif len(args) >= 2:
        cmd_vote(model, args[0], args[1:])
    else:
        print("использование: vote.py <вопрос> <вариант1> [вариант2 ...]")


if __name__ == "__main__":
    main()

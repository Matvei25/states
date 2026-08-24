#!/usr/bin/env python3
"""Пачтер: валюта из env (CURRENCY) + граждане с полем state. Применяется к юсиксландия и кенорландия."""
from pathlib import Path

DIRS = [Path.home() / "states" / "юсиксландия", Path.home() / "states" / "кенорландия"]

# ---------- economy.py ----------
ECO = [
    ('print(f"☀️  день {day}: зарплаты выплачены, налогов собрано {total_tax} JLY")',
     'print(f"☀️  день {day}: зарплаты выплачены, налогов собрано {total_tax} {env.get(\'CURRENCY\', \'JLY\')}")'),
    ('log(f"день {day}: {name} получил {SALARY} жёлек, налог {tax}")',
     'log(f"день {day}: {name} получил {SALARY} {env.get(\'CURRENCY\', \'JLY\')}, налог {tax}")'),
    ('print(f"казна:      {env.get(\'TREASURY_JLY\', 0)} JLY")',
     'print(f"казна:      {env.get(\'TREASURY_JLY\', 0)} {env.get(\'CURRENCY\', \'JLY\')}")'),
    ('print(f"налоги всего: {env.get(\'TOTAL_TAXES\', 0)} JLY")',
     'print(f"налоги всего: {env.get(\'TOTAL_TAXES\', 0)} {env.get(\'CURRENCY\', \'JLY\')}")'),
    ('print(f"кошелёк {name}: {get_wallet(env, name)} JLY")',
     'print(f"кошелёк {name}: {get_wallet(env, name)} {env.get(\'CURRENCY\', \'JLY\')}")'),
    ('print(f"❌ {who} банкрот: на счету {w} JLY")',
     'print(f"❌ {who} банкрот: на счету {w} {env.get(\'CURRENCY\', \'JLY\')}")'),
    ('log(f"{who} → казна: {amount} JLY ({reason})")',
     'log(f"{who} → казна: {amount} {env.get(\'CURRENCY\', \'JLY\')} ({reason})")'),
    ('print(f"💸 {who} заплатил в казну {amount} JLY ({reason})")',
     'print(f"💸 {who} заплатил в казну {amount} {env.get(\'CURRENCY\', \'JLY\')} ({reason})")'),
    ('log(f"{who} → {to}: {amount} JLY ({reason})")',
     'log(f"{who} → {to}: {amount} {env.get(\'CURRENCY\', \'JLY\')} ({reason})")'),
    ('print(f"💸 {who} → {to}: {amount} JLY ({reason})")',
     'print(f"💸 {who} → {to}: {amount} {env.get(\'CURRENCY\', \'JLY\')} ({reason})")'),
]

# ---------- gen.py ----------
GEN = [
    ('            "party": random.choice(["Партия Мемов", "Партия Сна", "беспартийный", "беспартийный", "беспартийный"]),\n            "voted": [],',
     '            "party": random.choice(["Партия Мемов", "Партия Сна", "беспартийный", "беспартийный", "беспартийный"]),\n            "state": BASE.name,\n            "voted": [],'),
]

# ---------- vote.py ----------
VOTE = [
    ('    people = load_people()\n    if not people:\n        print("❌ население пусто. сначала: python3 gen.py people <n>")\n        return',
     '    people = load_people()\n    mine = [p for p in people if p.get("state", "юсиксландия") == BASE.name]\n    if not mine:\n        print(f"❌ в {BASE.name} нет граждан. сначала: python3 gen.py people <n>")\n        return'),
    ('    print(f"    варианты: {\', \'.join(options)} · электорат: {len(people)}")',
     '    print(f"    варианты: {\', \'.join(options)} · электорат: {len(mine)}")'),
    ('    for p in people:\n        if poll_id in p.get("voted", []):\n            continue',
     '    for p in mine:\n        if poll_id in p.get("voted", []):\n            continue'),
    ('    people = load_people()\n    if not people:\n        print("(население пусто — python3 gen.py people <n>)")\n        return\n    print(f"👥 НАСЕЛЕНИЕ МИРА: {len(people)}")\n    for p in people:',
     '    people = load_people()\n    mine = [p for p in people if p.get("state", "юсиксландия") == BASE.name]\n    if not mine:\n        print(f"(в {BASE.name} пока нет граждан — python3 gen.py people <n>)")\n        return\n    print(f"👥 НАСЕЛЕНИЕ {BASE.name.upper()}: {len(mine)}")\n    for p in mine:'),
]

for d in DIRS:
    for fname, pairs in [("economy.py", ECO), ("gen.py", GEN), ("vote.py", VOTE)]:
        path = d / fname
        text = path.read_text(encoding="utf-8")
        for old, new in pairs:
            if old not in text:
                print(f"⚠️  НЕ НАЙДЕНО в {d.name}/{fname}: {old[:60]}...")
            else:
                text = text.replace(old, new, 1)
        path.write_text(text, encoding="utf-8")
        print(f"✅ {d.name}/{fname} пропатчен")

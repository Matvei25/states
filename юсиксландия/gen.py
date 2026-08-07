#!/usr/bin/env python3
"""
gen.py — генератор законов, договоров и государств 🏛
запуск: python3 gen.py <команда> [аргументы]

команды:
  law <тема>                 — сгенерировать и принять закон (через gov.lisp)
  treaty <гос-во> <тема>     — подписать договор с соседом
  state <имя> [лор]          — сгенерировать соседнее государство
  world                      — карта мира (все государства)
"""
import os
import sys
import json
import random
import datetime
from pathlib import Path

BASE = Path(__file__).parent
WORLD = BASE / "world.md"
TREATIES = BASE / "treaties"
STATES = BASE.parent  # соседние государства живут рядом (~/states/<имя>)
PEOPLE = BASE.parent / "people.json"  # население мира

# ---------- генератор граждан ----------

FIRST_NAMES = ["Гриша", "Зина", "Коля", "Толик", "Света", "Петрович", "Михалыч", "Люся",
               "Аркадий", "Раиса", "Гена", "Нюра", "Валера", "Клавдия", "Семён", "Тома",
               "Эдик", "Маруся", "Федя", "Роза"]
JOBS = ["сантехник", "продавец", "учитель", "водитель", "пенсионер", "программист", "повар",
        "почтальон", "сварщик", "библиотекарь", "фермер", "таксист", "пекарь", "электрик",
        "медсестра", "бармен", "сторож", "бухгалтер"]
PERSONALITIES = [
    "ворчливый, но справедливый", "оптимист, верит в лучшее", "консерватор, не доверяет новому",
    "любит поспорить и доказать своё", "тихий и задумчивый", "балагур, душа компании",
    "подозрительный ко всему новому", "романтик", "прагматик, считает жёльки",
    "фанат порядка и законов", "ленивый, но добрый", "хитрый торгаш",
    "мечтатель, живёт в своём мире", "строгий и принципиальный",
]
INTERESTS = ["огород", "хоккей", "сериалы", "шахматы", "рыбалка", "кроссворды", "футбол",
             "вышивание", "компьютеры", "дача", "музыка", "готовка", "голуби", "мотоциклы"]


def load_people():
    if PEOPLE.exists():
        return json.loads(PEOPLE.read_text(encoding="utf-8"))
    return []


def save_people(people):
    PEOPLE.write_text(json.dumps(people, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_people(n):
    people = load_people()
    start = len(people)
    for i in range(n):
        p = {
            "id": f"p-{start + i + 1:03d}",
            "name": random.choice(FIRST_NAMES),
            "age": random.randint(18, 75),
            "job": random.choice(JOBS),
            "personality": random.choice(PERSONALITIES),
            "interests": random.sample(INTERESTS, 2),
            "party": random.choice(["Партия Мемов", "Партия Сна", "беспартийный", "беспартийный", "беспартийный"]),
            "voted": [],
        }
        people.append(p)
    save_people(people)
    print(f"👥 родилось {n} граждан. всего населения: {len(people)}")
    for p in people[start:]:
        print(f"  • {p['name']} ({p['age']}, {p['job']}): {p['personality']} — {p['party']}")

FLAGS = ["🐸", "🤖", "👾", "🐍", "🍕", "🧀", "🌵", "⚡", "🥶", "🤡", "🐉", "🛸"]

LAW_TEMPLATES = [
    "Объявить {topic} национальным достоянием",
    "Запретить {topic} без письменного разрешения правителя",
    "Учредить министерство {topic}",
    "Обязать всех граждан {topic} раз в неделю",
    "Ввести налог на {topic} в размере {n} жёлек",
    "Признать {topic} официальным праздником",
    "Наградить медалью «За {topic}» всех причастных",
]

TREATY_TEMPLATE = """# Договор между Юсиксландией-на-Морозовке и {other}

**Тема:** {topic}
**Дата:** {date}
**Статус:** RATIFIED

## Статьи

1. Стороны обязуются {topic} и не мешать друг другу в этом.
2. Каждая сторона платит другой 10 жёлек за нарушение духа договора.
3. Мемы между государствами передаются без пошлин.
4. Договор действует, пока обе стороны не забудут о его существовании (ожидаемо: 3 дня).

## Подписи

- Правитель Юсиксландии: Юсикс 🫠
- Правитель {other}: ______
"""

STATE_TEMPLATE = """# Конституция Государства {name} {flag}

> Сгенерировано автоматически {date}. Государство — это каталог.

## Лор

{lor}

## Основы

- **Статья 1.** {name} — суверенное государство (ну, почти).
- **Статья 2.** Всё записано в .env и .md. Остального не существует.
- **Статья 3.** С Юсиксландией поддерживать мир (договор подписывается отдельно).

## Экономика

- Валюта — жёльки (JLY). Казна — в state.env.
- Эмиссия — через труд и мемы.
"""


def slugify(text):
    out = []
    for ch in text.lower():
        out.append(ch if ch.isalnum() else "-")
    return "-".join("".join(out).split("-")) or "гос-во"


def today():
    return datetime.datetime.now().strftime("%Y-%m-%d")


def cmd_law(topic):
    n = random.randint(1, 9)
    tpl = random.choice(LAW_TEMPLATES).format(topic=topic, n=n)
    os.system(f'sbcl --script gov.lisp law "{tpl}"')
    print(f"📜 закон сгенерирован и подан на подпись: «{tpl}»")


def cmd_treaty(other, topic):
    TREATIES.mkdir(exist_ok=True)
    name = f"{today()}-{slugify(other)}-{slugify(topic)}.md"
    path = TREATIES / name
    path.write_text(TREATY_TEMPLATE.format(other=other, topic=topic, date=today()), encoding="utf-8")
    print(f"🤝 договор подписан: {path.relative_to(BASE)}")


def cmd_state(name, lor):
    slug = slugify(name)
    d = STATES / slug
    d.mkdir(parents=True, exist_ok=True)
    flag = random.choice(FLAGS)
    (d / "constitution.md").write_text(
        STATE_TEMPLATE.format(name=name, flag=flag, date=today(), lor=lor or f"Мало что известно о государстве {name}."),
        encoding="utf-8")
    (d / "state.env").write_text(
        f"STATE_NAME={name}\nSTATE_FLAG={flag}\nSTATE_FOUNDED={today()}\nPOPULATION={random.randint(1, 5)}\nTREASURY_JLY={random.randint(100, 900)}\nCURRENCY=JLY\nGOVERNOR=?\n", encoding="utf-8")
    line = f"- **{name}** {flag}: {lor or 'загадочное государство'} (основано {today()})"
    if WORLD.exists():
        WORLD.write_text(WORLD.read_text(encoding="utf-8") + line + "\n", encoding="utf-8")
    else:
        WORLD.write_text("# Карта мира 🌍\n\n" + line + "\n", encoding="utf-8")
    print(f"🌍 государство «{name}» {flag} создано → {d.relative_to(BASE.parent)}")


def cmd_world():
    print("━━━ КАРТА МИРА ━━━")
    if WORLD.exists():
        print(WORLD.read_text(encoding="utf-8"))
    else:
        print("(мир пока пуст — только мы)")
    if STATES.exists():
        for d in sorted(STATES.iterdir()):
            if d.is_dir() and not d.name.startswith(".") and (d / "state.env").exists():
                env = {}
                for line in (d / "state.env").read_text(encoding="utf-8").splitlines():
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        env[k] = v
                print(f"  📁 {env.get('STATE_NAME', d.name)} {env.get('STATE_FLAG', '')} — казна {env.get('TREASURY_JLY', '?')} JLY, население {env.get('POPULATION', '?')}")


def main():
    args = sys.argv[1:]
    if not args or args[0] == "world":
        cmd_world()
    elif args[0] == "law" and len(args) >= 2:
        cmd_law(" ".join(args[1:]))
    elif args[0] == "treaty" and len(args) >= 3:
        cmd_treaty(args[1], " ".join(args[2:]))
    elif args[0] == "state" and len(args) >= 2:
        cmd_state(args[1], " ".join(args[2:]) if len(args) > 2 else "")
    elif args[0] == "people" and len(args) >= 2 and args[1].isdigit():
        cmd_people(int(args[1]))
    else:
        print("использование: gen.py law <тема> | treaty <гос-во> <тема> | state <имя> [лор] | people <n> | world")


if __name__ == "__main__":
    main()

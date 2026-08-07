#!/usr/bin/env python3
"""
lore.py — генератор лора Балбесии ⚡📜
запуск: python3 lore.py [--force]
пишет хронику в chronicle.md (по одному дню за тик)

концепция: государство вечного хаоса, фиолетовый блоб с party hat.
"""
import sys
import random
import datetime
from pathlib import Path

BASE = Path(__file__).parent
ENV = BASE / "state.env"
CHRONICLE = BASE / "chronicle.md"

# события лора: (шаблон, "благо" или "хаос")
LORE_EVENTS = [
    ("Блоб проснулся, надел party hat задом наперёд и объявил это новой модой.", "хаос"),
    ("В Балбесии прошёл фестиваль кривых бананов. Победил банан, похожий на знак вопроса.", "благо"),
    ("Юсиксландия прислала делегацию мемов. Три мема дезертировали и остались жить.", "благо"),
    ("Курлыка из Кенорландии прилетел с инспекцией. Инспекцию съел блоб. Курлыка доволен.", "хаос"),
    ("Казначейство Балбесии переехало в картонную коробку под столом. Бюджет сохранён.", "хаос"),
    ("Объявлен государственный праздник: День Носок-На-Ушах. Все носки на уши!", "благо"),
    ("Балбес написал закон, запрещающий запрещать. Закон принят единогласно (1 голос).", "благо"),
    ("Конфетти-генератор заклинило. Балбесию засыпало конфетти на 3 дня. Казна в конфетти.", "хаос"),
    ("Шпион из Кенорландии попытался украсть жёльки, но споткнулся о party hat и всё вернул.", "благо"),
    ("Блоб отрастил вторую пару глаз, чтобы лучше видеть мемы. Видит теперь в 4 раза лучше.", "хаос"),
    ("Экономический совет Балбесии (блоб + таракан) рекомендовал печатать больше жёлек.", "хаос"),
    ("Балбесия подписала меморандум о взаимном непонимании с соседями. Все довольны.", "благо"),
]


def load_env():
    env = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def main():
    force = "--force" in sys.argv[1:]
    env = load_env()
    day = int(env.get("DAY", 1))
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    header = f"## День {day} — {today}"
    if CHRONICLE.exists() and header in CHRONICLE.read_text(encoding="utf-8") and not force:
        print("📜 лор дня уже записан, пропускаю")
        return

    n_events = random.randint(2, 3)
    events = random.sample(LORE_EVENTS, min(n_events, len(LORE_EVENTS)))

    block = [header, ""]
    for e in events:
        icon = "💫" if e[1] == "благо" else "🌀"
        block.append(f"- {icon} {e[0]}")
    block.append("")

    with CHRONICLE.open("a", encoding="utf-8") as f:
        if not CHRONICLE.exists() or CHRONICLE.stat().st_size == 0:
            f.write("# Хроника Балбесии ⚡\n\n")
        f.write("\n".join(block))
    print(f"📜 день {day}: в хронику добавлено {len(events)} события")


if __name__ == "__main__":
    main()

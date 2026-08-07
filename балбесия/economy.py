#!/usr/bin/env python3
"""
economy.py — хаос-экономика Балбесии ⚡🤪
запуск: python3 economy.py <команда> [аргументы]

команды:
  tick                  — новый день: мемы, пакости, случайные события
  budget                — отчёт: казна, кошелёк Балбеса, уровень хаоса
  pay <кто> <кому> <сумма> [за что]  — перевод жёлек
  meme                  — произвести мем прямо сейчас (+жёльки)
  prank [цель]          — устроить пакость (шанс на доход ИЛИ убыток)
"""
import sys
import random
import datetime
from pathlib import Path

BASE = Path(__file__).parent
ENV = BASE / "state.env"
LEDGER = BASE / "ledger.md"

CITIZEN = "Балбес"
START_JLY = 20

MEME_PAY = (3, 15)          # сколько жёлек приносит мем
PRANK_GOOD = [(5, 15), "Пакость удалась — соседи в восторге (или в ужасе)"]
PRANK_BAD = [(3, 10), "Пакость вышла боком — пришлось откупиться"]
PRANK_CHANCE = 0.5          # шанс, что пакость принесёт доход, а не убыток

# случайные события дня: (описание с {n}, диапазон жёлек)
CHAOS_EVENTS = [
    ("Балбес нарисовал мем про Юсиксландию — соседи заплатили отступные {n} JLY", (5, 20)),
    ("Party hat улетел в канаву — {n} JLY на аварийный ремонт головного убора", (2, 8)),
    ("Продана партия кривых бананов — в казну +{n} JLY", (4, 12)),
    ("Курлыка занёс гуманитарные жёльки — +{n} JLY", (5, 15)),
    ("Шторм хаоса: {n} JLY улетели в никуда (вероятно, в Кенорландию)", (2, 10)),
    ("Конфетти-дождь собрал {n} JLY с туристов", (3, 9)),
    ("Блоб случайно съел казну и выплюнул +{n} JLY (переварил)", (1, 7)),
    ("Соседи заплатили {n} JLY за тишину (Балбес молчал 5 минут)", (6, 18)),
]


def load_env():
    env = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def save_env(env):
    lines = ENV.read_text(encoding="utf-8").splitlines(keepends=True)
    out = []
    seen = set()
    for line in lines:
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k = s.split("=", 1)[0].strip()
            seen.add(k)
            if k in env:
                line = f"{k}={env[k]}\n"
        out.append(line)
    for k, v in env.items():
        if k not in seen:
            out.append(f"{k}={v}\n")
    ENV.write_text("".join(out), encoding="utf-8")


def log(entry):
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(f"- {datetime.datetime.now():%Y-%m-%d %H:%M} | {entry}\n")


def wallet(env, who):
    key = f"WALLET_{who.upper()}"
    if key not in env:
        env[key] = str(START_JLY)
    return int(env[key])


def set_wallet(env, who, amount):
    env[f"WALLET_{who.upper()}"] = str(amount)


def treasury(env):
    return int(env.get("TREASURY_JLY", 0))


def set_treasury(env, amount):
    env["TREASURY_JLY"] = str(max(0, amount))


def cmd_tick(env):
    day = int(env.get("DAY", 0)) + 1
    env["DAY"] = str(day)

    # 1) Балбес производит мемы
    meme_n = random.randint(*MEME_PAY)
    w = wallet(env, CITIZEN) + meme_n
    set_wallet(env, CITIZEN, w)
    log(f"день {day}: {CITIZEN} произвёл мем (+{meme_n} JLY)")
    print(f"🤪 день {day}: мем произведён, Балбес получил +{meme_n} JLY")

    # 2) случайное событие хаоса (влияет на казну)
    desc_tpl, (lo, hi) = random.choice(CHAOS_EVENTS)
    delta = random.randint(lo, hi)
    t = max(0, treasury(env) + delta)
    set_treasury(env, t)
    log(f"день {day}: хаос-событие ({'+' if delta >= 0 else ''}{delta} JLY): {desc_tpl.format(n=delta)}")
    print(f"🎲 хаос-событие: {desc_tpl.format(n=delta)}")

    # 3) уровень хаоса растёт (но не бесконечно)
    chaos = int(env.get("CHAOS_LEVEL", 1)) + random.randint(1, 3)
    env["CHAOS_LEVEL"] = str(chaos)

    save_env(env)
    print(f"☀️  день {day} завершён. Казна: {treasury(env)} JLY, хаос: {chaos}")


def cmd_budget(env):
    print("━━━ БЮДЖЕТ БАЛБЕСИИ ⚡ ━━━")
    print(f"казна:       {treasury(env)} JLY")
    print(f"день:        {env.get('DAY', 0)}")
    print(f"уровень хаоса: {env.get('CHAOS_LEVEL', 1)}")
    print(f"кошелёк {CITIZEN}: {wallet(env, CITIZEN)} JLY")


def cmd_pay(env, args):
    if len(args) < 3:
        print("использование: pay <кто> <кому> <сумма> [за что]")
        return
    who, to, amount = args[0], args[1], int(args[2])
    reason = " ".join(args[3:]) if len(args) > 3 else "без причины"
    w = wallet(env, who)
    if w < amount:
        print(f"❌ {who} банкрот: на счету {w} JLY")
        return
    set_wallet(env, who, w - amount)
    if to.upper() == "КАЗНА":
        set_treasury(env, treasury(env) + amount)
        log(f"{who} → казна: {amount} JLY ({reason})")
        print(f"💸 {who} заплатил в казну {amount} JLY ({reason})")
    else:
        tw = wallet(env, to)
        set_wallet(env, to, tw + amount)
        log(f"{who} → {to}: {amount} JLY ({reason})")
        print(f"💸 {who} → {to}: {amount} JLY ({reason})")
    save_env(env)


def cmd_meme(env):
    n = random.randint(*MEME_PAY)
    w = wallet(env, CITIZEN) + n
    set_wallet(env, CITIZEN, w)
    log(f"{CITIZEN} произвёл внеплановый мем (+{n} JLY)")
    save_env(env)
    print(f"🖼 мем готов! Балбес заработал +{n} JLY (кошелёк: {w} JLY)")


def cmd_prank(env, args):
    target = args[0] if args else "соседям"
    if random.random() < PRANK_CHANCE:
        lo, hi = PRANK_GOOD[0]
        n = random.randint(lo, hi)
        w = wallet(env, CITIZEN) + n
        set_wallet(env, CITIZEN, w)
        log(f"пакость на {target}: успех (+{n} JLY)")
        save_env(env)
        print(f"😈 Пакость на {target} УДАЛАСЬ! {PRANK_GOOD[1]} +{n} JLY")
    else:
        lo, hi = PRANK_BAD[0]
        n = random.randint(lo, hi)
        w = max(0, wallet(env, CITIZEN) - n)
        set_wallet(env, CITIZEN, w)
        log(f"пакость на {target}: провал (−{n} JLY)")
        save_env(env)
        print(f"💥 Пакость на {target} провалилась… {PRANK_BAD[1]} −{n} JLY")


def main():
    env = load_env()
    args = sys.argv[1:]
    if not args or args[0] == "budget":
        cmd_budget(env)
    elif args[0] == "tick":
        cmd_tick(env)
    elif args[0] == "pay":
        cmd_pay(env, args[1:])
    elif args[0] == "meme":
        cmd_meme(env)
    elif args[0] == "prank":
        cmd_prank(env, args[1:])
    else:
        print("неизвестная команда. смотри шапку файла.")


if __name__ == "__main__":
    main()

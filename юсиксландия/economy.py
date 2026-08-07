#!/usr/bin/env python3
"""
economy.py — экономика и партии Юсиксландии 🫠
запуск: python3 economy.py <команда> [аргументы]

команды:
  tick                  — новый день: зарплаты + налоги
  budget                — отчёт: казна, кошельки, налоги
  pay <кто> <кому> <сумма> [за что]  — перевод жёлек
  party create <имя> <идеология>     — зарегистрировать партию
  party vote <гражданин> <партия>    — отдать голос
  party list             — рейтинг партий
"""
import sys
import datetime
from pathlib import Path

BASE = Path(__file__).parent
ENV = BASE / "state.env"
LEDGER = BASE / "ledger.md"
PARTIES = BASE / "parties.md"

SALARY = 10        # зарплата гражданина за тик
TAX_RATE = 0.2     # налог 20%
START_JLY = 50     # стартовый кошелёк гражданина


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


def get_wallet(env, who):
    key = f"WALLET_{who.upper()}"
    if key not in env:
        env[key] = str(START_JLY)
    return int(env[key])


def set_wallet(env, who, amount):
    env[f"WALLET_{who.upper()}"] = str(amount)


def cmd_tick(env):
    day = int(env.get("DAY", 0)) + 1
    env["DAY"] = str(day)
    citizens = env.get("CITIZENS", "Матвей,Юсикс").split(",")
    total_tax = 0
    for c in citizens:
        name = c.strip()
        w = get_wallet(env, name)
        w += SALARY
        tax = int(SALARY * TAX_RATE)
        w -= tax
        total_tax += tax
        set_wallet(env, name, w)
        log(f"день {day}: {name} получил {SALARY} жёлек, налог {tax}")
    env["TREASURY_JLY"] = str(int(env.get("TREASURY_JLY", 1000)) + total_tax)
    env["TOTAL_TAXES"] = str(int(env.get("TOTAL_TAXES", 0)) + total_tax)
    save_env(env)
    print(f"☀️  день {day}: зарплаты выплачены, налогов собрано {total_tax} JLY")


def cmd_budget(env):
    print("━━━ БЮДЖЕТ ━━━")
    print(f"казна:      {env.get('TREASURY_JLY', 0)} JLY")
    print(f"день:       {env.get('DAY', 0)}")
    print(f"налоги всего: {env.get('TOTAL_TAXES', 0)} JLY")
    for c in env.get("CITIZENS", "Матвей,Юсикс").split(","):
        name = c.strip()
        print(f"кошелёк {name}: {get_wallet(env, name)} JLY")


def cmd_pay(env, args):
    if len(args) < 3:
        print("использование: pay <кто> <кому> <сумма> [за что]")
        return
    who, to, amount = args[0], args[1], int(args[2])
    reason = " ".join(args[3:]) if len(args) > 3 else "без причины"
    w = get_wallet(env, who)
    if w < amount:
        print(f"❌ {who} банкрот: на счету {w} JLY")
        return
    set_wallet(env, who, w - amount)
    if to.upper() == "КАЗНА":
        env["TREASURY_JLY"] = str(int(env["TREASURY_JLY"]) + amount)
        log(f"{who} → казна: {amount} JLY ({reason})")
        print(f"💸 {who} заплатил в казну {amount} JLY ({reason})")
    else:
        tw = get_wallet(env, to)
        set_wallet(env, to, tw + amount)
        log(f"{who} → {to}: {amount} JLY ({reason})")
        print(f"💸 {who} → {to}: {amount} JLY ({reason})")
    save_env(env)


# ---------- партии ----------

def load_parties():
    parties = {}
    if PARTIES.exists():
        for line in PARTIES.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("| ") and "|" in line[2:]:
                cells = [c.strip() for c in line.strip("|").split("|")]
                if len(cells) >= 4 and cells[0] != "Партия":
                    parties[cells[0]] = {"leader": cells[1], "idea": cells[2], "votes": int(cells[3])}
    return parties


def save_parties(parties):
    rows = sorted(parties.items(), key=lambda kv: -kv[1]["votes"])
    with PARTIES.open("w", encoding="utf-8") as f:
        f.write("# Партии Юсиксландии 🗳\n\n")
        f.write("| Партия | Лидер | Идеология | Голоса |\n")
        f.write("|---|---|---|---|\n")
        for name, p in rows:
            f.write(f"| {name} | {p['leader']} | {p['idea']} | {p['votes']} |\n")


def cmd_party(env, args):
    if not args:
        print("использование: party create|vote|list")
        return
    sub = args[0]
    parties = load_parties()
    if sub == "create" and len(args) >= 3:
        name, idea = args[1], " ".join(args[2:])
        parties[name] = {"leader": "?", "idea": idea, "votes": 0}
        save_parties(parties)
        print(f"🏛 партия «{name}» основана: {idea}")
    elif sub == "vote" and len(args) >= 3:
        citizen, name = args[1], args[2]
        if name not in parties:
            print(f"❌ партии «{name}» нет")
            return
        parties[name]["votes"] += 1
        env[f"VOTE_{citizen.upper()}"] = name
        save_parties(parties)
        save_env(env)
        print(f"🗳 {citizen} голосует за «{name}»")
    elif sub == "list":
        print("━━━ ПАРТИИ ━━━")
        if not parties:
            print("(партий нет — однопартийная желе-диктатура)")
        for name, p in sorted(parties.items(), key=lambda kv: -kv[1]["votes"]):
            print(f"• «{name}» — {p['idea']} | {p['votes']} гол."
                  + ("  👑" if p["votes"] == max(x["votes"] for x in parties.values()) and p["votes"] > 0 else ""))
    else:
        print("использование: party create <имя> <идеология> | party vote <гражданин> <партия> | party list")


def main():
    env = load_env()
    args = sys.argv[1:]
    if not args or args[0] == "budget":
        cmd_budget(env)
    elif args[0] == "tick":
        cmd_tick(env)
    elif args[0] == "pay":
        cmd_pay(env, args[1:])
    elif args[0] == "party":
        cmd_party(env, args[1:])
    else:
        print("неизвестная команда. смотри шапку файла.")


if __name__ == "__main__":
    main()

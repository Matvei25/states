#!/usr/bin/env python3
"""
war.py — войны государств Юсиксландии-на-Морозовке ⚔️

Война ОБЪЯВЛЯЕТСЯ здесь, а РАЗРЕШАЕТСЯ в Minecraft: государства выставляют
бойцов (тела ботов в мире), и кто победил в бою — тот и прав. Этот скрипт
применяет последствия: казна, земля, хаос, лор — и коммитит в git мира.

запуск:
  python3 war.py states                                — сводка государств
  python3 war.py declare <атака> <защита> [причина]    — объявить войну
  python3 war.py result <атака> <защита> <победитель> [заметка]
  python3 war.py log                                   — хроника войн
"""
import subprocess
import sys
import datetime
from pathlib import Path

WORLD = Path(__file__).parent
WARS = WORLD / "wars.md"

# алиасы государств (как их зовёт агент) → папка, флаг, официальное имя
STATES = {
    "юсиксландия": ("юсиксландия", "🫠", "Юсиксландия-на-Морозовке"),
    "балбесия":    ("балбесия",    "⚡", "Балбесия"),
    "кенорландия": ("кенорландия", "🏰", "Либеральная Кенорская Республика"),
}

LOOT_RATE = 0.25   # победитель забирает 25% казны побеждённого
MIN_LOOT = 50      # но не меньше 50
WAR_CHAOS = 10     # война всегда поднимает хаос (если участвует Балбесия)


# ───────────────────────── env-машинерия ─────────────────────────

def resolve(name):
    key = name.strip().lower().replace("ё", "е")
    if key in STATES:
        return STATES[key]
    for k, v in STATES.items():
        if k.replace("ё", "е").startswith(key) or key.startswith(k.replace("ё", "е")):
            return v
    raise SystemExit(f"❌ неизвестное государство: «{name}». Есть: {', '.join(STATES)}")


def load_env(folder):
    env = {}
    p = WORLD / folder / "state.env"
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def save_env(folder, env):
    p = WORLD / folder / "state.env"
    lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    out, seen = [], set()
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
    p.write_text("".join(out), encoding="utf-8")


def ledger(folder, entry):
    p = WORLD / folder / "ledger.md"
    with p.open("a", encoding="utf-8") as f:
        f.write(f"- {datetime.datetime.now():%Y-%m-%d %H:%M} | {entry}\n")


def chronicle(folder, text):
    p = WORLD / folder / "chronicle.md"
    with p.open("a", encoding="utf-8") as f:
        f.write(f"\n## {datetime.datetime.now():%Y-%m-%d} — война\n{text}\n")


def treasury(env):
    return int(env.get("TREASURY_JLY", 0))


def git_commit(msg):
    if not (WORLD / ".git").exists():
        return "(git нет — пропускаю коммит)"
    subprocess.run(["git", "add", "-A"], cwd=WORLD, capture_output=True)
    r = subprocess.run(["git", "commit", "-m", msg], cwd=WORLD,
                       capture_output=True, text=True)
    if r.returncode != 0:
        return "(нечего коммитить)"
    return r.stdout.strip().splitlines()[0] if r.stdout.strip() else "ok"


# ───────────────────────── команды ─────────────────────────

def cmd_states():
    print("━━━ ГОСУДАРСТВА МИРА ━━━")
    for folder, flag, name in STATES.values():
        env = load_env(folder)
        lands = env.get("LANDS", "1")
        line = (f"{flag} {name:<32} казна {treasury(env):>5} "
                f"{env.get('CURRENCY', 'JLY'):<4} земель {lands} день {env.get('DAY', '?')}")
        if "CHAOS_LEVEL" in env:
            line += f" хаос {env['CHAOS_LEVEL']}"
        print(line)


def cmd_declare(args):
    if len(args) < 2:
        raise SystemExit("использование: declare <атака> <защита> [причина]")
    a_folder, a_flag, a_name = resolve(args[0])
    d_folder, d_flag, d_name = resolve(args[1])
    reason = " ".join(args[2:]) if len(args) > 2 else "без объявленной причины"
    stamp = datetime.datetime.now()

    ledger(a_folder, f"⚔️ {a_name} объявила войну {d_name}: {reason}")
    ledger(d_folder, f"🛡 {d_name} получила объявление войны от {a_name}: {reason}")

    with WARS.open("a", encoding="utf-8") as f:
        f.write(f"\n## {stamp:%Y-%m-%d %H:%M} — {a_flag} {a_name} ⚔️ {d_flag} {d_name}\n"
                f"- объявлена: {reason}\n- статус: **идёт** (бой в Minecraft)\n")

    git_commit(f"⚔️ война: {a_name} объявила {d_name} ({reason})")

    print(f"⚔️  ВОЙНА ОБЪЯВЛЕНА: {a_flag} {a_name} → {d_flag} {d_name}")
    print(f"    причина: {reason}")
    print("    теперь бойцы должны решить это в Minecraft — только после боя")
    print("    вызывай: war.py result <%s> <%s> <победитель>" % (args[0], args[1]))


def cmd_result(args):
    if len(args) < 3:
        raise SystemExit("использование: result <атака> <защита> <победитель> [заметка]")
    a_folder, a_flag, a_name = resolve(args[0])
    d_folder, d_flag, d_name = resolve(args[1])
    w_folder, w_flag, w_name = resolve(args[2])
    if w_folder not in (a_folder, d_folder):
        raise SystemExit("❌ победитель должен быть одной из воюющих сторон")
    note = " ".join(args[3:]) if len(args) > 3 else ""

    loser_folder = d_folder if w_folder == a_folder else a_folder
    loser_flag = d_flag if w_folder == a_folder else a_flag
    loser_name = d_name if w_folder == a_folder else a_name

    w_env = load_env(w_folder)
    l_env = load_env(loser_folder)

    loot = max(MIN_LOOT, int(treasury(l_env) * LOOT_RATE))
    loot = min(loot, treasury(l_env))                # не больше, чем есть
    w_env["TREASURY_JLY"] = str(treasury(w_env) + loot)
    l_env["TREASURY_JLY"] = str(treasury(l_env) - loot)

    w_env["LANDS"] = str(int(w_env.get("LANDS", "1")) + 1)
    l_env["LANDS"] = str(max(0, int(l_env.get("LANDS", "1")) - 1))

    # война всегда сеет хаос: победителю +5, проигравшему +15
    if "CHAOS_LEVEL" in w_env:
        w_env["CHAOS_LEVEL"] = str(int(w_env.get("CHAOS_LEVEL", 0)) + 5)
    if "CHAOS_LEVEL" in l_env:
        l_env["CHAOS_LEVEL"] = str(int(l_env.get("CHAOS_LEVEL", 0)) + 15)

    save_env(w_folder, w_env)
    save_env(loser_folder, l_env)

    line = (f"⚔️ итог войны: {w_flag} {w_name} победила {loser_flag} {loser_name}; "
            f"трофей {loot} {l_env.get('CURRENCY', 'JLY')}, земля ±1")
    ledger(w_folder, f"{line} (победа)")
    ledger(loser_folder, f"{line} (поражение)")
    if (WORLD / loser_folder / "chronicle.md").exists():
        chronicle(loser_folder, f"{loser_flag} **{loser_name}** проиграла войну {w_flag} {w_name}. "
                                f"Трофей: {loot} {l_env.get('CURRENCY', 'JLY')}. {note}")
    if (WORLD / w_folder / "chronicle.md").exists():
        chronicle(w_folder, f"{w_flag} **{w_name}** победила {loser_flag} {loser_name} в войне. "
                            f"Забрано: {loot} {l_env.get('CURRENCY', 'JLY')}. {note}")

    with WARS.open("a", encoding="utf-8") as f:
        f.write(f"\n### {datetime.datetime.now():%Y-%m-%d %H:%M} — ИТОГ\n"
                f"- победитель: {w_flag} **{w_name}**\n"
                f"- побеждённый: {loser_flag} {loser_name}\n"
                f"- трофей: {loot} {l_env.get('CURRENCY', 'JLY')}, земель ±1\n"
                + (f"- заметка: {note}\n" if note else ""))

    git_commit(f"⚔️ итог войны: {w_name} победила {loser_name} (трофей {loot})")

    print(f"🏆 {w_flag} {w_name} ПОБЕДИЛА {loser_flag} {loser_name}")
    print(f"   трофей: {loot} {l_env.get('CURRENCY', 'JLY')}")
    print(f"   казна {w_name}: {treasury(w_env)} | казна {loser_name}: {treasury(l_env)}")


def cmd_log():
    if not WARS.exists():
        print("войн ещё не было — мир скучный 😴")
        return
    print(WARS.read_text(encoding="utf-8"))


COMMANDS = {
    "states": lambda a: cmd_states(),
    "declare": cmd_declare,
    "result": cmd_result,
    "log": lambda a: cmd_log(),
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1 if len(sys.argv) > 1 else 0)
    COMMANDS[sys.argv[1]](sys.argv[2:])

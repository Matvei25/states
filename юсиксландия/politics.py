#!/usr/bin/env python3
"""
politics.py — политическая модель Юсиксландии 🫠🗳

МОДЕЛЬ ДАННЫХ (первая версия). Данные в politics.json, расчёты — в politics.lisp.
Питон НЕ считает политику: он рождает данные и ходит в лисп-мозг через sbcl.

запуск:
  python3 politics.py init          — построить parties + профили граждан из people.json
  python3 politics.py show          — показать политическую карту (оси, партии, граждане)
  python3 politics.py md            — перезаписать politics.md (реальность в .md, ст. 2 конституции)
  python3 politics.py rate [аргументы] — позвать politics.lisp (rate/axes/leader/closest)
  python3 politics.py reset         — забыть всё политическое (пересобрать с нуля)

опции: --seed N — фиксированное зерно шума профилей (по умолчанию 6)
"""
import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent
POLITICS = BASE / "politics.json"
POLITICS_MD = BASE / "politics.md"
PEOPLE = BASE.parent / "people.json"
LISP = BASE / "politics.lisp"
STATE_SLUG = BASE.name  # "юсиксландия"

# ---------------------------------------------------------------- оси

AXES = [
    {"id": "econ", "name": "жёлейки", "left": "общие", "right": "частные",
     "question": "кому принадлежат жёлейки — всем или тому, кто заработал?"},
    {"id": "order", "name": "порядок", "left": "свобода", "right": "порядок",
     "question": "сколько государства должно быть в жизни гражданина?"},
    {"id": "fun", "name": "мемность", "left": "серьёзность", "right": "мемы",
     "question": "мемы — это государственное дело или личное?"},
    {"id": "rest", "name": "сон", "left": "труд", "right": "отдых",
     "question": "спать — это тоже труд или это слабость?"},
]

# ---------------------------------------------------------------- партии

PARTIES = [
    {
        "id": "memes", "name": "Партия Мемов", "founded": "2026-08-07", "leader": None,
        "slogan": "мемы решают всё",
        "pos": {"econ": -0.5, "order": -0.7, "fun": 1.0, "rest": 0.3},
        "program": [
            "каждый день — день мемов (закон 01, действует)",
            "право на NO_REPLY без объяснений (ст. 5)",
            "мемы между государствами — без пошлин",
            "учредить государственный архив мемов",
        ],
    },
    {
        "id": "sleep", "name": "Партия Сна", "founded": "2026-08-07", "leader": None,
        "slogan": "спать — это тоже труд",
        "pos": {"econ": -0.3, "order": -0.4, "fun": 0.2, "rest": 1.0},
        "program": [
            "тихий час — государственный праздник",
            "ночная смена оплачивается двойными жёлейками",
            "воскресный сон не облагается налогом",
            "учредить министерство подушек",
        ],
    },
    {
        "id": "disks", "name": "Партия Дисков и Старых Компов", "founded": "2026-08-23",
        "leader": None,
        "slogan": "железо не умирает, оно ждёт",
        "pos": {"econ": 0.2, "order": 0.6, "fun": -0.6, "rest": -0.4},
        "program": [
            "министерство дисков и старых компов (закон 03, действует)",
            "налог на новое железо в пользу ретро-техники",
            "каждый винчестер — национальное достояние",
            "реставрация ордена «За шум кулера»",
        ],
    },
    {
        "id": "jelly", "name": "Партия Жёлек и Порядка", "founded": "2026-08-23", "leader": None,
        "slogan": "сначала баланс, потом мемы",
        "pos": {"econ": 0.9, "order": 0.8, "fun": -0.5, "rest": -0.6},
        "program": [
            "бюджет без дефицита, аудит казны каждый месяц",
            "налог мемами по твёрдой ставке",
            "запрет на эмиссию жёлек без коммита",
            "сепаратизм — конфискация казны (ст. 9, действует)",
        ],
    },
]

# ------------------------------------------------- правила профиля гражданина

JOB_BIAS = {
    "сантехник": {"econ": 0.2, "order": 0.2},
    "продавец": {"econ": 0.4, "fun": 0.1},
    "учитель": {"order": 0.4, "econ": -0.3},
    "водитель": {"econ": 0.2, "order": 0.2},
    "пенсионер": {"order": 0.4, "rest": 0.5},
    "программист": {"order": 0.3, "rest": -0.3},
    "повар": {"fun": 0.2, "rest": 0.1},
    "почтальон": {"order": 0.2, "fun": 0.1},
    "сварщик": {"order": 0.3, "econ": 0.1},
    "библиотекарь": {"order": 0.4, "fun": -0.3},
    "фермер": {"order": 0.3, "rest": -0.2},
    "таксист": {"econ": 0.5, "order": 0.1},
    "пекарь": {"order": 0.3, "econ": -0.1, "rest": -0.2},
    "электрик": {"order": 0.3},
    "медсестра": {"econ": -0.4, "rest": 0.2},
    "бармен": {"fun": 0.6, "rest": 0.3},
    "сторож": {"rest": 0.4, "order": 0.2},
    "бухгалтер": {"econ": 0.7, "order": 0.5, "fun": -0.4},
    "часовщик": {"order": 0.6, "rest": -0.5, "fun": -0.4},
    "рыбак": {"rest": 0.1, "order": -0.2},
}

PERSONALITY_BIAS = {
    "ворчливый, но справедливый": {"order": 0.3},
    "оптимист, верит в лучшее": {"fun": 0.4},
    "консерватор, не доверяет новому": {"order": 0.6, "fun": -0.5},
    "любит поспорить и доказать своё": {"order": -0.5, "fun": 0.3},
    "тихий и задумчивый": {"rest": 0.4, "fun": -0.2},
    "балагур, душа компании": {"fun": 0.7, "rest": 0.1},
    "подозрительный ко всему новому": {"order": 0.5, "econ": 0.2},
    "романтик": {"fun": 0.4, "rest": 0.2},
    "прагматик, считает жёльки": {"econ": 0.8, "order": 0.3},
    "фанат порядка и законов": {"order": 0.9, "fun": -0.3},
    "ленивый, но добрый": {"rest": 0.8, "econ": -0.3},
    "хитрый торгаш": {"econ": 0.8, "order": -0.5},
    "мечтатель, живёт в своём мире": {"fun": 0.5, "rest": 0.3, "order": -0.3},
    "строгий и принципиальный": {"order": 0.7, "fun": -0.4},
}

INTEREST_BIAS = {
    "огород": {"rest": -0.3, "order": 0.3},
    "хоккей": {"fun": 0.4, "order": 0.1},
    "сериалы": {"rest": 0.4, "fun": 0.2},
    "шахматы": {"order": 0.4, "fun": -0.1},
    "рыбалка": {"rest": 0.4, "order": -0.1},
    "кроссворды": {"order": 0.2, "rest": 0.1},
    "футбол": {"fun": 0.4, "order": 0.1},
    "вышивание": {"rest": 0.3, "order": 0.2},
    "компьютеры": {"order": 0.3, "rest": -0.2},
    "дача": {"rest": -0.2, "order": 0.3},
    "музыка": {"fun": 0.5, "rest": 0.1},
    "готовка": {"fun": 0.2, "rest": 0.1},
    "голуби": {"rest": 0.1, "order": 0.2},
    "мотоциклы": {"fun": 0.4, "order": -0.3},
}

AXIS_IDS = [a["id"] for a in AXES]


def noise(seed_str, axis, mag=0.15):
    """Стабильный псевдослучайный шум для гражданина: один и тот же id — один и тот же характер."""
    h = hashlib.sha256(f"{seed_str}:{axis}".encode("utf-8")).digest()
    r = random.Random(int.from_bytes(h[:8], "big"))
    return r.uniform(-mag, mag)


def clamp(x):
    return max(-1.0, min(1.0, round(x, 2)))


def build_citizen(seed_str, p):
    """Профиль гражданина из работы/характера/интересов + шум. Возвращает (pos, why)."""
    pos = {a: 0.0 for a in AXIS_IDS}
    why = []
    def apply(table, key, label):
        bias = table.get(key)
        if not bias:
            return
        for ax, v in bias.items():
            pos[ax] += v
        parts = ", ".join(f"{ax}{v:+.1f}" for ax, v in bias.items())
        why.append(f"{label} «{key}» → {parts}")
    apply(JOB_BIAS, p.get("job"), "работа")
    apply(PERSONALITY_BIAS, p.get("personality"), "характер")
    for it in p.get("interests", []):
        apply(INTEREST_BIAS, it, "интерес")
    for ax in AXIS_IDS:
        pos[ax] = clamp(pos[ax] * 0.85 + noise(seed_str, ax))
        if abs(pos[ax]) < 0.05:
            pos[ax] = 0.0
    return pos, why


# ---------------------------------------------------------------- файлы

def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def citizens_of_state():
    people = load_json(PEOPLE, [])
    return [p for p in people if p.get("state", STATE_SLUG) == STATE_SLUG]


def load_politics():
    if not POLITICS.exists():
        print("❌ politics.json нет. сначала: python3 politics.py init")
        sys.exit(1)
    return load_json(POLITICS, {})


# ---------------------------------------------------------------- команды

def cmd_init(seed=6):
    people = citizens_of_state()
    if not people:
        print("❌ в people.json нет граждан Юсиксландии. сначала: python3 gen.py people <n>")
        return
    parties = []
    for p in PARTIES:
        parties.append({**p, "influence": 0.0, "treasury": 0,
                        "members": [c["id"] for c in people if c.get("party") == p["name"]],
                        "status": "active"})
    citizens = []
    for p in people:
        pos, why = build_citizen(p["id"], p)
        declared = p.get("party")
        citizens.append({
            "id": p["id"], "name": p["name"], "age": p["age"], "job": p["job"],
            "personality": p["personality"], "interests": p.get("interests", []),
            "pos": pos,
            "party": next((pt["id"] for pt in parties if pt["name"] == declared), None),
            "declared_party": declared if declared != "беспартийный" else None,
            "loyalty": round(0.4 + noise(p["id"], "loyalty", 0.35) + 0.35, 2),
            "why": why,
        })
    data = {
        "version": 1,
        "state": "Юсиксландия-на-Морозовке",
        "seed": seed,
        "built": None,
        "axes": AXES,
        "parties": parties,
        "citizens": citizens,
        "ratings": {"updated": None, "support": {pt["id"]: 0.0 for pt in parties},
                    "leader": {pt["id"]: None for pt in parties}},
    }
    import datetime
    data["built"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    save_json(POLITICS, data)
    print(f"🏛 политическая модель собрана: {len(parties)} партии, {len(citizens)} граждан")
    for pt in parties:
        print(f"  • «{pt['name']}» — {pt['slogan']}"
              + (f" (членов: {len(pt['members'])})" if pt["members"] else " (пока никого)"))
    print(f"→ {POLITICS}")
    cmd_md(quiet=True)


def axis_bar(v, width=21):
    """-1..1 → полоска от центра."""
    half = (width - 1) // 2
    idx = round((v + 1) / 2 * (width - 1))
    row = ["·"] * width
    row[half] = "┼"
    row[idx] = "█"
    return "".join(row)


def cmd_show():
    d = load_politics()
    print(f"\n━━━ ПОЛИТИЧЕСКАЯ КАРТА: {d['state']} {d['built']} ━━━")
    print("\nОСИ (лево → право):")
    for a in d["axes"]:
        print(f"  {a['name']:<9} {a['left']:>10} {axis_bar(0)!s:>0} {a['right']:<10}")
    print("\nПАРТИИ:")
    for pt in d["parties"]:
        pos = " ".join(f"{k}{v:+.1f}" for k, v in pt["pos"].items())
        print(f"  «{pt['name']}» [{pt['id']}] {pt['slogan']}")
        print(f"      позиции: {pos}")
        print(f"      влияние: {pt['influence']:.2f} · касса: {pt['treasury']} JLY · члены: "
              + (", ".join(pt["members"]) if pt["members"] else "нет"))
        for item in pt["program"]:
            print(f"      · {item}")
    print("\nГРАЖДАНЕ:")
    for c in d["citizens"]:
        pos = " ".join(f"{k}{v:+.1f}" for k, v in c["pos"].items())
        print(f"  {c['id']} {c['name']} ({c['age']}, {c['job']}) {pos} "
              f"| лояльность {c['loyalty']:.2f} | партия: {c['party'] or c['declared_party'] or '—'}")
    print("\n(расчёты — в лиспе: python3 politics.py rate)")


def cmd_md(quiet=False):
    d = load_politics()
    L = ["# Политика Юсиксландии 🗳", "",
         f"> модель v{d['version']} · собрана {d['built']} · данные: `politics.json` · расчёты: `politics.lisp`",
         "", "## Политические оси", "", "| Ось | лево | право | вопрос |", "|---|---|---|---|"]
    for a in d["axes"]:
        L.append(f"| **{a['name']}** | {a['left']} | {a['right']} | {a['question']} |")
    L += ["", "## Партии", "", "| Партия | Слоган | econ | order | fun | rest | Влияние | Касса |",
          "|---|---|---|---|---|---|---|---|"]
    for pt in sorted(d["parties"], key=lambda x: -x["influence"]):
        p = pt["pos"]
        L.append(f"| «{pt['name']}» | {pt['slogan']} | {p['econ']:+.1f} | {p['order']:+.1f} | "
                 f"{p['fun']:+.1f} | {p['rest']:+.1f} | {pt['influence']:.2f} | {pt['treasury']} JLY |")
    L += ["", "## Программы", ""]
    for pt in d["parties"]:
        L.append(f"**«{pt['name']}»** — {pt['slogan']}")
        for item in pt["program"]:
            L.append(f"- {item}")
        L.append("")
    nearest = d.get("ratings", {}).get("nearest", {})
    pname = {x["id"]: x["name"] for x in d["parties"]}
    L += ["## Граждане", "",
          "| ID | Имя | Возраст | Работа | econ | order | fun | rest | Лояльность | Партия | Тянется к |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in d["citizens"]:
        p = c["pos"]
        L.append(f"| {c['id']} | {c['name']} | {c['age']} | {c['job']} | {p['econ']:+.1f} | {p['order']:+.1f} | "
                 f"{p['fun']:+.1f} | {p['rest']:+.1f} | {c['loyalty']:.2f} | "
                 f"{pname.get(c['party'] or c['declared_party'], '—')} | "
                 f"{pname.get(nearest.get(c['id']), '—')} |")
    L += ["", "## Почему так", "",
          "Профиль гражданина считается из работы, характера и интересов + стабильный шум по ID",
          "(один и тот же гражданин всегда повторится). Полное объяснение — в `politics.json` → `why`.", ""]
    if d.get("ratings", {}).get("updated"):
        r = d["ratings"]
        L += ["## Последний расчёт поддержки (лисп)", "", f"> обновлено: {r['updated']}", "",
              "| Партия | Поддержка | Лидер |", "|---|---|---|"]
        for pt in sorted(d["parties"], key=lambda x: -r["support"].get(x["id"], 0)):
            L.append(f"| «{pt['name']}» | {r['support'].get(pt['id'], 0):.1f}% | "
                     f"{r['leader'].get(pt['id']) or '—'} |")
        L.append("")
    POLITICS_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    if not quiet:
        print(f"📜 {POLITICS_MD} обновлён")


def cmd_rate(args):
    """Мост: лисп считает — питон сохраняет. Человеческий вывод лиспа идёт в stderr,
    машинный JSON — в stdout, поэтому оба не мешают друг другу."""
    if not LISP.exists():
        print(f"❌ нет {LISP}")
        return
    if not args:
        args = ["rate"]
    cmd = ["sbcl", "--script", str(LISP)] + args + ["--json"]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE))
    human = (r.stderr or "").strip()
    out = (r.stdout or "").strip()
    if human and "sbcl" not in human.splitlines()[0].lower():
        print(human)
    payload = None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                payload = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
    if payload and args[0] == "rate":
        import datetime
        d = load_politics()
        d["ratings"] = {
            "updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "support": {k: round(float(v), 2) for k, v in payload.get("support", {}).items()},
            "leader": payload.get("leader", {}),
            "nearest": payload.get("nearest", {}),
        }
        save_json(POLITICS, d)
        cmd_md(quiet=True)
        sup = d["ratings"]["support"]
        for pid, val in sorted(sup.items(), key=lambda kv: -kv[1]):
            name = next((x["name"] for x in d["parties"] if x["id"] == pid), pid)
            bar = "█" * max(1, round(val / 3))
            print(f"  {bar:<12} «{name}»: {val:.1f}%  (лидер: {d['ratings']['leader'].get(pid) or '—'})")
        top = max(sup.items(), key=lambda kv: kv[1])
        party = next((x["name"] for x in d["parties"] if x["id"] == top[0]), top[0])
        print(f"✔ рейтинги записаны (politics.json + politics.md): лидирует «{party}» — {top[1]:.1f}%")
    elif out:
        print(out)
    if r.returncode != 0:
        print(f"⚠️ лисп вернул {r.returncode}")
        if human:
            print(human[:1200])


def cmd_reset():
    if POLITICS.exists():
        POLITICS.unlink()
        print("🧹 politics.json удалён")
    print("(people.json не тронут — модель собирается из него заново)")


def main():
    args = sys.argv[1:]
    seed = 6
    if "--seed" in args:
        i = args.index("--seed")
        seed = int(args[i + 1])
        del args[i:i + 2]
    if not args or args[0] == "show":
        cmd_show()
    elif args[0] == "init":
        cmd_init(seed)
    elif args[0] == "md":
        cmd_md()
    elif args[0] == "rate":
        cmd_rate(args[1:])
    elif args[0] == "reset":
        cmd_reset()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

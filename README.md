# C.R.A.M — The Unbound

> **Combat. Revision. Advancement. Mastery.**  
> A full-stack educational RPG where you study by fighting. Answer questions correctly to deal damage, build streaks, and survive a procedurally generated world.

Built by **Lazarus Petrus** | [GitHub](https://github.com/HeisLazi)

---

## What is this?

C.R.A.M is a desktop/web game I built to make revision feel like something worth doing. Instead of reading flashcards, you explore a procedural world, face enemies that test your knowledge, and survive using what you've learned. The harder the question, the harder the enemy hits back.

It's a real game with real mechanics — streaks, equipment, god modifiers, ability stacking, anomaly events, boss fights — and it runs on actual university-level content (DSA, algorithms, complexity theory, etc.).

---

## Demo

![C.R.A.M Combat Screen](static/index.html)

**Run it yourself:**
```bash
# Clone and run (Python 3.11+)
git clone https://github.com/HeisLazi/C.R.A.M.git
cd C.R.A.M
pip install -r requirements_launcher.txt
python launcher.py
```

Or run as a standalone Windows `.exe` — see [Building](#building).

---

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.11 + FastAPI + Uvicorn |
| Frontend | Vanilla HTML / CSS / JavaScript (no frameworks) |
| Desktop App | pywebview + PyInstaller |
| Data | JSON question banks (no database — stateless by design) |
| Build | PyInstaller (Windows `.exe`) |

No React, no Vue, no ORM. I kept it lean on purpose — every byte of the frontend is hand-written in `play.html`.

---

## Features

### Core Gameplay
- **Question-driven combat** — correct answers deal damage, wrong answers let the enemy hit back
- **Streak system** — consecutive correct answers multiply your damage (up to ×3.4)
- **Procedural world** — 10-depth graph with combat nodes, taverns, anomaly events, and boss rooms
- **Tutorial mode** — guided intro with hand-crafted dialogue from Sir GetRICH and Cpt Shanyok

### Game Systems
- **Equipment** — weapons and armour with unique abilities (Binary Blade, Recursive Echo, Life Steal, etc.)
- **Ability stacking** — T2 weapon abilities carry over when upgrading to T3
- **God domains** — Aurex, Vyra, Khalen, Thren, Nyx — each modifies damage in a different direction
- **Run modifiers** — Glass Cannon, Focused Mind, Corrupted, Precision — picked per run
- **Anomaly events** — high-risk non-combat puzzles that permanently debuff you on failure
- **Codex** — tracks every question you've gotten wrong so you can review your mistakes
- **Past Papers mode** — timed quiz mode filtered by concept, tier, and question type
- **Ancient Library** — in-game PDF viewer for study materials tied to subjects

### Study Content
Subjects are swappable JSON question banks. Shipped with:
- **DSA2** — Binary trees, AVL trees, recursion, sorting algorithms, complexity analysis
- **ARI** — Arithmetic & reasoning
- **CTE** — Core theory
- **DTN** / **MAP** / **SPS** / **SVV** — Additional modules

Each subject folder contains `questions.json`, `concepts.json`, and optional PDF resources the Library pulls from.

---

## Architecture

```
C.R.A.M/
├── backend/
│   ├── main.py              # FastAPI entry point — all API routes
│   ├── combat.py            # Combat session state + damage resolution
│   ├── question_engine.py   # Question loading, filtering, answer evaluation
│   ├── equipment.py         # Weapons, armour, ability effects
│   ├── world.py             # Procedural world graph generation
│   ├── overworld.py         # Node detail, player state, progression
│   ├── progression.py       # XP + leveling system
│   ├── anomaly.py           # Non-combat anomaly challenge system
│   ├── run_modifiers.py     # Per-run modifier effects
│   ├── node_effects.py      # Node action handlers
│   ├── node_interaction.py  # Action availability by node type
│   ├── codex.py             # Attempt history + mistake tracking
│   ├── save.py              # In-memory save/load
│   └── tutorial_questions.py # Hardcoded general-knowledge tutorial Qs
│
├── play.html                # Entire frontend (~4500 lines, single file)
├── launcher.py              # Desktop app entry (pywebview wrapper)
├── static/                  # Static assets
├── subjects/                # Swappable question banks (JSON + PDFs)
├── docs/                    # Development documentation
│   ├── ARCHITECTURE.md
│   ├── DEVLOG.md
│   ├── DEVELOPMENT_RULES.md
│   ├── GAME_STORY.md
│   └── NEXT_STEPS.md
├── CRAM_SUBJECT_TEMPLATE.json  # Template for creating new subjects
├── CRAM_The_Unbound.spec       # PyInstaller build spec
├── build_windows.bat           # One-click Windows build script
└── requirements_launcher.txt   # Python dependencies
```

---

## Key Implementation Details

**Combat damage formula** (applied in sequence):
```
base_damage  = PLAYER_BASE_DAMAGE × dice_roll × streak_multiplier × weapon_multiplier
scaled       = base_damage × level_scaling         # +5% per level
god_modified = scaled × god_multiplier
run_modified = god_modified × run_multiplier
final        = run_modified + weapon_ability_bonus
```

**World generation:**
- Citadel at depth 0 → 10 depth layers with 2–4 nodes each
- Forward connections (depth → depth+1), occasional lateral same-depth links
- Difficulty scales with depth; node type distribution shifts (more elites/bosses late game)

**Ability stacking:**  
When a player upgrades from a T2 to T3 weapon, the T2 ability ID is pushed into `playerBonusAbilities[]`. The backend's `apply_weapon_ability_on_hit()` fires all abilities in the stack — with echo deduplication (only highest echo tier fires).

**Tutorial flow:**  
The tutorial uses a completely self-contained answer handler (`/api/tutorial/answer`) that evaluates against `TUTORIAL_QUESTIONS` directly — no dependency on the regular question bank, which might not be loaded.

---

## Building

Requires Python 3.11+ and the dependencies in `requirements_launcher.txt`.

```bash
pip install -r requirements_launcher.txt

# Run in dev mode (browser)
uvicorn backend.main:app --reload --port 8000
# then open play.html in a browser

# Run as desktop app
python launcher.py

# Build Windows .exe
build_windows.bat
```

---

## What I learned building this

- Designing a **modular backend** where combat, questions, equipment, and progression are all separate systems that interact through clean interfaces
- Managing **in-memory session state** across a stateless HTTP API (UUID-keyed dicts, proper lifecycle management)
- Building a **single-file frontend** at scale — `play.html` is ~4500 lines of vanilla JS and CSS that renders the entire game without any build tools
- **Iterative game design** — balancing XP curves, damage formulas, and enemy difficulty through play-testing and adjustment
- Writing a **procedural world generator** with graph traversal, depth-aware node distribution, and bidirectional connection enforcement

---

## Development Docs

See the [`docs/`](docs/) folder for:
- [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system design decisions
- [`DEVLOG.md`](docs/DEVLOG.md) — development history
- [`DEVELOPMENT_RULES.md`](docs/DEVELOPMENT_RULES.md) — constraints and conventions
- [`GAME_STORY.md`](docs/GAME_STORY.md) — narrative and world lore

---

*C.R.A.M — The Unbound was built as a personal project to make revision less terrible. It's also what I give to interviewers when they ask if I have any side projects.*

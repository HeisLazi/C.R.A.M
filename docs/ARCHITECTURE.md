# ARCHITECTURE

## Backend

- **Runtime:** Python 3.11 + FastAPI + Uvicorn
- **Entry point:** `backend/main.py` — mounts API routes and serves the static HTML frontend
- **`combat.py`** — manages combat sessions (in-memory dict keyed by UUID), player/enemy state, damage resolution
- **`question_engine.py`** — stores questions, exposes `get_question()` and `evaluate_answer(question_id, chosen_answer)`

## Frontend

- Plain HTML/CSS/JS (`backend/static/index.html`)
- No frameworks, no build step
- Communicates with the backend via `fetch()` API calls to the same origin

## Core Gameplay Loop

```
Start Combat → Get Question → Player Picks Answer → Submit → Apply Damage → Show Result → Next Question
```

- Correct answer: multiplier = 1.0 → full player damage, normal enemy counterattack
- Wrong answer: multiplier = 0.0 → 0 player damage, enemy counterattack at +50% bonus

## Session System

- Each `POST /start_combat` generates a UUID `session_id`
- Session state (player, enemy, log, pending question) lives in `combat._sessions` dict
- Client stores the `session_id` and sends it with every `POST /answer` request
- Sessions are not persisted; they reset when the server restarts

## File Layout

```
backend/
  main.py               # FastAPI app, routes
  combat.py             # Session store, Combatant class, damage logic
  question_engine.py    # Question bank, evaluate_answer()
  static/
    index.html          # Single-page game frontend
context/
  DEVLOG.md
  ARCHITECTURE.md
  NEXT_STEPS.md
  RULES.md
```

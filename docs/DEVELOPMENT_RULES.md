# RULES

These rules exist to prevent regressions and scope creep. Any future agent or developer must read this before making changes.

---

## General

- Do NOT rewrite working systems — make targeted, minimal edits
- Do NOT introduce frameworks (React, Vue, etc.) unless explicitly requested
- Do NOT change the combat damage formula or multiplier system without documenting the reason in DEVLOG.md
- Do NOT remove or rename existing API endpoints — only add new ones

## Backend

- Keep the backend in Python (FastAPI)
- Keep `combat.py`, `question_engine.py`, and `main.py` as separate, single-responsibility modules
- Session state lives in `combat._sessions` — do not move it without updating all callers
- Answer evaluation must remain case-insensitive and stripped

## Frontend

- Keep the frontend as plain HTML/CSS/JS — no build tools, no bundlers
- All game state lives in JS variables (`sessionId`, `pendingQuestion`) — do not add a state library
- Disable answer buttons on submit; re-enable only on `nextRound()` or `resetGame()`

## Questions

- Questions must follow the standard format:
  ```json
  {
    "id": "...",
    "topic": "...",
    "question": "...",
    "options": ["...", "..."],
    "correct_answer": "...",
    "explanation": "..."
  }
  ```
- `correct_answer` must exactly match one entry in `options` (case-sensitive match for consistency, evaluated case-insensitively)

## Design Principles

- Prefer data-driven design (JSON files) over hardcoding
- Maintain strict separation: combat logic ≠ question logic ≠ presentation
- Explicit failures over silent fallbacks — raise errors, don't swallow them

# NEXT STEPS

## Phase 3 — Codex + Subject System

### Goals

- Move questions to `/subjects/dsa2/questions.json` (one file per subject)
- Load questions at startup from subject folders instead of hardcoding in `question_engine.py`
- Implement a **Codex** system:
  - Track which questions the player answered incorrectly
  - Store mistakes per session (later: persist to disk or DB)
  - Expose a `GET /codex/{session_id}` endpoint returning missed questions + explanations
- Add Codex UI panel to the frontend (collapsible, read-only review section)

### Constraints

- Do NOT modify `combat.py` combat logic
- Do NOT break the session system
- Keep the frontend simple — no frameworks
- New endpoints must not conflict with existing `/start_combat` and `/answer` routes

### Suggested File Changes

| File | Change |
|------|--------|
| `question_engine.py` | Load from JSON files instead of hardcoded list |
| `combat.py` | Append wrong answers to `session["codex"]` list |
| `main.py` | Add `GET /codex/{session_id}` route |
| `static/index.html` | Add collapsible Codex panel |
| `subjects/dsa2/questions.json` | New — houses DSA questions in standard format |

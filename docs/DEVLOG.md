# DEVLOG

## Phase 1 — Combat + Question System

- Implemented `question_engine.py` with string-based answers
- Integrated question system into combat using multiplier
- Added FastAPI endpoints:
  - `/start_combat`
  - `/answer`
- Built minimal frontend UI

### Decisions

- Used string-based answer validation instead of index
- Used multiplier system (1.0 correct, 0.0 incorrect)
- Kept combat system unchanged

### Known Limitations

- Questions still partially hardcoded
- No codex yet
- No subject modularity yet

---

## Phase 2 — UI + Stability Improvements

- Added session-based combat using UUID
- Improved frontend UI (HP bars, answer buttons, combat log)
- Added visual feedback (correct/incorrect highlighting, explanations)
- Prevented double submissions
- Added more questions (6 total covering Arrays, Trees, Sorting, Linked Lists, Big-O, Recursion)

### Decisions

- Used in-memory session storage (no database yet)
- Kept frontend simple (no React)
- String comparison is case-insensitive and stripped to reduce evaluation errors

### Known Limitations

- No persistence beyond runtime
- No codex system yet
- Questions not yet loaded from subject folders

---

## Current Stable State

- Combat + question loop fully working
- FastAPI backend running
- Frontend UI functional
- Session-based combat working
- String-based answer validation implemented

## Known Bugs

- None currently identified

## Ready For

- Phase 3: Codex + Subject system

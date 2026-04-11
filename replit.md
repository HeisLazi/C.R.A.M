# Workspace

## Overview

pnpm workspace monorepo (TypeScript) + Python/FastAPI game backend.

---

## Game — Origins: The Unbound (Learning RPG)

A web-based learning RPG where combat is driven by answering DSA study questions.

### Structure

```
backend/
  main.py             # FastAPI app — POST /start_combat, POST /answer, GET /
  combat.py           # Player/Enemy classes, session management, damage rules
  question_engine.py  # Load questions from JSON, evaluate answers

subjects/dsa2/
  concepts.json       # 5 DSA concepts (recursion, binary search, BST, big-O, AVL)
  questions.json      # 8 questions mapped to concepts

static/
  index.html          # Plain HTML/CSS/JS game UI — no frameworks
```

### Workflow

**Game Backend** — runs `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload`

### Gameplay Loop

1. `POST /start_combat` — creates a UUID session, picks a random enemy (linked to a concept), returns first question
2. `POST /answer` — evaluates answer, applies damage:
   - Correct → player deals 20 damage to enemy
   - Wrong → player deals 0 damage, enemy counterattacks for `base_damage + bonus_damage`
3. Next question is served automatically until one side reaches 0 HP

### Rules

- Do NOT hardcode questions in Python — all questions come from JSON
- Session state lives in `combat._sessions` — do not move it
- Answer evaluation is case-insensitive and stripped
- Keep `combat.py`, `question_engine.py`, and `main.py` as separate modules
- Keep frontend as plain HTML/CSS/JS — no React, no bundlers

### Phase Status

- Phase 1 ✅ — Combat loop, question system, session management, frontend UI
- Phase 2 (next) — Codex system (mistake tracking), more concepts/questions

---

## TypeScript Stack (existing monorepo)

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)

## Key Commands

- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `pnpm --filter @workspace/api-server run dev` — run TypeScript API server locally

# Educational RPG Learning Platform (C.R.A.M)

An educational RPG web application that makes learning computer science concepts engaging through gamified combat and challenge systems.

## What I Built

This is a full-stack learning RPG I built to make practicing programming concepts more interactive and fun. Instead of traditional quizzes, players explore a procedural world, fight enemies by answering questions correctly, and complete challenges to progress.

## Features

**Procedural World Generation** — A dynamically generated graph-based world with depth-scaled difficulty. Each playthrough creates a unique map with different node types (combat, challenge, utility, event) and connections.

**Question-Driven Combat** — Combat uses actual programming questions. Correct answers deal damage to enemies while wrong answers let enemies counterattack. The streak system rewards consecutive correct answers with increasing damage multipliers.

**Progression System** — Earn XP from completing challenges to level up. Leveling increases your damage and max HP. The game tracks your progress through the Codex which records all questions attempted.

**Layered Modifiers** — Multiple systems interact to create varied gameplay: level scaling, streak bonuses, god domains (Aurex, Vyra, Khalen, Thren, Nyx), equipment abilities, and run-wide modifiers like Glass Cannon or Focused Mind.

**Anomaly Challenges** — Non-combat puzzles where you solve sequences, logic problems, and multiple-choice questions to earn XP rewards.

**Equipment System** — Different weapons and armor provide passive bonuses and special abilities that synergize with other modifier systems.

**Save System** — In-memory session storage lets you save and load your progress within a running server session.

## Tech Stack

| Technology   | Purpose               |
| ------------ | --------------------- |
| React 18     | Frontend framework    |
| TypeScript   | Type safety           |
| FastAPI      | Backend API framework |
| Python       | Backend logic         |
| Vite         | Frontend build tool   |
| Tailwind CSS | Styling               |

## Getting Started

### Backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 to play.

## Project Structure

```
backend/
├── main.py           # FastAPI entry point and routes
├── combat.py         # Combat resolution system
├── world.py          # Procedural world generation
├── anomaly.py        # Challenge puzzle system
├── progression.py    # XP and leveling system
├── equipment.py      # Weapons and armor definitions
├── node_effects.py   # Node action handlers
├── run_modifiers.py  # Run-wide gameplay modifiers
├── save.py           # Session save/load system
├── codex.py          # Question attempt tracking
└── question_engine.py # Question data and evaluation

frontend/
├── src/
│   └── App.tsx        # Main React application
└── play.html          # Alternative HTML player
```

## Notes

This project demonstrates my ability to build full-stack applications with clean architecture. I've focused on making the code modular so each system (combat, world generation, progression) can be understood and modified independently. The layered modifier system shows how multiple game mechanics can interact without becoming tangled.

The game runs entirely in-memory without a database — this was a design choice to keep the project self-contained and easy to run. In a production environment, I'd add database persistence.

Built by Lazarus Petrus

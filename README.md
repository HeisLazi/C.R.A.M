# Educational RPG Learning Platform (C.R.A.M)

An educational RPG web application that makes learning computer science concepts engaging through gamified combat and challenge systems.

## What I Built

This is a full-stack learning RPG I built to make practicing programming concepts more interactive and fun. Instead of traditional quizzes, players explore a procedural world, fight enemies by answering questions correctly, and complete challenges to progress.

## Features

**Procedural World Generation** — A dynamically generated graph-based world with depth-scaled difficulty. Each playthrough creates a unique map with different node types (combat, challenge, utility, event, hub) and connections. The world spans 10 depth levels with bidirectional connections between nodes.

**Question-Driven Combat** — Combat uses actual programming questions from topics like recursion, binary search, trees, and complexity analysis. Correct answers deal damage to enemies while wrong answers let enemies counterattack. The streak system rewards consecutive correct answers with increasing damage multipliers (1.10x at 2 streak, 1.25x at 3+ streak).

**Layered Modifier System** — Multiple systems interact to create varied gameplay:

- Level scaling: +5% player damage, +3% enemy damage per level
- God domains: Aurex (streak boost), Vyra (consecutive hits), Khalen (damage reduction), Thren (damage boost), Nyx (asymmetric boost)
- Equipment abilities: Binary Blade, Recursive Staff, Balance Shift
- Run modifiers: Glass Cannon, Focused Mind, Corrupted, Precision

**Anomaly Challenges** — Non-combat puzzles where you solve sequences, logic problems, and multiple-choice questions to earn XP rewards. Each anomaly has 2-4 steps and can be attempted at normal or hard difficulty.

**Equipment System** — Three weapon types (Binary Blade, Recursive Staff, Balance Edge) and two armor types (Data Vest, Stack Plate) with special abilities that synergize with god domains and level scaling.

**Progression System** — Earn XP from completing anomalies to level up. Leveling increases your damage (+5% per level), max HP (+5 per level), and provides a full heal on level up. XP required per level: 50 \* level.

**Save System** — In-memory session storage lets you save and load your progress within a running server session.

**Codex Tracking** — Records all question attempts, tracking correct/incorrect answers and identifying areas needing improvement.

## Tech Stack

| Technology  | Purpose                      |
| ----------- | ---------------------------- |
| Python      | Backend logic                |
| FastAPI     | REST API framework           |
| HTML/CSS/JS | Browser-based game interface |
| Vite        | Optional frontend build      |

## Getting Started

### Running the Backend

```bash
cd backend
pip install fastapi uvicorn pydantic
python -m uvicorn main:app --reload --port 8000
```

### Playing the Game

Simply open `play.html` in your browser. The HTML file connects directly to the backend API at `http://localhost:8000`.

Click "Start Game" to begin your adventure!

## Project Structure

```
backend/
├── main.py              # FastAPI entry point and game API routes
├── combat.py            # Combat resolution with layered damage formula
├── world.py             # Procedural graph-based world generation
├── anomaly.py           # Non-combat puzzle challenge system
├── progression.py      # XP and leveling system
├── equipment.py         # Weapons, armor, and ability effects
├── node_effects.py     # Node action handlers (engage, investigate, etc.)
├── node_interaction.py # Action availability by node type
├── run_modifiers.py    # Run-wide modifiers (Glass Cannon, etc.)
├── save.py             # In-memory save/load system
├── codex.py           # Question attempt tracking
├── question_engine.py  # Question data and answer evaluation
└── overworld.py        # Alternative world system (legacy)

play.html               # Browser-based game interface
```

## Key Implementation Details

**Combat Damage Formula** (applied in order):

1. Base damage = 20 _ dice_roll _ streak_mult \* weapon_mult
2. Level scaling: damage _= (1 + (level-1) _ 0.05)
3. God modifiers: damage \*= god_multiplier
4. Run modifiers: damage \*= run_modifier
5. Weapon ability: add ability_bonus

**World Generation Algorithm**:

- Create hub node at depth 0 (citadel)
- For each depth 1-10: generate 2-4 nodes with weighted type distribution
- Connect forward: each node connects to 1-2 nodes at depth+1
- Connect laterally: occasional same-depth connections
- Enforce bidirectional connections

**Anomaly Session Flow**:

- Player investigates/stabilizes at anomaly node
- Generate 2-4 questions based on node seed
- Player answers sequentially
- Correct: progress to next step or complete
- Wrong: fail and return to map
- Completion awards XP (10 normal, 20 hard)

## Notes

This project demonstrates my ability to build full-stack applications with clean architecture. Each system is modular and can be understood independently. The layered modifier system shows how multiple game mechanics can interact without becoming tangled — something I learned through iterative development.

The game runs entirely in-memory without a database — this was a design choice to keep the project self-contained and easy to run. In a production environment, I'd add database persistence.

Built by Lazarus Petrus

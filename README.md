# Educational RPG Learning Platform (C.R.A.M)

An educational RPG web application that makes learning computer science concepts engaging through gamified combat and challenge systems.

## What I Built

This is a full-stack learning RPG I built to make practicing programming concepts more interactive and fun. Instead of traditional quizzes, players explore a procedural world, fight enemies by answering questions correctly, and complete challenges to progress.

## Features

**Procedural World Generation** — A dynamically generated graph-based world with depth-scaled difficulty. Each playthrough creates a unique map with different node types (combat, challenge, utility, event, hub) and connections. The world spans 10 depth levels with bidirectional connections between nodes, rendered as an interactive spatial map.

**Question-Driven Combat** — Combat uses actual programming questions from topics like recursion, binary search, trees, and complexity analysis. Features include:

- Multiple question types: multiple choice, true/false, and open-ended self-evaluation
- Streak system rewarding consecutive correct answers with increasing damage multipliers
- Visual combat arena with animated fighters and particle effects
- Damage popups and hit animations
- Insight system for revealing hints

**Layered Modifier System** — Multiple systems interact to create varied gameplay:

- Level scaling: +5% player damage, +3% enemy damage per level
- God domains: Aurex (streak boost), Vyra (consecutive hits), Khalen (damage reduction), Thren (damage boost), Nyx (asymmetric boost)
- Equipment abilities: Binary Blade, Recursive Staff, Balance Shift
- Run modifiers: Glass Cannon, Focused Mind, Corrupted, Precision
- Debuffs from anomaly failures

**Game Modes** — Multiple ways to play:

- **Run Mode**: Explore the world, fight enemies, complete challenges
- **Past Papers Mode**: Timed quizzes with filtering by concept and difficulty
- **Codex**: Review mistakes from previous runs
- **Ancient Library**: Browse PDF resources from various subjects

**Anomaly Challenges** — Non-combat puzzles with multiple steps including logic problems and self-evaluation questions. Features warning screens and debuff system for failures.

**Progression System** — Earn XP from completing challenges to level up. Features:

- XP bars showing progress to next level
- Level up animations
- HP and damage scaling with level
- Insight charges for hints
- Upgrades and crafting system

**Equipment System** — Weapon and armor selection with ability system that synergizes with god domains and level scaling.

**Tavern / Site of Grace** — Rest area for healing, changing equipment, viewing bestiary, and accessing upgrades.

**Subject System** — Switch between different JSON question sets (DSA2, etc.) for varied content.

## Tech Stack

| Technology  | Purpose                      |
| ----------- | ---------------------------- |
| Python      | Backend logic                |
| FastAPI     | REST API framework           |
| HTML/CSS/JS | Browser-based game interface |
| PDF.js      | PDF rendering in browser     |

## Getting Started

### Running the Backend

```bash
cd backend
pip install fastapi uvicorn pydantic
python -m uvicorn main:app --reload --port 8000
```

### Playing the Game

Simply open `play.html` in your browser. The HTML file connects directly to the backend API at `http://localhost:8000`.

Click "Begin Your Run" to start your adventure, or explore:

- 📜 Past Papers Mode — Quick revision quizzes
- 📕 Open Codex — Review your mistakes
- 📚 Ancient Library — Browse PDF resources
- 📂 Switch Subject — Change question sets

## Project Structure

```
backend/
├── main.py              # FastAPI entry point and game API routes
├── combat.py            # Combat resolution with layered damage formula
├── world.py             # Procedural graph-based world generation
├── anomaly.py           # Non-combat puzzle challenge system
├── progression.py      # XP and leveling system
├── equipment.py         # Weapons, armor, and ability effects
├── node_effects.py     # Node action handlers
├── node_interaction.py # Action availability by node type
├── run_modifiers.py    # Run-wide modifiers
├── save.py             # In-memory save/load system
├── codex.py           # Question attempt tracking
├── question_engine.py  # Question data and answer evaluation
└── overworld.py       # Alternative world system

play.html               # Browser-based game interface (full UI overhaul)
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

**Multiple Question Types**:

- Multiple choice (4 options)
- True/False
- Open-ended self-evaluation with model answer reveal
- PDF viewing for study materials

## Notes

This project demonstrates my ability to build full-stack applications with clean architecture. Each system is modular and can be understood independently. The layered modifier system shows how multiple game mechanics can interact without becoming tangled — something I learned through iterative development.

The game runs entirely in-memory without a database — this was a design choice to keep the project self-contained and easy to run. In a production environment, I'd add database persistence.

Built by Lazarus Petrus

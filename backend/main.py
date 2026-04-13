"""
main.py

FastAPI entry point.

Endpoints:
  GET  /                                    → serves index.html
  POST /start_combat                        → creates a new combat session
  POST /answer                              → resolves a player's answer
  POST /insight                             → uses one insight charge
  GET  /codex/{session_id}                  → full attempt history
  GET  /codex/{session_id}/mistakes         → only incorrect attempts

  POST /world/generate                      → create a new procedural world
  GET  /world/{world_id}                    → fetch world state + all nodes
  GET  /world/{world_id}/player             → player HP / equipment / bonus
  GET  /world/{world_id}/node/{node_id}     → node detail + interaction options
  POST /world/{world_id}/node/{node_id}/state → update node state
  POST /world/{world_id}/node/{node_id}/combat → start combat from a node
  POST /world/{world_id}/tavern/rest        → tavern rest (heal + insight)
  POST /world/{world_id}/equip              → update player equipment
  GET  /world/{world_id}/lazi              → Lazi dialogue using codex data
"""

import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.combat    import start_combat, resolve_action, use_insight
from backend.codex     import log_attempt, get_codex, get_mistakes
from backend.question_engine import get_question_by_id
from backend.overworld import (
    generate_world, get_world, get_node_detail,
    update_node_state, tavern_rest, set_equipment,
    get_player_state, apply_combat_result, lazi_dialogue,
)
from backend.world import generate_world as gen_world

app = FastAPI(title="Origins: The Unbound — Learning RPG")

# Allow all origins so the browser doesn't block requests from play.html / React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Path resolution — works both from source and when frozen by PyInstaller ──
#
# PyInstaller 6+ (--onedir) layout:
#   dist/CRAM_The_Unbound/
#     CRAM_The_Unbound.exe      ← sys.executable
#     subjects/                 ← user-editable, lives NEXT TO the .exe
#     _internal/                ← sys._MEIPASS  (bundled read-only data)
#       static/
#       play.html
#       CRAM_SUBJECT_TEMPLATE.json
#
# When running from source, everything is relative to the project root.
if getattr(sys, 'frozen', False):
    _BUNDLE_DIR = Path(sys._MEIPASS)          # _internal/ — bundled assets
    _APP_ROOT   = Path(sys.executable).parent  # next to .exe — user files
else:
    _BUNDLE_DIR = Path(__file__).parent.parent
    _APP_ROOT   = Path(__file__).parent.parent

STATIC_DIR   = _BUNDLE_DIR / "static"
SUBJECTS_DIR = _APP_ROOT   / "subjects"
PLAY_HTML    = _BUNDLE_DIR / "play.html"

app.mount("/static",   StaticFiles(directory=str(STATIC_DIR)),   name="static")
app.mount("/subjects", StaticFiles(directory=str(SUBJECTS_DIR)), name="subjects")


# ────────────────────────────────────────────────────────────────────────────
# Static
# ────────────────────────────────────────────────────────────────────────────
@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/play")
def play():
    """
    Serve play.html — used by the pywebview launcher so the window points at
    http://127.0.0.1:8000/play instead of opening the file directly.
    """
    return FileResponse(str(PLAY_HTML))


# ────────────────────────────────────────────────────────────────────────────
# .exe / desktop utilities
# ────────────────────────────────────────────────────────────────────────────
@app.post("/api/open_subjects_folder")
def open_subjects_folder():
    """
    Open the subjects/ directory in the OS file manager.
    Called by the in-game 'Add Subject' button so players can drop new
    subject folders in without touching the command line.
    """
    import platform, subprocess
    path = str(SUBJECTS_DIR)
    SUBJECTS_DIR.mkdir(parents=True, exist_ok=True)  # create it if it doesn't exist yet
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return {"ok": True, "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reload_subjects")
def reload_subjects():
    """
    Force the question engine to rescan the subjects/ folder and reload the
    active subject's questions. Used by the in-game Refresh button so players
    don't need to restart after dropping in a new subject.
    """
    from backend.question_engine import reload_questions, list_subjects, get_active_subject
    count = reload_questions()
    return {
        "ok": True,
        "active": get_active_subject(),
        "question_count": count,
        "subjects": list_subjects(),
    }


# ────────────────────────────────────────────────────────────────────────────
# Combat
# ────────────────────────────────────────────────────────────────────────────
class StartCombatRequest(BaseModel):
    concept_id:      Optional[str]  = None
    weapon_id:       str            = "none"
    armor_id:        str            = "none"
    node_god:        Optional[str]  = None
    node_modifiers:  list[str]      = []
    bonus_insight:   int            = 0
    is_anomaly:      bool           = False
    node_difficulty: int            = 1
    bonus_abilities: list[str]      = []    # stacked abilities from prior weapon tiers


class AnswerRequest(BaseModel):
    session_id:  str
    question_id: str
    answer:      str


class InsightRequest(BaseModel):
    session_id: str


@app.post("/start_combat")
def post_start_combat(body: StartCombatRequest = StartCombatRequest()):
    try:
        return start_combat(
            concept_id=body.concept_id,
            weapon_id=body.weapon_id,
            armor_id=body.armor_id,
            node_god=body.node_god,
            node_modifiers=body.node_modifiers,
            bonus_insight=body.bonus_insight,
            is_anomaly=body.is_anomaly,
            node_difficulty=body.node_difficulty,
            bonus_abilities=body.bonus_abilities,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/answer")
def post_answer(body: AnswerRequest):
    try:
        result = resolve_action(
            session_id=body.session_id,
            question_id=body.question_id,
            answer=body.answer,
        )
        try:
            q = get_question_by_id(body.question_id)
            log_attempt(
                session_id=body.session_id,
                question_id=body.question_id,
                question_text=q["question"] if q else body.question_id,
                selected_answer=body.answer,
                correct_answer=result["correct_answer"],
                correct=result["correct"],
                explanation=result["explanation"],
                round=result["round"],
            )
        except Exception:
            pass
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class PeekRequest(BaseModel):
    question_id: str


@app.post("/peek_answer")
def post_peek_answer(body: PeekRequest):
    """Return model answer for an open-ended question without affecting combat state."""
    from backend.question_engine import get_question_by_id
    q = get_question_by_id(body.question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return {
        "correct_answer": q.get("correct_answer", ""),
        "explanation":    q.get("explanation", ""),
        "question_type":  q.get("type", "multiple_choice"),
    }


@app.post("/insight")
def post_insight(body: InsightRequest):
    try:
        return use_insight(session_id=body.session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/codex/{session_id}")
def get_codex_endpoint(session_id: str):
    return {"entries": get_codex(session_id)}


@app.get("/codex/{session_id}/mistakes")
def get_mistakes_endpoint(session_id: str):
    return {"entries": get_mistakes(session_id)}


# ────────────────────────────────────────────────────────────────────────────
# Overworld
# ────────────────────────────────────────────────────────────────────────────
class GenerateWorldRequest(BaseModel):
    seed: Optional[int] = None


class NodeStateRequest(BaseModel):
    state: str          # "unvisited" | "visited" | "cleared"


class NodeCombatRequest(BaseModel):
    world_id:    str
    node_id:     str


class EquipRequest(BaseModel):
    weapon_id: str = "none"
    armor_id:  str = "none"


class CombatResultRequest(BaseModel):
    player_hp_after: int


class LaziRequest(BaseModel):
    session_id: Optional[str] = None


@app.post("/world/generate")
def post_generate_world(body: GenerateWorldRequest = GenerateWorldRequest()):
    return generate_world(seed=body.seed)


@app.get("/world/{world_id}")
def get_world_endpoint(world_id: str):
    try:
        return get_world(world_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/world/{world_id}/player")
def get_player_endpoint(world_id: str):
    try:
        return get_player_state(world_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/world/{world_id}/node/{node_id}")
def get_node_endpoint(world_id: str, node_id: str):
    try:
        return get_node_detail(world_id, node_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/world/{world_id}/node/{node_id}/state")
def post_node_state(world_id: str, node_id: str, body: NodeStateRequest):
    try:
        return update_node_state(world_id, node_id, body.state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class NodeCombatRequest(BaseModel):
    bonus_abilities: list[str] = []   # stacked abilities from prior weapon tiers


@app.post("/world/{world_id}/node/{node_id}/combat")
def post_node_combat(world_id: str, node_id: str, body: NodeCombatRequest = NodeCombatRequest()):
    """Start combat from a specific node, injecting its metadata into the session."""
    try:
        detail = get_node_detail(world_id, node_id)
        node   = detail["node"]
        player = get_player_state(world_id)

        # Mark node as visited
        update_node_state(world_id, node_id, "visited")

        return start_combat(
            weapon_id=player["weapon_id"],
            armor_id=player["armor_id"],
            node_god=node.get("god"),
            node_modifiers=node.get("modifiers", []),
            bonus_insight=player["bonus_insight"],
            bonus_abilities=body.bonus_abilities,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/world/{world_id}/node/{node_id}/cleared")
def post_node_cleared(world_id: str, node_id: str, body: CombatResultRequest):
    """Mark a node cleared after combat and sync player HP."""
    try:
        apply_combat_result(world_id, body.player_hp_after)
        return update_node_state(world_id, node_id, "cleared")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/world/{world_id}/tavern/rest")
def post_tavern_rest(world_id: str):
    try:
        return tavern_rest(world_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/world/{world_id}/equip")
def post_equip(world_id: str, body: EquipRequest):
    try:
        return set_equipment(world_id, body.weapon_id, body.armor_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/world/{world_id}/lazi")
def get_lazi_endpoint(world_id: str, session_id: Optional[str] = None, depth: int = 0):
    try:
        mistake_topics: list[str] = []
        if session_id:
            mistakes = get_mistakes(session_id)
            mistake_topics = list({m["question_id"].split("_")[0] for m in mistakes})
        world = get_world(world_id)
        text = lazi_dialogue(world_id, mistake_topics, depth)
        return {"text": text}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ────────────────────────────────────────────────────────────────────────────
# Game Session (simplified)
# ────────────────────────────────────────────────────────────────────────────
from backend.run_modifiers import assign_random_modifiers


class GameSession:
    def __init__(self):
        self.world = gen_world()
        self.current_node = "citadel"
        self.level = 1
        self.xp = 0
        self.hp = 100
        self.max_hp = 100
        self.insight = 0
        self.modifiers = assign_random_modifiers()
        self.weapon_id = "none"
        self.armor_id  = "none"
        self.debuffs: list = []          # permanent debuffs from anomaly losses


_sessions: dict[str, GameSession] = {}


class MoveRequest(BaseModel):
    session_id: str
    target_node_id: str


@app.post("/api/game/start")
def start_game() -> dict:
    session_id = f"session_{len(_sessions) + 1}"
    _sessions[session_id] = GameSession()
    return {
        "session_id": session_id,
        "world": {nid: _node_to_dict(n) for nid, n in _sessions[session_id].world.items()},
        "current_node": _sessions[session_id].current_node,
    }


@app.get("/api/game/world/{session_id}")
def get_game_world(session_id: str) -> dict:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = _sessions[session_id]
    # Tutorial sessions have world=None (they use a flat dict, not WorldNode objects)
    world_out = {}
    if session.world is not None:
        try:
            world_out = {nid: _node_to_dict(n) for nid, n in session.world.items()}
        except Exception:
            world_out = {}
    return {
        "world": world_out,
        "current_node": session.current_node,
        "level": session.level,
        "xp": session.xp,
        "hp": session.hp,
        "max_hp": session.max_hp,
        "modifiers": session.modifiers,
        "insight": session.insight,
        "weapon_id": getattr(session, "weapon_id", "none"),
        "armor_id":  getattr(session, "armor_id", "none"),
        "debuffs":   getattr(session, "debuffs", []),
        "upgrades":  getattr(session, "upgrades", []),
    }


class EquipRequest(BaseModel):
    session_id: str
    weapon_id: Optional[str] = None
    armor_id:  Optional[str] = None

@app.post("/api/game/equip")
def equip_items(body: EquipRequest) -> dict:
    if body.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = _sessions[body.session_id]
    from backend.equipment import WEAPONS, ARMORS
    if body.weapon_id and body.weapon_id in WEAPONS:
        session.weapon_id = body.weapon_id
    if body.armor_id and body.armor_id in ARMORS:
        session.armor_id = body.armor_id
    return {
        "weapon_id": session.weapon_id,
        "armor_id": session.armor_id,
        "message": "Equipment updated.",
    }


@app.post("/api/game/move")
def move_node(body: MoveRequest) -> dict:
    if body.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = _sessions[body.session_id]
    current = session.world.get(session.current_node)
    if not current:
        raise HTTPException(status_code=400, detail="Current node not found")
    if body.target_node_id not in current.connections:
        raise HTTPException(status_code=400, detail="Cannot move to that node")
    session.current_node = body.target_node_id
    target = session.world[body.target_node_id]
    return {
        "node": _node_to_dict(target),
        "current_node": session.current_node,
    }


@app.get("/api/game/node/{session_id}")
def get_game_node(session_id: str) -> dict:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = _sessions[session_id]
    node = session.world.get(session.current_node)
    if not node:
        raise HTTPException(status_code=400, detail="Current node not found")
    from backend.node_interaction import get_node_actions
    actions = get_node_actions(node)
    return {
        "node": _node_to_dict(node),
        "actions": actions,
    }


class NodeActionRequest(BaseModel):
    session_id: str
    action_id: str


@app.post("/api/game/node/action")
def do_node_action(body: NodeActionRequest) -> dict:
    if body.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = _sessions[body.session_id]
    from backend.node_effects import apply_node_action
    result = apply_node_action(session, body.action_id)

    # If combat is starting from an anomaly node, wire the is_anomaly flag through
    if result.get("type") == "combat_started" and result.get("is_anomaly"):
        # Store anomaly flag on session so endCombat can trigger debuff
        session._pending_anomaly = True
    else:
        session._pending_anomaly = False

    return result


class AnomalyDebuffRequest(BaseModel):
    session_id: str


@app.post("/api/game/anomaly/debuff")
def apply_anomaly_debuff_endpoint(body: AnomalyDebuffRequest) -> dict:
    """Apply a permanent debuff to the player after losing an anomaly combat."""
    if body.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = _sessions[body.session_id]
    from backend.node_effects import apply_anomaly_debuff
    debuff = apply_anomaly_debuff(session)
    return {
        "debuff": debuff,
        "all_debuffs": getattr(session, "debuffs", []),
        "hp": session.hp,
        "max_hp": session.max_hp,
    }


def _node_to_dict(node) -> dict:
    return {
        "id": node.id,
        "type": node.type,
        "subtype": node.subtype,
        "biome": node.biome,
        "depth": node.depth,
        "difficulty": node.difficulty,
        "modifiers": node.modifiers,
        "connections": node.connections,
        "state": node.state,
        "seed": node.seed,
        "god": node.god,
    }


# ────────────────────────────────────────────────────────────────────────────
# Tutorial Routes
# ────────────────────────────────────────────────────────────────────────────

# Tutorial uses its own simple linear world, separate from normal procedural gen
# Structure: citadel → tut_combat_1 → tut_tavern → tut_combat_2 → tut_boss
_TUTORIAL_WORLD = {
    "citadel": {
        "id": "citadel", "type": "citadel", "subtype": "start", "biome": "tutorial",
        "depth": 0, "difficulty": 0, "modifiers": [], "god": None, "seed": 0,
        "connections": ["tut_combat_1"], "state": "active",
        "tutorial_step": "intro",
    },
    "tut_combat_1": {
        "id": "tut_combat_1", "type": "combat", "subtype": "guard", "biome": "tutorial",
        "depth": 1, "difficulty": 1, "modifiers": [], "god": None, "seed": 1,
        "connections": ["tut_tavern"], "state": "pending",
        "tutorial_step": "first_combat",
    },
    "tut_tavern": {
        "id": "tut_tavern", "type": "tavern", "subtype": "rest", "biome": "tutorial",
        "depth": 2, "difficulty": 0, "modifiers": [], "god": None, "seed": 2,
        "connections": ["tut_combat_2"], "state": "pending",
        "tutorial_step": "tavern",
    },
    "tut_combat_2": {
        "id": "tut_combat_2", "type": "combat", "subtype": "elite", "biome": "tutorial",
        "depth": 3, "difficulty": 2, "modifiers": [], "god": None, "seed": 3,
        "connections": ["tut_boss"], "state": "pending",
        "tutorial_step": "second_combat",
    },
    "tut_boss": {
        "id": "tut_boss", "type": "boss", "subtype": "boss", "biome": "tutorial",
        "depth": 4, "difficulty": 3, "modifiers": [], "god": None, "seed": 4,
        "connections": [], "state": "pending",
        "tutorial_step": "boss",
    },
}

_tutorial_sessions: dict[str, GameSession] = {}


@app.post("/api/tutorial/start")
def start_tutorial() -> dict:
    """Start a tutorial run with a linear world and easy general-knowledge questions."""
    import copy
    session_id = f"tutorial_{len(_tutorial_sessions) + 1}"
    session = GameSession.__new__(GameSession)
    session.world      = None           # tutorial uses flat dict, not gen_world() nodes
    session.current_node = "citadel"
    session.level      = 1
    session.xp         = 0
    session.hp         = 100
    session.max_hp     = 100
    session.insight    = 0
    session.modifiers  = []
    session.weapon_id  = "none"
    session.armor_id   = "none"
    session.debuffs    = []
    session.is_tutorial = True
    _tutorial_sessions[session_id] = session
    _sessions[session_id] = session    # share the same dict so /api/game/* routes work

    world_out = copy.deepcopy(_TUTORIAL_WORLD)
    return {
        "session_id": session_id,
        "world": world_out,
        "current_node": "citadel",
        "is_tutorial": True,
    }


@app.post("/api/tutorial/combat/start")
def start_tutorial_combat(body: StartCombatRequest = StartCombatRequest()):
    """Start a tutorial combat with easy general-knowledge questions."""
    from backend.tutorial_questions import get_tutorial_question
    try:
        # Use start_combat but override the question with a tutorial one
        result = start_combat(
            weapon_id=body.weapon_id,
            armor_id=body.armor_id,
            node_difficulty=body.node_difficulty or 1,
            bonus_insight=body.bonus_insight,
            bonus_abilities=body.bonus_abilities,
        )
        # Replace the question with a tutorial-level one
        seen: set = set()
        tut_q = get_tutorial_question(seen)
        if tut_q:
            # Find and update the session's current question
            from backend.combat import _sessions as _combat_sessions
            csession = _combat_sessions.get(result["session_id"])
            if csession:
                csession.current_question = tut_q
                csession.question_tier    = "tutorial"
                csession.seen_question_ids = {tut_q["id"]}
            result["question"] = {
                "id":       tut_q["id"],
                "question": tut_q["question"],
                "options":  tut_q.get("options", []),
                "type":     tut_q.get("type", "multiple_choice"),
                "tier":     "tutorial",
                "concept":  "general",
            }
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tutorial/answer")
def answer_tutorial(body: AnswerRequest):
    """
    Self-contained tutorial answer handler.
    Does NOT call resolve_action — evaluates entirely from TUTORIAL_QUESTIONS
    so the regular question bank is never touched.
    """
    import random as _rand
    from backend.tutorial_questions import TUTORIAL_QUESTIONS, get_tutorial_question
    from backend.combat import _sessions as _combat_sessions

    # ── 1. Fetch the combat session ─────────────────────────────────────────
    csession = _combat_sessions.get(body.session_id)
    if csession is None:
        raise HTTPException(status_code=404, detail="Tutorial session not found.")
    if csession.over:
        raise HTTPException(status_code=400, detail="Combat already over.")

    # ── 2. Find the question in TUTORIAL_QUESTIONS ──────────────────────────
    tut_q = next((q for q in TUTORIAL_QUESTIONS if q["id"] == body.question_id), None)
    if tut_q is None:
        # Fallback: accept any question still in the session
        tut_q = csession.current_question
        if tut_q is None:
            raise HTTPException(status_code=404, detail=f"Tutorial question '{body.question_id}' not found.")

    # ── 3. Evaluate the answer ───────────────────────────────────────────────
    correct_answer = tut_q.get("answer") or tut_q.get("correct_answer", "")
    correct = correct_answer.strip().lower() == body.answer.strip().lower()
    explanation = tut_q.get("explanation", "")

    # ── 4. Apply simple damage ───────────────────────────────────────────────
    streak_before = csession.streak
    damage_dealt  = 0
    enemy_damage  = 0

    if correct:
        # Base 15 + slight random + streak bonus
        base = 15 + _rand.randint(0, 8)
        streak_mult = 1.0 + (streak_before * 0.15)
        damage_dealt = max(1, int(round(base * streak_mult)))
        csession.enemy_hp  = max(0, csession.enemy_hp - damage_dealt)
        csession.streak    = streak_before + 1
        csession.last_feedback = f"Streak ×{csession.streak}!" if csession.streak > 1 else None
    else:
        enemy_damage = 8 + _rand.randint(0, 6)
        if streak_before >= 3:
            enemy_damage += 4          # counter-attack bonus for broken streaks
        csession.player_hp = max(0, csession.player_hp - enemy_damage)
        csession.streak    = 0
        csession.last_feedback = "Streak broken!" if streak_before > 0 else None

    # ── 5. Mark seen & check combat over ────────────────────────────────────
    if csession.seen_question_ids is None:
        csession.seen_question_ids = set()
    csession.seen_question_ids.add(body.question_id)

    combat_over = False
    winner      = None
    if csession.enemy_hp <= 0:
        combat_over = True; winner = "player"
        csession.over = True; csession.winner = "player"
    elif csession.player_hp <= 0:
        combat_over = True; winner = "enemy"
        csession.over = True; csession.winner = "enemy"

    # ── 6. Pick next tutorial question ──────────────────────────────────────
    next_question = None
    if not combat_over:
        csession.round += 1
        next_tq = get_tutorial_question(csession.seen_question_ids)
        if next_tq:
            csession.current_question = next_tq
            csession.seen_question_ids.add(next_tq["id"])
            next_question = {
                "id":      next_tq["id"],
                "question":next_tq["question"],
                "options": next_tq.get("options", []),
                "type":    next_tq.get("type", "multiple_choice"),
                "tier":    "tutorial",
                "concept": "general",
            }

    # ── 7. Return response in the exact same shape as resolve_action ─────────
    return {
        "correct":           correct,
        "correct_answer":    correct_answer,
        "explanation":       explanation,
        "damage_dealt":      damage_dealt,
        "dice_roll":         None,
        "enemy_damage":      enemy_damage,
        "player_hp":         csession.player_hp,
        "player_max_hp":     csession.player_max_hp,
        "enemy_hp":          csession.enemy_hp,
        "enemy_max_hp":      csession.enemy["hp"],
        "combat_over":       combat_over,
        "winner":            winner,
        "next_question":     next_question,
        "round":             csession.round,
        "streak":            csession.streak,
        "damage_multiplier": 1.0 + (streak_before * 0.15),
        "streak_feedback":   csession.last_feedback,
        "weapon_mult":       1.0,
        "ability_triggered": None,
        "abilities_triggered": [],
        "ability_bonus":     0,
    }


# ────────────────────────────────────────────────────────────────────────────
# Anomaly Routes
# ────────────────────────────────────────────────────────────────────────────
class AnomalyAnswerRequest(BaseModel):
    session_id: str
    answer: str


@app.get("/api/game/anomaly/{session_id}")
def get_anomaly(session_id: str) -> dict:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = _sessions[session_id]
    if not hasattr(session, "anomaly_session") or not session.anomaly_session:
        raise HTTPException(status_code=400, detail="No active anomaly session")
    from backend.anomaly import get_current_step
    anomaly = session.anomaly_session
    return {
        "session_id": session_id,
        "anomaly_id": anomaly.id,
        "step_data": get_current_step(anomaly),
    }


@app.post("/api/game/anomaly/answer")
def submit_anomaly_answer(body: AnomalyAnswerRequest) -> dict:
    if body.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = _sessions[body.session_id]
    if not hasattr(session, "anomaly_session") or not session.anomaly_session:
        raise HTTPException(status_code=400, detail="No active anomaly session")
    from backend.anomaly import submit_anomaly_answer as submit_answer
    from backend.progression import add_xp
    result = submit_answer(session.anomaly_session.id, body.answer)
    if result.get("completed"):
        node = session.world.get(session.current_node)
        if node:
            node.state = "cleared"
        if result.get("correct"):
            xp_result = add_xp(session, result.get("reward", {}).get("xp", 10))
            result["xp_result"] = xp_result
        session.anomaly_session = None
    return result


# ────────────────────────────────────────────────────────────────────────────
# Progression + HP sync routes
# ────────────────────────────────────────────────────────────────────────────
from backend.progression import add_xp

class XPRequest(BaseModel):
    session_id: str
    amount: int

class DamageRequest(BaseModel):
    session_id: str
    amount: int

@app.post("/api/game/xp")
def award_xp(body: XPRequest) -> dict:
    if body.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = _sessions[body.session_id]
    result = add_xp(session, body.amount)
    return result

@app.post("/api/game/damage")
def apply_damage(body: DamageRequest) -> dict:
    if body.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = _sessions[body.session_id]
    session.hp = max(0, session.hp - body.amount)
    return {"hp": session.hp, "max_hp": session.max_hp, "dead": session.hp <= 0}

@app.post("/api/game/heal")
def apply_heal(body: DamageRequest) -> dict:
    """Heal the game session player (amount = hp restored)."""
    if body.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = _sessions[body.session_id]
    session.hp = min(session.max_hp, session.hp + body.amount)
    return {"hp": session.hp, "max_hp": session.max_hp}


# ────────────────────────────────────────────────────────────────────────────
# Save/Load Routes
# ────────────────────────────────────────────────────────────────────────────
from backend.save import save_session, load_session, list_saves


@app.post("/api/game/save")
def save_game(body: MoveRequest) -> dict:
    if body.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = _sessions[body.session_id]
    return save_session(session, body.session_id)


@app.get("/api/game/load/{session_id}")
def load_game(session_id: str) -> dict:
    data = load_session(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Save not found")
    return data


@app.get("/api/game/saves")
def get_saves() -> dict:
    return {"saves": list_saves()}


# ────────────────────────────────────────────────────────────────────────────
# Subject management
# ────────────────────────────────────────────────────────────────────────────
@app.get("/api/subjects")
def get_subjects() -> dict:
    """List all available subject folders + which one is currently active."""
    from backend.question_engine import list_subjects, get_active_subject
    return {
        "active":   get_active_subject(),
        "subjects": list_subjects(),
    }


class SetSubjectRequest(BaseModel):
    subject_id: str


@app.post("/api/set_subject")
def set_subject(body: SetSubjectRequest) -> dict:
    """Switch the active subject. Clears question/concept caches immediately."""
    from backend.question_engine import set_subject as qe_set_subject
    try:
        result = qe_set_subject(body.subject_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ────────────────────────────────────────────────────────────────────────────
# Ancient Library — concept study notes + PDFs across all subjects
# ────────────────────────────────────────────────────────────────────────────
@app.get("/api/library")
def get_library() -> dict:
    """
    Return:
     - concepts from the active subject's concepts.json (for Field Notes tab)
     - all_pdf_groups: PDFs from every subject folder, grouped by folder (for Ancient Library tab)
     - active_subject: which subject is currently loaded
    """
    from backend.question_engine import (
        get_active_subject, _load_concepts, list_all_pdfs
    )
    concepts = _load_concepts()
    pdf_groups = list_all_pdfs()
    return {
        "active_subject": get_active_subject(),
        "concepts": concepts,
        "pdf_groups": pdf_groups,
    }


# ────────────────────────────────────────────────────────────────────────────
# Subject game config — custom enemies / weapons / armors / upgrades
# ────────────────────────────────────────────────────────────────────────────
@app.get("/api/subject_config")
def get_subject_config() -> dict:
    """
    Return the game_config block from the active subject's questions.json _meta.
    The frontend uses this to merge subject-specific custom weapons, armors,
    upgrades, and enemies into the live catalogs without restarting the server.

    Returns an object with any of these optional keys:
      custom_enemies  — list of enemy objects added to the combat pool
      extra_weapons   — dict keyed by weapon_id, merged into WEAPONS_CATALOG
      extra_armors    — dict keyed by armor_id,  merged into ARMORS_CATALOG
      extra_upgrades  — dict keyed by upgrade_id, merged into UPGRADES_CATALOG
    Returns {} if the active subject has no game_config section.
    """
    from backend.question_engine import get_game_config, get_active_subject
    return {
        "subject": get_active_subject(),
        "game_config": get_game_config(),
    }


# ────────────────────────────────────────────────────────────────────────────
# Past Papers Mode
# ────────────────────────────────────────────────────────────────────────────
class PPQuestionRequest(BaseModel):
    concept_id:    Optional[str] = None
    question_type: Optional[str] = None
    tier:          Optional[str] = None
    seen_ids:      list[str]     = []


class PPEvalRequest(BaseModel):
    question_id: str
    answer: str


@app.post("/api/past_papers/question")
def past_papers_question(body: PPQuestionRequest = PPQuestionRequest()) -> dict:
    """Return a random question for Past Papers mode."""
    from backend.question_engine import get_question, get_question_by_id
    seen = set(body.seen_ids)
    q = get_question(
        concept_id=body.concept_id or None,
        seen_ids=seen,
        question_types=[body.question_type] if body.question_type else None,
        tier=body.tier or None,
    )
    if not q:
        raise HTTPException(status_code=404, detail="No questions available")
    return {
        "id":       q["id"],
        "question": q["question"],
        "options":  q.get("options", []),
        "type":     q.get("type", "multiple_choice"),
        "tier":     q.get("tier", "standard"),
        "concept":  q.get("concept_id", ""),
    }


@app.post("/api/past_papers/evaluate")
def past_papers_evaluate(body: PPEvalRequest) -> dict:
    """Evaluate an answer in Past Papers mode (no combat state affected)."""
    from backend.question_engine import evaluate_answer
    try:
        return evaluate_answer(body.question_id, body.answer)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ────────────────────────────────────────────────────────────────────────────
# Upgrades system
# ────────────────────────────────────────────────────────────────────────────
class UpgradeRequest(BaseModel):
    session_id:  str
    upgrade_id:  str
    cost_type:   str   # "xp" | "insight"
    cost_amount: int


@app.post("/api/game/upgrade")
def buy_upgrade(body: UpgradeRequest) -> dict:
    """Purchase an upgrade at a Tavern."""
    if body.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = _sessions[body.session_id]

    if not hasattr(session, "upgrades"):
        session.upgrades = []

    # Check if already owned
    if body.upgrade_id in session.upgrades:
        raise HTTPException(status_code=400, detail="Already owned")

    # Deduct cost
    if body.cost_type == "xp":
        if getattr(session, "xp", 0) < body.cost_amount:
            raise HTTPException(status_code=400, detail="Not enough XP")
        session.xp -= body.cost_amount
    elif body.cost_type == "insight":
        if getattr(session, "insight", 0) < body.cost_amount:
            raise HTTPException(status_code=400, detail="Not enough Insight")
        session.insight -= body.cost_amount
    else:
        raise HTTPException(status_code=400, detail="Unknown cost type")

    session.upgrades.append(body.upgrade_id)
    return {
        "upgrades": session.upgrades,
        "xp":       getattr(session, "xp", 0),
        "insight":  getattr(session, "insight", 0),
    }


class RestoreGearRequest(BaseModel):
    session_id: str
    upgrades: list[str] = []


@app.post("/api/game/restore_gear")
def restore_gear(body: RestoreGearRequest) -> dict:
    """
    Restore persistent upgrades to a new session without deducting cost.
    Called on game start when the player already owns gear from a previous run.
    """
    if body.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = _sessions[body.session_id]
    if not hasattr(session, "upgrades"):
        session.upgrades = []
    # Merge in any upgrades not already on this session
    for uid in body.upgrades:
        if uid not in session.upgrades:
            session.upgrades.append(uid)
    return {"upgrades": session.upgrades}

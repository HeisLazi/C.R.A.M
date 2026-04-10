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

STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ────────────────────────────────────────────────────────────────────────────
# Static
# ────────────────────────────────────────────────────────────────────────────
@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


# ────────────────────────────────────────────────────────────────────────────
# Combat
# ────────────────────────────────────────────────────────────────────────────
class StartCombatRequest(BaseModel):
    concept_id:     Optional[str] = None
    weapon_id:      str = "none"
    armor_id:       str = "none"
    node_god:       Optional[str]  = None
    node_modifiers: list[str]      = []
    bonus_insight:  int            = 0


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


@app.post("/world/{world_id}/node/{node_id}/combat")
def post_node_combat(world_id: str, node_id: str):
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
    return {
        "world": {nid: _node_to_dict(n) for nid, n in session.world.items()},
        "current_node": session.current_node,
        "level": session.level,
        "xp": session.xp,
        "hp": session.hp,
        "max_hp": session.max_hp,
        "modifiers": session.modifiers,
        "insight": session.insight,
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
    return result


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

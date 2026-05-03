"""
save.py

Session save/load system (in-memory for now).
"""

import json
from typing import Optional


_saves: dict[str, dict] = {}


def save_session(session, session_id: str) -> dict:
    """Convert session to dict and store."""
    world_dict = {}
    for nid, node in session.world.items():
        world_dict[nid] = {
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

    save_data = {
        "session_id": session_id,
        "world": world_dict,
        "current_node": session.current_node,
        "level": session.level,
        "xp": session.xp,
        "hp": session.hp,
        "max_hp": session.max_hp,
        "insight": session.insight,
        "modifiers": session.modifiers,
    }

    _saves[session_id] = save_data
    return {"saved": True, "session_id": session_id}


def load_session(session_id: str) -> Optional[dict]:
    """Return saved session data."""
    return _saves.get(session_id)


def delete_save(session_id: str) -> bool:
    """Delete a save."""
    if session_id in _saves:
        del _saves[session_id]
        return True
    return False


def list_saves() -> list[dict]:
    """List all save summaries."""
    return [
        {
            "session_id": sid,
            "level": data.get("level", 1),
            "xp": data.get("xp", 0),
            "current_node": data.get("current_node", ""),
        }
        for sid, data in _saves.items()
    ]
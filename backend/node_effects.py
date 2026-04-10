"""
node_effects.py

Node action effect handlers.
Maps action IDs from node_interaction.py to actual game-state changes.
"""

from typing import Optional


def apply_node_action(session, action_id: str) -> dict:
    node = session.world.get(session.current_node)
    if not node:
        return {"type": "error", "message": "Node not found"}

    if node.state == "unvisited":
        node.state = "visited"

    # ── Combat / engage ───────────────────────────────────────────────────
    if action_id == "engage":
        node.state = "cleared"
        return {
            "type": "combat_started",
            "node_type": node.type,
            "subtype": node.subtype,
            "god": node.god,
            "difficulty": node.difficulty,
            "level": session.level,
            "weapon_id": getattr(session, "weapon_id", "none"),
            "armor_id":  getattr(session, "armor_id", "none"),
        }

    if action_id == "study":
        insight_gain = 1
        if "focused_mind" in getattr(session, "modifiers", []):
            insight_gain *= 2
        session.insight = min(3, getattr(session, "insight", 0) + insight_gain)
        return {"type": "bonus", "message": f"Gained {insight_gain} insight.", "insight": insight_gain}

    if action_id == "observe":
        return {
            "type": "info",
            "message": f"You study the {node.subtype}. God: {node.god or 'none'}. Mods: {', '.join(node.modifiers) or 'none'}.",
            "god": node.god,
            "modifiers": node.modifiers,
        }

    # ── Challenge / investigate / quiz → start combat encounter ──────────────
    if action_id == "investigate":
        node.state = "cleared"
        return {
            "type": "combat_started",
            "node_type": node.type,
            "subtype": node.subtype,
            "god": node.god,
            "difficulty": node.difficulty,
            "level": session.level,
            "weapon_id": getattr(session, "weapon_id", "none"),
            "armor_id":  getattr(session, "armor_id", "none"),
        }

    # ── Utility: heal / rest ──────────────────────────────────────────────
    if action_id == "rest":
        old_hp = session.hp
        session.hp = session.max_hp
        healed = session.hp - old_hp
        return {"type": "heal", "message": f"Restored {healed} HP. ({session.hp}/{session.max_hp})", "hp": session.hp}

    if action_id == "change_equipment":
        return {"type": "equipment_menu", "message": "Opening equipment..."}

    if action_id == "browse_shop":
        return {"type": "shop_menu", "message": "The merchant spreads their wares before you."}

    if action_id == "save":
        return {"type": "save_prompt", "message": "Progress saved."}

    # ── Events ────────────────────────────────────────────────────────────
    if action_id == "open_chest":
        import random
        xp_reward = random.randint(5, 15) * node.difficulty
        session.xp = getattr(session, "xp", 0) + xp_reward
        node.state = "cleared"
        return {"type": "reward", "message": f"Found {xp_reward} XP!", "xp": xp_reward}

    if action_id == "listen":
        hint = _generate_lazi_hint(session)
        return {"type": "story", "message": hint}

    if action_id == "flee":
        return {"type": "flee", "message": "You escaped!"}

    # ── Hub ───────────────────────────────────────────────────────────────
    if action_id == "view_map":
        return {"type": "map_view", "message": "You survey the land from the Citadel."}

    if action_id == "view_codex":
        return {"type": "codex_view", "message": "Opening your codex..."}

    # ── Navigation ────────────────────────────────────────────────────────
    if action_id == "leave":
        return {"type": "leave", "message": "You step back to the overworld."}

    return {"type": "error", "message": f"Unknown action: {action_id}"}


def _generate_lazi_hint(session) -> str:
    codex = getattr(session, "codex", None)
    if not codex:
        return "The wind carries whispers of forgotten knowledge. You've barely started your journey."

    mistakes = [e for e in codex if not e.get("correct", True)]
    if not mistakes:
        return "Clean so far. The Pale Drift watches, but finds nothing to feed on. Don't get cocky."

    topic_counts: dict[str, int] = {}
    for m in mistakes:
        qid = m.get("question_id", "")
        topic = qid.split("_")[0] if "_" in qid else qid
        topic_counts[topic] = topic_counts.get(topic, 0) + 1

    weakest = max(topic_counts, key=topic_counts.get)
    return f"You keep stumbling on {weakest.replace('_', ' ').title()}. The Pale Drift feeds on that weakness. Don't let it follow you deeper."

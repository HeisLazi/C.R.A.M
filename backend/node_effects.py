"""
node_effects.py

Node action effect handlers.
Maps action IDs from node_interaction.py to actual game-state changes.
"""

import random
from typing import Optional

# ── Anomaly debuff table ───────────────────────────────────────────────────────
ANOMALY_DEBUFFS = [
    {
        "id": "pale_mark",
        "name": "Pale Mark",
        "desc": "The Drift has branded you. Max HP reduced by 15.",
        "effect": "max_hp_down",
        "value": 15,
        "icon": "💀",
    },
    {
        "id": "shattered_focus",
        "name": "Shattered Focus",
        "desc": "Your concentration fractures. Insight charges reduced by 1.",
        "effect": "insight_down",
        "value": 1,
        "icon": "🧠",
    },
    {
        "id": "xp_curse",
        "name": "XP Curse",
        "desc": "Knowledge bleeds from your mind. XP gains reduced by 25%.",
        "effect": "xp_curse",
        "value": 0.25,
        "icon": "⚗️",
    },
    {
        "id": "void_wound",
        "name": "Void Wound",
        "desc": "A wound that won't close. Lose 5 HP at the start of each combat.",
        "effect": "combat_start_damage",
        "value": 5,
        "icon": "🩸",
    },
]


def apply_anomaly_debuff(session) -> dict:
    """Apply a random permanent debuff to the session. Returns the debuff applied."""
    debuff = random.choice(ANOMALY_DEBUFFS)

    if not hasattr(session, "debuffs"):
        session.debuffs = []

    # Don't stack the same debuff — skip if already applied
    existing_ids = [d["id"] for d in session.debuffs]
    available = [d for d in ANOMALY_DEBUFFS if d["id"] not in existing_ids]
    if available:
        debuff = random.choice(available)
    # else: all debuffs already applied, still return one for display purposes

    session.debuffs.append(debuff)

    # Apply immediate numeric effects
    if debuff["effect"] == "max_hp_down":
        session.max_hp = max(10, session.max_hp - debuff["value"])
        session.hp = min(session.hp, session.max_hp)
    elif debuff["effect"] == "insight_down":
        session.insight = max(0, getattr(session, "insight", 0) - debuff["value"])

    return debuff


def apply_node_action(session, action_id: str) -> dict:
    node = session.world.get(session.current_node)
    if not node:
        return {"type": "error", "message": "Node not found"}

    if node.state == "unvisited":
        node.state = "visited"

    # ── Anomaly: face / study ─────────────────────────────────────────────
    if action_id == "face_anomaly":
        return {
            "type": "combat_started",
            "node_type": "anomaly",
            "subtype": node.subtype,
            "god": node.god,
            "difficulty": node.difficulty,
            "level": session.level,
            "weapon_id": getattr(session, "weapon_id", "none"),
            "armor_id":  getattr(session, "armor_id", "none"),
            "is_anomaly": True,
            "warning": (
                "⚠️ ANOMALY — The Pale Drift stirs. "
                "Defeat it for legendary rewards, "
                "but failure brands you permanently."
            ),
        }

    if action_id == "study_anomaly":
        debuffs_desc = ", ".join(d["name"] for d in ANOMALY_DEBUFFS)
        return {
            "type": "info",
            "message": (
                f"The rift pulses with forbidden knowledge. "
                f"Engaging risks a permanent curse: {debuffs_desc}. "
                f"But those who endure claim the greatest rewards of all."
            ),
        }

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

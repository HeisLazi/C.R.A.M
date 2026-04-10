"""
combat.py

Responsibilities:
- Manage player and enemy state
- Handle sessions (in-memory, UUID keyed)
- Resolve combat turns using question multiplier

Rules:
- Correct answer  → player deals full damage to enemy (scaled by streak + weapon)
- Wrong answer    → player deals zero damage; enemy counterattacks (reduced by armor)
                    (slightly increased if player had a streak ≥ 3)
"""

import uuid
import random
from dataclasses import dataclass, field as dc_field
from typing import Optional

from backend.question_engine import get_question, evaluate_answer, get_hint
from backend.equipment import (
    Weapon, Armor,
    WEAPONS, ARMORS,
    apply_weapon_ability_on_hit,
    effective_damage_reduction,
)
from backend.run_modifiers import (
    get_run_player_damage_mult,
    get_run_enemy_damage_mult,
    get_run_streak_bonus,
)


PLAYER_MAX_HP = 100
PLAYER_BASE_DAMAGE = 20
INSIGHT_USES_PER_COMBAT = 2

# ── Streak constants ──────────────────────────────────────────────────────────
STREAK_COUNTER_THRESHOLD = 3   # streak length that triggers enemy counter bonus
STREAK_COUNTER_BONUS     = 5   # extra enemy damage when counter is triggered

# ── Level scaling (placeholder for future XP system) ──────────────────────────
LEVEL_SCALING = 1.0  # legacy fallback


def _get_level_scaling(level: int) -> float:
    """Player damage scaling: +5% per level above 1."""
    return 1.0 + (level - 1) * 0.05


def _get_enemy_scaling(level: int) -> float:
    """Enemy damage scaling: +3% per level above 1."""
    return 1.0 + (level - 1) * 0.03


def _get_god_player_multiplier(god: Optional[str], streak: int) -> float:
    """God-based player damage multipliers."""
    if god == "aurex":
        return 1.10 if streak >= 2 else 1.0
    if god == "vyra":
        return 1.20 if streak > 0 else 1.0
    if god == "thren":
        return 1.05
    if god == "nyx":
        return 1.15
    return 1.0


def _get_god_enemy_multiplier(god: Optional[str]) -> float:
    """God-based enemy damage multipliers."""
    if god == "khalen":
        return 0.90
    if god == "nyx":
        return 1.15
    return 1.0


def _streak_multiplier(streak: int, run_bonus: float = 0.0) -> float:
    """Damage multiplier based on current correct-answer streak."""
    base = 1.0
    if streak >= 3:
        base = 1.25
    elif streak == 2:
        base = 1.10
    mult = base + run_bonus
    return min(mult, 2.5)


def _dice_roll(wits: float = 1.0) -> float:
    """Return a damage multiplier in [0.8, 1.2]; higher wits slightly widens the upper end."""
    low  = 0.8 + (wits - 1.0) * 0.05
    high = 1.2 + (wits - 1.0) * 0.05
    return round(random.uniform(low, high), 2)


ENEMIES = [
    {"name": "Recursive Wraith",    "concept_id": "recursion",      "difficulty": 1, "hp": 60,  "base_damage": 15, "bonus_damage": 10},
    {"name": "Binary Shade",        "concept_id": "binary_search",  "difficulty": 2, "hp": 80,  "base_damage": 18, "bonus_damage": 12},
    {"name": "BST Revenant",        "concept_id": "bst",            "difficulty": 2, "hp": 80,  "base_damage": 18, "bonus_damage": 12},
    {"name": "Complexity Specter",  "concept_id": "big_o",          "difficulty": 1, "hp": 60,  "base_damage": 15, "bonus_damage": 10},
    {"name": "AVL Titan",           "concept_id": "avl_tree",       "difficulty": 3, "hp": 100, "base_damage": 22, "bonus_damage": 15},
]


@dataclass
class CombatSession:
    session_id: str
    player_hp: int
    player_max_hp: int
    player_wits: float
    enemy: dict
    enemy_hp: int
    current_question: dict
    level: int = 1
    god: Optional[str] = None
    weapon: Optional[Weapon] = None      # set in start_combat
    armor:  Optional[Armor]  = None      # set in start_combat
    last_damage: int = 0                 # last hit dealt (used by recursive_echo)
    insight_uses: int = INSIGHT_USES_PER_COMBAT
    streak: int = 0                      # consecutive correct answers
    last_feedback: Optional[str] = None  # "Streak x3!" or "Streak broken!"
    over: bool = False
    winner: Optional[str] = None
    round: int = 1
    seen_question_ids: object = dc_field(default_factory=set)  # set[str] — anti-repeat tracker
    # ── Node context (passed through, not used in calculations yet) ────────────
    node_god:       Optional[str] = None
    node_modifiers: list = None          # list[str]
    run_modifiers:  list = None          # run-based modifiers


_sessions: dict[str, CombatSession] = {}


def start_combat(
    concept_id:     Optional[str]  = None,
    weapon_id:      str            = "none",
    armor_id:       str            = "none",
    node_god:       Optional[str]  = None,
    node_modifiers: Optional[list] = None,
    bonus_insight:  int            = 0,
    player_hp:      Optional[int]  = None,
    level:          int            = 1,
    god:            Optional[str]  = None,
    run_modifiers:  Optional[list] = None,
) -> dict:
    session_id = str(uuid.uuid4())

    if concept_id:
        candidates = [e for e in ENEMIES if e["concept_id"] == concept_id]
        enemy_template = random.choice(candidates) if candidates else random.choice(ENEMIES)
    else:
        enemy_template = random.choice(ENEMIES)

    enemy = dict(enemy_template)
    seen: set = set()
    question = get_question(concept_id=enemy["concept_id"], seen_ids=seen)
    if question is None:
        raise RuntimeError("No questions available for this concept.")
    seen.add(question["id"])

    weapon = WEAPONS.get(weapon_id, WEAPONS["none"])
    armor  = ARMORS.get(armor_id,  ARMORS["none"])

    actual_hp = min(PLAYER_MAX_HP, max(1, player_hp)) if player_hp is not None else PLAYER_MAX_HP
    session = CombatSession(
        session_id=session_id,
        player_hp=actual_hp,
        player_max_hp=PLAYER_MAX_HP,
        player_wits=1.0,
        enemy=enemy,
        enemy_hp=enemy["hp"],
        current_question=question,
        level=level,
        god=god or node_god,
        weapon=weapon,
        armor=armor,
        insight_uses=INSIGHT_USES_PER_COMBAT + bonus_insight,
        seen_question_ids=seen,
        node_god=node_god,
        node_modifiers=node_modifiers or [],
        run_modifiers=run_modifiers or [],
    )
    _sessions[session_id] = session

    return _session_state(session)


def resolve_action(session_id: str, question_id: str, answer: str) -> dict:
    session = _sessions.get(session_id)
    if session is None:
        raise ValueError(f"Session '{session_id}' not found.")
    if session.over:
        raise ValueError("Combat is already over.")

    result = evaluate_answer(question_id, answer)

    # ── Streak: read before mutation ──────────────────────────────────────────
    streak_before = session.streak

    roll = _dice_roll(session.player_wits)
    ability_triggered = None

    if result["correct"]:
        run_bonus = get_run_streak_bonus(session.run_modifiers)
        streak_mult  = _streak_multiplier(streak_before, run_bonus)
        weapon_mult  = 1.0 + session.weapon.damage_bonus

        # Formula: base × dice × streak × weapon
        base_damage  = max(1, int(round(
            PLAYER_BASE_DAMAGE * roll * streak_mult * weapon_mult
        )))

        # Apply level scaling AFTER base
        level_mult = _get_level_scaling(session.level)
        base_damage = int(round(base_damage * level_mult))

        # Apply god effects
        god_mult = _get_god_player_multiplier(session.god, streak_before)
        base_damage = int(round(base_damage * god_mult))

        # Apply run modifiers
        run_mult = get_run_player_damage_mult(session.run_modifiers, session.level)
        base_damage = int(round(base_damage * run_mult))

        # ── Weapon ability (on-hit) ───────────────────────────────────────────
        ability_bonus, ability_triggered = apply_weapon_ability_on_hit(
            session.weapon.ability, base_damage, session.last_damage,
            god=session.god, streak=session.streak
        )
        damage_dealt = base_damage + ability_bonus

        enemy_damage = 0
        session.last_damage = damage_dealt
        session.enemy_hp = max(0, session.enemy_hp - damage_dealt)

        session.streak        = streak_before + 1
        session.last_feedback = f"Streak x{session.streak}!" if session.streak > 1 else None
    else:
        streak_mult   = 1.0
        weapon_mult   = 1.0
        damage_dealt  = 0
        ability_bonus = 0
        counter_bonus = STREAK_COUNTER_BONUS if streak_before >= STREAK_COUNTER_THRESHOLD else 0
        raw_enemy_dmg = session.enemy["base_damage"] + session.enemy["bonus_damage"] + counter_bonus

        # Apply level scaling
        enemy_mult = _get_enemy_scaling(session.level)

        # Apply god effects LAST
        god_mult = _get_god_enemy_multiplier(session.god)
        enemy_mult *= god_mult

        # Apply run modifiers
        run_mult = get_run_enemy_damage_mult(session.run_modifiers, session.level)
        enemy_mult *= run_mult

        # ── Armor reduction (includes balance_shift weapon ability) ───────────
        reduction    = effective_damage_reduction(
            session.armor, session.weapon,
            god=session.god, level=session.level, streak=session.streak
        )
        enemy_damage = max(1, int(round(raw_enemy_dmg * enemy_mult * (1.0 - reduction))))
        session.player_hp = max(0, session.player_hp - enemy_damage)
        roll = None

        session.last_feedback = "Streak broken!" if streak_before > 0 else None
        session.streak = 0

    combat_over = False
    winner = None
    if session.enemy_hp <= 0:
        combat_over = True
        winner = "player"
        session.over = True
        session.winner = "player"
    elif session.player_hp <= 0:
        combat_over = True
        winner = "enemy"
        session.over = True
        session.winner = "enemy"

    next_question = None
    if not combat_over:
        session.round += 1
        # Track the just-answered question as seen
        if session.seen_question_ids is None:
            session.seen_question_ids = set()
        session.seen_question_ids.add(question_id)
        next_q = get_question(
            concept_id=session.enemy["concept_id"],
            seen_ids=session.seen_question_ids,
        )
        if next_q:
            session.current_question = next_q
            session.seen_question_ids.add(next_q["id"])
            next_question = _question_payload(next_q)

    return {
        "correct": result["correct"],
        "correct_answer": result["correct_answer"],
        "explanation": result["explanation"],
        "damage_dealt": damage_dealt,
        "dice_roll": roll,
        "enemy_damage": enemy_damage,
        "player_hp": session.player_hp,
        "player_max_hp": session.player_max_hp,
        "enemy_hp": session.enemy_hp,
        "enemy_max_hp": session.enemy["hp"],
        "combat_over": combat_over,
        "winner": winner,
        "next_question": next_question,
        "round": session.round,
        # ── Streak fields ─────────────────────────────────────────────────────
        "streak": session.streak,
        "damage_multiplier": streak_mult,
        "streak_feedback": session.last_feedback,
        # ── Equipment fields ──────────────────────────────────────────────────
        "weapon_mult": weapon_mult,
        "ability_triggered": ability_triggered,
        "ability_bonus": ability_bonus if result["correct"] else 0,
    }


def _session_state(session: CombatSession) -> dict:
    return {
        "session_id": session.session_id,
        "player_hp": session.player_hp,
        "player_max_hp": session.player_max_hp,
        "player_wits": session.player_wits,
        "insight_uses": session.insight_uses,
        "streak": session.streak,
        "level": session.level,
        "god": session.god,
        "player_scaling": _get_level_scaling(session.level),
        "enemy_scaling": _get_enemy_scaling(session.level),
        "enemy_name": session.enemy["name"],
        "enemy_concept": session.enemy["concept_id"],
        "enemy_hp": session.enemy_hp,
        "enemy_max_hp": session.enemy["hp"],
        "question": _question_payload(session.current_question),
        "round": session.round,
        # ── Equipment ─────────────────────────────────────────────────────────
        "weapon": {
            "name":         session.weapon.name,
            "damage_bonus": session.weapon.damage_bonus,
            "ability":      session.weapon.ability,
        },
        "armor": {
            "name":             session.armor.name,
            "damage_reduction": session.armor.damage_reduction,
        },
        # ── Node context ──────────────────────────────────────────────────────
        "node_god":       session.node_god,
        "node_modifiers": session.node_modifiers,
        # ── Run modifiers ─────────────────────────────────────────────────────
        "run_modifiers": session.run_modifiers,
    }


def use_insight(session_id: str) -> dict:
    """Reveal a concept-level hint for the current question. Costs one insight use."""
    session = _sessions.get(session_id)
    if session is None:
        raise ValueError(f"Session '{session_id}' not found.")
    if session.over:
        raise ValueError("Combat is already over.")
    if session.insight_uses <= 0:
        return {"hint": None, "insight_uses": 0, "error": "No insight uses remaining."}

    session.insight_uses -= 1
    hint = get_hint(session.current_question["id"])
    return {"hint": hint, "insight_uses": session.insight_uses}


def _question_payload(q: dict) -> dict:
    return {
        "id": q["id"],
        "question": q["question"],
        "options": q["options"],
    }

"""
run_modifiers.py

Run-based global modifiers that affect combat for the entire run.
"""

import random
from typing import Optional


RUN_MODIFIERS = {
    "glass_cannon": {
        "player_damage_mult": 1.20,
        "enemy_damage_mult": 1.20,
        "description": "+20% player damage, +20% enemy damage",
    },
    "focused_mind": {
        "insight_mult": 2.0,
        "description": "Insight bonus doubled",
    },
    "corrupted": {
        "enemy_damage_mult": 1.15,
        "description": "+15% enemy damage",
    },
    "precision": {
        "streak_bonus": 0.10,
        "description": "Streak bonus increased by +10%",
    },
}


def assign_random_modifiers(rng: Optional[random.Random] = None) -> list[str]:
    """Assign 1-2 random modifiers to a new run."""
    if rng is None:
        rng = random.Random()
    pool = list(RUN_MODIFIERS.keys())
    count = rng.randint(1, 2)
    return rng.sample(pool, k=min(count, len(pool)))


def get_run_player_damage_mult(modifiers: list[str], level: int = 1) -> float:
    """Apply player damage modifiers from run."""
    mult = 1.0
    for mod in modifiers:
        if mod == "glass_cannon":
            scale = 1 + (level * 0.02)
            mult *= (1.20 * scale)
        elif mod in RUN_MODIFIERS:
            mult *= RUN_MODIFIERS[mod].get("player_damage_mult", 1.0)
    return mult


def get_run_enemy_damage_mult(modifiers: list[str], level: int = 1) -> float:
    """Apply enemy damage modifiers from run."""
    mult = 1.0
    for mod in modifiers:
        if mod == "glass_cannon":
            scale = 1 + (level * 0.02)
            mult *= (1.20 * scale)
        elif mod in RUN_MODIFIERS:
            mult *= RUN_MODIFIERS[mod].get("enemy_damage_mult", 1.0)
    return mult


def get_run_streak_bonus(modifiers: list[str]) -> float:
    """Get additional streak bonus from run modifiers."""
    bonus = 0.0
    for mod in modifiers:
        if mod in RUN_MODIFIERS:
            bonus += RUN_MODIFIERS[mod].get("streak_bonus", 0.0)
    return bonus


def get_run_insight_mult(modifiers: list[str]) -> float:
    """Get insight multiplier from run modifiers."""
    mult = 1.0
    for mod in modifiers:
        if mod in RUN_MODIFIERS:
            mult *= RUN_MODIFIERS[mod].get("insight_mult", 1.0)
    return mult
"""
equipment.py

Weapon and armor definitions for Origins: The Unbound.

Responsibilities:
- Define Weapon / Armor dataclasses
- Maintain the equipment catalog (WEAPONS, ARMORS)
- Resolve weapon abilities (conditional logic, isolated here)

Combat system is NOT modified here — only called from combat.py.

Ability identifiers:
  binary_strike   → +50% damage on a correct answer
  recursive_echo  → deal 30% of last hit again as a bonus
  balance_shift   → extra 40% damage reduction on wrong answers
"""

from dataclasses import dataclass
from typing import Optional


# ── Ability identifiers ────────────────────────────────────────────────────────
ABILITY_BINARY_STRIKE  = "binary_strike"
ABILITY_RECURSIVE_ECHO = "recursive_echo"
ABILITY_BALANCE_SHIFT  = "balance_shift"


@dataclass
class Weapon:
    name:         str
    damage_bonus: float           # additive %, e.g. 0.20 = +20 % on top of base
    ability:      Optional[str] = None


@dataclass
class Armor:
    name:             str
    damage_reduction: float       # percentage of incoming damage negated (0.0–1.0)


# ── Catalogs ──────────────────────────────────────────────────────────────────
WEAPONS: dict[str, Weapon] = {
    "none":           Weapon("Bare Hands",      damage_bonus=0.00, ability=None),
    "binary_blade":   Weapon("Binary Blade",    damage_bonus=0.15, ability=ABILITY_BINARY_STRIKE),
    "recursive_staff":Weapon("Recursive Staff", damage_bonus=0.10, ability=ABILITY_RECURSIVE_ECHO),
    "balance_edge":   Weapon("Balance Edge",    damage_bonus=0.08, ability=ABILITY_BALANCE_SHIFT),
}

ARMORS: dict[str, Armor] = {
    "none":        Armor("No Armor",    damage_reduction=0.00),
    "data_vest":   Armor("Data Vest",   damage_reduction=0.15),
    "stack_plate": Armor("Stack Plate", damage_reduction=0.25),
}


# ── Ability: correct-answer hook ──────────────────────────────────────────────
def apply_weapon_ability_on_hit(
    ability:     Optional[str],
    base_damage: int,
    last_damage: int,
    god:         Optional[str] = None,
    streak:      int = 0,
) -> tuple[int, Optional[str]]:
    """
    Called after base_damage is computed on a correct answer.
    Returns (bonus_damage, ability_name_if_triggered).
    Synergies: binary_blade (streak), recursive_staff (vyra god).
    """
    if ability == ABILITY_BINARY_STRIKE and streak >= 2:
        return int(base_damage * 0.50), ABILITY_BINARY_STRIKE

    if ability == ABILITY_RECURSIVE_ECHO and last_damage > 0:
        bonus_pct = 0.40 if god == "vyra" else 0.30
        bonus = int(last_damage * bonus_pct)
        bonus = min(bonus, int(base_damage * 0.5))
        return bonus, ABILITY_RECURSIVE_ECHO

    return 0, None


# ── Ability: wrong-answer hook (armor modifier) ───────────────────────────────
def effective_damage_reduction(
    armor: Armor,
    weapon: Weapon,
    god: Optional[str] = None,
    level: int = 1,
    streak: int = 0,
) -> float:
    """
    Total damage reduction applied to incoming enemy damage.
    Synergies:
    - balance_edge + khalen: extra 5% reduction
    - data_vest + level >= 3: extra 5% reduction
    - stack_plate + streak >= 3: extra 10% reduction
    balance_shift adds +40% reduction when the player answers wrong.
    Capped at 50% from gear, then 90% overall.
    """
    total = armor.damage_reduction

    if weapon.ability == ABILITY_BALANCE_SHIFT:
        total = min(0.50, total + 0.40)

    if armor.name == "Data Vest" and level >= 3:
        total = min(0.50, total + 0.05)

    if armor.name == "Stack Plate" and streak >= 3:
        total = min(0.50, total + 0.10)

    if weapon.ability == ABILITY_BALANCE_SHIFT and god == "khalen":
        total = min(0.50, total + 0.05)

    return min(total, 0.50)

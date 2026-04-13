"""
equipment.py

Weapon and armor definitions for C.R.A.M — The Unbound.

Three weapon PATHS (Aggressor, Scholar, Warden), each with T1/T2/T3 tiers
and branching choices at T2 and T3. Three armor PATHS (Iron Guard, Sorcerer,
Drifter) that auto-upgrade at level milestones.

Abilities:
  binary_strike   → +50% bonus on 2+ streak
  chain_strike    → +15 flat bonus on 3+ streak
  life_steal      → +5 HP per correct answer
  recursive_echo  → 30% of last hit as bonus
  echo_double     → recursive echo × 2; extra insight at combat start
  echo_triple     → recursive echo × 3; extra insight at combat start
  seeker          → insight use → +20% damage this turn
  oracle          → every 4th correct answer → free insight
  balance_shift   → +40% DR on wrong answers
  counter         → wrong answer → 10 dmg back at enemy
  null_first      → first wrong answer has 0 enemy damage
  fortify_wep     → +30 max HP; 3-streak heals 5 HP
  mirror          → 20% chance to fully reflect enemy damage
"""

import random
from dataclasses import dataclass, field as dc_field
from typing import Optional


# ── Ability identifiers ────────────────────────────────────────────────────────
ABILITY_BINARY_STRIKE  = "binary_strike"
ABILITY_CHAIN_STRIKE   = "chain_strike"
ABILITY_LIFE_STEAL     = "life_steal"
ABILITY_RECURSIVE_ECHO = "recursive_echo"
ABILITY_ECHO_DOUBLE    = "echo_double"
ABILITY_ECHO_TRIPLE    = "echo_triple"
ABILITY_SEEKER         = "seeker"
ABILITY_ORACLE         = "oracle"
ABILITY_BALANCE_SHIFT  = "balance_shift"
ABILITY_COUNTER        = "counter"
ABILITY_NULL_FIRST     = "null_first"
ABILITY_FORTIFY_WEP    = "fortify_wep"
ABILITY_MIRROR         = "mirror"
ABILITY_INSIGHT_BONUS  = "insight_bonus"   # armor: extra insight at combat start
ABILITY_PHASE_DODGE    = "phase_dodge"     # armor: 10% dodge chance on wrong
ABILITY_RIFT_DODGE     = "rift_dodge"      # armor: 20% dodge chance on wrong


@dataclass
class Weapon:
    name:         str
    damage_bonus: float           # additive %, e.g. 0.20 = +20% on top of base
    ability:      Optional[str] = None


@dataclass
class Armor:
    name:             str
    damage_reduction: float       # percentage of incoming damage negated (0.0–1.0)
    damage_bonus:     float = 0.0 # additive damage bonus (drifter path)
    insight_bonus:    int   = 0   # extra insight charges at combat start
    dodge_chance:     float = 0.0 # probability (0–1) to negate a wrong-answer hit


# ── Weapon catalog ─────────────────────────────────────────────────────────────
WEAPONS: dict[str, Weapon] = {
    # ── Default ──
    "none":              Weapon("Bare Hands",       damage_bonus=0.00, ability=None),

    # ── Aggressor path ──
    "binary_blade":      Weapon("Binary Blade",     damage_bonus=0.15, ability=ABILITY_BINARY_STRIKE),
    "cleave_edge":       Weapon("Cleave Edge",      damage_bonus=0.25, ability=ABILITY_CHAIN_STRIKE),
    "blood_blade":       Weapon("Blood Blade",      damage_bonus=0.20, ability=ABILITY_LIFE_STEAL),
    "void_cleaver":      Weapon("Void Cleaver",     damage_bonus=0.35, ability=ABILITY_BINARY_STRIKE),  # execute TBD
    "berserker_blade":   Weapon("Berserker Blade",  damage_bonus=0.30, ability=ABILITY_LIFE_STEAL),    # berserk TBD

    # ── Scholar path ──
    "recursive_staff":   Weapon("Recursive Staff",  damage_bonus=0.10, ability=ABILITY_RECURSIVE_ECHO),
    "echo_codex":        Weapon("Echo Codex",       damage_bonus=0.18, ability=ABILITY_ECHO_DOUBLE),
    "seeker_rod":        Weapon("Seeker Rod",       damage_bonus=0.15, ability=ABILITY_SEEKER),
    "grand_codex":       Weapon("Grand Codex",      damage_bonus=0.28, ability=ABILITY_ECHO_TRIPLE),
    "oracle_staff":      Weapon("Oracle Staff",     damage_bonus=0.22, ability=ABILITY_ORACLE),

    # ── Warden path ──
    "balance_edge":      Weapon("Balance Edge",     damage_bonus=0.08, ability=ABILITY_BALANCE_SHIFT),
    "iron_bulwark":      Weapon("Iron Bulwark",     damage_bonus=0.12, ability=ABILITY_COUNTER),
    "null_blade":        Weapon("Null Blade",       damage_bonus=0.10, ability=ABILITY_NULL_FIRST),
    "fortress_edge":     Weapon("Fortress Edge",    damage_bonus=0.15, ability=ABILITY_FORTIFY_WEP),
    "reflect_blade":     Weapon("Reflect Blade",    damage_bonus=0.18, ability=ABILITY_MIRROR),
}

# ── Armor catalog ──────────────────────────────────────────────────────────────
ARMORS: dict[str, Armor] = {
    # ── Default ──
    "none":              Armor("No Armor",         damage_reduction=0.00),

    # ── Iron Guard path ──
    "cloth_wraps":       Armor("Cloth Wraps",      damage_reduction=0.05),
    "data_vest":         Armor("Data Vest",        damage_reduction=0.15),
    "stack_plate":       Armor("Stack Plate",      damage_reduction=0.25),

    # ── Sorcerer path ──
    "scholars_robe":     Armor("Scholar's Robe",   damage_reduction=0.03, insight_bonus=1),
    "codex_cloak":       Armor("Codex Cloak",      damage_reduction=0.08, insight_bonus=2),
    "void_shroud":       Armor("Void Shroud",      damage_reduction=0.12, insight_bonus=3),

    # ── Drifter path ──
    "battle_wraps":      Armor("Battle Wraps",     damage_reduction=0.02, damage_bonus=0.05),
    "phase_coat":        Armor("Phase Coat",       damage_reduction=0.06, damage_bonus=0.10, dodge_chance=0.10),
    "rift_cloak":        Armor("Rift Cloak",       damage_reduction=0.10, damage_bonus=0.15, dodge_chance=0.20),
}


# ── Ability: correct-answer hook ──────────────────────────────────────────────
def _apply_single_ability_on_hit(
    ability:     str,
    base_damage: int,
    last_damage: int,
    god:         Optional[str] = None,
    streak:      int = 0,
) -> tuple[int, Optional[str]]:
    """Apply one ability and return (bonus_damage, ability_name_if_triggered)."""
    if ability == ABILITY_BINARY_STRIKE and streak >= 2:
        return int(base_damage * 0.50), ABILITY_BINARY_STRIKE

    if ability == ABILITY_CHAIN_STRIKE and streak >= 3:
        return 15, ABILITY_CHAIN_STRIKE

    if ability == ABILITY_LIFE_STEAL:
        # life steal is handled separately by the game loop (HP restore)
        return 0, None

    if ability == ABILITY_RECURSIVE_ECHO and last_damage > 0:
        bonus_pct = 0.40 if god == "vyra" else 0.30
        bonus = int(last_damage * bonus_pct)
        bonus = min(bonus, int(base_damage * 0.5))
        return bonus, ABILITY_RECURSIVE_ECHO

    if ability == ABILITY_ECHO_DOUBLE and last_damage > 0:
        bonus_pct = 0.40 if god == "vyra" else 0.30
        bonus = int(last_damage * bonus_pct) * 2
        bonus = min(bonus, int(base_damage * 0.8))
        return bonus, ABILITY_ECHO_DOUBLE

    if ability == ABILITY_ECHO_TRIPLE and last_damage > 0:
        bonus_pct = 0.40 if god == "vyra" else 0.30
        bonus = int(last_damage * bonus_pct) * 3
        bonus = min(bonus, base_damage)
        return bonus, ABILITY_ECHO_TRIPLE

    return 0, None


def apply_weapon_ability_on_hit(
    ability:          Optional[str],
    base_damage:      int,
    last_damage:      int,
    god:              Optional[str] = None,
    streak:           int = 0,
    correct_count:    int = 0,
    bonus_abilities:  Optional[list] = None,
) -> tuple[int, list[str]]:
    """
    Called after base_damage is computed on a correct answer.
    Applies the primary ability PLUS any stacked bonus_abilities (from previous tiers).
    Returns (total_bonus_damage, list_of_triggered_ability_names).

    Ability stacking rules:
    - Echo abilities (recursive_echo, echo_double, echo_triple): only the highest-tier
      echo is applied (they scale multiplicatively; stacking would be unbalanced).
    - All others stack independently.
    """
    all_abilities: list[str] = []
    if ability:
        all_abilities.append(ability)
    if bonus_abilities:
        for ab in bonus_abilities:
            if ab and ab not in all_abilities:
                all_abilities.append(ab)

    # De-duplicate echo abilities — keep only the highest-tier one
    ECHO_TIER = {ABILITY_RECURSIVE_ECHO: 1, ABILITY_ECHO_DOUBLE: 2, ABILITY_ECHO_TRIPLE: 3}
    echo_in_list = [a for a in all_abilities if a in ECHO_TIER]
    if len(echo_in_list) > 1:
        best_echo = max(echo_in_list, key=lambda a: ECHO_TIER[a])
        all_abilities = [a for a in all_abilities if a not in ECHO_TIER] + [best_echo]

    total_bonus = 0
    triggered: list[str] = []
    for ab in all_abilities:
        bonus, name = _apply_single_ability_on_hit(ab, base_damage, last_damage, god, streak)
        if name:
            total_bonus += bonus
            triggered.append(name)

    return total_bonus, triggered


# ── Ability: wrong-answer hook ────────────────────────────────────────────────
def apply_wrong_answer_hooks(
    weapon: Weapon,
    armor:  Armor,
    wrong_count_this_combat: int = 0,
) -> tuple[int, bool, Optional[str]]:
    """
    Called when player answers wrong.
    Returns (counter_damage_to_enemy, dodge_triggered, ability_name).
    """
    counter_dmg = 0
    dodge = False
    triggered = None

    # Null Shield: negate damage on first wrong answer
    if weapon.ability == ABILITY_NULL_FIRST and wrong_count_this_combat == 0:
        dodge = True
        triggered = ABILITY_NULL_FIRST

    # Mirror: 20% chance to reflect
    elif weapon.ability == ABILITY_MIRROR and random.random() < 0.20:
        dodge = True
        triggered = ABILITY_MIRROR

    # Phase/Rift dodge chance
    elif armor.dodge_chance > 0 and random.random() < armor.dodge_chance:
        dodge = True
        triggered = "dodge"

    # Counter: deal damage back
    if weapon.ability == ABILITY_COUNTER and not dodge:
        counter_dmg = 10
        triggered = ABILITY_COUNTER

    return counter_dmg, dodge, triggered


# ── Ability: effective damage reduction ───────────────────────────────────────
def effective_damage_reduction(
    armor: Armor,
    weapon: Weapon,
    god: Optional[str] = None,
    level: int = 1,
    streak: int = 0,
) -> float:
    """
    Total damage reduction applied to incoming enemy damage on a wrong answer.
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

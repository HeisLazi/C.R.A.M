"""
progression.py

XP and level progression system.
"""


def calculate_level(xp: int) -> int:
    return 1 + (xp // 50)


def add_xp(session, amount: int) -> dict:
    session.xp = min(10000, getattr(session, "xp", 0) + amount)

    if not hasattr(session, "level"):
        session.level = calculate_level(session.xp)

    old_level = getattr(session, "level", 1)
    new_level = calculate_level(session.xp)

    session.level = new_level
    level_up = new_level > old_level

    if level_up:
        session.max_hp = getattr(session, "max_hp", 100) + 5
        session.hp = session.max_hp

    return {
        "xp": session.xp,
        "level": session.level,
        "level_up": level_up,
    }
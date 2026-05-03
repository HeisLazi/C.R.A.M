"""
overworld.py

Procedural overworld graph generator and world-state manager.

Responsibilities:
- Generate a deterministic node graph from a seed
- Track node states (unvisited / visited / cleared)
- Track persistent player state across nodes (HP, equipment, bonus insight)
- Provide interaction options per node type
- Generate Lazi dialogue from codex data

Nothing in here touches combat, equipment abilities, or question logic.
"""

import uuid
import random
from dataclasses import dataclass, field
from typing import Optional


# ── Flavor pools ──────────────────────────────────────────────────────────────
BIOMES = [
    "thornwood", "echo_forest", "binary_vault",
    "fractured_depths", "pale_drift", "null_spire",
]

GODS = ["aurex", "vyra", "khalen", "thren", "nyx"]

MODIFIERS_POOL = [
    "corrupted", "fast", "no_insight",
    "topic_trees", "shielded", "volatile",
]

GOD_CHANCE     = 0.25
MAX_DEPTH      = 10
NODES_PER_DEPTH_MIN = 2
NODES_PER_DEPTH_MAX = 5

NODE_COLORS = {
    ("combat",    "standard"): "#c0392b",
    ("combat",    "trial"):    "#e67e22",
    ("combat",    "forest"):   "#1e8449",
    ("combat",    "dungeon"):  "#6c3483",
    ("challenge", "anomaly"):  "#8e44ad",
    ("utility",   "tavern"):   "#27ae60",
    ("event",     "lazi"):     "#2980b9",
    ("hub",       "citadel"):  "#7c6fff",
}


# ── Data model ────────────────────────────────────────────────────────────────
@dataclass
class WorldNode:
    id:          str
    type:        str          # "combat" | "challenge" | "utility" | "event" | "hub"
    subtype:     str
    biome:       str
    difficulty:  int
    depth:       int
    modifiers:   list[str]
    connections: list[str]
    state:       str          # "unvisited" | "visited" | "cleared"
    seed:        int
    god:         Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "type":        self.type,
            "subtype":     self.subtype,
            "biome":       self.biome,
            "difficulty":  self.difficulty,
            "depth":       self.depth,
            "modifiers":   self.modifiers,
            "connections": self.connections,
            "state":       self.state,
            "seed":        self.seed,
            "god":         self.god,
            "color":       NODE_COLORS.get((self.type, self.subtype), "#5a6070"),
        }


@dataclass
class WorldGraph:
    world_id:       str
    seed:           int
    hub_id:         str = ""
    player_hp:      int = 100
    player_max_hp:  int = 100
    weapon_id:      str = "none"
    armor_id:       str = "none"
    bonus_insight:  int = 0          # granted by tavern rest
    nodes:          dict = field(default_factory=dict)   # id → WorldNode


_worlds: dict[str, WorldGraph] = {}


# ── World generation ──────────────────────────────────────────────────────────
def generate_world(seed: Optional[int] = None) -> dict:
    if seed is None:
        seed = random.randint(0, 2 ** 32 - 1)

    rng = random.Random(seed)
    world_id = str(uuid.uuid4())
    world = WorldGraph(world_id=world_id, seed=seed)

    # Hub node
    hub_id = f"hub_{world_id[:8]}"
    hub = WorldNode(
        id=hub_id, type="hub", subtype="citadel",
        biome="pale_drift", difficulty=0, depth=0,
        modifiers=[], connections=[], state="visited", seed=seed,
    )
    world.nodes[hub_id] = hub
    world.hub_id = hub_id

    nodes_by_depth: dict[int, list[str]] = {0: [hub_id]}

    for depth in range(1, MAX_DEPTH + 1):
        count = rng.randint(NODES_PER_DEPTH_MIN, NODES_PER_DEPTH_MAX)
        depth_nodes: list[str] = []

        for i in range(count):
            node_seed = rng.randint(0, 2 ** 32 - 1)
            nrng = random.Random(node_seed)

            ntype, nsubtype = _pick_node_type(depth, nrng)
            biome      = rng.choice(BIOMES)
            difficulty = max(1, min(5, depth // 2)) if depth > 1 else 1
            modifiers  = _pick_modifiers(nrng)

            god = None
            if nsubtype == "trial" and nrng.random() < GOD_CHANCE:
                god = nrng.choice(GODS)

            node_id = f"n{depth}_{i}_{node_seed % 100000:05d}"
            node = WorldNode(
                id=node_id, type=ntype, subtype=nsubtype,
                biome=biome, difficulty=difficulty, depth=depth,
                modifiers=modifiers, connections=[],
                state="unvisited", seed=node_seed, god=god,
            )
            world.nodes[node_id] = node
            depth_nodes.append(node_id)

        nodes_by_depth[depth] = depth_nodes

        # Forward connections: each new node links back to 1–2 parents
        prev = nodes_by_depth[depth - 1]
        for nid in depth_nodes:
            parents = rng.sample(prev, k=min(len(prev), rng.randint(1, 2)))
            for pid in parents:
                if nid not in world.nodes[pid].connections:
                    world.nodes[pid].connections.append(nid)

        # Lateral connections (~40% chance per depth layer)
        if len(depth_nodes) >= 2 and rng.random() < 0.40:
            a, b = rng.sample(depth_nodes, k=2)
            if b not in world.nodes[a].connections:
                world.nodes[a].connections.append(b)

        # Rare back-links (~10%)
        if depth >= 2 and rng.random() < 0.10:
            backlink_pool = nodes_by_depth[depth - 2]
            target = rng.choice(backlink_pool)
            donor  = rng.choice(depth_nodes)
            if target not in world.nodes[donor].connections:
                world.nodes[donor].connections.append(target)

    # Hub connects to 3–4 depth-1 nodes
    depth1 = nodes_by_depth.get(1, [])
    hub_conns = rng.sample(depth1, k=min(len(depth1), rng.randint(3, 4)))
    world.nodes[hub_id].connections = hub_conns

    _worlds[world_id] = world
    return _world_dict(world)


# ── State queries ─────────────────────────────────────────────────────────────
def get_world(world_id: str) -> dict:
    world = _require_world(world_id)
    return _world_dict(world)


def get_node_detail(world_id: str, node_id: str) -> dict:
    world = _require_world(world_id)
    node  = _require_node(world, node_id)
    return {
        "node":    node.to_dict(),
        "options": _node_options(node),
    }


def update_node_state(world_id: str, node_id: str, new_state: str) -> dict:
    world = _require_world(world_id)
    node  = _require_node(world, node_id)
    if new_state not in ("unvisited", "visited", "cleared"):
        raise ValueError(f"Invalid state '{new_state}'.")
    node.state = new_state
    return node.to_dict()


def tavern_rest(world_id: str) -> dict:
    """Heal player and grant +1 bonus insight for next combat."""
    world = _require_world(world_id)
    heal  = max(1, world.player_max_hp // 5)   # 20 % of max HP
    world.player_hp     = min(world.player_max_hp, world.player_hp + heal)
    world.bonus_insight = min(world.bonus_insight + 1, 3)
    return {
        "player_hp":     world.player_hp,
        "player_max_hp": world.player_max_hp,
        "bonus_insight": world.bonus_insight,
        "healed":        heal,
    }


def set_equipment(world_id: str, weapon_id: str, armor_id: str) -> dict:
    world = _require_world(world_id)
    world.weapon_id = weapon_id
    world.armor_id  = armor_id
    return {"weapon_id": weapon_id, "armor_id": armor_id}


def get_player_state(world_id: str) -> dict:
    world = _require_world(world_id)
    return {
        "player_hp":     world.player_hp,
        "player_max_hp": world.player_max_hp,
        "weapon_id":     world.weapon_id,
        "armor_id":      world.armor_id,
        "bonus_insight": world.bonus_insight,
    }


def apply_combat_result(world_id: str, player_hp_after: int) -> None:
    """Called after combat resolves to sync player HP back into world state."""
    world = _require_world(world_id)
    world.player_hp    = max(0, player_hp_after)
    world.bonus_insight = 0   # used


def lazi_dialogue(world_id: str, mistake_topics: list[str], depth: int) -> str:
    """Generate Lazi's contextual dialogue based on mistakes and world depth."""
    rng = random.Random(world_id + str(depth))

    if mistake_topics:
        topic = rng.choice(mistake_topics)
        lines = [
            f"You keep stumbling on {topic}. Spend a moment with it before you go deeper.",
            f"I've watched you. {topic.replace('_', ' ').title()} still trips you up — that's fine. Fix it.",
            f"Depth {depth} ahead. If {topic} shows up again, and it will... you know what to do.",
            f"Hey. {topic.replace('_', ' ').title()} — you missed that one back there. Don't let it follow you.",
        ]
    else:
        lines = [
            f"Clean answers so far. Depth {depth} is a different story.",
            "You look ready. Don't let that feeling fool you.",
            f"Depth {depth} is where things start to fracture. Stay focused.",
            "I've seen people turn back here. Up to you.",
            "The deeper you go, the more the questions change shape. Same answers, different pressure.",
        ]

    return rng.choice(lines)


# ── Internal helpers ──────────────────────────────────────────────────────────
def _pick_node_type(depth: int, rng: random.Random) -> tuple[str, str]:
    roll = rng.random()
    if depth <= 2:
        if roll < 0.40: return "combat",    "standard"
        if roll < 0.55: return "combat",    "forest"
        if roll < 0.70: return "utility",   "tavern"
        if roll < 0.85: return "event",     "lazi"
        return              "challenge", "anomaly"
    elif depth <= 5:
        if roll < 0.30: return "combat",    "standard"
        if roll < 0.50: return "combat",    "trial"
        if roll < 0.60: return "combat",    "forest"
        if roll < 0.72: return "challenge", "anomaly"
        if roll < 0.85: return "utility",   "tavern"
        return              "event",     "lazi"
    else:
        if roll < 0.28: return "combat",    "dungeon"
        if roll < 0.52: return "combat",    "trial"
        if roll < 0.65: return "combat",    "standard"
        if roll < 0.78: return "challenge", "anomaly"
        if roll < 0.88: return "utility",   "tavern"
        return              "event",     "lazi"


def _pick_modifiers(rng: random.Random) -> list[str]:
    count = rng.choices([0, 1, 2], weights=[0.55, 0.35, 0.10])[0]
    return rng.sample(MODIFIERS_POOL, k=count) if count else []


def _node_options(node: WorldNode) -> list[dict]:
    sub = node.subtype
    if node.type == "hub":
        return [{"action": "leave", "label": "Set Out", "desc": "Return to the map."}]

    if sub == "trial":
        god_hint = f" — {node.god} watches" if node.god else ""
        return [
            {"action": "engage",  "label": "Begin Trial",
             "desc": f"Enter the trial{god_hint}."},
            {"action": "observe", "label": "Observe",
             "desc": "Reveal this node's modifiers" + (" and its god." if node.god else ".")},
            {"action": "leave",   "label": "Leave", "desc": "Return to the map."},
        ]
    if node.type == "combat":
        return [
            {"action": "engage", "label": "Engage Enemy",   "desc": "Start combat."},
            {"action": "study",  "label": "Study Area",
             "desc": "Gain +1 insight before fighting."},
            {"action": "leave",  "label": "Leave",          "desc": "Return to the map."},
        ]
    if sub == "anomaly":
        return [
            {"action": "investigate", "label": "Investigate",
             "desc": "Probe the anomaly."},
            {"action": "stabilize",   "label": "Stabilize",
             "desc": "Harder version. Greater reward."},
            {"action": "leave",       "label": "Leave", "desc": "Return to the map."},
        ]
    if sub == "tavern":
        return [
            {"action": "rest",  "label": "Rest",
             "desc": "Restore 20% HP and gain +1 insight charge."},
            {"action": "equip", "label": "Change Equipment",
             "desc": "Swap weapon or armor before your next fight."},
            {"action": "leave", "label": "Leave", "desc": "Return to the map."},
        ]
    if sub == "lazi":
        return [
            {"action": "listen", "label": "Listen",
             "desc": "Hear what Lazi has to say."},
            {"action": "ignore", "label": "Ignore",
             "desc": "Walk past without a word."},
        ]
    # fallback
    return [
        {"action": "engage", "label": "Enter",  "desc": "Face what lies ahead."},
        {"action": "leave",  "label": "Leave",  "desc": "Return to the map."},
    ]


def _require_world(world_id: str) -> WorldGraph:
    w = _worlds.get(world_id)
    if w is None:
        raise ValueError(f"World '{world_id}' not found.")
    return w


def _require_node(world: WorldGraph, node_id: str) -> WorldNode:
    n = world.nodes.get(node_id)
    if n is None:
        raise ValueError(f"Node '{node_id}' not found.")
    return n


def _world_dict(world: WorldGraph) -> dict:
    return {
        "world_id":      world.world_id,
        "seed":          world.seed,
        "hub_id":        world.hub_id,
        "player_hp":     world.player_hp,
        "player_max_hp": world.player_max_hp,
        "weapon_id":     world.weapon_id,
        "armor_id":      world.armor_id,
        "bonus_insight": world.bonus_insight,
        "nodes":         {nid: n.to_dict() for nid, n in world.nodes.items()},
    }

"""
world.py

Node data structure for the dynamic overworld system.
"""

from dataclasses import dataclass, field
from typing import Optional
import random


NODE_TYPES = ("combat", "challenge", "utility", "event", "hub", "anomaly")
NODE_SUBTYPES = {
    "combat": ("drone", "guard", "elite", "boss"),
    "challenge": ("puzzle", "quiz", "time_trial"),
    "utility": ("shop", "healer", "save_point"),
    "event": ("story", "ambush", "treasure"),
    "hub": ("base", "crossroads", "sanctuary"),
    "anomaly": ("rift", "void_tear", "pale_gate"),  # rare anomaly variants
}
BIOMES = ("forest", "desert", "ice", "void", "city", "ruins")
NODE_STATES = ("unvisited", "visited", "cleared")

# Anomaly nodes: rare, only at depth ≥ 3, ~8% chance per eligible depth layer
ANOMALY_SPAWN_CHANCE = 0.08
ANOMALY_MIN_DEPTH = 3


@dataclass
class Node:
    id: str
    type: str
    subtype: str
    biome: str
    depth: int
    difficulty: int
    modifiers: list[str] = field(default_factory=list)
    connections: list[str] = field(default_factory=list)
    state: str = "unvisited"
    seed: int = 0
    god: Optional[str] = None


def create_node(id: str, type: str, depth: int, biome: str = "forest") -> Node:
    subtype = random.choice(NODE_SUBTYPES.get(type, ("generic",)))
    difficulty = min(10, max(1, depth // 2))
    seed = random.randint(0, 2**31 - 1)
    return Node(
        id=id,
        type=type,
        subtype=subtype,
        biome=biome,
        depth=depth,
        difficulty=difficulty,
        modifiers=[],
        connections=[],
        state="unvisited",
        seed=seed,
        god=None,
    )


def generate_world() -> dict[str, Node]:
    nodes: dict[str, Node] = {}

    hub = create_node("citadel", "hub", 0, "city")
    hub.subtype = "citadel"
    nodes["citadel"] = hub

    depth_nodes: dict[int, list[str]] = {0: ["citadel"]}

    for depth in range(1, 11):
        count = random.randint(2, 4)
        depth_nodes[depth] = []
        for i in range(count):
            node_id = f"node_{depth}_{i}"
            weights = [0.5, 0.25, 0.15, 0.1]
            node_type = random.choices(
                ["combat", "challenge", "utility", "event"],
                weights=weights,
            )[0]
            node = create_node(node_id, node_type, depth)
            nodes[node_id] = node
            depth_nodes[depth].append(node_id)

        # ── Anomaly node: rare spawn at depth ≥ ANOMALY_MIN_DEPTH ────────────
        if depth >= ANOMALY_MIN_DEPTH and random.random() < ANOMALY_SPAWN_CHANCE:
            anomaly_id = f"anomaly_{depth}"
            anomaly = create_node(anomaly_id, "anomaly", depth, biome="void")
            anomaly.difficulty = min(10, depth + 2)  # harder than regular nodes
            nodes[anomaly_id] = anomaly
            depth_nodes[depth].append(anomaly_id)

    # ── Step 1: Forward connections depth → depth+1 (occasionally +2 skip) ──
    for depth in range(1, 11):
        for node_id in depth_nodes[depth]:
            node = nodes[node_id]

            # Always connect to 1–2 nodes at depth+1
            if depth < 10:
                fwd_pool = depth_nodes[depth + 1]
                fwd_count = min(len(fwd_pool), random.randint(1, 2))
                for target in random.sample(fwd_pool, fwd_count):
                    if target not in node.connections:
                        node.connections.append(target)

                # 20% chance: single skip connection to depth+2 (no further)
                if depth < 9 and random.random() < 0.20:
                    skip_pool = depth_nodes[depth + 2]
                    skip_target = random.choice(skip_pool)
                    if skip_target not in node.connections:
                        node.connections.append(skip_target)

            # 30% chance: lateral connection within same depth layer
            same = [n for n in depth_nodes[depth] if n != node_id and n not in node.connections]
            if same and random.random() < 0.30:
                node.connections.append(random.choice(same))

    # ── Step 2: Citadel (depth 0) connects only to ALL depth-1 nodes ─────────
    for node_id in depth_nodes[1]:
        if node_id not in nodes["citadel"].connections:
            nodes["citadel"].connections.append(node_id)

    # ── Step 3: Bidirectional edges — only for depth diff ≤ 2 ────────────────
    # (prevents deep nodes from tunnelling back to citadel via the fallback)
    for node in list(nodes.values()):
        for conn_id in list(node.connections):
            if conn_id not in nodes:
                continue
            other = nodes[conn_id]
            depth_diff = abs(other.depth - node.depth)
            if depth_diff <= 2 and node.id not in other.connections:
                other.connections.append(node.id)

    return nodes
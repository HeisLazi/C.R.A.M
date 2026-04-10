"""
world.py

Node data structure for the dynamic overworld system.
"""

from dataclasses import dataclass, field
from typing import Optional
import random


NODE_TYPES = ("combat", "challenge", "utility", "event", "hub")
NODE_SUBTYPES = {
    "combat": ("drone", "guard", "elite", "boss"),
    "challenge": ("puzzle", "quiz", "time_trial"),
    "utility": ("shop", "healer", "save_point"),
    "event": ("story", "ambush", "treasure"),
    "hub": ("base", "crossroads", "sanctuary"),
}
BIOMES = ("forest", "desert", "ice", "void", "city", "ruins")
NODE_STATES = ("unvisited", "visited", "cleared")


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

    for depth in range(1, 11):
        for node_id in depth_nodes[depth]:
            node = nodes[node_id]

            if depth < 10:
                forward_targets = random.sample(
                    depth_nodes[depth + 1],
                    min(len(depth_nodes[depth + 1]), random.randint(1, 2)),
                )
                node.connections.extend(forward_targets)

            if depth > 1:
                same_depth_targets = [
                    n for n in depth_nodes[depth]
                    if n != node_id and n not in node.connections
                ]
                if same_depth_targets:
                    lateral = random.choice(same_depth_targets)
                    node.connections.append(lateral)

            if len(node.connections) < 2:
                fallback = random.choice(depth_nodes[0])
                if fallback not in node.connections:
                    node.connections.append(fallback)

    for node in nodes.values():
        for conn_id in node.connections:
            if conn_id in nodes and node.id not in nodes[conn_id].connections:
                nodes[conn_id].connections.append(node.id)

    return nodes
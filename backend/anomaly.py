"""
anomaly.py

Anomaly challenge system - non-combat gameplay.
"""

import random
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AnomalyStep:
    question: str
    step_type: str
    options: list[str]
    answer: str


@dataclass
class AnomalySession:
    id: str
    node_id: str
    steps: list[AnomalyStep] = field(default_factory=list)
    current_step: int = 0
    completed: bool = False
    hard: bool = False


_anomaly_sessions: dict[str, AnomalySession] = {}


ANOMALY_TEMPLATES = [
    {
        "type": "multi",
        "question": "Which data structure uses LIFO ordering?",
        "options": ["Queue", "Stack", "Array", "Tree"],
        "answer": "Stack",
    },
    {
        "type": "multi",
        "question": "What is the time complexity of binary search?",
        "options": ["O(n)", "O(log n)", "O(n log n)", "O(1)"],
        "answer": "O(log n)",
    },
    {
        "type": "sequence",
        "question": "What comes next: 2, 4, 8, 16, ?",
        "options": ["24", "32", "30", "28"],
        "answer": "32",
    },
    {
        "type": "logic",
        "question": "If A → B and A is true, then:",
        "options": ["B is false", "B is true", "B is unknown", "A is false"],
        "answer": "B is true",
    },
    {
        "type": "multi",
        "question": "Which traversal visits root first?",
        "options": ["Inorder", "Preorder", "Postorder", "Level-order"],
        "answer": "Preorder",
    },
    {
        "type": "logic",
        "question": "NOT (A AND B) is equivalent to:",
        "options": ["NOT A OR NOT B", "NOT A AND NOT B", "A OR B", "A AND B"],
        "answer": "NOT A OR NOT B",
    },
    {
        "type": "sequence",
        "question": "What comes next: A, C, E, G, ?",
        "options": ["H", "I", "J", "K"],
        "answer": "I",
    },
    {
        "type": "multi",
        "question": "What is a hash table's average lookup time?",
        "options": ["O(n)", "O(log n)", "O(1)", "O(n^2)"],
        "answer": "O(1)",
    },
]


def start_anomaly(node, hard: bool = False) -> AnomalySession:
    for s in _anomaly_sessions.values():
        if s.node_id == node.id and not s.completed:
            return s

    rng = random.Random(node.seed)
    step_count = 4 if hard else 2
    templates = rng.sample(ANOMALY_TEMPLATES, k=min(step_count, len(ANOMALY_TEMPLATES)))

    steps = []
    for t in templates:
        step = AnomalyStep(
            question=t["question"],
            step_type=t["type"],
            options=t["options"],
            answer=t["answer"],
        )
        steps.append(step)

    session = AnomalySession(
        id=str(uuid.uuid4()),
        node_id=node.id,
        steps=steps,
        current_step=0,
        completed=False,
        hard=hard,
    )

    _anomaly_sessions[session.id] = session
    return session


def get_current_step(session: AnomalySession) -> dict:
    step = session.steps[session.current_step]
    return {
        "question": step.question,
        "type": step.step_type,
        "options": step.options,
        "step": session.current_step,
        "total": len(session.steps),
    }


def get_anomaly_session(session_id: str) -> Optional[AnomalySession]:
    return _anomaly_sessions.get(session_id)


def submit_anomaly_answer(session_id: str, answer: str) -> dict:
    session = _anomaly_sessions.get(session_id)
    if not session:
        return {"type": "error", "message": "Anomaly session not found"}

    if session.completed:
        return {"type": "error", "message": "Anomaly already completed"}

    current = session.steps[session.current_step]
    correct = answer.lower().strip() == current.answer.lower().strip()

    if correct:
        session.current_step += 1
        if session.current_step >= len(session.steps):
            session.completed = True
            return {
                "type": "anomaly_complete",
                "correct": True,
                "completed": True,
                "reward": {"xp": 10 if not session.hard else 20},
            }
        return {
            "type": "anomaly_progress",
            "correct": True,
            "step_data": get_current_step(session),
        }
    else:
        session.completed = True
        return {
            "type": "anomaly_fail",
            "correct": False,
            "completed": True,
            "correct_answer": current.answer,
            "step": session.current_step,
        }
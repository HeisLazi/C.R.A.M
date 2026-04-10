"""
question_engine.py

Responsibilities:
- Load questions from JSON
- Serve a question (optionally filtered by concept_id, excluding already-seen IDs)
- Evaluate a player's answer
- Return concept hints via get_hint()
"""

import json
import random
from pathlib import Path
from typing import Optional

QUESTIONS_PATH = Path(__file__).parent.parent / "subjects" / "dsa2" / "questions.json"
CONCEPTS_PATH  = Path(__file__).parent.parent / "subjects" / "dsa2" / "concepts.json"

_questions: list[dict] = []
_concepts:  list[dict] = []


def _load() -> list[dict]:
    global _questions
    if not _questions:
        with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
            _questions = json.load(f)
    return _questions


def _load_concepts() -> list[dict]:
    global _concepts
    if not _concepts:
        with open(CONCEPTS_PATH, "r", encoding="utf-8") as f:
            _concepts = json.load(f)
    return _concepts


def get_question(
    concept_id: Optional[str] = None,
    seen_ids: Optional[set] = None,
    difficulty_max: Optional[int] = None,
) -> Optional[dict]:
    """
    Return a random question, preferring unseen questions.

    Args:
        concept_id:    Filter to a specific concept. Falls back to full pool if none match.
        seen_ids:      Set of question IDs already asked this combat. Excluded first;
                       if the filtered pool is exhausted, seen questions are re-used
                       (pool reset) so combat never deadlocks.
        difficulty_max: If set, only serve questions with difficulty <= this value.
    """
    questions = _load()

    # ── Filter by concept ─────────────────────────────────────────────────
    if concept_id:
        pool = [q for q in questions if q["concept_id"] == concept_id]
        if not pool:
            pool = questions  # fallback to full pool if concept not found
    else:
        pool = questions

    # ── Filter by difficulty ──────────────────────────────────────────────
    if difficulty_max is not None:
        filtered = [q for q in pool if q.get("difficulty", 1) <= difficulty_max]
        if filtered:
            pool = filtered

    # ── Anti-repeat: exclude already-seen questions ───────────────────────
    if seen_ids:
        unseen = [q for q in pool if q["id"] not in seen_ids]
        if unseen:
            pool = unseen
        # else: all questions seen — reset (allow repeats rather than deadlock)

    return random.choice(pool) if pool else None


def get_question_by_id(question_id: str) -> Optional[dict]:
    questions = _load()
    for q in questions:
        if q["id"] == question_id:
            return q
    return None


def evaluate_answer(question_id: str, answer: str) -> dict:
    question = get_question_by_id(question_id)
    if question is None:
        raise ValueError(f"Question '{question_id}' not found.")

    correct = question["correct_answer"].strip().lower() == answer.strip().lower()
    return {
        "correct": correct,
        "correct_answer": question["correct_answer"],
        "explanation": question["explanation"],
    }


def get_hint(question_id: str) -> str:
    """Return the concept-level explanation — partial help without revealing the answer."""
    question = get_question_by_id(question_id)
    if question is None:
        return "No hint available."

    concept_id = question.get("concept_id")
    concepts = _load_concepts()
    for concept in concepts:
        if concept.get("id") == concept_id:
            return concept.get("explanation", "No hint available.")
    return "No hint available."


def reload_questions() -> int:
    """Force reload questions from disk. Returns count. Useful after adding new questions."""
    global _questions
    _questions = []
    return len(_load())

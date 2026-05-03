"""
codex.py

Tracks all answered questions per session.
Responsibilities:
- log_attempt: record each answer attempt
- get_codex:   return full attempt history for a session
- get_mistakes: return only incorrect attempts

Combat logic is NOT touched here.
"""

from dataclasses import dataclass


@dataclass
class CodexEntry:
    question_id:     str
    question_text:   str
    selected_answer: str
    correct_answer:  str
    correct:         bool
    explanation:     str
    round:           int


_codex: dict[str, list[CodexEntry]] = {}


def log_attempt(
    session_id:      str,
    question_id:     str,
    question_text:   str,
    selected_answer: str,
    correct_answer:  str,
    correct:         bool,
    explanation:     str,
    round:           int = 1,
) -> None:
    if session_id not in _codex:
        _codex[session_id] = []
    _codex[session_id].append(CodexEntry(
        question_id=question_id,
        question_text=question_text,
        selected_answer=selected_answer,
        correct_answer=correct_answer,
        correct=correct,
        explanation=explanation,
        round=round,
    ))


def get_codex(session_id: str) -> list[dict]:
    return [_to_dict(e) for e in _codex.get(session_id, [])]


def get_mistakes(session_id: str) -> list[dict]:
    return [_to_dict(e) for e in _codex.get(session_id, []) if not e.correct]


def _to_dict(e: CodexEntry) -> dict:
    return {
        "question_id":     e.question_id,
        "question":        e.question_text,
        "selected":        e.selected_answer,
        "correct_answer":  e.correct_answer,
        "correct":         e.correct,
        "explanation":     e.explanation,
        "round":           e.round,
    }

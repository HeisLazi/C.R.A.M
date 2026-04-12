"""
question_engine.py

Responsibilities:
- Load questions from JSON (flat array OR new {_meta, questions} object format)
- Serve a question filtered by concept_id, tier, question types, and seen IDs
- Evaluate a player's answer (auto for MC/TF; self-evaluated for open-ended)
- Return concept hints via get_hint()
- Support hot-swapping the active subject folder via set_subject()
"""

import json
import random
import sys
from pathlib import Path
from typing import Optional

# Same frozen-mode path logic as main.py — subjects/ must be next to the .exe
if getattr(sys, 'frozen', False):
    SUBJECTS_DIR = Path(sys.executable).parent / "subjects"
else:
    SUBJECTS_DIR = Path(__file__).parent.parent / "subjects"

# ── Active subject state ─────────────────────────────────────────────────────
_active_subject: str       = "dsa2"
_questions:      list[dict] = []
_concepts:       list[dict] = []
_meta:           dict       = {}

# Question types that require self-evaluation (player sees model answer and clicks yes/no)
OPEN_ENDED_TYPES = ("define", "short_exam", "long_exam")

# Valid tiers in ascending difficulty
VALID_TIERS = ("standard", "elite", "boss", "anomaly")


# ── Subject management ───────────────────────────────────────────────────────

def get_active_subject() -> str:
    return _active_subject


def set_subject(subject_id: str) -> dict:
    """
    Switch the active subject. Clears all caches so the next call to _load()
    picks up the new subject's files. Returns a summary of the new subject.
    """
    global _active_subject, _questions, _concepts, _meta

    subject_dir = SUBJECTS_DIR / subject_id
    questions_path = subject_dir / "questions.json"

    if not subject_dir.is_dir():
        raise ValueError(f"Subject folder '{subject_id}' not found in subjects/")
    if not questions_path.exists():
        raise ValueError(f"No questions.json found in subjects/{subject_id}/")

    _active_subject = subject_id
    _questions = []
    _concepts  = []
    _meta      = {}

    # Eagerly load so we can return stats
    qs = _load()
    return {
        "active": subject_id,
        "question_count": len(qs),
        "has_concepts": (subject_dir / "concepts.json").exists(),
    }


def list_subjects() -> list[dict]:
    """Return all subject folders that contain a questions.json file."""
    result = []
    if not SUBJECTS_DIR.is_dir():
        return result

    for folder in sorted(SUBJECTS_DIR.iterdir()):
        if not folder.is_dir():
            continue
        qpath = folder / "questions.json"
        cpath = folder / "concepts.json"
        if not qpath.exists():
            continue  # must have questions to count as a subject

        # Count questions without fully caching them if not active
        q_count = 0
        try:
            with open(qpath, "r", encoding="utf-8") as f:
                raw = json.load(f)
            qs = raw.get("questions", raw) if isinstance(raw, dict) else raw
            q_count = len(qs) if isinstance(qs, list) else 0
        except Exception:
            pass

        # Count PDFs in this folder
        pdf_count = len(list(folder.glob("*.pdf")))

        # Pretty name: folder name uppercased, underscores → spaces
        display = folder.name.replace("_", " ").replace("-", " ").upper()

        result.append({
            "id":            folder.name,
            "name":          display,
            "question_count": q_count,
            "has_concepts":  cpath.exists(),
            "pdf_count":     pdf_count,
            "is_active":     folder.name == _active_subject,
        })

    return result


def list_all_pdfs() -> list[dict]:
    """
    Return PDFs from ALL subject folders, grouped by folder.
    Each entry: { folder, folder_name, pdfs: [{name, filename, url, size_kb}] }
    """
    groups = []
    if not SUBJECTS_DIR.is_dir():
        return groups

    for folder in sorted(SUBJECTS_DIR.iterdir()):
        if not folder.is_dir():
            continue
        pdfs = []
        for pdf_path in sorted(folder.glob("*.pdf")):
            pdfs.append({
                "name":     pdf_path.stem.replace("_", " ").replace("-", " "),
                "filename": pdf_path.name,
                "url":      f"/subjects/{folder.name}/{pdf_path.name}",
                "size_kb":  round(pdf_path.stat().st_size / 1024),
            })
        if pdfs:
            groups.append({
                "folder":      folder.name,
                "folder_name": folder.name.replace("_", " ").replace("-", " ").upper(),
                "pdfs":        pdfs,
            })

    return groups


# ── Internal loaders ─────────────────────────────────────────────────────────

def _questions_path() -> Path:
    return SUBJECTS_DIR / _active_subject / "questions.json"


def _concepts_path() -> Path:
    return SUBJECTS_DIR / _active_subject / "concepts.json"


def _load() -> list[dict]:
    global _questions, _meta
    if not _questions:
        path = _questions_path()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Support both old flat-array format and new {_meta, questions} object format
        if isinstance(data, list):
            _questions = data
            _meta = {}
        else:
            _questions = data.get("questions", [])
            _meta = data.get("_meta", {})
    return _questions


def _load_concepts() -> list[dict]:
    global _concepts
    if not _concepts:
        path = _concepts_path()
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                _concepts = json.load(f)
    return _concepts


# ── Public API ───────────────────────────────────────────────────────────────

def get_meta() -> dict:
    """Return the _meta block from the questions JSON (empty dict if flat format)."""
    _load()
    return _meta


def get_game_config() -> dict:
    """
    Return the optional game_config section from _meta.
    This allows subjects to extend the game with custom enemies, weapons,
    armors, and upgrades without touching the base game code.

    Structure:
      {
        "custom_enemies":  [...],   # extra enemies added to the combat pool
        "extra_weapons":   {...},   # keyed by weapon_id, merged into WEAPONS_CATALOG
        "extra_armors":    {...},   # keyed by armor_id,  merged into ARMORS_CATALOG
        "extra_upgrades":  {...},   # keyed by upgrade_id, merged into UPGRADES_CATALOG
      }
    Returns an empty dict if the section is absent.
    """
    _load()
    return _meta.get("game_config", {})


def get_question(
    concept_id:     Optional[str]  = None,
    seen_ids:       Optional[set]  = None,
    difficulty_max: Optional[int]  = None,
    tier:           Optional[str]  = None,       # "standard" | "elite" | "boss" | "anomaly"
    question_types: Optional[list] = None,       # ["multiple_choice", "true_false", "define", ...]
) -> Optional[dict]:
    """
    Return a random question matching the given filters.

    Filtering order:
      1. concept_id  — fallback to full pool if concept not found
      2. tier        — fallback to lower tiers if requested tier is empty
      3. question_types — fallback to all types if specified types yield nothing
      4. difficulty_max
      5. Anti-repeat: exclude seen_ids (resets pool if all seen)
    """
    questions = _load()

    # ── 1. Filter by concept ────────────────────────────────────────────────
    if concept_id:
        pool = [q for q in questions if q.get("concept_id") == concept_id]
        if not pool:
            pool = questions          # concept not found → full pool
    else:
        pool = questions

    # ── 2. Filter by tier ───────────────────────────────────────────────────
    if tier:
        tier_pool = [q for q in pool if q.get("tier") == tier]
        if tier_pool:
            pool = tier_pool
        else:
            # Fallback: allow any tier lower than the requested one
            idx = VALID_TIERS.index(tier) if tier in VALID_TIERS else 0
            allowed_tiers = VALID_TIERS[:max(1, idx)]
            fallback_pool = [q for q in pool if q.get("tier", "standard") in allowed_tiers]
            if fallback_pool:
                pool = fallback_pool
            # else: keep pool as-is (no tier match at all)

    # ── 3. Filter by question_types ──────────────────────────────────────────
    if question_types:
        type_pool = [q for q in pool if q.get("type", "multiple_choice") in question_types]
        if type_pool:
            pool = type_pool
        # else: keep pool — no questions of requested types, use anything available

    # ── 4. Filter by difficulty ──────────────────────────────────────────────
    if difficulty_max is not None:
        diff_pool = [q for q in pool if q.get("difficulty", 1) <= difficulty_max]
        if diff_pool:
            pool = diff_pool

    # ── 5. Anti-repeat: exclude already-seen questions ───────────────────────
    if seen_ids:
        unseen = [q for q in pool if q["id"] not in seen_ids]
        if unseen:
            pool = unseen
        # else: all questions seen — allow repeats (pool reset) to avoid deadlock

    return random.choice(pool) if pool else None


def get_question_by_id(question_id: str) -> Optional[dict]:
    questions = _load()
    for q in questions:
        if q["id"] == question_id:
            return q
    return None


def evaluate_answer(question_id: str, answer: str) -> dict:
    """
    Evaluate a player's answer.

    For multiple_choice / true_false: automatic exact-match comparison.
    For define / short_exam / long_exam: self-evaluated — the player submits
    "self:correct" or "self:incorrect" after viewing the model answer.
    """
    question = get_question_by_id(question_id)
    if question is None:
        raise ValueError(f"Question '{question_id}' not found.")

    q_type = question.get("type", "multiple_choice")

    if q_type in OPEN_ENDED_TYPES:
        # Self-evaluation: frontend shows model answer, player clicks yes/no
        ans_clean = answer.strip().lower()
        correct = ans_clean in ("self:correct", "correct", "yes", "1", "true")
        return {
            "correct": correct,
            "correct_answer": question["correct_answer"],
            "explanation": question.get("explanation", ""),
            "self_evaluated": True,
            "question_type": q_type,
        }

    # Auto-evaluated (multiple_choice, true_false)
    correct = question["correct_answer"].strip().lower() == answer.strip().lower()
    return {
        "correct": correct,
        "correct_answer": question["correct_answer"],
        "explanation": question.get("explanation", ""),
        "self_evaluated": False,
        "question_type": q_type,
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
    global _questions, _meta
    _questions = []
    _meta = {}
    return len(_load())


def get_question_stats() -> dict:
    """Return distribution stats for the loaded question pool."""
    questions = _load()
    by_type: dict[str, int] = {}
    by_tier: dict[str, int] = {}
    by_concept: dict[str, int] = {}
    for q in questions:
        t = q.get("type", "multiple_choice")
        ti = q.get("tier", "standard")
        c = q.get("concept_id", "unknown")
        by_type[t]    = by_type.get(t, 0) + 1
        by_tier[ti]   = by_tier.get(ti, 0) + 1
        by_concept[c] = by_concept.get(c, 0) + 1
    return {
        "total": len(questions),
        "by_type": by_type,
        "by_tier": by_tier,
        "by_concept": by_concept,
    }

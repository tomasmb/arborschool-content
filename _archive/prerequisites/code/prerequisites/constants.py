"""Constants for the prerequisite atom generation pipeline.

Defines grade levels, ID schemes, output paths, and ordering used
throughout the pipeline. Prerequisite content covers Educación Básica
(1°-8°) and Educación Media (1°-2°), levels below PAES M1.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Grade levels
# ---------------------------------------------------------------------------

# Grade-level prefixes used in standard and atom IDs.
# Ordered from lowest to highest for bottom-up generation.
GRADE_LEVELS: list[str] = [
    "EB1", "EB2", "EB3", "EB4",
    "EB5", "EB6", "EB7", "EB8",
    "EM1", "EM2",
]

GRADE_LEVEL_LABELS: dict[str, str] = {
    "EB1": "1° Educación Básica",
    "EB2": "2° Educación Básica",
    "EB3": "3° Educación Básica",
    "EB4": "4° Educación Básica",
    "EB5": "5° Educación Básica",
    "EB6": "6° Educación Básica",
    "EB7": "7° Educación Básica",
    "EB8": "8° Educación Básica",
    "EM1": "1° Educación Media",
    "EM2": "2° Educación Media",
}

VALID_GRADE_PREFIXES = frozenset(GRADE_LEVELS)

# Regex fragment for matching any valid grade-level prefix in IDs
_GRADE_RE = "|".join(GRADE_LEVELS)
PREREQ_STANDARD_ID_RE = rf"^({_GRADE_RE})-(NUM|ALG|GEO|PROB)-\d{{2}}$"
PREREQ_ATOM_ID_RE = rf"^A-({_GRADE_RE})-(NUM|ALG|GEO|PROB)-\d{{2}}-\d{{2}}$"

# Non-capturing version for free-text extraction (findall returns strings).
PREREQ_ATOM_ID_PATTERN = r"A-(?:EB[1-8]|EM[12])-(?:NUM|ALG|GEO|PROB)-\d{2}-\d{2}"


def grade_order(grade: str) -> int:
    """Return sort key for a grade prefix (lower = earlier in curriculum)."""
    try:
        return GRADE_LEVELS.index(grade)
    except ValueError:
        return len(GRADE_LEVELS)


def extract_grade_from_atom_id(atom_id: str) -> str | None:
    """Extract grade prefix from an atom ID like A-EB5-NUM-01-02."""
    parts = atom_id.split("-")
    if len(parts) >= 3 and parts[0] == "A":
        candidate = parts[1]
        if candidate in VALID_GRADE_PREFIXES or candidate == "M1":
            return candidate
    return None

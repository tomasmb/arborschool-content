"""Shared helpers for the mini-lesson generation pipeline.

Input loading (atom + enrichment + questions), checkpoint management,
template type resolution, and question sampling.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from app.atoms.models import Atom, CanonicalAtomsFile
from app.mini_lessons.models import (
    PHASE_PREREQUISITES,
    TEMPLATE_MAP,
    LessonContext,
    LessonPlan,
    LessonSection,
)
from app.question_generation.models import AtomEnrichment
from app.utils.paths import (
    ATOMS_DIR,
    MINI_LESSONS_DIR,
    QUESTION_GENERATION_DIR,
)

logger = logging.getLogger(__name__)

# Max sample questions per difficulty for context (avoid huge prompts)
_MAX_SAMPLES_PER_DIFFICULTY = 3


# ---------------------------------------------------------------------------
# Atom loading (reuses canonical atoms infrastructure)
# ---------------------------------------------------------------------------


def load_atom(atom_id: str) -> Atom | None:
    """Load an atom by ID from the canonical atoms files."""
    if not ATOMS_DIR.exists():
        logger.error("Atoms directory not found: %s", ATOMS_DIR)
        return None

    for atoms_file in ATOMS_DIR.glob("*_atoms.json"):
        try:
            data = json.loads(atoms_file.read_text(encoding="utf-8"))
            canonical = CanonicalAtomsFile.model_validate(data)
            atom = canonical.get_atom_by_id(atom_id)
            if atom:
                return atom
        except Exception as exc:
            logger.warning("Error reading %s: %s", atoms_file, exc)

    logger.error("Atom %s not found in any atoms file", atom_id)
    return None


# ---------------------------------------------------------------------------
# Enrichment loading (from question pipeline checkpoints)
# ---------------------------------------------------------------------------


def load_enrichment(atom_id: str) -> AtomEnrichment | None:
    """Load enrichment data from the question pipeline checkpoint."""
    ckpt_path = (
        QUESTION_GENERATION_DIR
        / atom_id
        / "checkpoints"
        / "phase_1_enrichment.json"
    )
    if not ckpt_path.exists():
        logger.warning("No enrichment checkpoint for %s", atom_id)
        return None

    try:
        data = json.loads(ckpt_path.read_text(encoding="utf-8"))
        raw = data.get("enrichment_data")
        if not raw:
            logger.warning("Empty enrichment data for %s", atom_id)
            return None
        return AtomEnrichment.model_validate(raw)
    except Exception as exc:
        logger.warning("Error loading enrichment for %s: %s", atom_id, exc)
        return None


def atom_requires_images(atom_id: str) -> bool:
    """Return True if the atom's enrichment lists required image types.

    Checks ``required_image_types`` in the enrichment checkpoint.
    Returns False when no enrichment exists (conservative: allow run).
    """
    enrichment = load_enrichment(atom_id)
    if enrichment is None:
        return False
    return len(enrichment.required_image_types) > 0


# ---------------------------------------------------------------------------
# Question sampling (from question pipeline final validation)
# ---------------------------------------------------------------------------


def load_sample_questions(
    atom_id: str,
    max_per_difficulty: int = _MAX_SAMPLES_PER_DIFFICULTY,
) -> dict[str, list[str]]:
    """Load sample question summaries from the question pipeline.

    Extracts plain-text question stems (not full QTI XML) grouped
    by difficulty. Used to anchor lesson content to what students
    will actually practice.

    Returns:
        Dict mapping difficulty -> list of question stem texts.
    """
    ckpt_path = (
        QUESTION_GENERATION_DIR
        / atom_id
        / "checkpoints"
        / "phase_9_final_validation.json"
    )
    if not ckpt_path.exists():
        logger.info("No final questions checkpoint for %s", atom_id)
        return {}

    try:
        data = json.loads(ckpt_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Error reading questions for %s: %s", atom_id, exc)
        return {}

    items = data.get("items", [])
    result: dict[str, list[str]] = {"easy": [], "medium": [], "hard": []}

    for item in items:
        meta = item.get("pipeline_meta", {})
        difficulty = meta.get("difficulty_level", "medium")
        if difficulty not in result:
            continue
        if len(result[difficulty]) >= max_per_difficulty:
            continue

        stem = _extract_question_stem(item.get("qti_xml", ""))
        if stem:
            result[difficulty].append(stem)

    loaded = sum(len(v) for v in result.values())
    if loaded:
        logger.info(
            "Loaded %d sample questions for %s", loaded, atom_id,
        )
    return result


def _extract_question_stem(qti_xml: str) -> str:
    """Extract plain-text question stem from QTI XML.

    Uses simple tag stripping to get readable text without
    importing heavy XML parsers. Returns empty string on failure.
    """

    prompt_match = re.search(
        r"<prompt[^>]*>(.*?)</prompt>",
        qti_xml,
        re.DOTALL,
    )
    if not prompt_match:
        return ""

    text = prompt_match.group(1)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:300] if text else ""


# ---------------------------------------------------------------------------
# Template type resolution
# ---------------------------------------------------------------------------


def resolve_template_type(tipo_atomico: str) -> str | None:
    """Map atom tipo_atomico to template type (P, C, or M).

    Returns None for unknown tipo_atomico values (no fallback).
    """
    return TEMPLATE_MAP.get(tipo_atomico)


# ---------------------------------------------------------------------------
# Context builder (Phase 0)
# ---------------------------------------------------------------------------


def build_lesson_context(
    atom: Atom,
    enrichment: AtomEnrichment | None,
    sample_questions: dict[str, list[str]],
) -> LessonContext | None:
    """Build the full lesson context from atom + enrichment + questions.

    Returns None if the atom's tipo_atomico is unrecognized.
    """
    template = resolve_template_type(atom.tipo_atomico)
    if template is None:
        logger.error(
            "Unknown tipo_atomico '%s' for atom %s — cannot "
            "determine template type",
            atom.tipo_atomico, atom.id,
        )
        return None
    return LessonContext(
        atom_id=atom.id,
        atom_title=atom.titulo,
        atom_description=atom.descripcion,
        eje=atom.eje,
        tipo_atomico=atom.tipo_atomico,
        template_type=template,
        criterios_atomicos=atom.criterios_atomicos,
        ejemplos_conceptuales=atom.ejemplos_conceptuales,
        notas_alcance=atom.notas_alcance,
        prerequisites=atom.prerrequisitos,
        enrichment=enrichment,
        sample_questions=sample_questions,
    )


# ---------------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------------


def get_output_dir(atom_id: str, override: str | None = None) -> Path:
    """Get the output directory for a mini-lesson run."""
    if override:
        return Path(override)
    return MINI_LESSONS_DIR / atom_id


# ---------------------------------------------------------------------------
# Checkpoint management
# ---------------------------------------------------------------------------


def save_checkpoint(
    output_dir: Path,
    phase_num: int,
    phase_name: str,
    data: dict,
) -> None:
    """Save a phase checkpoint to disk."""
    ckpt_dir = output_dir / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    path = ckpt_dir / f"phase_{phase_num}_{phase_name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    logger.info("Checkpoint saved: %s", path.name)


def load_checkpoint(
    output_dir: Path,
    phase_num: int,
    phase_name: str,
) -> dict | None:
    """Load a phase checkpoint from disk, or None if not found."""
    path = (
        output_dir / "checkpoints"
        / f"phase_{phase_num}_{phase_name}.json"
    )
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Checkpoint loaded: %s", path.name)
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Invalid checkpoint %s: %s", path.name, exc)
        return None


def check_prerequisites(
    phase_group: str,
    output_dir: Path,
) -> tuple[bool, list[str]]:
    """Validate required checkpoints exist for a phase group."""
    reqs = PHASE_PREREQUISITES.get(phase_group, [])
    missing: list[str] = []

    for phase_num, phase_name in reqs:
        ckpt = load_checkpoint(output_dir, phase_num, phase_name)
        if ckpt is None:
            missing.append(
                f"Phase {phase_num} ({phase_name}) must complete "
                f"before '{phase_group}' can run",
            )

    return len(missing) == 0, missing


def find_resume_phase_group(output_dir: Path) -> str | None:
    """Find the phase group to resume from based on checkpoints."""
    ckpt_dir = output_dir / "checkpoints"
    if not ckpt_dir.exists():
        return None

    max_phase: int | None = None
    for path in ckpt_dir.glob("phase_*_*.json"):
        try:
            phase_num = int(path.stem.split("_")[1])
            if max_phase is None or phase_num > max_phase:
                max_phase = phase_num
        except (IndexError, ValueError):
            continue

    if max_phase is None:
        return None

    checkpoint_to_next: dict[int, str] = {
        0: "plan",
        1: "generate",
        2: "generate",
        3: "assemble",
        4: "quality",
        5: "output",
    }
    return checkpoint_to_next.get(max_phase)


# ---------------------------------------------------------------------------
# Enrichment extraction (shared by validators + batch builders)
# ---------------------------------------------------------------------------


def extract_plan_error_families(plan: LessonPlan) -> list[str]:
    """Return the deduplicated set of error families used in a plan.

    Extracts families from the single worked example so the quality
    gate checks coverage against the plan's selected families
    instead of the full enrichment list.
    """
    families: set[str] = set()
    families.update(plan.worked_example.error_families_addressed)
    return sorted(families)


def extract_enrichment_for_gate(
    ctx: LessonContext,
    plan: LessonPlan | None = None,
) -> tuple[list[str], list[str], dict[str, list[str]]]:
    """Extract enrichment data needed for quality gate evaluation.

    When a plan is provided, uses the plan's selected error
    families (max 5) instead of the full enrichment list.

    Returns:
        Tuple of (in_scope items, error family names, difficulty rubric).
    """
    if ctx.enrichment is None:
        return [], [], {}

    data = ctx.enrichment.model_dump()
    scope = data.get("scope_guardrails", {})
    in_scope = scope.get("in_scope", [])

    if plan is not None:
        error_names = extract_plan_error_families(plan)
    else:
        error_fams = data.get("error_families", [])
        error_names = [e.get("name", "") for e in error_fams]

    rubric = data.get("difficulty_rubric", {})

    return in_scope, error_names, rubric


# ---------------------------------------------------------------------------
# Section serialization
# ---------------------------------------------------------------------------


def serialize_sections(sections: list[LessonSection]) -> list[dict]:
    """Serialize LessonSection list for checkpoint storage."""
    return [s.model_dump() for s in sections]


def deserialize_sections(data: list[dict]) -> list[LessonSection]:
    """Deserialize LessonSection list from checkpoint data."""
    return [LessonSection.model_validate(d) for d in data]


def deserialize_plan(data: dict) -> LessonPlan:
    """Deserialize a LessonPlan from checkpoint data."""
    return LessonPlan.model_validate(data)


def write_json(path: Path, data: dict) -> None:
    """Write a dict as pretty-printed JSON to *path*."""
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8",
    )

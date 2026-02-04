"""Status tracker service - computes pipeline status from file existence.

The dashboard derives all status from the file system (source of truth).
No separate state database is needed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from api.config import (
    ATOMS_DIR,
    PRUEBAS_ALTERNATIVAS_DIR,
    PRUEBAS_FINALIZADAS_DIR,
    PRUEBAS_PROCESADAS_DIR,
    PRUEBAS_RAW_DIR,
    STANDARDS_DIR,
    SUBJECTS_CONFIG,
    TEMARIOS_JSON_DIR,
)


class StatusTracker:
    """Computes content pipeline status from file system state."""

    def __init__(self, subject_id: str = "paes-m1-2026"):
        """Initialize tracker for a subject.

        Args:
            subject_id: The subject identifier (e.g., "paes-m1-2026")
        """
        self.subject_id = subject_id
        self.config = SUBJECTS_CONFIG.get(subject_id, {})
        self._atoms_cache: list[dict] | None = None
        self._standards_cache: list[dict] | None = None

    # -------------------------------------------------------------------------
    # Temario status
    # -------------------------------------------------------------------------

    def temario_exists(self) -> bool:
        """Check if temario JSON exists."""
        temario_file = self.config.get("temario_file")
        if not temario_file:
            return False
        return (TEMARIOS_JSON_DIR / temario_file).exists()

    def get_temario_path(self) -> Path | None:
        """Get path to temario JSON if it exists."""
        temario_file = self.config.get("temario_file")
        if not temario_file:
            return None
        path = TEMARIOS_JSON_DIR / temario_file
        return path if path.exists() else None

    # -------------------------------------------------------------------------
    # Standards status
    # -------------------------------------------------------------------------

    def get_standards(self) -> list[dict]:
        """Load and return standards from JSON file."""
        if self._standards_cache is not None:
            return self._standards_cache

        standards_file = self.config.get("standards_file")
        if not standards_file:
            return []

        path = STANDARDS_DIR / standards_file
        if not path.exists():
            return []

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        self._standards_cache = data.get("standards", [])
        return self._standards_cache

    def standards_count(self) -> int:
        """Count number of standards."""
        return len(self.get_standards())

    # -------------------------------------------------------------------------
    # Atoms status
    # -------------------------------------------------------------------------

    def get_atoms(self) -> list[dict]:
        """Load and return atoms from JSON file."""
        if self._atoms_cache is not None:
            return self._atoms_cache

        atoms_file = self.config.get("atoms_file")
        if not atoms_file:
            return []

        path = ATOMS_DIR / atoms_file
        if not path.exists():
            return []

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        self._atoms_cache = data.get("atoms", [])
        return self._atoms_cache

    def atoms_count(self) -> int:
        """Count number of atoms."""
        return len(self.get_atoms())

    def get_atoms_by_standard(self, standard_id: str) -> list[dict]:
        """Get atoms that belong to a specific standard."""
        atoms = self.get_atoms()
        return [a for a in atoms if standard_id in a.get("standard_ids", [])]

    # -------------------------------------------------------------------------
    # Tests status
    # -------------------------------------------------------------------------

    def get_test_dirs(self) -> list[Path]:
        """Get list of finalized test directories."""
        if not PRUEBAS_FINALIZADAS_DIR.exists():
            return []
        return sorted(
            [d for d in PRUEBAS_FINALIZADAS_DIR.iterdir() if d.is_dir()]
        )

    def tests_count(self) -> int:
        """Count number of tests."""
        return len(self.get_test_dirs())

    def get_test_status(self, test_id: str) -> dict:
        """Get detailed status for a single test.

        Returns:
            Dict with raw_pdf_exists, split_count, qti_count, finalized_count,
            tagged_count, variants_count, questions list
        """
        test_dir = PRUEBAS_FINALIZADAS_DIR / test_id
        procesadas_dir = PRUEBAS_PROCESADAS_DIR / test_id
        alternativas_dir = PRUEBAS_ALTERNATIVAS_DIR / test_id

        # Check raw PDF - look in the test's subdirectory
        raw_pdf_exists = False
        raw_test_dir = PRUEBAS_RAW_DIR / test_id
        if raw_test_dir.exists():
            raw_pdf_exists = any(
                f.suffix.lower() == ".pdf" for f in raw_test_dir.iterdir()
            )

        # Count split PDFs (in procesadas/pdf directory)
        pdf_split_count = 0
        split_dir = procesadas_dir / "pdf" if procesadas_dir.exists() else None
        if split_dir and split_dir.exists():
            pdf_split_count = len([f for f in split_dir.iterdir() if f.suffix == ".pdf"])

        # Count QTI and finalized questions
        qti_count = 0
        finalized_count = 0
        tagged_count = 0
        enriched_count = 0
        validated_count = 0
        questions = []

        qti_dir = test_dir / "qti" if test_dir.exists() else None
        if qti_dir and qti_dir.exists():
            q_dirs = sorted(
                [d for d in qti_dir.iterdir() if d.is_dir() and d.name.startswith("Q")],
                key=lambda x: int(re.search(r"\d+", x.name).group())
                if re.search(r"\d+", x.name) else 0,
            )

            for q_dir in q_dirs:
                q_num_match = re.search(r"(\d+)", q_dir.name)
                if not q_num_match:
                    continue
                q_num = int(q_num_match.group(1))
                q_id = f"{test_id}-Q{q_num}"

                has_qti = (q_dir / "question.xml").exists()
                is_tagged = (q_dir / "metadata_tags.json").exists()

                # Check enrichment/validation status
                is_enriched = (q_dir / "question_validated.xml").exists()
                is_validated = False
                validation_result_file = q_dir / "validation_result.json"
                if validation_result_file.exists():
                    try:
                        with open(validation_result_file, encoding="utf-8") as f:
                            vdata = json.load(f)
                        is_validated = vdata.get("can_sync", False) or vdata.get("success", False)
                    except (json.JSONDecodeError, OSError):
                        pass

                if has_qti:
                    qti_count += 1
                    finalized_count += 1  # In finalizadas = finalized
                if is_tagged:
                    tagged_count += 1
                if is_enriched:
                    enriched_count += 1
                if is_validated:
                    validated_count += 1

                # Count variants for this question
                q_variants_count = 0
                q_alternativas_dir = alternativas_dir / f"Q{q_num}" / "approved"
                if q_alternativas_dir.exists():
                    q_variants_count = len([
                        d for d in q_alternativas_dir.iterdir()
                        if d.is_dir()
                    ])

                # Count atoms from metadata
                atoms_count = 0
                metadata_file = q_dir / "metadata_tags.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, encoding="utf-8") as f:
                            metadata = json.load(f)
                        atoms_count = len(metadata.get("selected_atoms", []))
                    except (json.JSONDecodeError, OSError):
                        pass

                questions.append({
                    "id": q_id,
                    "question_number": q_num,
                    "has_split_pdf": split_dir
                        and (split_dir / f"Q{q_num}.pdf").exists()
                        if split_dir
                        else False,
                    "has_qti": has_qti,
                    "is_finalized": has_qti,  # If in finalizadas with QTI, it's finalized
                    "is_tagged": is_tagged,
                    "is_enriched": is_enriched,
                    "is_validated": is_validated,
                    "atoms_count": atoms_count,
                    "variants_count": q_variants_count,
                })

        # Count total variants
        variants_count = 0
        if alternativas_dir.exists():
            for q_dir in alternativas_dir.iterdir():
                if not q_dir.is_dir():
                    continue
                approved_dir = q_dir / "approved"
                if approved_dir.exists():
                    variants_count += len([
                        d for d in approved_dir.iterdir() if d.is_dir()
                    ])

        # split_count: if QTI exists, consider it "split" even without PDF
        # (QTI is the goal, PDF is just an intermediate step)
        split_count = max(pdf_split_count, qti_count)

        return {
            "raw_pdf_exists": raw_pdf_exists,
            "split_count": split_count,
            "qti_count": qti_count,
            "finalized_count": finalized_count,
            "tagged_count": tagged_count,
            "enriched_count": enriched_count,
            "validated_count": validated_count,
            "variants_count": variants_count,
            "questions": questions,
        }

    # -------------------------------------------------------------------------
    # Aggregate stats
    # -------------------------------------------------------------------------

    def questions_count(self) -> int:
        """Count total finalized questions across all tests."""
        total = 0
        for test_dir in self.get_test_dirs():
            qti_dir = test_dir / "qti"
            if qti_dir.exists():
                total += len([
                    d for d in qti_dir.iterdir()
                    if d.is_dir() and (d / "question.xml").exists()
                ])
        return total

    def variants_count(self) -> int:
        """Count total approved variants across all tests."""
        total = 0
        if not PRUEBAS_ALTERNATIVAS_DIR.exists():
            return total

        for test_dir in PRUEBAS_ALTERNATIVAS_DIR.iterdir():
            if not test_dir.is_dir():
                continue
            for q_dir in test_dir.iterdir():
                if not q_dir.is_dir():
                    continue
                approved_dir = q_dir / "approved"
                if approved_dir.exists():
                    total += len([d for d in approved_dir.iterdir() if d.is_dir()])

        return total

    def tagging_completion(self) -> float:
        """Calculate tagging completion percentage (0-100)."""
        total = 0
        tagged = 0

        for test_dir in self.get_test_dirs():
            qti_dir = test_dir / "qti"
            if not qti_dir.exists():
                continue

            for q_dir in qti_dir.iterdir():
                if not q_dir.is_dir() or not (q_dir / "question.xml").exists():
                    continue
                total += 1
                if (q_dir / "metadata_tags.json").exists():
                    tagged += 1

        if total == 0:
            return 0.0
        return round((tagged / total) * 100, 1)

    def get_subject_stats(self) -> dict:
        """Get all stats for the subject."""
        return {
            "temario_exists": self.temario_exists(),
            "standards_count": self.standards_count(),
            "atoms_count": self.atoms_count(),
            "tests_count": self.tests_count(),
            "questions_count": self.questions_count(),
            "variants_count": self.variants_count(),
            "tagging_completion": self.tagging_completion(),
        }

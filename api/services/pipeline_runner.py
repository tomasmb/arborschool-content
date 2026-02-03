"""Pipeline runner service - executes pipelines via subprocess and tracks job state.

Jobs are tracked in JSON files at app/data/.jobs/{job_id}.json for persistence.
This allows resuming jobs after server restarts and provides progress tracking.
"""

from __future__ import annotations

import json
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.schemas.api_models import JobStatus, PipelineDefinition, PipelineParam
from app.utils.paths import JOBS_DIR, REPO_ROOT


# -----------------------------------------------------------------------------
# Pipeline definitions
# -----------------------------------------------------------------------------

PIPELINES: dict[str, PipelineDefinition] = {
    "standards_gen": PipelineDefinition(
        id="standards_gen",
        name="Standards Generation",
        description="Generate standards from temario",
        has_ai_cost=True,
        requires=["temario"],
        produces="standards/*.json",
    ),
    "atoms_gen": PipelineDefinition(
        id="atoms_gen",
        name="Atoms Generation",
        description="Generate atoms from standards",
        has_ai_cost=True,
        requires=["standards"],
        produces="atoms/*.json",
    ),
    "pdf_split": PipelineDefinition(
        id="pdf_split",
        name="PDF Split",
        description="Split test PDF into individual questions",
        has_ai_cost=True,
        requires=["raw_pdf"],
        produces="procesadas/{test}/pdf/*.pdf",
    ),
    "pdf_to_qti": PipelineDefinition(
        id="pdf_to_qti",
        name="PDF to QTI",
        description="Convert question PDFs to QTI XML format",
        has_ai_cost=True,
        requires=["split_pdfs"],
        produces="procesadas/{test}/qti/*/question.xml",
    ),
    "finalize": PipelineDefinition(
        id="finalize",
        name="Finalize Questions",
        description="Copy validated QTI to finalizadas/",
        has_ai_cost=False,
        requires=["qti"],
        produces="finalizadas/{test}/qti/*",
    ),
    "tagging": PipelineDefinition(
        id="tagging",
        name="Question Tagging",
        description="Tag questions with relevant atoms",
        has_ai_cost=True,
        requires=["atoms", "finalized_questions"],
        produces="finalizadas/{test}/qti/*/metadata_tags.json",
    ),
    "variant_gen": PipelineDefinition(
        id="variant_gen",
        name="Variant Generation",
        description="Generate alternative versions of questions",
        has_ai_cost=True,
        requires=["tagged_questions"],
        produces="alternativas/{test}/Q*/approved/*",
    ),
    "question_sets": PipelineDefinition(
        id="question_sets",
        name="Question Sets (PP100)",
        description="Generate ~60 practice questions per atom",
        has_ai_cost=True,
        requires=["atoms", "all_tagged"],
        produces="question_sets/{atom_id}/*.json",
    ),
    "lessons": PipelineDefinition(
        id="lessons",
        name="Lessons",
        description="Generate micro-lessons for atoms",
        has_ai_cost=True,
        requires=["atoms", "question_sets_or_all_tagged"],
        produces="lessons/{atom_id}.json",
    ),
}

# Pipeline parameters
PIPELINE_PARAMS: dict[str, list[PipelineParam]] = {
    "standards_gen": [
        PipelineParam(
            name="temario_file",
            type="select",
            label="Temario",
            required=True,
            options=[
                "temario-paes-m1-invierno-y-regular-2026.json",
            ],
        ),
        PipelineParam(
            name="eje",
            type="select",
            label="Eje (optional)",
            required=False,
            options=[
                "numeros",
                "algebra_y_funciones",
                "geometria",
                "probabilidad_y_estadistica",
            ],
            description="Leave empty to generate all ejes",
        ),
    ],
    "atoms_gen": [
        PipelineParam(
            name="standards_file",
            type="select",
            label="Standards File",
            required=True,
            options=["paes_m1_2026.json"],
        ),
    ],
    "tagging": [
        PipelineParam(
            name="test_id",
            type="select",
            label="Test",
            required=True,
            options=[],  # Populated dynamically
        ),
        PipelineParam(
            name="question_ids",
            type="string",
            label="Question IDs (optional)",
            required=False,
            description="Comma-separated list (e.g., Q1,Q2,Q3). Leave empty for all.",
        ),
    ],
    "variant_gen": [
        PipelineParam(
            name="test_id",
            type="select",
            label="Source Test",
            required=True,
            options=[],  # Populated dynamically
        ),
        PipelineParam(
            name="question_ids",
            type="string",
            label="Question IDs",
            required=True,
            description="Comma-separated list (e.g., Q1,Q2,Q3)",
        ),
        PipelineParam(
            name="variants_per_question",
            type="number",
            label="Variants per Question",
            required=False,
            default=3,
        ),
    ],
}


# -----------------------------------------------------------------------------
# Job management
# -----------------------------------------------------------------------------


def _ensure_jobs_dir() -> None:
    """Ensure the jobs directory exists."""
    JOBS_DIR.mkdir(parents=True, exist_ok=True)


def _job_file(job_id: str) -> Path:
    """Get path to a job's state file."""
    return JOBS_DIR / f"{job_id}.json"


def _load_job(job_id: str) -> JobStatus | None:
    """Load a job from disk."""
    path = _job_file(job_id)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return JobStatus(**data)


def _save_job(job: JobStatus) -> None:
    """Save job state to disk."""
    _ensure_jobs_dir()
    path = _job_file(job.job_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(job.model_dump(), f, indent=2, default=str)


class PipelineRunner:
    """Service for running pipelines and tracking job state."""

    def __init__(self):
        """Initialize the runner."""
        self._running_jobs: dict[str, subprocess.Popen] = {}
        _ensure_jobs_dir()

    def get_pipelines(self) -> list[PipelineDefinition]:
        """Get all available pipeline definitions."""
        return list(PIPELINES.values())

    def get_pipeline(self, pipeline_id: str) -> PipelineDefinition | None:
        """Get a specific pipeline definition."""
        return PIPELINES.get(pipeline_id)

    def get_pipeline_params(self, pipeline_id: str) -> list[PipelineParam]:
        """Get parameters for a pipeline."""
        return PIPELINE_PARAMS.get(pipeline_id, [])

    def create_job(
        self,
        pipeline_id: str,
        params: dict[str, Any],
    ) -> JobStatus:
        """Create a new job (but don't start it yet)."""
        job_id = f"{pipeline_id}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

        job = JobStatus(
            job_id=job_id,
            pipeline_id=pipeline_id,
            status="pending",
            params=params,
        )
        _save_job(job)
        return job

    def start_job(self, job_id: str) -> JobStatus:
        """Start a job running in background."""
        job = _load_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        if job.status not in ("pending", "failed"):
            raise ValueError(f"Job {job_id} cannot be started (status: {job.status})")

        # Build the command
        cmd = self._build_command(job.pipeline_id, job.params)
        if not cmd:
            job.status = "failed"
            job.error = f"Unknown pipeline: {job.pipeline_id}"
            _save_job(job)
            return job

        # Start the subprocess
        job.status = "running"
        job.started_at = datetime.now(timezone.utc).isoformat()
        _save_job(job)

        # Run in background thread
        thread = threading.Thread(
            target=self._run_subprocess,
            args=(job_id, cmd),
            daemon=True,
        )
        thread.start()

        return job

    def _build_command(
        self,
        pipeline_id: str,
        params: dict[str, Any],
    ) -> list[str] | None:
        """Build the command line for a pipeline."""
        commands = {
            "standards_gen": self._cmd_standards_gen,
            "atoms_gen": self._cmd_atoms_gen,
            "tagging": self._cmd_tagging,
            "variant_gen": self._cmd_variant_gen,
        }

        builder = commands.get(pipeline_id)
        if not builder:
            return None
        return builder(params)

    def _cmd_standards_gen(self, params: dict[str, Any]) -> list[str]:
        """Build command for standards generation."""
        cmd = ["python", "-m", "app.standards.run_single_eje"]
        if params.get("eje"):
            cmd.extend(["--eje", params["eje"]])
        return cmd

    def _cmd_atoms_gen(self, params: dict[str, Any]) -> list[str]:
        """Build command for atoms generation."""
        return ["python", "-m", "app.atoms.scripts.run_single_standard"]

    def _cmd_tagging(self, params: dict[str, Any]) -> list[str]:
        """Build command for tagging."""
        cmd = ["python", "-m", "app.tagging.batch_runner"]
        # Note: batch_runner doesn't have params yet, we'd need to extend it
        return cmd

    def _cmd_variant_gen(self, params: dict[str, Any]) -> list[str]:
        """Build command for variant generation."""
        cmd = [
            "python", "-m", "app.question_variants.run_variant_generation",
            "--source-test", params.get("test_id", ""),
        ]
        if params.get("question_ids"):
            cmd.extend(["--questions", params["question_ids"]])
        if params.get("variants_per_question"):
            cmd.extend(["--variants-per-question", str(params["variants_per_question"])])
        return cmd

    def _run_subprocess(self, job_id: str, cmd: list[str]) -> None:
        """Run a pipeline subprocess and update job state."""
        job = _load_job(job_id)
        if not job:
            return

        try:
            process = subprocess.Popen(
                cmd,
                cwd=str(REPO_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self._running_jobs[job_id] = process

            logs: list[str] = []
            if process.stdout:
                for line in process.stdout:
                    logs.append(line.rstrip())
                    # Update job logs periodically (every 10 lines)
                    if len(logs) % 10 == 0:
                        job.logs = logs[-100:]  # Keep last 100 lines
                        _save_job(job)

            process.wait()

            # Final status update
            job = _load_job(job_id) or job
            job.logs = logs[-100:]
            job.completed_at = datetime.now(timezone.utc).isoformat()

            if process.returncode == 0:
                job.status = "completed"
            else:
                job.status = "failed"
                job.error = f"Process exited with code {process.returncode}"

        except Exception as e:
            job.status = "failed"
            job.error = str(e)

        finally:
            _save_job(job)
            self._running_jobs.pop(job_id, None)

    def get_job(self, job_id: str) -> JobStatus | None:
        """Get current status of a job."""
        return _load_job(job_id)

    def list_jobs(self, limit: int = 20) -> list[JobStatus]:
        """List recent jobs, newest first."""
        _ensure_jobs_dir()
        job_files = sorted(JOBS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

        jobs = []
        for path in job_files[:limit]:
            try:
                job = _load_job(path.stem)
                if job:
                    jobs.append(job)
            except (json.JSONDecodeError, OSError):
                continue

        return jobs

    def cancel_job(self, job_id: str) -> JobStatus | None:
        """Cancel a running job."""
        job = _load_job(job_id)
        if not job:
            return None

        if job.status != "running":
            return job

        # Kill the subprocess
        process = self._running_jobs.get(job_id)
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            self._running_jobs.pop(job_id, None)

        job.status = "cancelled"
        job.completed_at = datetime.now(timezone.utc).isoformat()
        _save_job(job)

        return job

    def delete_job(self, job_id: str) -> bool:
        """Delete a job's state file (only completed/failed/cancelled jobs)."""
        job = _load_job(job_id)
        if not job:
            return False

        if job.status == "running":
            return False

        path = _job_file(job_id)
        if path.exists():
            path.unlink()
            return True
        return False


# Singleton instance
_runner: PipelineRunner | None = None


def get_runner() -> PipelineRunner:
    """Get the singleton pipeline runner instance."""
    global _runner
    if _runner is None:
        _runner = PipelineRunner()
    return _runner

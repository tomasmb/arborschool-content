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
from api.services.pipeline_definitions import PIPELINE_PARAMS, PIPELINES
from app.utils.paths import JOBS_DIR, REPO_ROOT

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

        # Pipelines that support resume (have item-level processing)
        resumable_pipelines = {
            "tagging", "variant_gen", "pdf_to_qti", "pdf_split",
            "question_gen",
        }

        job = JobStatus(
            job_id=job_id,
            pipeline_id=pipeline_id,
            status="pending",
            params=params,
            can_resume=pipeline_id in resumable_pipelines,
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
            "pdf_split": self._cmd_pdf_split,
            "pdf_to_qti": self._cmd_pdf_to_qti,
            "finalize": self._cmd_finalize,
            "tagging": self._cmd_tagging,
            "variant_gen": self._cmd_variant_gen,
            "question_gen": self._cmd_question_gen,
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
        cmd = ["python", "-m", "app.atoms.scripts.generate_all_atoms"]
        if params.get("eje"):
            cmd.extend(["--eje", params["eje"]])
        if params.get("standard_ids"):
            ids = [
                s.strip()
                for s in params["standard_ids"].split(",")
                if s.strip()
            ]
            if ids:
                cmd.extend(["--standard-ids"] + ids)
        return cmd

    def _cmd_pdf_split(self, params: dict[str, Any]) -> list[str]:
        """Build command for PDF splitting."""
        cmd = ["python", "-m", "app.pruebas.pdf-splitter.main"]
        if params.get("pdf_path"):
            cmd.append(params["pdf_path"])
        if params.get("output_dir"):
            cmd.extend(["--output-dir", params["output_dir"]])
        return cmd

    def _cmd_pdf_to_qti(self, params: dict[str, Any]) -> list[str]:
        """Build command for PDF to QTI conversion."""
        cmd = ["python", "-m", "app.pruebas.pdf-to-qti.scripts.process_test"]
        if params.get("test_id"):
            cmd.extend(["--test", params["test_id"]])
        if params.get("question_ids"):
            cmd.extend(["--questions", params["question_ids"]])
        return cmd

    def _cmd_finalize(self, params: dict[str, Any]) -> list[str]:
        """Build command for finalization (copy to finalizadas/).

        Note: This is a simple file operation, not AI. Uses a script that copies
        validated QTI files from procesadas/ to finalizadas/.
        """
        # For now, return a simple echo - finalization logic can be added
        # when the finalization script is implemented
        return ["echo", "Finalization pipeline not yet implemented via CLI"]

    def _cmd_tagging(self, params: dict[str, Any]) -> list[str]:
        """Build command for tagging."""
        cmd = ["python", "-m", "app.tagging.batch_runner"]
        if params.get("test_id"):
            cmd.extend(["--test", params["test_id"]])
        if params.get("question_ids"):
            cmd.extend(["--questions", params["question_ids"]])
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

    def _cmd_question_gen(self, params: dict[str, Any]) -> list[str]:
        """Build command for question generation."""
        cmd = [
            "python", "-m",
            "app.question_generation.scripts.run_generation",
            "--atom-id", params.get("atom_id", ""),
        ]
        phase = params.get("phase", "all")
        if phase and phase != "all":
            cmd.extend(["--phase", phase])
        if params.get("pool_size"):
            cmd.extend(["--pool-size", str(params["pool_size"])])
        if params.get("dry_run") == "true":
            cmd.append("--dry-run")
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

    def resume_job(self, job_id: str, mode: str = "remaining") -> JobStatus | None:
        """Resume a failed or cancelled job.

        Args:
            job_id: The original job to resume from
            mode: 'remaining' to run all items not yet completed,
                  'failed_only' to retry only failed items

        Returns:
            New JobStatus for the resume job, or None if resume not possible
        """
        original_job = _load_job(job_id)
        if not original_job:
            return None

        if original_job.status not in ("failed", "cancelled"):
            return None

        # Build the item list based on mode
        items_to_process: list[str] = []
        if mode == "failed_only":
            items_to_process = [item.id for item in original_job.failed_item_details]
        else:
            # Calculate remaining items - this is a simplified version
            # In a real implementation, the original job would track all item IDs
            if original_job.failed_item_details:
                items_to_process = [item.id for item in original_job.failed_item_details]
            # Add any items not in completed_item_ids (if we have total item tracking)
            # For now, we focus on failed items

        if not items_to_process:
            return None

        # Create new job params with the items to retry
        new_params = dict(original_job.params)

        # Update question_ids if this is a tagging or variant job
        if original_job.pipeline_id in ("tagging", "variant_gen"):
            new_params["question_ids"] = ",".join(items_to_process)

        # Create and start the new job
        new_job = self.create_job(original_job.pipeline_id, new_params)
        new_job.logs.append(f"Resumed from job {job_id} with mode '{mode}'")
        new_job.logs.append(f"Items to process: {items_to_process}")
        _save_job(new_job)

        return self.start_job(new_job.job_id)


# Singleton instance
_runner: PipelineRunner | None = None


def get_runner() -> PipelineRunner:
    """Get the singleton pipeline runner instance."""
    global _runner
    if _runner is None:
        _runner = PipelineRunner()
    return _runner

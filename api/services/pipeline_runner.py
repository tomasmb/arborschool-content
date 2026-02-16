"""Pipeline runner service - executes pipelines via subprocess and tracks job state.

Jobs are tracked in JSON files at app/data/.jobs/{job_id}.json for persistence.
This allows resuming jobs after server restarts and provides progress tracking.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.schemas.api_models import JobStatus, PipelineDefinition, PipelineParam
from api.services.pipeline_definitions import PIPELINE_PARAMS, PIPELINES
from app.utils.paths import JOBS_DIR, REPO_ROOT

# Use the same Python interpreter that's running this server (the venv one).
# This avoids "python not found" on systems where only python3 exists,
# and ensures subprocesses have access to venv packages.
_PYTHON = sys.executable

# Pattern emitted by pipeline phases (e.g. generator.py) to report
# per-item progress.  Format: ``[PROGRESS] completed/total``
_PROGRESS_RE = re.compile(r"\[PROGRESS\]\s+(\d+)/(\d+)")

# Pattern emitted at end of pipeline for actual cost tracking.
# Format: ``[COST] $X.XXXX``
_COST_RE = re.compile(r"\[COST\]\s+\$?([\d.]+)")

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
    """Load a job from disk.

    Handles transient empty files caused by concurrent writes
    by returning None instead of raising JSONDecodeError.
    """
    path = _job_file(job_id)
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return None
        data = json.loads(text)
    except (json.JSONDecodeError, OSError):
        return None
    return JobStatus(**data)


def _save_job(job: JobStatus) -> None:
    """Save job state to disk atomically.

    Writes to a temp file in the same directory, then renames.
    Rename is atomic on POSIX, preventing readers from seeing
    a truncated/empty file.
    """
    _ensure_jobs_dir()
    path = _job_file(job.job_id)
    # Write to temp file in same dir so rename is same-filesystem
    fd, tmp_path = tempfile.mkstemp(
        dir=str(JOBS_DIR), suffix=".tmp",
    )
    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(job.model_dump(), f, indent=2, default=str)
        Path(tmp_path).replace(path)
    except BaseException:
        # Clean up temp file on any error
        Path(tmp_path).unlink(missing_ok=True)
        raise


class PipelineRunner:
    """Service for running pipelines and tracking job state."""

    def __init__(self):
        """Initialize the runner."""
        self._running_jobs: dict[str, subprocess.Popen] = {}
        _ensure_jobs_dir()
        self._cleanup_zombie_jobs()

    def _cleanup_zombie_jobs(self) -> None:
        """Mark stale 'running' jobs as failed on startup.

        After a server restart, no subprocess is tracked in
        ``_running_jobs``, so any job file still showing
        ``status=running`` is a zombie left from the previous
        process.
        """
        for path in JOBS_DIR.glob("*.json"):
            try:
                job = _load_job(path.stem)
            except (json.JSONDecodeError, OSError):
                continue
            if job and job.status == "running":
                job.status = "failed"
                job.error = "Server restarted during execution"
                job.completed_at = datetime.now(
                    timezone.utc,
                ).isoformat()
                _save_job(job)

    def get_pipelines(self) -> list[PipelineDefinition]:
        """Get all available pipeline definitions."""
        return list(PIPELINES.values())

    def get_pipeline(self, pipeline_id: str) -> PipelineDefinition | None:
        """Get a specific pipeline definition."""
        return PIPELINES.get(pipeline_id)

    def get_pipeline_params(self, pipeline_id: str) -> list[PipelineParam]:
        """Get parameters for a pipeline."""
        return PIPELINE_PARAMS.get(pipeline_id, [])

    _RESUMABLE = {"tagging", "variant_gen", "pdf_to_qti", "pdf_split", "question_gen"}

    def create_job(
        self, pipeline_id: str, params: dict[str, Any],
    ) -> JobStatus:
        """Create a new job (but don't start it yet)."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        job_id = f"{pipeline_id}-{ts}-{uuid.uuid4().hex[:6]}"
        job = JobStatus(
            job_id=job_id, pipeline_id=pipeline_id,
            status="pending", params=params,
            can_resume=pipeline_id in self._RESUMABLE,
        )
        _save_job(job)
        return job

    def start_job(self, job_id: str) -> JobStatus:
        """Start a job running in background."""
        job = _load_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        if job.status not in ("pending", "failed"):
            raise ValueError(
                f"Job {job_id} cannot be started (status: {job.status})",
            )
        cmd = self._build_command(job.pipeline_id, job.params)
        if not cmd:
            job.status = "failed"
            job.error = f"Unknown pipeline: {job.pipeline_id}"
            _save_job(job)
            return job

        job.status = "running"
        job.started_at = datetime.now(timezone.utc).isoformat()
        _save_job(job)
        thread = threading.Thread(
            target=self._run_subprocess,
            args=(job_id, cmd), daemon=True,
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

    # -- Command builders per pipeline --

    def _cmd_standards_gen(self, p: dict[str, Any]) -> list[str]:
        cmd = [_PYTHON, "-m", "app.standards.run_single_eje"]
        if p.get("eje"):
            cmd.extend(["--eje", p["eje"]])
        return cmd

    def _cmd_atoms_gen(self, p: dict[str, Any]) -> list[str]:
        cmd = [_PYTHON, "-m", "app.atoms.scripts.generate_all_atoms"]
        if p.get("eje"):
            cmd.extend(["--eje", p["eje"]])
        if p.get("standard_ids"):
            ids = [s.strip() for s in p["standard_ids"].split(",") if s.strip()]
            if ids:
                cmd.extend(["--standard-ids"] + ids)
        return cmd

    def _cmd_pdf_split(self, p: dict[str, Any]) -> list[str]:
        cmd = [_PYTHON, "-m", "app.pruebas.pdf-splitter.main"]
        if p.get("pdf_path"):
            cmd.append(p["pdf_path"])
        if p.get("output_dir"):
            cmd.extend(["--output-dir", p["output_dir"]])
        return cmd

    def _cmd_pdf_to_qti(self, p: dict[str, Any]) -> list[str]:
        cmd = [_PYTHON, "-m", "app.pruebas.pdf-to-qti.scripts.process_test"]
        if p.get("test_id"):
            cmd.extend(["--test", p["test_id"]])
        if p.get("question_ids"):
            cmd.extend(["--questions", p["question_ids"]])
        return cmd

    def _cmd_finalize(self, _p: dict[str, Any]) -> list[str]:
        return ["echo", "Finalization pipeline not yet implemented"]

    def _cmd_tagging(self, p: dict[str, Any]) -> list[str]:
        cmd = [_PYTHON, "-m", "app.tagging.batch_runner"]
        if p.get("test_id"):
            cmd.extend(["--test", p["test_id"]])
        if p.get("question_ids"):
            cmd.extend(["--questions", p["question_ids"]])
        return cmd

    def _cmd_variant_gen(self, p: dict[str, Any]) -> list[str]:
        cmd = [
            _PYTHON, "-m",
            "app.question_variants.run_variant_generation",
            "--source-test", p.get("test_id", ""),
        ]
        if p.get("question_ids"):
            cmd.extend(["--questions", p["question_ids"]])
        if p.get("variants_per_question"):
            cmd.extend(["--variants-per-question", str(p["variants_per_question"])])
        return cmd

    def _cmd_question_gen(self, p: dict[str, Any]) -> list[str]:
        """Always passes --resume unless force_all=true."""
        cmd = [
            _PYTHON, "-m",
            "app.question_generation.scripts.run_generation",
            "--atom-id", p.get("atom_id", ""),
        ]
        if not p.get("force_all"):
            cmd.append("--resume")
        phase = p.get("phase", "all")
        if phase and phase != "all":
            cmd.extend(["--phase", phase])
        if p.get("dry_run") == "true":
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
                    stripped = line.rstrip()
                    logs.append(stripped)

                    # Parse progress markers (immediate save)
                    match = _PROGRESS_RE.search(stripped)
                    cost_match = _COST_RE.search(stripped)
                    if match:
                        job.completed_items = int(match.group(1))
                        job.total_items = int(match.group(2))
                        job.logs = logs[-100:]
                        _save_job(job)
                    elif cost_match:
                        job.cost_actual = float(
                            cost_match.group(1),
                        )
                        job.logs = logs[-100:]
                        _save_job(job)
                    elif len(logs) % 10 == 0:
                        # Periodic log save for non-progress lines
                        job.logs = logs[-100:]
                        _save_job(job)

            process.wait()

            # Final status update — reload to pick up cancellation
            job = _load_job(job_id) or job
            job.logs = logs[-100:]

            # If the job was cancelled while running, keep that status
            if job.status == "cancelled":
                pass
            elif process.returncode == 0:
                job.status = "completed"
                job.completed_at = datetime.now(
                    timezone.utc,
                ).isoformat()
            else:
                job.status = "failed"
                job.completed_at = datetime.now(
                    timezone.utc,
                ).isoformat()
                job.error = (
                    f"Process exited with code {process.returncode}"
                )

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

    def resume_job(
        self, job_id: str, mode: str = "remaining",
    ) -> JobStatus | None:
        """Resume a failed or cancelled job.

        For ``question_gen`` pipelines, resume relies on the
        checkpoint system (``--resume`` flag) rather than
        per-item tracking.  A new job is created with the same
        params and ``--resume`` is automatically added by
        ``_cmd_question_gen``.

        For other pipelines with per-item tracking (tagging,
        variant_gen), the original item-list approach is used
        when ``failed_item_details`` is populated.

        Args:
            job_id: The original job to resume from.
            mode: 'remaining' or 'failed_only'.

        Returns:
            New JobStatus for the resume job, or None if not
            possible.
        """
        original_job = _load_job(job_id)
        if not original_job:
            return None

        if original_job.status not in ("failed", "cancelled"):
            return None

        new_params = dict(original_job.params)

        # question_gen uses checkpoint-based resume (always works)
        if original_job.pipeline_id == "question_gen":
            new_job = self.create_job(
                original_job.pipeline_id, new_params,
            )
            new_job.logs.append(
                f"Resumed from job {job_id} "
                f"(checkpoint-based resume)",
            )
            _save_job(new_job)
            return self.start_job(new_job.job_id)

        # Other pipelines: try item-level resume
        items_to_process: list[str] = []
        if mode == "failed_only":
            items_to_process = [
                item.id
                for item in original_job.failed_item_details
            ]
        elif original_job.failed_item_details:
            items_to_process = [
                item.id
                for item in original_job.failed_item_details
            ]

        if not items_to_process:
            return None

        if original_job.pipeline_id in ("tagging", "variant_gen"):
            new_params["question_ids"] = ",".join(
                items_to_process,
            )

        new_job = self.create_job(
            original_job.pipeline_id, new_params,
        )
        new_job.logs.append(
            f"Resumed from job {job_id} with mode '{mode}'",
        )
        new_job.logs.append(
            f"Items to process: {items_to_process}",
        )
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

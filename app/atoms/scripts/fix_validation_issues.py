"""CLI entry point for the LLM atom fix pipeline.

Reads validation results, executes LLM-powered fixes, and applies
changes to the canonical atoms file + question mappings.

Usage:
    # Dry-run (default) — show proposed changes without writing files:
    python -m app.atoms.scripts.fix_validation_issues

    # Apply changes:
    python -m app.atoms.scripts.fix_validation_issues --apply

    # Apply saved dry-run results (no LLM re-run):
    python -m app.atoms.scripts.fix_validation_issues --apply-saved

    # Retry only the failed actions from the last run:
    python -m app.atoms.scripts.fix_validation_issues --retry-failed

    # Filter by fix type:
    python -m app.atoms.scripts.fix_validation_issues --fix-types split,fix_prerequisites

    # Filter by standard:
    python -m app.atoms.scripts.fix_validation_issues --standards M1-ALG-01,M1-NUM-01
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.atoms.fixing import (
    ChangeReport,
    FixResult,
    FixType,
    apply_saved_results,
    fix_all_validation_issues,
    retry_failed_actions,
)
from app.llm_clients import load_default_openai_client
from app.utils.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# CLI argument parser
# -----------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Fix atom validation issues using GPT-5.1.",
    )

    # Mutually exclusive modes.
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Run pipeline AND write changes to files.",
    )
    mode.add_argument(
        "--apply-saved",
        action="store_true",
        help=(
            "Apply the most recent saved dry-run results "
            "without re-running LLM calls."
        ),
    )
    mode.add_argument(
        "--retry-failed",
        action="store_true",
        help="Re-run only the actions that failed in the last run.",
    )

    parser.add_argument(
        "--fix-types",
        type=str,
        default=None,
        help=(
            "Comma-separated fix types to apply. "
            "Options: split, merge, fix_content, fix_fidelity, "
            "fix_completeness, fix_prerequisites, add_missing."
        ),
    )
    parser.add_argument(
        "--standards",
        type=str,
        default=None,
        help="Comma-separated standard IDs to fix (e.g. M1-ALG-01).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser


# -----------------------------------------------------------------------------
# Mode dispatchers
# -----------------------------------------------------------------------------


def _run_apply_saved() -> int:
    """Apply previously saved dry-run results."""
    logger.info("=" * 60)
    logger.info("APPLY SAVED RESULTS")
    logger.info("=" * 60)
    try:
        results, report = apply_saved_results()
    except FileNotFoundError as exc:
        logger.error(str(exc))
        return 1
    return _log_summary(results, report, dry_run=False)


def _run_retry_failed(*, dry_run: bool) -> int:
    """Retry only failed actions from the last run."""
    logger.info("Initialising OpenAI client (GPT-5.1)…")
    try:
        client = load_default_openai_client()
    except RuntimeError as exc:
        logger.error("Failed to initialise client: %s", exc)
        return 1

    mode = "DRY RUN" if dry_run else "APPLY"
    logger.info("=" * 60)
    logger.info("RETRY FAILED ACTIONS — %s", mode)
    logger.info("=" * 60)

    try:
        results, report = retry_failed_actions(client, dry_run=dry_run)
    except FileNotFoundError as exc:
        logger.error(str(exc))
        return 1

    return _log_summary(results, report, dry_run=dry_run)


def _run_full_pipeline(args: argparse.Namespace) -> int:
    """Run the standard pipeline (dry-run or apply)."""
    dry_run = not args.apply
    fix_types = _parse_fix_types(args.fix_types)
    standard_ids = (
        [s.strip() for s in args.standards.split(",")]
        if args.standards
        else None
    )

    logger.info("Initialising OpenAI client (GPT-5.1)…")
    try:
        client = load_default_openai_client()
    except RuntimeError as exc:
        logger.error("Failed to initialise client: %s", exc)
        return 1

    mode = "DRY RUN" if dry_run else "APPLY"
    logger.info("=" * 60)
    logger.info("ATOM FIX PIPELINE — %s", mode)
    logger.info("=" * 60)
    if fix_types:
        logger.info("Fix types: %s", [ft.value for ft in fix_types])
    if standard_ids:
        logger.info("Standards: %s", standard_ids)
    logger.info("")

    results, report = fix_all_validation_issues(
        client,
        dry_run=dry_run,
        fix_types=fix_types,
        standard_ids=standard_ids,
    )

    return _log_summary(results, report, dry_run)


# -----------------------------------------------------------------------------
# Summary and next-steps
# -----------------------------------------------------------------------------


def _log_summary(
    results: list[FixResult],
    report: ChangeReport,
    dry_run: bool,
) -> int:
    """Log results summary and return exit code (0 success, 1 failures)."""
    succeeded = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)

    logger.info("")
    logger.info("=" * 60)
    logger.info("RESULTS")
    logger.info("=" * 60)
    logger.info("Total actions: %d", len(results))
    logger.info("Succeeded:     %d", succeeded)
    logger.info("Failed:        %d", failed)
    logger.info("")
    logger.info(report.summary())

    if report.manual_review_needed:
        logger.warning("")
        logger.warning("MANUAL REVIEW NEEDED:")
        for item in report.manual_review_needed:
            logger.warning("  - %s", item)

    if failed:
        logger.error("")
        logger.error("FAILED ACTIONS:")
        for r in results:
            if not r.success:
                logger.error(
                    "  - %s [%s]: %s",
                    r.action.fix_type.value,
                    ", ".join(r.action.atom_ids),
                    r.error,
                )

    logger.info("=" * 60)

    # Clear next-steps guidance.
    _log_next_steps(dry_run, succeeded, failed)

    return 1 if failed else 0


def _log_next_steps(dry_run: bool, succeeded: int, failed: int) -> None:
    """Print actionable next-steps after a run."""
    cmd = "python -m app.atoms.scripts.fix_validation_issues"

    if dry_run:
        logger.info("")
        logger.info("NEXT STEPS:")
        logger.info("-" * 40)
        if succeeded:
            logger.info(
                "  Apply saved results:  %s --apply-saved", cmd,
            )
        if failed:
            logger.info(
                "  Retry failed only:    %s --retry-failed", cmd,
            )
        if succeeded:
            logger.info(
                "  Re-run and apply:     %s --apply", cmd,
            )
        logger.info("")
        logger.info(
            "Results are saved — you can review and apply later.",
        )
    else:
        logger.info("")
        if failed:
            logger.info("NEXT STEPS:")
            logger.info("-" * 40)
            logger.info(
                "  Retry failed only:  %s --retry-failed", cmd,
            )
        else:
            logger.info("All changes applied successfully.")


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _parse_fix_types(raw: str | None) -> list[FixType] | None:
    """Parse comma-separated fix type names into FixType enums."""
    if not raw:
        return None
    types: list[FixType] = []
    for name in raw.split(","):
        name = name.strip()
        try:
            types.append(FixType(name))
        except ValueError:
            logger.error(
                "Unknown fix type '%s'. Valid: %s",
                name,
                [ft.value for ft in FixType],
            )
            sys.exit(1)
    return types


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------


def main() -> None:
    """Parse arguments and run the fix pipeline."""
    args = _build_parser().parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.apply_saved:
        sys.exit(_run_apply_saved())
    elif args.retry_failed:
        sys.exit(_run_retry_failed(dry_run=True))
    else:
        sys.exit(_run_full_pipeline(args))


if __name__ == "__main__":
    main()

"""Orchestrator for the prerequisite atom generation pipeline.

Runs all 5 phases in sequence, with the ability to resume from any phase.
Each phase reads its inputs from the previous phase's output on disk.

Usage:
    python -m app.prerequisites.pipeline                # all phases
    python -m app.prerequisites.pipeline --phase 0      # demand analysis only
    python -m app.prerequisites.pipeline --phase 1      # standards gen only
    python -m app.prerequisites.pipeline --phase 2      # atoms gen only
    python -m app.prerequisites.pipeline --phase 3      # graph connection only
    python -m app.prerequisites.pipeline --phase 4      # validation only
    python -m app.prerequisites.pipeline --from-phase 2  # phases 2-4
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from app.llm_clients import load_default_openai_client

logger = logging.getLogger(__name__)

_PHASE_NAMES = {
    0: "Demand Analysis",
    1: "Standards Generation",
    2: "Atom Generation",
    3: "Graph Connection",
    4: "Validation",
}


def _run_phase_0() -> None:
    """Phase 0: Demand analysis."""
    from app.prerequisites.demand_analysis import (
        run_demand_analysis,
        save_demand_analysis,
    )

    client = load_default_openai_client()
    result = run_demand_analysis(client)
    save_demand_analysis(result)

    topics = result.get("prerequisite_topics", [])
    logger.info("Phase 0 complete: %d topics identified", len(topics))


def _run_phase_1() -> None:
    """Phase 1: Standards generation."""
    from app.prerequisites.standards_generation import (
        run_standards_generation,
        save_standards,
    )

    client = load_default_openai_client()
    standards = run_standards_generation(client)
    save_standards(standards)

    logger.info("Phase 1 complete: %d standards generated", len(standards))


def _run_phase_2() -> None:
    """Phase 2: Atom generation."""
    from app.prerequisites.atoms_generation import (
        run_atoms_generation,
        save_atoms,
    )

    client = load_default_openai_client()
    atoms = run_atoms_generation(client)
    save_atoms(atoms)

    logger.info("Phase 2 complete: %d atoms generated", len(atoms))


def _run_phase_3() -> None:
    """Phase 3: Graph connection."""
    from app.prerequisites.graph_connection import (
        run_graph_connection,
        save_connections,
    )

    client = load_default_openai_client()
    result = run_graph_connection(client)
    save_connections(result)

    connections = result.get("connections", [])
    logger.info("Phase 3 complete: %d connections", len(connections))


def _run_phase_4() -> None:
    """Phase 4: Validation."""
    from app.prerequisites.validation import (
        run_full_validation,
        save_validation,
    )

    client = load_default_openai_client()
    result = run_full_validation(client)
    save_validation(result)

    status = "PASSED" if result.passed else "FAILED"
    logger.info("Phase 4 complete: %s", status)


_PHASE_RUNNERS = {
    0: _run_phase_0,
    1: _run_phase_1,
    2: _run_phase_2,
    3: _run_phase_3,
    4: _run_phase_4,
}


def run_pipeline(
    phases: list[int] | None = None,
) -> None:
    """Run specified pipeline phases (or all if None).

    Args:
        phases: List of phase numbers to run (0-4). None = all.
    """
    if phases is None:
        phases = list(range(5))

    total_start = time.time()

    for phase_num in phases:
        name = _PHASE_NAMES.get(phase_num, f"Phase {phase_num}")
        runner = _PHASE_RUNNERS.get(phase_num)
        if runner is None:
            logger.error("Unknown phase: %d", phase_num)
            sys.exit(1)

        logger.info("")
        logger.info("=" * 60)
        logger.info("PHASE %d: %s", phase_num, name)
        logger.info("=" * 60)

        phase_start = time.time()
        try:
            runner()
        except Exception as e:
            logger.error(
                "Phase %d failed: %s", phase_num, e, exc_info=True,
            )
            sys.exit(1)

        elapsed = time.time() - phase_start
        logger.info(
            "Phase %d completed in %.1fs", phase_num, elapsed,
        )

    total_elapsed = time.time() - total_start
    logger.info("")
    logger.info("=" * 60)
    logger.info(
        "PIPELINE COMPLETE (%.1fs total)", total_elapsed,
    )
    logger.info("=" * 60)
    logger.info("Output directory: app/data/prerequisites/")
    logger.info("")
    logger.info("Artifacts:")
    logger.info("  Phase 0: app/data/prerequisites/demand_analysis.json")
    logger.info("  Phase 1: app/data/prerequisites/standards.json")
    logger.info("  Phase 2: app/data/prerequisites/atoms.json")
    logger.info("  Phase 3: app/data/prerequisites/connections.json")
    logger.info("  Phase 4: app/data/prerequisites/validation_result.json")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run the prerequisite atom generation pipeline.",
    )
    parser.add_argument(
        "--phase", type=int, choices=range(5),
        help="Run a single phase (0-4).",
    )
    parser.add_argument(
        "--from-phase", type=int, choices=range(5),
        help="Run from this phase through phase 4.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.phase is not None:
        phases = [args.phase]
    elif args.from_phase is not None:
        phases = list(range(args.from_phase, 5))
    else:
        phases = None

    run_pipeline(phases)


if __name__ == "__main__":
    main()

"""Prerequisite atom generation pipeline.

Generates foundational math atoms (1° básico through 2° medio) that serve as
prerequisites for existing PAES M1 atoms. Uses a targeted demand-driven
approach: only generates atoms for topics that current M1 leaf atoms require.

Pipeline phases:
    0. Demand analysis — identify missing prerequisite knowledge from M1 atoms
    1. Standards generation — create canonical standards for each prereq topic
    2. Atom generation — generate atoms bottom-up (lowest grade first)
    3. Graph connection — link prereq atoms to M1 atoms
    4. Validation — validate the combined prerequisite + M1 graph
"""

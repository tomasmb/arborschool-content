# Knowledge Graph Construction Methodology

This methodology describes how to convert high-level educational standards into:
1. canonical standards,
2. atoms,
3. prerequisite relationships,
4. final knowledge graph structures.

## Step 1 — Standards Canonicalization
Clean and normalize the human-written standards into a canonical list.

## Step 2 — Atom Generation
For each standard, generate atoms.  
Each atom must include:
- atom_id  
- title  
- description  
- supports (which standards it contributes to)  
- potential_prerequisite_standards  
- example_easy_question  
- example_medium_question  
- example_hard_question  

## Step 3 — Granularity Validation
Check each atom using the atom-granularity guidelines.

## Step 4 — Prerequisite Generation
Infer prerequisite relationships between atoms:
- based on cognitive order,
- required prior knowledge,
- potential_prerequisite_standards.

## Step 5 — Export Knowledge Graph
Output:
- standards_canonical.json  
- atoms.json  
- atoms_with_prereqs.json  

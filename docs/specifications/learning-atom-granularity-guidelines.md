## Atom Granularity Guidelines

This document captures the atom granularity guidelines we will use
across the knowledge graph, adapted from the original demo work.

---

## 1. What is an atom?

An **atom** is the smallest cognitively meaningful unit of knowledge
that can be taught, practiced and assessed independently.

In practical terms, an atom should:

- have exactly **one cognitive intention**,  
- be teachable in an **isolated mini-lesson**,  
- support one or more **standards** in a traceable way.

---

## 2. Criteria for deciding atom boundaries

We use the following checks when deciding whether a learning element
is a valid atom or should be split:

1. **Retrieval coherence**  
   The concept should typically be recalled as a single unit.  
   If students naturally retrieve subparts separately, it should be
   split into multiple atoms.

2. **Working-memory load**  
   An atom should not overload working memory.  
   As a rule of thumb, if the element requires more than ~4 novel
   pieces of information to manipulate at once, consider splitting it.

3. **Prerequisite independence**  
   If part A must be learned before part B, then A and B cannot belong
   to the same atom. They should be modeled as distinct atoms with an
   explicit prerequisite edge.

4. **Assessment independence**  
   If a teacher can reasonably assess two parts separately (with
   different questions or rubrics), they should be separate atoms.

5. **Generalization boundary**  
   If two skills generalize differently across contexts (e.g. one
   works in discrete settings but not in continuous, or one transfers
   to geometry but not to probability), they should not be in the same
   atom.

---

## 3. Practical examples

- **Good atom candidates**
  - “Interpretar la pendiente como tasa de cambio constante.”
  - “Calcular el porcentaje de una cantidad en contextos cotidianos.”
  - “Identificar el vértice de una parábola en una tabla de valores.”

- **Likely too large (should be split)**
  - “Entender todo sobre funciones lineales”  
    → split into atoms for pendiente, intercepto, forma y = mx + b,
    lectura de gráficos, etc.

---

## 4. How this connects to standards and the graph

- Each **standard** (from canonical standards JSON) is supported by
  several atoms.
- Atoms are linked by prerequisite edges that respect the criteria
  above.
- The **knowledge graph** is the union of:
  - standards nodes,
  - atom nodes,
  - prerequisite and support edges between them.



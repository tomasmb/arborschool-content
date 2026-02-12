# Arbor Data Model

## System Context

Test preparation platform for PAES Chile. Content repo manages atoms, questions, lessons. Student app serves content and tracks progress.

Core flow: Diagnostic → Learning plan → PP100 mastery → Practice tests → Spaced repetition

---

## Enums

```sql
CREATE TYPE atom_type AS ENUM (
    'concepto',
    'procedimiento',
    'representacion',
    'concepto_procedimental',
    'modelizacion',
    'argumentacion'
);

CREATE TYPE skill_type AS ENUM (
    'representar',
    'resolver_problemas',
    'modelar',
    'argumentar'
);

CREATE TYPE question_source AS ENUM (
    'official',
    'alternate',
    'question_set'
);

CREATE TYPE difficulty_level AS ENUM ('low', 'medium', 'high');

CREATE TYPE atom_relevance AS ENUM ('primary', 'secondary');

CREATE TYPE test_type AS ENUM ('official', 'diagnostic', 'practice');

CREATE TYPE mastery_status AS ENUM ('not_started', 'in_progress', 'mastered', 'frozen');

CREATE TYPE mastery_source AS ENUM ('diagnostic', 'practice_test', 'pp100');

CREATE TYPE question_set_status AS ENUM ('pending', 'generated', 'reviewed');

CREATE TYPE user_role AS ENUM ('student', 'admin');
```

---

## Schema

### Content Tables

```sql
CREATE TABLE subjects (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    short_name VARCHAR(50) NOT NULL,
    description TEXT,
    admission_year INTEGER,
    application_types VARCHAR(100)[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE standards (
    id VARCHAR(50) PRIMARY KEY,
    subject_id VARCHAR(50) REFERENCES subjects(id),
    axis VARCHAR(50) NOT NULL,
    unit VARCHAR(255),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    includes JSONB,
    excludes JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE atoms (
    id VARCHAR(50) PRIMARY KEY,
    subject_id VARCHAR(50) REFERENCES subjects(id),
    axis VARCHAR(50) NOT NULL,
    standard_ids VARCHAR(50)[] NOT NULL,
    atom_type atom_type NOT NULL,
    primary_skill skill_type NOT NULL,
    secondary_skills skill_type[],
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    mastery_criteria JSONB NOT NULL,
    conceptual_examples JSONB,
    scope_notes JSONB,
    prerequisite_ids VARCHAR(50)[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE question_sets (
    id VARCHAR(100) PRIMARY KEY,
    atom_id VARCHAR(50) REFERENCES atoms(id) UNIQUE NOT NULL,
    status question_set_status NOT NULL DEFAULT 'pending',
    low_count INTEGER DEFAULT 0,
    medium_count INTEGER DEFAULT 0,
    high_count INTEGER DEFAULT 0,
    generated_at TIMESTAMPTZ,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE lessons (
    id VARCHAR(100) PRIMARY KEY,
    atom_id VARCHAR(50) REFERENCES atoms(id) UNIQUE NOT NULL,
    question_set_id VARCHAR(100) REFERENCES question_sets(id),
    title VARCHAR(255) NOT NULL,
    worked_example_html TEXT NOT NULL,
    explanation_html TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE questions (
    id VARCHAR(100) PRIMARY KEY,
    source question_source NOT NULL,
    parent_question_id VARCHAR(100) REFERENCES questions(id),
    question_set_id VARCHAR(100) REFERENCES question_sets(id),
    qti_xml TEXT NOT NULL,
    title VARCHAR(255),
    correct_answer VARCHAR(50),
    difficulty_level difficulty_level NOT NULL,
    difficulty_score DECIMAL(3,2),
    difficulty_analysis TEXT,
    general_analysis TEXT,
    feedback_general TEXT,
    feedback_per_option JSONB,
    source_test_id VARCHAR(100),
    source_question_number INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE question_atoms (
    question_id VARCHAR(100) REFERENCES questions(id) ON DELETE CASCADE,
    atom_id VARCHAR(50) REFERENCES atoms(id),
    relevance atom_relevance NOT NULL,
    reasoning TEXT,
    PRIMARY KEY (question_id, atom_id)
);

CREATE TABLE tests (
    id VARCHAR(100) PRIMARY KEY,
    subject_id VARCHAR(50) REFERENCES subjects(id),
    test_type test_type NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    admission_year INTEGER,
    application_type VARCHAR(50),
    question_count INTEGER NOT NULL,
    time_limit_minutes INTEGER,
    is_adaptive BOOLEAN DEFAULT FALSE,
    stages INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE test_questions (
    test_id VARCHAR(100) REFERENCES tests(id) ON DELETE CASCADE,
    question_id VARCHAR(100) REFERENCES questions(id),
    position INTEGER NOT NULL,
    stage INTEGER DEFAULT 1,
    PRIMARY KEY (test_id, question_id)
);
```

### User Tables

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    role user_role NOT NULL DEFAULT 'student',
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    subscription_status VARCHAR(50),
    subscription_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE atom_mastery (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    atom_id VARCHAR(50) REFERENCES atoms(id),
    status mastery_status NOT NULL DEFAULT 'not_started',
    is_mastered BOOLEAN NOT NULL DEFAULT FALSE,
    mastery_source mastery_source,
    first_mastered_at TIMESTAMPTZ,
    last_demonstrated_at TIMESTAMPTZ,
    current_streak INTEGER DEFAULT 0,
    total_attempts INTEGER DEFAULT 0,
    correct_attempts INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, atom_id)
);

CREATE TABLE test_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    test_id VARCHAR(100) REFERENCES tests(id),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    total_questions INTEGER,
    correct_answers INTEGER,
    score_percentage DECIMAL(5,2),
    stage_1_score INTEGER,
    stage_2_difficulty VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE student_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    question_id VARCHAR(100) REFERENCES questions(id),
    test_attempt_id UUID REFERENCES test_attempts(id),
    selected_answer VARCHAR(50) NOT NULL,
    is_correct BOOLEAN NOT NULL,
    response_time_seconds INTEGER,
    answered_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Indexes

```sql
CREATE INDEX idx_atoms_subject ON atoms(subject_id);
CREATE INDEX idx_atoms_axis ON atoms(axis);
CREATE INDEX idx_atoms_prerequisites ON atoms USING GIN(prerequisite_ids);
CREATE INDEX idx_questions_source ON questions(source);
CREATE INDEX idx_questions_difficulty ON questions(difficulty_level);
CREATE INDEX idx_questions_question_set ON questions(question_set_id);
CREATE INDEX idx_question_atoms_atom ON question_atoms(atom_id);
CREATE INDEX idx_test_questions_position ON test_questions(test_id, position);
CREATE INDEX idx_atom_mastery_user ON atom_mastery(user_id);
CREATE INDEX idx_atom_mastery_status ON atom_mastery(status);
CREATE INDEX idx_atom_mastery_spaced_rep ON atom_mastery(last_demonstrated_at) WHERE is_mastered = TRUE;
CREATE INDEX idx_test_attempts_user ON test_attempts(user_id);
CREATE INDEX idx_student_responses_user ON student_responses(user_id);
CREATE INDEX idx_student_responses_question ON student_responses(question_id);
```

---

## Relationships

```
subjects ──1:N──▶ atoms ──1:1──▶ question_sets ──1:N──▶ questions
                    │                   │
                    │                   └──1:1──▶ lessons
                    │
                    ├──N:N──▶ atoms (prerequisites)
                    │
                    └──N:N──▶ questions (via question_atoms)

tests ──N:N──▶ questions (via test_questions)

users ──N:N──▶ atoms (via atom_mastery)
  │
  ├──1:N──▶ test_attempts ──1:N──▶ student_responses
  │
  └──1:N──▶ student_responses ──N:1──▶ questions
```

---

## ID Formats

| Entity | Format | Example |
|--------|--------|---------|
| Subject | `paes_{test}` | `paes_m1` |
| Standard | `{subject}-{axis}-{seq}` | `M1-ALG-01` |
| Atom | `A-{subject}-{axis}-{std}-{seq}` | `A-M1-ALG-01-01` |
| Question Set | `qs-{atom_id}` | `qs-A-M1-ALG-01-01` |
| Lesson | `lesson-{atom_id}` | `lesson-A-M1-ALG-01-01` |
| Question (official) | `{test_id}-Q{num}` | `prueba-invierno-2026-Q1` |
| Question (alternate) | `alt-{parent_id}-{seq}` | `alt-prueba-invierno-2026-Q1-001` |
| Question (set) | `{set_id}-{diff}-{seq}` | `qs-A-M1-ALG-01-01-low-001` |

---

## Business Rules

### Mastery
- Binary: `is_mastered` is TRUE or FALSE
- PP100 pass: 3 correct in a row, at least 2 at Hard
- PP100 fail: 3 wrong in a row OR <70% accuracy over 10+ questions → status = `frozen`
- Max 20 questions per attempt; no provisional mastery
- Auto-unfreeze: when all prerequisites become mastered, frozen → in_progress
- `mastery_source`: records how mastery was achieved (diagnostic, practice_test, pp100)
- `last_demonstrated_at`: used for spaced repetition scheduling

### Question Generation
- Generate question_sets BEFORE lessons
- Minimum 14 easy, 18 medium, 14 hard (46 total per atom)
- Lessons only created after question_set status = `reviewed`

### Prerequisites
- `prerequisite_ids` array defines direct dependencies
- Use recursive CTE for full prerequisite chain
- Cannot start atom until all prerequisites mastered

---

## Key Queries

```sql
-- Get questions for atom
SELECT q.* FROM questions q
JOIN question_atoms qa ON q.id = qa.question_id
WHERE qa.atom_id = $1
ORDER BY q.difficulty_level;

-- Get PP100 questions
SELECT * FROM questions
WHERE question_set_id = $1
ORDER BY CASE difficulty_level
    WHEN 'low' THEN 1 WHEN 'medium' THEN 2 WHEN 'high' THEN 3
END;

-- Get prerequisites (recursive)
WITH RECURSIVE prereqs AS (
    SELECT id, prerequisite_ids, 0 as depth FROM atoms WHERE id = $1
    UNION ALL
    SELECT a.id, a.prerequisite_ids, p.depth + 1
    FROM atoms a JOIN prereqs p ON a.id = ANY(p.prerequisite_ids)
    WHERE p.depth < 10
)
SELECT DISTINCT id FROM prereqs WHERE id != $1;

-- Check if should unfreeze
SELECT BOOL_AND(COALESCE(am.is_mastered, FALSE)) as all_prereqs_mastered
FROM atoms a
CROSS JOIN LATERAL unnest(a.prerequisite_ids) AS prereq_id
LEFT JOIN atom_mastery am ON am.atom_id = prereq_id AND am.user_id = $1
WHERE a.id = $2;

-- Atoms due for spaced repetition
SELECT a.id, a.title, am.last_demonstrated_at
FROM atom_mastery am
JOIN atoms a ON am.atom_id = a.id
WHERE am.user_id = $1 AND am.is_mastered = TRUE
  AND am.last_demonstrated_at < NOW() - INTERVAL '7 days'
ORDER BY am.last_demonstrated_at LIMIT 10;

-- Update mastery from PP100
UPDATE atom_mastery SET
    status = 'mastered',
    is_mastered = TRUE,
    mastery_source = 'pp100',
    first_mastered_at = COALESCE(first_mastered_at, NOW()),
    last_demonstrated_at = NOW(),
    current_streak = $streak,
    total_attempts = total_attempts + $attempts,
    correct_attempts = correct_attempts + $correct,
    updated_at = NOW()
WHERE user_id = $1 AND atom_id = $2;
```

---

## Sample Data

### Atom
```json
{
  "id": "A-M1-ALG-01-01",
  "subject_id": "paes_m1",
  "axis": "algebra_y_funciones",
  "standard_ids": ["M1-ALG-01"],
  "atom_type": "representacion",
  "primary_skill": "representar",
  "title": "Traducción bidireccional entre lenguaje natural y algebraico",
  "mastery_criteria": ["Traduce enunciados con operaciones básicas", "Representa relaciones de cantidad"],
  "prerequisite_ids": []
}
```

### Question feedback_per_option
```json
{
  "ChoiceA": "Error: applied operations in wrong order...",
  "ChoiceB": "Correct: parentheses first, then multiplication...",
  "ChoiceC": "Error: miscalculated inside parentheses...",
  "ChoiceD": "Error: treated multiplication as addition..."
}
```

### Atom Mastery
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "atom_id": "A-M1-ALG-01-01",
  "status": "mastered",
  "is_mastered": true,
  "mastery_source": "pp100",
  "first_mastered_at": "2026-01-10T14:30:00Z",
  "last_demonstrated_at": "2026-01-10T14:30:00Z",
  "current_streak": 11
}
```

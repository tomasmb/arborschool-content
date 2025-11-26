# Gemini 3 Pro Prompt Engineering Best Practices

**Last Updated**: 2025-01-24  
**Source**: [Gemini 3 Developer Guide](https://ai.google.dev/gemini-api/docs/gemini-3?thinking=high) and Google AI Documentation

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [Thinking Levels](#thinking-levels)
3. [Prompt Structure](#prompt-structure)
4. [Context Management](#context-management)
5. [Output Format Control](#output-format-control)
6. [Temperature and Configuration](#temperature-and-configuration)
7. [Advanced Techniques](#advanced-techniques)
8. [Avoiding Prompt Overfitting](#avoiding-prompt-overfitting)
9. [Common Pitfalls](#common-pitfalls)
10. [Best Practices Checklist](#best-practices-checklist)

---

## Core Principles

### 1. Be Precise and Direct

Gemini 3 Pro is a reasoning model that responds best to **direct, clear instructions**. Unlike older models that required verbose prompt engineering, Gemini 3 may over-analyze overly complex prompts.

**✅ Good:**
```
Convert this question to QTI 3.0 XML. Use the choice interaction type.
```

**❌ Bad:**
```
I would like you to carefully consider the following task. Please take your time to understand the requirements. The task involves converting educational content. Specifically, I need you to transform a question format into a standardized XML format known as QTI 3.0...
```

### 2. Output Verbosity Control

By default, Gemini 3 is **less verbose** and prefers providing direct, efficient answers. If you need a more conversational tone, explicitly request it.

**✅ Good:**
```
Explain this as a friendly, talkative assistant. Provide detailed explanations.
```

**❌ Bad:**
```
Explain this. (Assumes verbose output)
```

### 3. Context Placement Strategy

For large datasets (entire books, codebases, long videos), **place specific instructions at the END** of the prompt, after the data context.

**✅ Good:**
```
[Large context data here - 50 pages of text]

Based on the information above, segment this text into individual questions.
```

**❌ Bad:**
```
Segment this text into questions: [50 pages of text here]
```

### 4. Anchor Context with Transition Phrases

Use phrases like "Based on the information above..." to anchor the model's reasoning to the provided data.

---

## Thinking Levels

Gemini 3 Pro uses **dynamic thinking by default** (`high`). You can control the maximum depth of reasoning with the `thinking_level` parameter.

### Available Levels

- **`low`**: Minimizes latency and cost. Best for:
  - Simple instruction following
  - Chat applications
  - High-throughput applications
  - Tasks that don't require deep reasoning

- **`high`** (Default): Maximizes reasoning depth. Best for:
  - Complex problem-solving
  - Code analysis and debugging
  - Mathematical reasoning
  - Structured output generation (JSON/XML)
  - Tasks requiring careful analysis

**⚠️ Warning**: You cannot use both `thinking_level` and the legacy `thinking_budget` parameter in the same request.

### When to Use Each Level

**Use `low` for:**
- Simple text transformations
- Format conversions
- Basic validation checks
- High-volume, low-complexity tasks

**Use `high` (default) for:**
- Question segmentation (requires understanding structure)
- QTI XML generation (requires schema adherence)
- Semantic validation (requires comparison reasoning)
- Complex multi-step tasks

---

## Prompt Structure

### Recommended Structure

```
<role>
You are [specific role/expertise]
</role>

<task>
[Clear, direct task description]
</task>

<rules>
1. Rule 1
2. Rule 2
3. Rule 3
</rules>

<output_format>
[Explicit format requirements]
</output_format>

<constraints>
- Constraint 1
- Constraint 2
</constraints>

<context>
[Data/input to process]
</context>

<final_instruction>
[Anchor phrase: "Based on the information above..."]
</final_instruction>
```

### Alternative: Markdown Structure

```
# Role
You are an expert QTI 3.0 XML developer.

# Task
Convert this question to valid QTI 3.0 XML.

# Rules
1. Use correct namespace
2. Include all required elements
3. Output only XML

# Output Format
Return ONLY the raw XML string. No markdown blocks.

# Context
[Question content here]
```

---

## Context Management

### 1. Large Context Windows

Gemini 3 Pro supports **1M token input context**. For large documents:

1. **Provide all context first**
2. **Place instructions at the end**
3. **Use anchor phrases** to connect context to task

### 2. Structured Context Separation

Use clear delimiters to separate different parts of context:

```
### Input Text
[Text to segment]

### Shared Context
[Passage that applies to multiple questions]

### Question
[Individual question]
```

### 3. Context Preservation

When working with fragmented content (e.g., PDF chunks):

- Preserve structure markers
- Maintain references (images, tables)
- Keep sequential ordering
- Use placeholders for non-text content

---

## Output Format Control

### 1. Structured Output (JSON)

For JSON responses, use `response_mime_type="application/json"` in generation config:

```python
config = GenerationConfig(
    temperature=0.0,
    response_mime_type="application/json"
)
```

**Prompt should include:**
- Explicit JSON schema
- Example output
- Field descriptions

### 2. XML Output

For XML (like QTI), explicitly state:

```
Output ONLY the raw XML string. No markdown blocks, no explanations.
```

**Common issues:**
- Model wraps XML in ```xml blocks
- Model adds explanatory text
- Model includes XML declaration when not needed

**Solution:**
- Explicitly state "ONLY XML, no markdown"
- Post-process to remove wrappers
- Validate structure in code

### 3. Text Output

For plain text, be explicit about verbosity:

```
Provide a concise answer (2-3 sentences).
```

or

```
Provide a detailed explanation with examples.
```

---

## Temperature and Configuration

### Recommended Settings

**For Deterministic Tasks** (segmentation, validation, XML generation):
```python
GenerationConfig(
    temperature=0.0,      # Deterministic
    top_p=1.0,           # No nucleus sampling
    top_k=1,             # Greedy decoding
    max_output_tokens=8192
)
```

**For Creative Tasks**:
```python
GenerationConfig(
    temperature=0.7-1.0,  # More creative
    top_p=0.95,
    top_k=40
)
```

### ⚠️ Important: Temperature Settings in Gemini 3

According to the Gemini 3 documentation:
> "If your existing code explicitly sets temperature (especially to low values for deterministic outputs), we recommend removing this parameter and using the Gemini 3 default of 1.0 to avoid potential looping issues or performance degradation on complex tasks."

**However**, for structured output tasks (JSON/XML), `temperature=0.0` is still recommended for consistency.

---

## Advanced Techniques

### 1. Few-Shot Learning

Provide concrete examples in your prompt:

```
### Example

Input:
"1. What is 2+2?
A. 3
B. 4"

Output:
{
  "id": "Q1",
  "content": "1. What is 2+2?\nA. 3\nB. 4"
}
```

### 2. Negative Examples

Show what NOT to do:

```
### Critical Requirements
- NEVER invent questions not in the source text
- NEVER add content not in the original
- NEVER skip required elements
```

### 3. Explicit Checklists

For validation tasks, provide checklists:

```
### Validation Checklist (All must pass)
1. Has question stem
2. Has all answer choices
3. No contamination from other questions
4. Self-contained
```

### 4. Role-Based Prompting

Prime the model with expertise:

```
You are an expert QTI 3.0 XML developer with 10 years of experience.
```

### 5. Step-by-Step Instructions

For complex tasks, break into steps:

```
### Process
1. Analyze the question structure
2. Identify the interaction type
3. Map content to QTI elements
4. Generate XML
5. Validate structure
```

---

## Avoiding Prompt Overfitting

A critical mistake in prompt engineering is **overfitting** a prompt to solve one specific example or edge case, 
which then degrades performance on the general task.

### The Problem

When debugging a prompt that fails on a specific input, it's tempting to add instructions that fix *that exact case*.
This often introduces brittleness:

- The prompt becomes too specific and fails on other valid inputs
- Rules accumulate that contradict each other
- The prompt grows verbose, confusing the model

### Best Practices to Avoid Overfitting

**1. Write Abstract, Generalizable Instructions**

Instead of fixing a specific symptom, identify the **underlying principle** and express it generally.

**❌ Overfitted:**
```
If the question mentions "función lineal", make sure to tag it as "linear-functions".
```

**✅ Generalized:**
```
Tag each question with the most specific applicable topic from the taxonomy.
```

**2. Use Diverse Examples in Few-Shot Prompts**

When providing examples, include variety that covers different aspects of the task—not just the case you're debugging.

- Include edge cases alongside typical cases
- Show different valid output structures
- Demonstrate the range of acceptable responses

**3. Maintain a Separate Evaluation Set**

Keep a set of test inputs that you **don't use** when developing the prompt. After making changes, verify
the prompt still works on this unseen set. If it doesn't, you've likely overfitted.

**4. Prefer Removing Over Adding**

When a prompt fails:
1. First, check if existing rules are conflicting or unclear
2. Simplify before adding complexity
3. Only add new rules if simplification doesn't work

**5. Document the Intent, Not the Fix**

When you must add a rule, write it as the **general principle** you want enforced, not the specific bug you're fixing.

**❌ Bug-fix comment:**
```
# Added because question 47 was being split incorrectly
```

**✅ Intent comment:**
```
# Ensure multi-part questions remain grouped when they share context
```

### Red Flags That Suggest Overfitting

- Prompt changes that reference specific IDs, values, or test cases
- Rules that only make sense for one input
- Frequent prompt changes after each failure
- Accumulating "exception" rules
- Prompt length growing without clear benefit

---

## Common Pitfalls

### 1. Over-Engineering Prompts

**Problem**: Adding unnecessary complexity that confuses the model.

**Solution**: Keep prompts concise and direct.

### 2. Ignoring Default Behavior

**Problem**: Not accounting for Gemini 3's less verbose default output.

**Solution**: Explicitly request verbosity if needed.

### 3. Poor Context Ordering

**Problem**: Instructions before large context, causing model to lose focus.

**Solution**: Context first, instructions last, with anchor phrases.

### 4. Missing Format Constraints

**Problem**: Model adds markdown wrappers or explanatory text.

**Solution**: Explicitly state "ONLY XML" or "ONLY JSON", and post-process.

### 5. Temperature Misuse

**Problem**: Using low temperature for tasks that benefit from reasoning.

**Solution**: Use `high` thinking level for complex tasks, `low` for simple ones.

### 6. Not Using Structured Output

**Problem**: Parsing free-form text when JSON would be better.

**Solution**: Use `response_mime_type="application/json"` for structured data.

### 7. Overfitting to Specific Examples

**Problem**: Adding rules to fix one failing case, degrading general performance.

**Solution**: Fix the underlying principle, not the symptom. Test on diverse inputs. See [Avoiding Prompt Overfitting](#avoiding-prompt-overfitting).

---

## Best Practices Checklist

### Before Writing a Prompt

- [ ] Is the task clearly defined?
- [ ] Are instructions placed after context (for large inputs)?
- [ ] Is the output format explicitly specified?
- [ ] Are negative constraints included (what NOT to do)?
- [ ] Is verbosity level specified?

### For Structured Output

- [ ] Is the schema clearly defined?
- [ ] Are example outputs provided?
- [ ] Is `response_mime_type` set correctly?
- [ ] Is temperature set appropriately (0.0 for deterministic)?

### For Complex Tasks

- [ ] Is thinking level appropriate (`high` for complex, `low` for simple)?
- [ ] Are step-by-step instructions provided?
- [ ] Is role/expertise specified?
- [ ] Are validation criteria included?

### For Large Context

- [ ] Is context placed before instructions?
- [ ] Are anchor phrases used?
- [ ] Is structure preserved?
- [ ] Are placeholders used for non-text content?

### Post-Processing

- [ ] Is output cleaned (remove markdown wrappers)?
- [ ] Is output validated (schema, structure)?
- [ ] Are errors handled gracefully?
- [ ] Is logging in place for debugging?

### Avoiding Overfitting

- [ ] Does the fix address a general principle, not a specific symptom?
- [ ] Have you tested on diverse inputs, not just the failing case?
- [ ] Did you simplify existing rules before adding new ones?
- [ ] Are there any rules that reference specific IDs or values?
- [ ] Is the prompt growing without clear benefit?

---

## Example: Complete Prompt Template

```
<role>
You are an expert QTI 3.0 XML developer with deep knowledge of the IMS Global QTI specification.
</role>

<task>
Convert the following question into valid QTI 3.0 XML using the {question_type} interaction type.
</task>

<rules>
1. Use namespace: xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
2. Include all required QTI elements
3. Remove choice labels (A., B., C., D.) from choice text
4. Preserve mathematical notation exactly
5. Include shared context if provided
</rules>

<output_format>
Return ONLY the raw XML string. No markdown code blocks, no XML declaration, no explanatory text.
</output_format>

<constraints>
- NEVER add content not in the original question
- NEVER skip required QTI elements
- ALWAYS use correct element names (qti-* prefix)
- ALWAYS close all elements properly
</constraints>

<example>
Input: "1. What is 2+2?\nA. 3\nB. 4\nC. 5"

Output:
<qti-assessment-item xmlns="..." identifier="Q1" ...>
  [Complete QTI XML]
</qti-assessment-item>
</example>

<context>
{shared_context}

Question ID: {question_id}
Question Type: {question_type}
Question Content:
{question_content}
</context>

<final_instruction>
Based on the question content above, generate the QTI 3.0 XML following all rules and constraints.
</final_instruction>
```

---

## References

1. [Gemini 3 Developer Guide](https://ai.google.dev/gemini-api/docs/gemini-3?thinking=high)
2. [Gemini 3 Prompting Best Practices](https://ai.google.dev/docs/prompt_best_practices)
3. [Prompt Design Strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies)
4. [Gemini API Reference](https://ai.google.dev/api)

---

**Note**: This document is based on Gemini 3 Pro Preview (January 2025). Best practices may evolve as the model is updated.




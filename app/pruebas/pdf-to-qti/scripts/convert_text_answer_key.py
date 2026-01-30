#!/usr/bin/env python3
"""
Script para convertir un clavijero en formato texto a JSON.

El formato esperado es tabular con pares pregunta-respuesta:
1	B	23	B	45	B
2	D	24	C	46	-
...

Las preguntas con "-" se omiten del JSON final.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict


def parse_text_answer_key(text_path: Path) -> Dict[str, str]:
    """
    Parse a text file with answer key in tabular format.

    Format: Each line contains 3 pairs of question-answer separated by tabs:
    1	B	23	B	45	B

    Questions with "-" are skipped.

    Returns a dictionary mapping question numbers to answers (e.g., {"1": "ChoiceB", ...})
    """
    answers: Dict[str, str] = {}

    with open(text_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            # Split by tabs
            parts = line.split("\t")

            # Process pairs: each line has 3 pairs (6 elements total)
            for i in range(0, len(parts), 2):
                if i + 1 >= len(parts):
                    break

                q_num = parts[i].strip()
                answer = parts[i + 1].strip()

                # Skip if question number is empty or answer is "-"
                if not q_num or answer == "-":
                    continue

                # Normalize answer to ChoiceX format
                answer_upper = answer.upper()
                if answer_upper in ["A", "B", "C", "D", "E"]:
                    answers[q_num] = f"Choice{answer_upper}"
                else:
                    print(f"⚠️  Warning: Unexpected answer format '{answer}' for question {q_num} on line {line_num}")

    return answers


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert text answer key to JSON format"
    )
    parser.add_argument(
        "--text-path",
        required=True,
        help="Path to text file with answer key"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON file path"
    )
    parser.add_argument(
        "--test-name",
        help="Test name (for documentation in output file)"
    )

    args = parser.parse_args()

    text_path = Path(args.text_path)
    if not text_path.exists():
        print(f"❌ Text file not found: {text_path}")
        sys.exit(1)

    print(f"📄 Parsing answer key from: {text_path}")
    answers = parse_text_answer_key(text_path)

    if not answers:
        print("❌ No answers found in text file")
        sys.exit(1)

    print(f"✅ Parsed {len(answers)} answer(s)")

    # Create output structure
    output_data = {
        "test_name": args.test_name or text_path.stem,
        "source_file": str(text_path),
        "total_questions": len(answers),
        "answers": answers,
        "metadata": {
            "extraction_method": "Text file parsing",
            "question_numbers": sorted(answers.keys(), key=lambda x: int(x) if x.isdigit() else 999)
        }
    }

    # Save output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Answer key saved to: {output_path}")
    print("\n📊 Summary:")
    print(f"   Total questions with answers: {len(answers)}")
    if answers:
        q_nums = sorted(answers.keys(), key=lambda x: int(x) if x.isdigit() else 999)
        print(f"   Question range: {q_nums[0]} - {q_nums[-1]}")
    print("\n💡 Next step: Use this answer key when processing QTI questions")


if __name__ == "__main__":
    main()

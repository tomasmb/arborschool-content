#!/usr/bin/env python3
"""
Update correct answers in existing QTI XML files.

This script reads a respuestas_correctas.json file and updates the
<qti-correct-response> elements in all QTI XML files.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

# Namespace for QTI
QTI_NS = "{http://www.imsglobal.org/xsd/imsqtiasi_v3p0}"


def extract_question_number(xml_path: Path) -> Optional[int]:
    """Extract question number from XML filename (e.g., Q3.xml -> 3)."""
    match = re.search(r"Q(\d+)\.xml$", xml_path.name)
    return int(match.group(1)) if match else None


def update_qti_correct_answer(xml_path: Path, correct_answer: str) -> tuple[bool, Optional[str]]:
    """
    Update the correct answer in a QTI XML file.

    Returns (success, old_value) where old_value is None if not found.
    """
    try:
        # Read the file as text to preserve formatting
        with open(xml_path, "r", encoding="utf-8") as f:
            f.read()

        # Parse XML
        tree = ET.parse(str(xml_path))
        root = tree.getroot()

        # Find qti-correct-response element (it's inside qti-response-declaration)
        # The actual tag includes 'qti-' prefix in the namespace
        response_decl = root.find(f".//{QTI_NS}qti-response-declaration")
        if response_decl is None:
            return (False, None)

        correct_response = response_decl.find(f"{QTI_NS}qti-correct-response")
        if correct_response is None:
            return (False, None)

        # Find qti-value element
        qti_value = correct_response.find(f"{QTI_NS}qti-value")
        if qti_value is None:
            return (False, None)

        old_value = qti_value.text
        qti_value.text = correct_answer

        # Write back to file
        tree.write(str(xml_path), encoding="utf-8", xml_declaration=True)

        return (True, old_value)

    except ET.ParseError as e:
        print(f"❌ Error parsing {xml_path.name}: {e}")
        return (False, None)
    except Exception as e:
        print(f"❌ Error processing {xml_path.name}: {e}")
        return (False, None)


def main() -> None:
    parser = argparse.ArgumentParser(description="Update correct answers in QTI XML files")
    parser.add_argument("--answers-json", type=Path, required=True, help="Path to respuestas_correctas.json file")
    parser.add_argument("--xml-dir", type=Path, required=True, help="Directory containing QTI XML files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be updated without making changes")

    args = parser.parse_args()

    # Load answer key
    if not args.answers_json.exists():
        print(f"❌ Answer key file not found: {args.answers_json}")
        sys.exit(1)

    with open(args.answers_json, "r", encoding="utf-8") as f:
        answer_data = json.load(f)

    answers = answer_data.get("answers", {})
    if not answers:
        print("❌ No answers found in JSON file")
        sys.exit(1)

    print(f"📚 Loaded {len(answers)} answers from {args.answers_json.name}")

    # Find all QTI XML files
    xml_dir = args.xml_dir
    if not xml_dir.exists():
        print(f"❌ XML directory not found: {xml_dir}")
        sys.exit(1)

    xml_files = sorted(xml_dir.glob("Q*.xml"))
    if not xml_files:
        print(f"⚠️  No Q*.xml files found in {xml_dir}")
        sys.exit(1)

    print(f"📁 Found {len(xml_files)} XML files in {xml_dir}")

    if args.dry_run:
        print("\n🔍 DRY RUN - No files will be modified\n")

    # Update each XML file
    updated_count = 0
    skipped_count = 0
    not_found_count = 0

    for xml_file in xml_files:
        question_num = extract_question_number(xml_file)
        if question_num is None:
            print(f"⚠️  Could not extract question number from {xml_file.name}")
            skipped_count += 1
            continue

        question_key = str(question_num)
        if question_key not in answers:
            print(f"⚠️  No answer found for question {question_num} ({xml_file.name})")
            not_found_count += 1
            continue

        correct_answer = answers[question_key]

        if args.dry_run:
            # Just show what would be updated
            try:
                tree = ET.parse(str(xml_file))
                root = tree.getroot()
                response_decl = root.find(f".//{QTI_NS}qti-response-declaration")
                if response_decl is None:
                    print(f"⚠️  {xml_file.name}: no <qti-response-declaration> found")
                    skipped_count += 1
                    continue
                correct_response = response_decl.find(f"{QTI_NS}qti-correct-response")
                if correct_response is not None:
                    qti_value = correct_response.find(f"{QTI_NS}qti-value")
                    old_value = qti_value.text if qti_value is not None else "NOT FOUND"
                    if old_value != correct_answer:
                        print(f"📝 Would update {xml_file.name}: {old_value} -> {correct_answer}")
                        updated_count += 1
                    else:
                        print(f"✓  {xml_file.name}: already correct ({correct_answer})")
                else:
                    print(f"⚠️  {xml_file.name}: no <qti-correct-response> found")
                    skipped_count += 1
            except Exception as e:
                print(f"❌ Error reading {xml_file.name}: {e}")
                skipped_count += 1
        else:
            success, old_value = update_qti_correct_answer(xml_file, correct_answer)
            if success:
                if old_value != correct_answer:
                    print(f"✅ Updated {xml_file.name}: {old_value} -> {correct_answer}")
                    updated_count += 1
                else:
                    print(f"ℹ️  {xml_file.name}: already correct ({correct_answer})")
            else:
                print(f"⚠️  {xml_file.name}: could not update (element not found)")
                skipped_count += 1

    # Summary
    print("\n📊 Summary:")
    if args.dry_run:
        print(f"   Would update: {updated_count} files")
        print(f"   Already correct: {len(xml_files) - updated_count - skipped_count - not_found_count} files")
    else:
        print(f"   Updated: {updated_count} files")
    print(f"   Skipped: {skipped_count} files")
    print(f"   Missing answers: {not_found_count} files")


if __name__ == "__main__":
    main()

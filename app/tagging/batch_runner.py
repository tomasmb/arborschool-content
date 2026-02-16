import glob
import os
import time

from app.question_generation.progress import report_progress
from app.tagging.tagger import AtomTagger


def run_batch(base_dir: str = "app/data/pruebas/finalizadas"):
    """Runs tagging on all questions in the finalizadas directory."""

    tagger = AtomTagger()

    # Recursive search for question.xml
    patterns = [
        os.path.join(base_dir, "**", "question.xml"),
        os.path.join(base_dir, "**", "*.xml"),  # Catch flat files too
    ]

    xml_files = set()
    for pattern in patterns:
        for f in glob.glob(pattern, recursive=True):
            if "pre_validation" in f or "manifest" in f:
                continue
            xml_files.add(f)

    sorted_files = sorted(list(xml_files))
    total_files = len(sorted_files)
    print(f"Found {total_files} XML files to process.")

    success_count = 0
    fail_count = 0
    skipped_count = 0

    report_progress(0, total_files)

    for i, xml_path in enumerate(sorted_files):
        dir_name = os.path.dirname(xml_path)
        file_name = os.path.basename(xml_path)

        if file_name == "question.xml":
            output_path = os.path.join(dir_name, "metadata_tags.json")
        else:
            base_name = os.path.splitext(file_name)[0]
            output_path = os.path.join(
                dir_name, f"{base_name}_metadata_tags.json",
            )

        print(f"[{i + 1}/{total_files}] Processing {xml_path}...")

        # Check if output exists (optional skip logic)
        if os.path.exists(output_path):
            print("  Skipping (already tagged)")
            skipped_count += 1
            report_progress(i + 1, total_files)
            continue

        result = tagger.tag_xml_file(xml_path, output_path)

        if result:
            success_count += 1
            val = result.get("validation", {}).get("status", "UNKNOWN")
            print(f"  Result: SUCCESS (Validation: {val})")
        else:
            fail_count += 1
            print("  Result: FAILED")

        report_progress(i + 1, total_files)

        # Rate limiting sleep
        time.sleep(2)

    print("\n" + "=" * 40)
    print("BATCH TAGGING COMPLETE")
    print("=" * 40)
    print(f"Total Files: {total_files}")
    print(f"Success:     {success_count}")
    print(f"Failed:      {fail_count}")
    print(f"Skipped:     {skipped_count}")
    print("=" * 40)


if __name__ == "__main__":
    run_batch()

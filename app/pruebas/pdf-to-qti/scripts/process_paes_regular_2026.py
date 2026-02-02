#!/usr/bin/env python3
"""
Script para procesar PAES Regular 2026.

Esta prueba tiene solo 45 preguntas (no está completa).
El clavijero está en formato texto.
"""

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Load environment variables from .env file
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment variables from {env_file}")

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))

from backup_manager import create_qti_backup
from main import process_single_question_pdf


def process_all_questions(
    questions_dir: str,
    output_base_dir: str,
    paes_mode: bool = True,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Process all question PDFs from a directory.

    Args:
        questions_dir: Directory containing individual question PDFs
        output_base_dir: Base directory for outputs
        paes_mode: Use PAES optimizations

    Returns:
        Summary of processing results
    """
    questions_path = Path(questions_dir)
    if not questions_path.exists():
        return {
            "success": False,
            "error": f"Questions directory not found: {questions_dir}"
        }

    # Find all PDF files
    question_pdfs = sorted(questions_path.glob("*.pdf"))

    if not question_pdfs:
        return {
            "success": False,
            "error": f"No PDF files found in {questions_dir}"
        }

    print(f"📋 Found {len(question_pdfs)} question PDFs")
    print(f"⚡ PAES mode: {'Enabled' if paes_mode else 'Disabled'}")
    print()

    results = {
        "total": len(question_pdfs),
        "successful": [],
        "failed": [],
        "processing_times": [],
        "start_time": time.time()
    }

    # Load answer key if available
    answer_key_data = None
    answer_key_path = Path(output_base_dir).parent.parent / "procesadas" / "seleccion-regular-2026" / "respuestas_correctas.json"
    if not answer_key_path.exists():
        # Try alternative location
        answer_key_path = Path(output_base_dir).parent / "respuestas_correctas.json"

    if answer_key_path.exists():
        try:
            with open(answer_key_path, "r", encoding="utf-8") as f:
                answer_key_data = json.load(f)
            print(f"✅ Loaded answer key with {len(answer_key_data.get('answers', {}))} answers")
        except Exception as e:
            print(f"⚠️  Could not load answer key: {e}")

    # Process each question
    generated_folders_with_xml = []  # Track folders with successfully generated XMLs
    backup_batch_size = 10  # OPTIMIZACIÓN: Crear backup cada N preguntas procesadas

    for i, pdf_path in enumerate(question_pdfs, 1):
        # Use actual question number from PDF filename (e.g., "Q19" from "Q19.pdf")
        # NOT the position in the selection file - this ensures folders match PDF names
        question_id = pdf_path.stem  # e.g., "Q1" or "Q19" from "Q1.pdf" or "Q19.pdf"
        output_dir = Path(output_base_dir) / question_id

        print(f"[{i}/{len(question_pdfs)}] Processing {question_id}...")
        start_time = time.time()

        try:
            result = process_single_question_pdf(
                input_pdf_path=str(pdf_path),
                output_dir=str(output_dir),
                openai_api_key=None,  # Use from .env
                paes_mode=paes_mode,
                skip_if_exists=True,  # OPTIMIZACIÓN: Saltarse si ya existe XML válido
            )

            elapsed = time.time() - start_time
            results["processing_times"].append(elapsed)

            if result.get("success"):
                status_msg = "Skipped (exists)" if result.get("skipped") else "Success"
                regenerated_msg = " (regenerated)" if result.get("regenerated") else ""
                print(f"   ✅ {status_msg}{regenerated_msg} ({elapsed:.1f}s)")
                results["successful"].append({
                    "question": question_id,
                    "time": elapsed,
                    "title": result.get("title", "Unknown"),
                    "skipped": result.get("skipped", False),
                    "regenerated": result.get("regenerated", False),
                })
                # Check if XML was actually generated
                xml_file = output_dir / "question.xml"
                if xml_file.exists() and not result.get("skipped"):
                    generated_folders_with_xml.append(question_id)

                    # OPTIMIZACIÓN: Crear backup incremental cada N preguntas
                    if len(generated_folders_with_xml) % backup_batch_size == 0:
                        print("   💾 Creando backup incremental...")
                        try:
                            backup_metadata = {
                                "test_name": "seleccion-regular-2026",
                                "batch_number": len(generated_folders_with_xml) // backup_batch_size,
                                "total_processed": i,
                            }
                            # Crear backup solo de las últimas N preguntas generadas
                            last_batch = generated_folders_with_xml[-backup_batch_size:]
                            backup_dir = create_qti_backup(
                                output_dir=Path(output_base_dir),
                                generated_folders=last_batch,
                                backup_metadata=backup_metadata,
                            )
                            print(f"   ✅ Backup incremental creado: {backup_dir.name}")
                        except Exception as e:
                            print(f"   ⚠️  Error creando backup incremental: {e}")
            else:
                print(f"   ❌ Failed: {result.get('error', 'Unknown error')} ({elapsed:.1f}s)")
                results["failed"].append({
                    "question": question_id,
                    "time": elapsed,
                    "error": result.get("error", "Unknown error")
                })

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   ❌ Exception: {e} ({elapsed:.1f}s)")
            results["failed"].append({
                "question": question_id,
                "time": elapsed,
                "error": str(e)
            })

        print()

    # Calculate summary
    total_time = time.time() - results["start_time"]
    avg_time = sum(results["processing_times"]) / len(results["processing_times"]) if results["processing_times"] else 0

    results["summary"] = {
        "total_questions": results["total"],
        "successful": len(results["successful"]),
        "failed": len(results["failed"]),
        "success_rate": f"{(len(results['successful']) / results['total'] * 100):.1f}%",
        "total_time_seconds": total_time,
        "total_time_minutes": total_time / 60,
        "avg_time_per_question": avg_time
    }

    return results, generated_folders_with_xml


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Process PAES Regular 2026"
    )
    parser.add_argument(
        "--questions-dir",
        default="../../data/pruebas/procesadas/seleccion-regular-2026/questions_pdfs",
        help="Directory with individual question PDFs"
    )
    parser.add_argument(
        "--output-dir",
        default="../../data/pruebas/procesadas/seleccion-regular-2026/qti",
        help="Output directory for QTI files"
    )
    parser.add_argument(
        "--paes-mode",
        action="store_true",
        default=True,
        help="Use PAES optimizations (default: True)"
    )
    parser.add_argument(
        "--no-paes-mode",
        action="store_true",
        help="Disable PAES mode"
    )

    args = parser.parse_args()

    paes_mode = args.paes_mode and not args.no_paes_mode

    print("=" * 60)
    print("PAES Regular 2026 - Procesamiento")
    print("=" * 60)
    print()

    # Check if questions directory exists
    questions_dir = Path(args.questions_dir)
    if not questions_dir.exists():
        print(f"❌ Questions directory not found: {questions_dir}")
        print()
        print("💡 Necesitas primero dividir el PDF en preguntas individuales.")
        print("   Usa pdf-splitter para crear PDFs individuales.")
        return

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process all questions
    results, generated_folders_with_xml = process_all_questions(
        questions_dir=str(questions_dir),
        output_base_dir=str(output_dir),
        paes_mode=paes_mode
    )

    # Save results
    results_file = output_dir / "processing_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    # Create backup of generated XMLs
    if generated_folders_with_xml:
        print("=" * 60)
        print("CREANDO BACKUP DE XMLs GENERADOS")
        print("=" * 60)
        print()

        backup_metadata = {
            "test_name": "seleccion-regular-2026",
            "processing_results_file": str(results_file),
            "total_questions": results["summary"]["total_questions"],
            "successful": results["summary"]["successful"],
            "failed": results["summary"]["failed"],
        }

        backup_dir = create_qti_backup(
            output_dir=output_dir,
            generated_folders=generated_folders_with_xml,
            backup_metadata=backup_metadata,
        )

        print("💡 El backup permanecerá hasta que confirmes que todo está correcto.")
        print(f"   Para eliminar el backup, usa: python3 backup_manager.py --delete {backup_dir.name}")
        print()

    # Print summary
    print("=" * 60)
    print("RESUMEN DE PROCESAMIENTO")
    print("=" * 60)
    print(f"Total preguntas: {results['summary']['total_questions']}")
    print(f"Exitosas: {results['summary']['successful']}")
    print(f"Fallidas: {results['summary']['failed']}")
    print(f"Tasa de éxito: {results['summary']['success_rate']}")
    print(f"Tiempo total: {results['summary']['total_time_minutes']:.1f} minutos")
    print(f"Tiempo promedio: {results['summary']['avg_time_per_question']:.1f} seg/pregunta")
    print()

    if results["failed"]:
        print("❌ Preguntas fallidas:")
        for fail in results["failed"]:
            print(f"   - {fail['question']}: {fail['error']}")
        print()

    print(f"📄 Resultados guardados en: {results_file}")
    print()

    # Exit with error code if any failed
    sys.exit(0 if results["summary"]["failed"] == 0 else 1)


if __name__ == "__main__":
    main()

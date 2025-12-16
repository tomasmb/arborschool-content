#!/usr/bin/env python3
"""
Script para procesar PAES Invierno 2026 con el nuevo código
y comparar con resultados del pipeline anterior.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List

# Load environment variables from .env file
from dotenv import load_dotenv
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment variables from {env_file}")

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))

from main import process_single_question_pdf

def process_all_questions(
    questions_dir: str,
    output_base_dir: str,
    paes_mode: bool = True,
) -> Dict[str, Any]:
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
    answer_key_path = Path(output_base_dir).parent.parent / "procesadas" / "prueba-invierno-2026" / "respuestas_correctas.json"
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
    for i, pdf_path in enumerate(question_pdfs, 1):
        question_id = pdf_path.stem  # e.g., "Q1" from "Q1.pdf"
        output_dir = Path(output_base_dir) / question_id
        
        print(f"[{i}/{len(question_pdfs)}] Processing {question_id}...")
        start_time = time.time()
        
        try:
            result = process_single_question_pdf(
                input_pdf_path=str(pdf_path),
                output_dir=str(output_dir),
                openai_api_key=None,  # Use from .env
                paes_mode=paes_mode,
            )
            
            elapsed = time.time() - start_time
            results["processing_times"].append(elapsed)
            
            if result.get("success"):
                print(f"   ✅ Success ({elapsed:.1f}s)")
                results["successful"].append({
                    "question": question_id,
                    "time": elapsed,
                    "title": result.get("title", "Unknown")
                })
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
    
    return results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Process PAES Invierno 2026 with new code"
    )
    parser.add_argument(
        "--questions-dir",
        default="../app/data/pruebas/procesadas/prueba-invierno-2026/questions_pdfs",
        help="Directory with individual question PDFs"
    )
    parser.add_argument(
        "--output-dir",
        default="./output/paes-invierno-2026-new",
        help="Output directory for results"
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
    print("PAES Invierno 2026 - Procesamiento con Nuevo Código")
    print("=" * 60)
    print()
    
    # Check if questions directory exists
    questions_dir = Path(args.questions_dir)
    if not questions_dir.exists():
        print(f"❌ Questions directory not found: {questions_dir}")
        print()
        print("💡 Necesitas primero dividir el PDF en preguntas individuales.")
        print("   Opciones:")
        print("   1. Usar pdf-splitter para crear PDFs individuales")
        print("   2. O usar las preguntas ya procesadas del pipeline anterior")
        return
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process all questions
    results = process_all_questions(
        questions_dir=str(questions_dir),
        output_base_dir=str(output_dir),
        paes_mode=paes_mode
    )
    
    # Save results
    results_file = output_dir / "processing_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
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

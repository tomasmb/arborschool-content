#!/usr/bin/env python3
"""
Script para procesar preguntas específicas.

Usa el número de pregunta real (e.g., Q19, Q22) para nombrar las carpetas,
no la posición en el archivo de selección. Esto asegura que los nombres
coincidan con los PDFs (Q19.pdf -> Q19/).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
project_root = Path(__file__).parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import process_single_question_pdf

def main():
    """Procesar preguntas específicas."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Process specific questions using actual question numbers for folder names"
    )
    parser.add_argument(
        "--question-numbers",
        nargs="+",
        type=int,
        required=True,
        help="Question numbers to process (e.g., 11 15 41 57)"
    )
    parser.add_argument(
        "--questions-dir",
        default="../../data/pruebas/procesadas/seleccion-regular-2026/questions_pdfs",
        help="Directory with question PDFs"
    )
    parser.add_argument(
        "--output-dir",
        default="../../data/pruebas/procesadas/seleccion-regular-2026/qti",
        help="Output directory for QTI files"
    )
    parser.add_argument(
        "--segmentation-file",
        default="splitter_output_regular_2026/part_1/segmentation_results.json",
        help="Path to segmentation results JSON"
    )
    
    args = parser.parse_args()
    
    questions_dir = Path(args.questions_dir)
    output_base_dir = Path(args.output_dir)
    
    print(f"🔄 Procesando {len(args.question_numbers)} preguntas...")
    print()
    
    success_count = 0
    failed_count = 0
    
    for i, q_num in enumerate(args.question_numbers, 1):
        pdf_path = questions_dir / f"Q{q_num}.pdf"
        
        # Usar el número de pregunta real para el nombre de la carpeta (como los PDFs)
        output_dir = output_base_dir / f"Q{q_num}"
        
        print(f"[{i}/{len(args.question_numbers)}] Procesando Q{q_num}...")
        
        if not pdf_path.exists():
            print(f"   ❌ PDF no encontrado: {pdf_path}")
            failed_count += 1
            continue
        
        try:
            result = process_single_question_pdf(
                input_pdf_path=str(pdf_path),
                output_dir=str(output_dir),
                openai_api_key=None,
                paes_mode=True,
            )
            
            if result.get('success'):
                print(f"   ✅ Éxito")
                success_count += 1
            else:
                print(f"   ❌ Falló: {result.get('error', 'Unknown')}")
                failed_count += 1
        except Exception as e:
            print(f"   ❌ Excepción: {e}")
            failed_count += 1
        
        print()
    
    print("=" * 60)
    print(f"✅ Exitosas: {success_count}")
    print(f"❌ Fallidas: {failed_count}")
    print(f"📊 Total: {len(args.question_numbers)}")
    print("=" * 60)


if __name__ == "__main__":
    main()

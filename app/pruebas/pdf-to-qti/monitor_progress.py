#!/usr/bin/env python3
"""
Script para monitorear el progreso del procesamiento de preguntas PAES.
"""

import os
import time
from datetime import datetime
from pathlib import Path


def monitor_progress(output_dir: str, questions_dir: str, refresh_interval: int = 5):
    """
    Monitorea el progreso del procesamiento.

    Args:
        output_dir: Directorio de salida donde se guardan los resultados
        questions_dir: Directorio con los PDFs de preguntas
        refresh_interval: Segundos entre actualizaciones
    """
    output_path = Path(output_dir)
    questions_path = Path(questions_dir)

    # Contar total de preguntas
    total_pdfs = len(list(questions_path.glob("*.pdf")))

    print("=" * 70)
    print("MONITOR DE PROGRESO - Procesamiento PAES Invierno 2026")
    print("=" * 70)
    print(f"📊 Total de preguntas: {total_pdfs}")
    print(f"📁 Directorio de salida: {output_dir}")
    print(f"🔄 Actualizando cada {refresh_interval} segundos...")
    print("=" * 70)
    print()

    last_processed = set()
    start_time = time.time()

    try:
        while True:
            # Contar preguntas procesadas (que tienen al menos extracted_content.json)
            processed_questions = set()
            successful = 0
            failed = 0

            for question_dir in output_path.glob("question_*"):
                question_id = question_dir.name
                extracted_file = question_dir / "extracted_content.json"
                question_xml = question_dir / "question.xml"

                if extracted_file.exists():
                    processed_questions.add(question_id)

                    # Verificar si fue exitosa (tiene question.xml válido)
                    if question_xml.exists() and question_xml.stat().st_size > 100:
                        successful += 1
                    else:
                        failed += 1

            # Encontrar la última pregunta procesada
            current_question = None
            if processed_questions:
                # Ordenar por número de pregunta
                sorted_questions = sorted(
                    processed_questions,
                    key=lambda x: int(x.replace("question_", ""))
                )
                current_question = sorted_questions[-1]

            # Verificar archivos recientes para ver qué está procesando ahora
            processing_now = None
            if output_path.exists():
                recent_files = []
                for question_dir in output_path.glob("question_*"):
                    for file in question_dir.glob("*.json"):
                        if file.stat().st_mtime > time.time() - 30:  # Últimos 30 segundos
                            recent_files.append((file.stat().st_mtime, question_dir.name))

                if recent_files:
                    recent_files.sort(reverse=True)
                    processing_now = recent_files[0][1]

            # Calcular estadísticas
            processed_count = len(processed_questions)
            remaining = total_pdfs - processed_count
            progress_pct = (processed_count / total_pdfs * 100) if total_pdfs > 0 else 0

            # Calcular tiempo estimado
            elapsed = time.time() - start_time
            if processed_count > 0:
                avg_time_per_question = elapsed / processed_count
                estimated_remaining_time = avg_time_per_question * remaining
                estimated_minutes = estimated_remaining_time / 60
            else:
                estimated_minutes = 0

            # Limpiar pantalla (ANSI escape code)
            os.system('clear' if os.name != 'nt' else 'cls')

            # Mostrar información
            print("=" * 70)
            print("MONITOR DE PROGRESO - Procesamiento PAES Invierno 2026")
            print("=" * 70)
            print(f"⏰ Hora: {datetime.now().strftime('%H:%M:%S')}")
            print()
            print(f"📊 Progreso: {processed_count}/{total_pdfs} preguntas ({progress_pct:.1f}%)")
            print(f"   ✅ Exitosas: {successful}")
            print(f"   ❌ Fallidas: {failed}")
            print(f"   ⏳ Pendientes: {remaining}")
            print()

            if current_question:
                question_num = current_question.replace("question_", "")
                print(f"📝 Última completada: {current_question} (Pregunta #{question_num})")

            if processing_now and processing_now != current_question:
                question_num = processing_now.replace("question_", "")
                print(f"🔄 Procesando ahora: {processing_now} (Pregunta #{question_num})")

            print()
            print(f"⏱️  Tiempo transcurrido: {elapsed/60:.1f} minutos")
            if estimated_minutes > 0:
                print(f"⏳ Tiempo estimado restante: {estimated_minutes:.1f} minutos")

            # Mostrar últimas preguntas procesadas
            if processed_questions:
                sorted_recent = sorted(
                    processed_questions - last_processed,
                    key=lambda x: int(x.replace("question_", ""))
                )
                if sorted_recent:
                    print()
                    print(f"✨ Nuevas desde última actualización: {', '.join(sorted_recent[:5])}")
                    if len(sorted_recent) > 5:
                        print(f"   ... y {len(sorted_recent) - 5} más")

            last_processed = processed_questions.copy()

            print()
            print("=" * 70)
            print("Presiona Ctrl+C para salir")
            print("=" * 70)

            time.sleep(refresh_interval)

    except KeyboardInterrupt:
        print("\n\n👋 Monitoreo detenido por el usuario")
        print(f"📊 Estado final: {processed_count}/{total_pdfs} preguntas procesadas")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Monitorear progreso del procesamiento PAES")
    parser.add_argument(
        "--output-dir",
        default="./output/paes-invierno-2026-new",
        help="Directorio de salida (default: ./output/paes-invierno-2026-new)"
    )
    parser.add_argument(
        "--questions-dir",
        default="../pdf-splitter/output/paes-invierno/questions_pdfs",
        help="Directorio con PDFs de preguntas"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Intervalo de actualización en segundos (default: 5)"
    )

    args = parser.parse_args()

    monitor_progress(
        output_dir=args.output_dir,
        questions_dir=args.questions_dir,
        refresh_interval=args.interval
    )

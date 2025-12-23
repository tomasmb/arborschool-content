#!/bin/bash
# Script para preparar y procesar PAES Regular 2026

set -e

echo "=========================================="
echo "PAES Regular 2026 - Setup y Procesamiento"
echo "=========================================="
echo ""

# Paths
PDF_PATH="../../data/pruebas/raw/seleccion-regular-2026/2026-25-12-03-paes-regular-matematica1-p2026.pdf"
ANSWER_KEY_TEXT="../../data/pruebas/raw/seleccion-regular-2026/Claves-regular-2026.txt"
SPLITTER_OUTPUT="./splitter_output_regular_2026"
QUESTIONS_PDFS="../../data/pruebas/procesadas/seleccion-regular-2026/questions_pdfs"
FINAL_OUTPUT="../../data/pruebas/procesadas/seleccion-regular-2026/qti"

echo "📋 Paso 1: Convertir clavijero de texto a JSON..."
echo "   Text file: $ANSWER_KEY_TEXT"
echo ""

# Check if answer key text exists
if [ ! -f "$ANSWER_KEY_TEXT" ]; then
    echo "❌ Answer key text file not found: $ANSWER_KEY_TEXT"
    exit 1
fi

# Convert answer key to JSON
python3 scripts/convert_text_answer_key.py \
    --text-path "$ANSWER_KEY_TEXT" \
    --output ../../data/pruebas/procesadas/seleccion-regular-2026/respuestas_correctas.json \
    --test-name seleccion-regular-2026

echo ""
echo "✅ Clavijero convertido a JSON"
echo ""

# Check if questions directory already exists
if [ -d "$QUESTIONS_PDFS" ] && [ "$(ls -A $QUESTIONS_PDFS/*.pdf 2>/dev/null | wc -l)" -gt 0 ]; then
    echo "📁 PDFs de preguntas ya existen en: $QUESTIONS_PDFS"
    echo "   Saltando división del PDF..."
    echo ""
else
    echo "📋 Paso 2: Dividir PDF en preguntas individuales..."
    echo "   PDF: $PDF_PATH"
    echo "   Output: $SPLITTER_OUTPUT"
    echo ""
    
    # Check if PDF exists
    if [ ! -f "$PDF_PATH" ]; then
        echo "❌ PDF not found: $PDF_PATH"
        exit 1
    fi
    
    # Step 2: Use pdf-splitter to create individual question PDFs
    echo "🔀 Ejecutando pdf-splitter..."
    cd ../pdf-splitter
    python3 main.py "$PDF_PATH" "../pdf-to-qti/$SPLITTER_OUTPUT"
    cd ../pdf-to-qti
    
    # Check if questions were created
    if [ ! -d "$SPLITTER_OUTPUT/questions" ]; then
        echo "❌ pdf-splitter did not create questions directory"
        exit 1
    fi
    
    # Copy questions to a simpler location
    echo ""
    echo "📁 Organizando PDFs de preguntas..."
    mkdir -p "$QUESTIONS_PDFS"
    cp "$SPLITTER_OUTPUT/questions"/*.pdf "$QUESTIONS_PDFS/" 2>/dev/null || true
    
    # Rename to Q1.pdf, Q2.pdf, etc. if needed
    cd "$QUESTIONS_PDFS"
    for file in question_*.pdf; do
        if [ -f "$file" ]; then
            # Extract question number
            num=$(echo "$file" | sed 's/question_\([0-9]*\)\.pdf/\1/' | sed 's/^0*//')
            newname="Q${num}.pdf"
            if [ "$file" != "$newname" ]; then
                mv "$file" "$newname"
            fi
        fi
    done
    cd ../../../../app/pruebas/pdf-to-qti
    
    echo "✅ PDFs de preguntas listos en: $QUESTIONS_PDFS"
    echo ""
fi

# Step 3: Process all questions
echo "🚀 Paso 3: Procesando preguntas con nuevo código..."
echo "   Modo: PAES (optimizado)"
echo "   Output: $FINAL_OUTPUT"
echo "   Nota: Esta prueba tiene solo 45 preguntas (no está completa)"
echo ""

python3 process_paes_regular_2026.py \
    --questions-dir "$QUESTIONS_PDFS" \
    --output-dir "$FINAL_OUTPUT" \
    --paes-mode

echo ""
echo "✅ Procesamiento completado!"
echo "📊 Revisa los resultados en: $FINAL_OUTPUT"

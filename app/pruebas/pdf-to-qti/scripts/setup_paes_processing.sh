#!/bin/bash
# Script para preparar y procesar PAES Invierno 2026

set -e

echo "=========================================="
echo "PAES Invierno 2026 - Setup y Procesamiento"
echo "=========================================="
echo ""

# Paths
PDF_PATH="../../data/pruebas/raw/prueba-invierno-2026.pdf"
SPLITTER_OUTPUT="./splitter_output"
QUESTIONS_PDFS="./questions_pdfs"
FINAL_OUTPUT="./output/paes-invierno-2026-new"

echo "📋 Paso 1: Dividir PDF en preguntas individuales..."
echo "   PDF: $PDF_PATH"
echo "   Output: $SPLITTER_OUTPUT"
echo ""

# Check if PDF exists
if [ ! -f "$PDF_PATH" ]; then
    echo "❌ PDF not found: $PDF_PATH"
    exit 1
fi

# Step 1: Use pdf-splitter to create individual question PDFs
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
cd ..

echo "✅ PDFs de preguntas listos en: $QUESTIONS_PDFS"
echo ""

# Step 2: Process all questions
echo "🚀 Paso 2: Procesando preguntas con nuevo código..."
echo "   Modo: PAES (optimizado)"
echo "   Output: $FINAL_OUTPUT"
echo ""

python3 process_paes_invierno.py \
    --questions-dir "$QUESTIONS_PDFS" \
    --output-dir "$FINAL_OUTPUT" \
    --paes-mode

echo ""
echo "✅ Procesamiento completado!"
echo "📊 Revisa los resultados en: $FINAL_OUTPUT"

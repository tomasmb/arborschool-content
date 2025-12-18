#!/bin/bash
# Script rápido para verificar el progreso del procesamiento

QTI_DIR="app/data/pruebas/procesadas/seleccion-regular-2025/qti"

echo "============================================================"
echo "📊 VERIFICACIÓN RÁPIDA DEL PROGRESO"
echo "============================================================"

# Contar XMLs
XML_COUNT=$(ls $QTI_DIR/*/question.xml 2>/dev/null | wc -l | tr -d ' ')
echo ""
echo "✅ XMLs generados: $XML_COUNT/45 ($(echo "scale=1; $XML_COUNT*100/45" | bc)%)"

# Verificar procesos activos
PROCESS_COUNT=$(ps aux | grep -E "process|reproces|regular_2025" | grep -v grep | wc -l | tr -d ' ')
if [ "$PROCESS_COUNT" -gt 0 ]; then
    echo "🔄 Procesos activos: $PROCESS_COUNT"
else
    echo "⏸️  No hay procesos activos"
fi

# Último XML modificado
if [ -n "$(ls $QTI_DIR/*/question.xml 2>/dev/null)" ]; then
    LATEST_XML=$(ls -t $QTI_DIR/*/question.xml 2>/dev/null | head -1)
    LATEST_AGE=$(($(date +%s) - $(stat -f %m "$LATEST_XML" 2>/dev/null || stat -c %Y "$LATEST_XML" 2>/dev/null)))
    LATEST_Q=$(basename $(dirname "$LATEST_XML"))
    echo "📄 Último XML: $LATEST_Q (hace ${LATEST_AGE}s)"
    
    if [ $LATEST_AGE -lt 120 ]; then
        echo "   ✅ Proceso activo recientemente"
    fi
fi

# Archivos modificados en últimos 2 minutos
RECENT_FILES=$(find $QTI_DIR -type f -mmin -2 2>/dev/null | wc -l | tr -d ' ')
if [ "$RECENT_FILES" -gt 0 ]; then
    echo "🔄 Archivos modificados (últimos 2 min): $RECENT_FILES"
fi

echo ""
echo "============================================================"

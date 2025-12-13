# Instrucciones para corregir preguntas

## Pasos

1. **Abre el PDF original**: `app/data/pruebas/raw/prueba-invierno-2026.pdf`

2. **Para cada pregunta problemática**:
   - Encuentra la pregunta en el PDF
   - Completa el archivo correspondiente (Q3, Q7, o Q32) con el contenido correcto
   - Copia exactamente el texto y opciones como aparecen en el PDF

3. **Aplica las correcciones**:
   ```bash
   cd app/pdf-to-qti
   python corregir_preguntas.py Q7 ../data/pruebas/procesadas/prueba-invierno-2026/correcciones/Q7_CONTENIDO_CORREGIDO.txt
   python corregir_preguntas.py Q3 ../data/pruebas/procesadas/prueba-invierno-2026/correcciones/Q3_CONTENIDO_CORREGIDO.txt
   python corregir_preguntas.py Q32 ../data/pruebas/procesadas/prueba-invierno-2026/correcciones/Q32_CONTENIDO_CORREGIDO.txt
   ```

## Archivos de plantilla

- `Q3_CONTENIDO_CORREGIDO.txt` - Para la pregunta sobre gráficos circulares
- `Q7_CONTENIDO_CORREGIDO.txt` - Para la pregunta de huevos (opciones faltantes)
- `Q32_CONTENIDO_CORREGIDO.txt` - Para la pregunta del intervalo

## Notas

- El script crea un backup automático antes de modificar
- Las preguntas corregidas se moverán automáticamente a `validated_questions`
- Los errores relacionados se limpiarán automáticamente

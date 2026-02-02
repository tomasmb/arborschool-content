# Tests de Generación de Estándares

Esta carpeta contiene los resultados de tests de generación de estándares para validar el pipeline.

## Archivos

- `standards_numeros_test.json`: Test final y definitivo del eje "numeros" generado con `gemini-3-pro-preview` siguiendo todas las buenas prácticas.

## Ejecutar generación

Para generar estándares para un eje:

```bash
python3 -m app.standards.run_single_eje \
  --temario app/data/temarios/json/temario-paes-m1-invierno-y-regular-2026.json \
  --eje numeros \
  --output tests/standards/standards_numeros_test.json
```


# Pruebas Raw - PDFs Originales

Esta carpeta contiene los PDFs originales organizados por prueba.

## 📁 Estructura

Cada prueba tiene su propia carpeta:

```
raw/
  └── prueba-invierno-2026/
      ├── prueba-invierno-2026.pdf        # PDF de la prueba
      └── respuestas-prueba-invierno-2026.pdf  # PDF con respuestas correctas (opcional)
```

## 📋 Convenciones de Nombres

- **Carpeta de prueba**: `prueba-{nombre}-{año}/` (e.g., `prueba-invierno-2026/`)
- **PDF de prueba**: `{nombre-prueba}.pdf` o el nombre original del PDF
- **PDF de respuestas**: `respuestas-{nombre-prueba}.pdf` o `clavijero-{nombre-prueba}.pdf`

## 🔄 Uso

Los PDFs en esta carpeta son **solo lectura** - son los documentos originales fuente.

Los PDFs procesados y resultados se guardan en:
- `app/data/pruebas/procesadas/{test_name}/`

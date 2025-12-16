# Documentación del Pipeline QTI

**Última actualización**: 2025-12-14

Este directorio contiene toda la documentación relacionada con la conversión de PDFs a QTI 3.0 XML.

---

## 📚 Índice de Documentación

### 🎯 Documentos Principales

1. **[Estado del Proyecto](./ESTADO-PROYECTO.md)** ⭐ **EMPEZAR AQUÍ**
   - Estado actual del trabajo
   - Información nueva del socio
   - Tareas pendientes
   - Plan de acción

2. **[Comparación de Pipelines](./COMPARACION-PIPELINES.md)**
   - Pipeline actual vs. nuevo código
   - Pros/contras de cada enfoque
   - Recomendaciones

### 📝 Documentación Técnica

3. **[Limitaciones de Extend.ai](../qti-pipeline-4steps/docs/LIMITACIONES-EXTEND-AI-Y-SOLUCIONES.md)**
   - Errores comunes de parsing
   - Soluciones implementadas
   - Posibles mejoras futuras

4. **[Corrección Matemática](../qti-pipeline-4steps/CORRECCION_MATEMATICA.md)**
   - Cómo funciona MathCorrector
   - Patrones que corrige
   - Limitaciones

### 📋 Trabajo Realizado

5. **[Agenda de Correcciones Manuales](./CORRECCIONES-MANUALES.md)**
   - Todas las correcciones manuales realizadas
   - 13 preguntas corregidas
   - Patrones de errores identificados

6. **[Recomendaciones y Decisiones](./RECOMENDACIONES.md)**
   - Recomendaciones sobre re-correr pasos
   - Preguntas sobre mejoras
   - Plan para revisión manual

### 🛠️ Guías de Trabajo

7. **[Ayuda para Revisión PDF](./AYUDA-REVISION-PDF.md)**
   - Cómo usar el extractor de PDF
   - Workflow para revisión manual
   - Scripts disponibles

8. **[Resumen Visual](./RESUMEN-VISUAL.md)**
   - Diagramas y resúmenes visuales
   - Estado del proyecto en formato visual
   - Referencia rápida

---

## 📁 Estructura de Archivos

```
docs/qti-pipeline/
├── README.md                    # Este archivo (índice)
├── ESTADO-PROYECTO.md          # Estado actual y plan
├── COMPARACION-PIPELINES.md    # Comparación de enfoques
├── CORRECCIONES-MANUALES.md    # Correcciones realizadas
├── RECOMENDACIONES.md           # Recomendaciones y decisiones
└── AYUDA-REVISION-PDF.md       # Guía de revisión manual

docs/
└── agenda-cambios-manuales-prueba-invierno-2026.md  # (mantener por compatibilidad)

app/qti-pipeline-4steps/
├── docs/
│   └── LIMITACIONES-EXTEND-AI-Y-SOLUCIONES.md  # Documentación técnica
└── CORRECCION_MATEMATICA.md                    # Documentación técnica
```

---

## 🚀 Inicio Rápido

**Si quieres entender el estado actual del proyecto:**
1. Lee [Estado del Proyecto](./ESTADO-PROYECTO.md)

**Si quieres ver qué correcciones se hicieron:**
1. Lee [Correcciones Manuales](./CORRECCIONES-MANUALES.md)

**Si quieres comparar los dos enfoques:**
1. Lee [Comparación de Pipelines](./COMPARACION-PIPELINES.md)

**Si quieres hacer revisión manual:**
1. Lee [Ayuda para Revisión PDF](./AYUDA-REVISION-PDF.md)

---

## 📝 Notas

- Los documentos técnicos específicos del módulo están en `app/pdf-to-qti/docs/`
- Los documentos de trabajo y decisiones están en `docs/qti-pipeline/`
- La agenda de correcciones original está en `docs/` por compatibilidad

---

**Última actualización**: 2025-12-14

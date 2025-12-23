# Plan de Trabajo: Conversión de Pruebas PAES M1 a QTI

## 🎯 Objetivo

Convertir **10 pruebas PAES M1** (las más valiosas y representativas) a formato QTI 3.0 XML.

## 📋 Estrategia

1. **Empezar con 1 prueba** (la más reciente)
2. **Perfeccionar el proceso** hasta que la conversión sea perfecta
3. **Aplicar el proceso** a las otras 9 pruebas

## 📁 Estructura de Directorios

```
app/data/pruebas/
├── raw/                    # PDFs originales (solo lectura)
│   ├── prueba-001.pdf
│   ├── prueba-002.pdf
│   └── ...
├── procesadas/             # Pruebas en proceso de conversión
│   ├── prueba-001/
│   │   ├── parsed.json              # Extend.ai parsed PDF output (CACHÉ - reutilizar!)
│   │   ├── segmented.json           # Segmented questions
│   │   ├── questions/               # Individual question markdown
│   │   │   ├── Q1.md
│   │   │   ├── Q2.md
│   │   │   └── ...
│   │   ├── qti/                     # Generated QTI XML files
│   │   │   ├── Q1.xml
│   │   │   ├── Q2.xml
│   │   │   └── ...
│   │   ├── generator_output.json    # Generator results with all QTI items
│   │   ├── validation_output.json   # Full validation results
│   │   ├── validation_summary.json  # Summary of validation results
│   │   └── report.json              # Pipeline execution report
│   └── ...
└── finalizadas/            # Pruebas completamente convertidas y validadas
    ├── prueba-001/         # Misma estructura que procesadas/ (cuando está lista)
    └── ...
```

## 🔄 Flujo de Trabajo por Prueba

### Fase 1: Preparación
1. Seleccionar la prueba (empezar con la más reciente)
2. Copiar PDF a `app/data/pruebas/raw/prueba-001.pdf` (o el nombre que prefieras)
3. El directorio de procesamiento se crea automáticamente

### Fase 2: Conversión Inicial

#### Opción A: Usando el script helper (recomendado)
```bash
cd app/pdf-to-qti

# Pipeline completo
python convertir_prueba.py prueba-001

# O paso por paso
python convertir_prueba.py prueba-001 --paso parse
python convertir_prueba.py prueba-001 --paso segment
python convertir_prueba.py prueba-001 --paso generate
python convertir_prueba.py prueba-001 --paso validate
```

#### Opción B: Usando run.py directamente
```bash
cd app/pdf-to-qti

# Paso 1: Parsear (UNA SOLA VEZ - usa créditos)
python run.py ../../data/pruebas/raw/prueba-001.pdf \
  --step parse \
  --output ../../data/pruebas/procesadas/prueba-001

# Paso 2: Segmentar
python run.py ../../data/pruebas/procesadas/prueba-001/parsed.json \
  --step segment \
  --output ../../data/pruebas/procesadas/prueba-001

# Paso 3: Generar QTI
python run.py ../../data/pruebas/procesadas/prueba-001/segmented.json \
  --step generate \
  --output ../../data/pruebas/procesadas/prueba-001

# Paso 4: Validar
python run.py ../../data/pruebas/procesadas/prueba-001/qti \
  --step validate \
  --output ../../data/pruebas/procesadas/prueba-001
```

### Fase 3: Revisión y Ajustes
1. Revisar `validation_summary.json` para ver problemas
2. Revisar QTI generados en `qti/` para verificar calidad
3. Ajustar prompts o configuración si es necesario
4. Re-ejecutar pasos necesarios (usando `parsed.json` guardado)

### Fase 4: Finalización
1. Cuando la prueba esté perfecta, mover a `finalizadas/`
2. Documentar cualquier ajuste especial necesario

## 📝 Criterios para Seleccionar las 10 Pruebas

### Prioridad Alta:
- ✅ **Prueba más reciente** (empezar aquí)
- ✅ Cobertura completa de ejes temáticos (Números, Álgebra, Geometría, Probabilidad)
- ✅ Diferentes tipos de preguntas (opción múltiple, desarrollo, etc.)
- ✅ Incluye gráficos, tablas, imágenes

### Prioridad Media:
- ✅ Pruebas oficiales DEMRE
- ✅ Pruebas con buen balance de dificultad
- ✅ Pruebas representativas de cada eje

### Prioridad Baja:
- ⚠️ Pruebas muy antiguas (formato puede diferir)
- ⚠️ Pruebas con formato no estándar

## 🎯 Primera Prueba: La Más Reciente

**Recomendación:** Empezar con la prueba más reciente porque:
- Formato más actualizado
- Representa el estándar actual de PAES M1
- Si funciona bien aquí, funcionará con las demás

## 📊 Tracking de Progreso

| # | Prueba | Estado | Notas |
|---|--------|--------|-------|
| 1 | prueba-001 (más reciente) | 🔄 En proceso | - |
| 2 | prueba-002 | ⏳ Pendiente | - |
| 3 | prueba-003 | ⏳ Pendiente | - |
| ... | ... | ... | ... |
| 10 | prueba-010 | ⏳ Pendiente | - |

**Estados:**
- ⏳ Pendiente
- 🔄 En proceso
- ✅ Finalizada
- ⚠️ Requiere ajustes

## 💡 Tips

1. **Siempre guarda `parsed.json`** - Es tu caché, no lo borres
2. **Revisa `validation_summary.json`** después de cada paso
3. **Trabaja iterativamente** - Ajusta y re-ejecuta hasta que esté perfecto
4. **Documenta ajustes especiales** - Pueden ser útiles para otras pruebas

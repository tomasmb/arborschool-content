# Selección MST: 32 Preguntas para Prueba Diagnóstica

**Fecha:** 2026-01-08  
**Arquitectura:** MST (Multistage Test)  
**Total preguntas:** 32 (8 por módulo)  
**Versión:** 2.0 (optimizada por score de dificultad)

---

## Estructura del Test

```
┌─────────────────────────────────────────────────────────────┐
│  R1: ROUTING (8 preguntas iguales para todos)               │
│  Score promedio: 0.48                                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
         Correctas: 0-3        4-6          7-8
                              ↓
┌─────────────────┬─────────────────┬─────────────────────────┐
│   RUTA A        │   RUTA B        │   RUTA C                │
│   (bajo)        │   (medio)       │   (alto)                │
│   Score: 0.21   │   Score: 0.45   │   Score: 0.64           │
└─────────────────┴─────────────────┴─────────────────────────┘
```

---

## Resumen de Dificultad por Score

| Módulo | Score Promedio | Rango | Nivel |
|--------|----------------|-------|-------|
| **A2** | 0.21 | 0.15-0.25 | Bajo |
| **B2** | 0.45 | 0.45 | Medio |
| **R1** | 0.48 | 0.45-0.50 | Medio |
| **C2** | 0.64 | 0.60-0.65 | Alto* |

*C2 usa los Medium más difíciles disponibles (score 0.60-0.65)

---

## R1: Routing (8 preguntas)

Todos los estudiantes responden estas 8 preguntas primero.  
**Criterio:** Medium con score intermedio (~0.50)

| # | Examen | ID | Eje | Score | Habilidad |
|---|--------|-----|-----|-------|-----------|
| 1 | seleccion-regular-2025 | Q32 | ALG | 0.50 | RES |
| 2 | Prueba-invierno-2025 | Q11 | ALG | 0.50 | RES |
| 3 | prueba-invierno-2026 | Q7 | NUM | 0.50 | RES |
| 4 | Prueba-invierno-2025 | Q18 | NUM | 0.50 | RES |
| 5 | seleccion-regular-2026 | Q41 | GEO | 0.45 | RES |
| 6 | seleccion-regular-2026 | Q45 | GEO | 0.45 | RES |
| 7 | seleccion-regular-2026 | Q62 | PROB | 0.50 | RES |
| 8 | seleccion-regular-2026 | Q60 | PROB | 0.45 | RES |

**Distribución:** 2 ALG, 2 NUM, 2 GEO, 2 PROB  
**Score promedio:** 0.48

---

## Regla de Routing

| Correctas en R1 | Ruta asignada |
|-----------------|---------------|
| 0-3 | A (bajo) |
| 4-6 | B (medio) |
| 7-8 | C (alto) |

---

## A2: Ruta Bajo (8 preguntas)

Para estudiantes con 0-3 correctas en R1.  
**Criterio:** Low con score más bajo disponible

| # | Examen | ID | Eje | Score | Habilidad |
|---|--------|-----|-----|-------|-----------|
| 1 | prueba-invierno-2026 | Q37 | ALG | 0.20 | RES |
| 2 | seleccion-regular-2025 | Q42 | ALG | 0.20 | RES |
| 3 | seleccion-regular-2026 | Q30 | ALG | 0.25 | ARG |
| 4 | prueba-invierno-2026 | Q19 | NUM | 0.15 | RES |
| 5 | Prueba-invierno-2025 | Q19 | NUM | 0.15 | RES |
| 6 | prueba-invierno-2026 | Q22 | GEO | 0.25 | RES |
| 7 | prueba-invierno-2026 | Q53 | PROB | 0.20 | RES |
| 8 | seleccion-regular-2026 | Q54 | PROB | 0.25 | REP |

**Distribución:** 3 ALG, 2 NUM, 1 GEO, 2 PROB  
**Score promedio:** 0.21

---

## B2: Ruta Medio (8 preguntas)

Para estudiantes con 4-6 correctas en R1.  
**Criterio:** Medium con score intermedio (~0.45)

| # | Examen | ID | Eje | Score | Habilidad |
|---|--------|-----|-----|-------|-----------|
| 1 | seleccion-regular-2026 | Q31 | ALG | 0.45 | RES |
| 2 | seleccion-regular-2026 | Q47 | ALG | 0.45 | ARG |
| 3 | seleccion-regular-2026 | Q14 | ALG | 0.45 | ARG |
| 4 | seleccion-regular-2026 | Q1 | NUM | 0.45 | RES |
| 5 | seleccion-regular-2026 | Q13 | NUM | 0.45 | RES |
| 6 | prueba-invierno-2026 | Q52 | GEO | 0.45 | RES |
| 7 | seleccion-regular-2026 | Q61 | PROB | 0.45 | REP |
| 8 | prueba-invierno-2026 | Q54 | PROB | 0.45 | REP |

**Distribución:** 3 ALG, 2 NUM, 1 GEO, 2 PROB  
**Score promedio:** 0.45

---

## C2: Ruta Alto (8 preguntas)

Para estudiantes con 7-8 correctas en R1.  
**Criterio:** Medium con score MÁS ALTO (0.60-0.65)

| # | Examen | ID | Eje | Score | Habilidad |
|---|--------|-----|-----|-------|-----------|
| 1 | seleccion-regular-2026 | Q48 | ALG | 0.65 | MOD |
| 2 | seleccion-regular-2026 | Q27 | ALG | 0.65 | RES |
| 3 | seleccion-regular-2025 | Q57 | ALG | 0.65 | RES |
| 4 | seleccion-regular-2025 | Q23 | NUM | 0.65 | MOD |
| 5 | Prueba-invierno-2025 | Q56 | NUM | 0.65 | ARG |
| 6 | seleccion-regular-2026 | Q50 | GEO | 0.60 | RES |
| 7 | Prueba-invierno-2025 | Q60 | PROB | 0.65 | RES |
| 8 | Prueba-invierno-2025 | Q61 | PROB | 0.65 | ARG |

**Distribución:** 3 ALG, 2 NUM, 1 GEO, 2 PROB  
**Score promedio:** 0.64

---

## Resumen de Distribución

### Por Eje (Total 32)

| Eje | R1 | A2 | B2 | C2 | Total |
|-----|----|----|----|----|-------|
| ALG | 2 | 3 | 3 | 3 | **11** |
| NUM | 2 | 2 | 2 | 2 | **8** |
| GEO | 2 | 1 | 1 | 1 | **5** |
| PROB | 2 | 2 | 2 | 2 | **8** |

### Por Habilidad (Total 32)

| Habilidad | R1 | A2 | B2 | C2 | Total |
|-----------|----|----|----|----|-------|
| RES | 8 | 6 | 4 | 4 | **22** |
| MOD | 0 | 0 | 0 | 2 | **2** |
| REP | 0 | 1 | 2 | 0 | **3** |
| ARG | 0 | 1 | 2 | 2 | **5** |

---

## Notas de Optimización

> [!TIP]
> La selección usa el score numérico de dificultad para crear una progresión clara:
> - **A2 (0.21):** Preguntas más fáciles del banco
> - **B2 (0.45):** Dificultad media
> - **C2 (0.64):** Los Medium más difíciles (cercanos a High)

> [!NOTE]
> R1 tiene score similar a B2 para que funcione como punto de referencia neutral.

---

## Rutas de Archivos

Las preguntas seleccionadas están en:

```
app/data/pruebas/finalizadas/<examen>/qti/<ID>/
├── question.xml
├── question.html
└── metadata_tags.json
```

# Selección MST: 32 Preguntas para Prueba Diagnóstica

**Fecha:** 2026-01-08  
**Arquitectura:** MST (Multistage Test)  
**Total preguntas:** 32 (8 por módulo)  
**Versión:** 3.0 (balanceada por habilidades)

---

## Estructura del Test

```
┌─────────────────────────────────────────────────────────────┐
│  R1: ROUTING (8 preguntas iguales para todos)               │
│  Score promedio: 0.47 | Habilidades: 4 RES, 1 MOD, 2 ARG, 1 REP │
└─────────────────────────────────────────────────────────────┘
                              ↓
         Correctas: 0-3        4-6          7-8
                              ↓
┌─────────────────┬─────────────────┬─────────────────────────┐
│   RUTA A        │   RUTA B        │   RUTA C                │
│   (bajo)        │   (medio)       │   (alto)                │
│   Score: 0.23   │   Score: 0.48   │   Score: 0.62           │
└─────────────────┴─────────────────┴─────────────────────────┘
```

---

## Principio de Selección

> **"Primero balance de habilidades, después optimización de score"**

La selección prioriza cubrir las 4 habilidades (RES, MOD, REP, ARG) para permitir diagnóstico válido de cada una.

---

## R1: Routing (8 preguntas)

Todos los estudiantes responden estas 8 preguntas primero.

| # | Examen | ID | Eje | Score | Habilidad |
|---|--------|-----|-----|-------|-----------|
| 1 | seleccion-regular-2025 | Q32 | ALG | 0.50 | RES |
| 2 | seleccion-regular-2026 | Q33 | ALG | 0.45 | MOD |
| 3 | prueba-invierno-2026 | Q7 | NUM | 0.50 | RES |
| 4 | prueba-invierno-2026 | Q23 | NUM | 0.45 | ARG |
| 5 | seleccion-regular-2026 | Q41 | GEO | 0.45 | RES |
| 6 | prueba-invierno-2026 | Q48 | GEO | 0.45 | ARG |
| 7 | seleccion-regular-2026 | Q62 | PROB | 0.50 | RES |
| 8 | seleccion-regular-2026 | Q61 | PROB | 0.45 | REP |

**Distribución:** 2 ALG, 2 NUM, 2 GEO, 2 PROB  
**Habilidades:** RES(4), MOD(1), ARG(2), REP(1)  
**Score promedio:** 0.47

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

| # | Examen | ID | Eje | Score | Habilidad |
|---|--------|-----|-----|-------|-----------|
| 1 | prueba-invierno-2026 | Q37 | ALG | 0.20 | RES |
| 2 | seleccion-regular-2026 | Q40 | ALG | 0.25 | MOD |
| 3 | seleccion-regular-2026 | Q30 | ALG | 0.25 | ARG |
| 4 | prueba-invierno-2026 | Q19 | NUM | 0.15 | RES |
| 5 | prueba-invierno-2026 | Q18 | NUM | 0.25 | MOD |
| 6 | prueba-invierno-2026 | Q22 | GEO | 0.25 | RES |
| 7 | prueba-invierno-2026 | Q53 | PROB | 0.20 | RES |
| 8 | seleccion-regular-2026 | Q54 | PROB | 0.25 | REP |

**Distribución:** 3 ALG, 2 NUM, 1 GEO, 2 PROB  
**Habilidades:** RES(4), MOD(2), ARG(1), REP(1)  
**Score promedio:** 0.23

---

## B2: Ruta Medio (8 preguntas)

Para estudiantes con 4-6 correctas en R1.

| # | Examen | ID | Eje | Score | Habilidad |
|---|--------|-----|-----|-------|-----------|
| 1 | Prueba-invierno-2025 | Q11 | ALG | 0.50 | RES |
| 2 | prueba-invierno-2026 | Q6 | ALG | 0.45 | MOD |
| 3 | seleccion-regular-2026 | Q47 | ALG | 0.45 | ARG |
| 4 | Prueba-invierno-2025 | Q18 | NUM | 0.50 | RES |
| 5 | seleccion-regular-2026 | Q5 | NUM | 0.55 | ARG |
| 6 | seleccion-regular-2026 | Q45 | GEO | 0.45 | RES |
| 7 | prueba-invierno-2026 | Q54 | PROB | 0.45 | REP |
| 8 | prueba-invierno-2026 | Q57 | PROB | 0.45 | ARG |

**Distribución:** 3 ALG, 2 NUM, 1 GEO, 2 PROB  
**Habilidades:** RES(3), MOD(1), ARG(3), REP(1)  
**Score promedio:** 0.48

---

## C2: Ruta Alto (8 preguntas)

Para estudiantes con 7-8 correctas en R1.

| # | Examen | ID | Eje | Score | Habilidad |
|---|--------|-----|-----|-------|-----------|
| 1 | seleccion-regular-2026 | Q27 | ALG | 0.65 | RES |
| 2 | seleccion-regular-2026 | Q48 | ALG | 0.65 | MOD |
| 3 | prueba-invierno-2026 | Q36 | ALG | 0.55 | ARG |
| 4 | seleccion-regular-2025 | Q23 | NUM | 0.65 | MOD |
| 5 | Prueba-invierno-2025 | Q56 | NUM | 0.65 | ARG |
| 6 | seleccion-regular-2025 | Q65 | GEO | 0.60 | ARG |
| 7 | Prueba-invierno-2025 | Q61 | PROB | 0.65 | ARG |
| 8 | seleccion-regular-2026 | Q53 | PROB | 0.60 | REP |

**Distribución:** 3 ALG, 2 NUM, 1 GEO, 2 PROB  
**Habilidades:** RES(1), MOD(2), ARG(4), REP(1)  
**Score promedio:** 0.62

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

| Habilidad | R1 | A2 | B2 | C2 | Total | % |
|-----------|----|----|----|----|-------|---|
| RES | 4 | 4 | 3 | 1 | **12** | 38% |
| MOD | 1 | 2 | 1 | 2 | **6** | 19% |
| REP | 1 | 1 | 1 | 1 | **4** | 12% |
| ARG | 2 | 1 | 3 | 4 | **10** | 31% |

### Comparación con PAES Real

| Habilidad | PAES Real | Nuestra Prueba | Estado |
|-----------|-----------|----------------|--------|
| RES | ~49% | 38% | ✅ Representada |
| MOD | ~16% | 19% | ✅ Representada |
| REP | ~14% | 12% | ✅ Representada |
| ARG | ~13% | 31% | ⚠️ Sobre-representada* |

*ARG está sobre-representada porque C2 tiene mayoría ARG (las preguntas Medium más difíciles tienden a ser ARG).

---

## Notas de Optimización

> [!TIP]
> Esta versión prioriza **validez diagnóstica** sobre máxima dificultad en C2.
> El score de C2 bajó de 0.64 a 0.62 para incluir más variedad de habilidades.

> [!NOTE]
> Cada módulo tiene al menos 1 pregunta de cada habilidad representada (excepto donde no hay disponibilidad).

---

## Rutas de Archivos

Las preguntas seleccionadas están en:

```
app/data/pruebas/finalizadas/<examen>/qti/<ID>/
├── question.xml
├── question.html
└── metadata_tags.json
```

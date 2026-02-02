# Selección MST: 32 Preguntas para Prueba Diagnóstica

**Fecha:** 2026-01-09  
**Arquitectura:** MST (Multistage Test)  
**Total preguntas:** 32 (8 por módulo)  
**Versión:** 3.0 (optimizada para cobertura de átomos)  
**Cobertura:** 83% de átomos (190/229)

---

## Estructura del Test

```
┌─────────────────────────────────────────────────────────────┐
│  R1: ROUTING (8 preguntas iguales para todos)               │
│  Score promedio: 0.48 | Habilidades: 4 RES, 4 ARG           │
└─────────────────────────────────────────────────────────────┘
                              ↓
         Correctas: 0-3        4-6          7-8
                              ↓
┌─────────────────┬─────────────────┬─────────────────────────┐
│   RUTA A        │   RUTA B        │   RUTA C                │
│   (bajo)        │   (medio)       │   (alto)                │
│   Low: 100%     │   Medium: 100%  │   Medium: 100%          │
└─────────────────┴─────────────────┴─────────────────────────┘
```

---

## R1: Routing (8 preguntas)

| # | Examen | ID | Eje | Score | Habilidad |
|---|--------|-----|-----|-------|-----------|
| 1 | prueba-invierno-2025 | Q28 | ALG | 0.45 | RES |
| 2 | prueba-invierno-2026 | Q31 | ALG | 0.55 | MOD |
| 3 | prueba-invierno-2026 | Q23 | NUM | 0.45 | ARG |
| 4 | seleccion-regular-2025 | Q15 | NUM | 0.55 | ARG |
| 5 | prueba-invierno-2025 | Q46 | GEO | 0.45 | ARG |
| 6 | prueba-invierno-2026 | Q45 | GEO | 0.55 | ARG |
| 7 | prueba-invierno-2026 | Q58 | PROB | 0.45 | REP |
| 8 | seleccion-regular-2026 | Q60 | PROB | 0.45 | RES |

**Distribución:** 2 ALG, 2 NUM, 2 GEO, 2 PROB ✅

---

## A2: Ruta Bajo (8 preguntas)

| # | Examen | ID | Eje | Score | Habilidad |
|---|--------|-----|-----|-------|-----------|
| 1 | prueba-invierno-2025 | Q40 | ALG | 0.25 | RES |
| 2 | seleccion-regular-2026 | Q35 | ALG | 0.25 | MOD |
| 3 | prueba-invierno-2026 | Q40 | ALG | 0.25 | RES |
| 4 | seleccion-regular-2025 | Q10 | NUM | 0.30 | RES |
| 5 | prueba-invierno-2025 | Q6 | NUM | 0.30 | RES |
| 6 | seleccion-regular-2025 | Q63 | GEO | 0.30 | REP |
| 7 | prueba-invierno-2026 | Q64 | PROB | 0.35 | ARG |
| 8 | seleccion-regular-2025 | Q54 | PROB | 0.25 | RES |

**Distribución:** 3 ALG, 2 NUM, 1 GEO, 2 PROB ✅  
**Dificultad:** 100% Low ✅

---

## B2: Ruta Medio (8 preguntas)

| # | Examen | ID | Eje | Score | Habilidad |
|---|--------|-----|-----|-------|-----------|
| 1 | prueba-invierno-2026 | Q42 | ALG | 0.45 | MOD |
| 2 | seleccion-regular-2025 | Q38 | ALG | 0.55 | RES |
| 3 | seleccion-regular-2025 | Q36 | ALG | 0.55 | MOD |
| 4 | seleccion-regular-2025 | Q3 | NUM | 0.55 | ARG |
| 5 | prueba-invierno-2025 | Q22 | NUM | 0.45 | MOD |
| 6 | seleccion-regular-2025 | Q60 | GEO | 0.45 | RES |
| 7 | seleccion-regular-2025 | Q55 | PROB | 0.55 | RES |
| 8 | prueba-invierno-2025 | Q65 | PROB | 0.45 | REP |

**Distribución:** 3 ALG, 2 NUM, 1 GEO, 2 PROB ✅  
**Dificultad:** 100% Medium ✅

---

## C2: Ruta Alto (8 preguntas)

| # | Examen | ID | Eje | Score | Habilidad |
|---|--------|-----|-----|-------|-----------|
| 1 | seleccion-regular-2026 | Q59 | ALG | 0.60 | RES |
| 2 | seleccion-regular-2026 | Q11 | ALG | 0.55 | MOD |
| 3 | prueba-invierno-2025 | Q33 | ALG | 0.60 | MOD |
| 4 | prueba-invierno-2025 | Q56 | NUM | 0.65 | ARG |
| 5 | seleccion-regular-2026 | Q23 | NUM | 0.55 | RES |
| 6 | prueba-invierno-2025 | Q50 | GEO | 0.55 | REP |
| 7 | prueba-invierno-2025 | Q61 | PROB | 0.65 | ARG |
| 8 | prueba-invierno-2026 | Q60 | PROB | 0.55 | ARG |

**Distribución:** 3 ALG, 2 NUM, 1 GEO, 2 PROB ✅  
**Dificultad:** 100% Medium ✅

---

## Validación vs Blueprint

| Criterio | Esperado | Actual | Estado |
|----------|----------|--------|--------|
| Ejes R1 | 2-2-2-2 | 2-2-2-2 | ✅ |
| Ejes A2/B2/C2 | 3-2-1-2 | 3-2-1-2 | ✅ |
| Dificultad A2 | Low | 100% Low | ✅ |
| Dificultad B2 | Medium | 100% Medium | ✅ |
| Dificultad C2 | Medium+ | 100% Medium | ✅ |
| Cobertura átomos | Máxima | 83% (190/229) | ✅ |

---

## Historial de Versiones

| Versión | Fecha | Cambio | Cobertura |
|---------|-------|--------|-----------|
| 1.0 | 2026-01-08 | Selección inicial | 58% (133/229) |
| **3.0** | **2026-01-09** | **Optimizada para cobertura** | **83% (190/229)** |

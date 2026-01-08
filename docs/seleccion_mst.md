# Selección MST: 32 Preguntas para Prueba Diagnóstica

**Fecha:** 2026-01-08  
**Arquitectura:** MST (Multistage Test)  
**Total preguntas:** 32 (8 por módulo)

---

## Estructura del Test

```
┌─────────────────────────────────────────────────────────────┐
│  R1: ROUTING (8 preguntas iguales para todos)               │
│  Dificultad: Medium                                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
         Correctas: 0-3        4-6          7-8
                              ↓
┌─────────────────┬─────────────────┬─────────────────────────┐
│   RUTA A        │   RUTA B        │   RUTA C                │
│   (bajo)        │   (medio)       │   (alto)                │
│   8 preguntas   │   8 preguntas   │   8 preguntas           │
│   Low           │   Medium        │   Medium                │
└─────────────────┴─────────────────┴─────────────────────────┘
```

---

## R1: Routing (8 preguntas)

Todos los estudiantes responden estas 8 preguntas primero.

| # | Examen | ID | Eje | Dificultad | Habilidad |
|---|--------|-----|-----|------------|-----------|
| 1 | Prueba-invierno-2025 | Q27 | ALG | Medium | MOD |
| 2 | seleccion-regular-2026 | Q34 | ALG | Medium | REP |
| 3 | seleccion-regular-2026 | Q1 | NUM | Medium | RES |
| 4 | Prueba-invierno-2025 | Q17 | NUM | Medium | ARG |
| 5 | prueba-invierno-2026 | Q50 | GEO | Medium | REP |
| 6 | prueba-invierno-2026 | Q48 | GEO | Medium | ARG |
| 7 | prueba-invierno-2026 | Q60 | PROB | Medium | ARG |
| 8 | prueba-invierno-2026 | Q63 | PROB | Medium | RES |

**Distribución:** 2 ALG, 2 NUM, 2 GEO, 2 PROB  
**Habilidades:** 2 RES, 1 MOD, 2 REP, 3 ARG

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

| # | Examen | ID | Eje | Dificultad | Habilidad |
|---|--------|-----|-----|------------|-----------|
| 1 | seleccion-regular-2026 | Q35 | ALG | Low | MOD |
| 2 | Prueba-invierno-2025 | Q32 | ALG | Low | RES |
| 3 | seleccion-regular-2026 | Q57 | ALG | Low | MOD |
| 4 | Prueba-invierno-2025 | Q12 | NUM | Low | RES |
| 5 | seleccion-regular-2025 | Q2 | NUM | Low | REP |
| 6 | prueba-invierno-2026 | Q22 | GEO | Low | RES |
| 7 | seleccion-regular-2026 | Q55 | PROB | Low | REP |
| 8 | seleccion-regular-2026 | Q56 | PROB | Low | RES |

**Distribución:** 3 ALG, 2 NUM, 1 GEO, 2 PROB  
**Habilidades:** 4 RES, 2 MOD, 2 REP, 0 ARG

---

## B2: Ruta Medio (8 preguntas)

Para estudiantes con 4-6 correctas en R1.

| # | Examen | ID | Eje | Dificultad | Habilidad |
|---|--------|-----|-----|------------|-----------|
| 1 | seleccion-regular-2026 | Q42 | ALG | Medium | REP |
| 2 | prueba-invierno-2026 | Q38 | ALG | Medium | REP |
| 3 | seleccion-regular-2025 | Q29 | ALG | Medium | RES |
| 4 | Prueba-invierno-2025 | Q1 | NUM | Medium | RES |
| 5 | seleccion-regular-2026 | Q13 | NUM | Medium | RES |
| 6 | Prueba-invierno-2025 | Q47 | GEO | Medium | ARG |
| 7 | prueba-invierno-2026 | Q58 | PROB | Medium | REP |
| 8 | Prueba-invierno-2025 | Q59 | PROB | Medium | ARG |

**Distribución:** 3 ALG, 2 NUM, 1 GEO, 2 PROB  
**Habilidades:** 3 RES, 0 MOD, 3 REP, 2 ARG

---

## C2: Ruta Alto (8 preguntas)

Para estudiantes con 7-8 correctas en R1.

| # | Examen | ID | Eje | Dificultad | Habilidad |
|---|--------|-----|-----|------------|-----------|
| 1 | seleccion-regular-2025 | Q6 | ALG | Medium | ARG |
| 2 | prueba-invierno-2026 | Q31 | ALG | Medium | MOD |
| 3 | seleccion-regular-2025 | Q32 | ALG | Medium | RES |
| 4 | Prueba-invierno-2025 | Q22 | NUM | Medium | MOD |
| 5 | prueba-invierno-2026 | Q23 | NUM | Medium | ARG |
| 6 | seleccion-regular-2026 | Q64 | GEO | Medium | RES |
| 7 | prueba-invierno-2026 | Q54 | PROB | Medium | REP |
| 8 | Prueba-invierno-2025 | Q14 | PROB | Medium | ARG |

**Distribución:** 3 ALG, 2 NUM, 1 GEO, 2 PROB  
**Habilidades:** 2 RES, 2 MOD, 1 REP, 3 ARG

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
| RES | 2 | 4 | 3 | 2 | **11** |
| MOD | 1 | 2 | 0 | 2 | **5** |
| REP | 2 | 2 | 3 | 1 | **8** |
| ARG | 3 | 0 | 2 | 3 | **8** |

### Por Dificultad (Total 32)

| Dificultad | R1 | A2 | B2 | C2 | Total |
|------------|----|----|----|----|-------|
| Low | 0 | 8 | 0 | 0 | **8** |
| Medium | 8 | 0 | 8 | 8 | **24** |
| High | 0 | 0 | 0 | 0 | **0** |

---

## Notas

> [!WARNING]
> No tenemos preguntas de dificultad High. La Ruta C usa Medium igual que B, limitando la discriminación en el extremo alto.

> [!TIP]
> Para mejorar la prueba en el futuro, crear 8-10 preguntas de dificultad High para reemplazar en Ruta C.

---

## Próximos Pasos

- [ ] Revisar y validar la selección manualmente
- [ ] Verificar que las preguntas seleccionadas no tienen problemas conocidos
- [ ] Implementar lógica de routing en el sistema
- [ ] Diseñar UI de presentación

---

## Rutas de Archivos

Las preguntas seleccionadas están en:

```
app/data/pruebas/finalizadas/<examen>/qti/<ID>/
├── question.xml
├── question.html
└── metadata_tags.json
```

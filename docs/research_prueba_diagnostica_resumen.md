# Prueba Diagnóstica PAES M1 - Resumen Ejecutivo

**Objetivo:** Predecir puntaje PAES M1 con la menor cantidad de preguntas posible.  
**Fecha:** 2026-01-06  
**Versión:** 2.0

---

## 1. Contexto

### La Prueba PAES M1 Real

| Parámetro | Valor |
|-----------|-------|
| Total preguntas | 65 |
| Duración | 2h 20min (140 min) |
| Escala de puntaje | 100-1000 |
| Ejes temáticos | Números, Álgebra, Geometría, Prob/Estadística |
| Habilidades | Resolver, Modelar, Representar, Argumentar |

### Nuestro Objetivo

Crear una prueba de **12-18 preguntas** (~30 min) que:
1. Prediga el puntaje PAES con correlación r ≥ 0.85
2. Diagnostique fortalezas/debilidades por eje y habilidad
3. Sea eficiente en tiempo de onboarding

---

## 2. Nuestro Banco de Preguntas

### Inventario

| Métrica | Valor |
|---------|-------|
| Preguntas taggeadas | **202** |
| Átomos en alcance M1 | **199** |
| Exámenes fuente | Selección Regular 2025, Invierno 2025, Selección Regular 2026 |

### Distribución por Dificultad

| Dificultad | Cantidad | % |
|------------|----------|---|
| Low | 85 | 42% |
| Medium | 117 | 58% |
| **High** | **0** | **0%** |

> ⚠️ **Limitación crítica:** No tenemos ítems High. Esto genera un techo de medición para alumnos de alto rendimiento.

### Distribución por Habilidad

| Habilidad | Código | Cantidad | % |
|-----------|--------|----------|---|
| Resolver problemas | RES | 99 | 49% |
| Modelar | MOD | 33 | 16% |
| Representar | REP | 28 | 14% |
| Argumentar | ARG | 27 | 13% |

### Distribución por Eje

| Eje | Preguntas | % PAES aproximado |
|-----|-----------|-------------------|
| Álgebra y Funciones | 152 | ~35% |
| Números | 110 | ~24% |
| Probabilidad y Estadística | 72 | ~22% |
| Geometría | 47 | ~19% |

---

## 3. Las 3 Opciones de Arquitectura

### Opción 1: Forma Fija (18 preguntas)

**Descripción:** Todos los alumnos responden las mismas 18 preguntas.

**Distribución sugerida:**

| Eje | Preguntas | Desglose |
|-----|-----------|----------|
| Álgebra | 6 | 2 Low + 4 Med |
| Números | 5 | 2 Low + 3 Med |
| Prob/Est | 4 | 1 Low + 3 Med |
| Geometría | 3 | 1 Low + 2 Med |
| **Total** | **18** | 6 Low + 12 Med |

**Ventajas:**
- ✅ Implementación inmediata (3-5 días)
- ✅ Sin lógica condicional
- ✅ Fácil de mantener y debuggear

**Limitaciones:**
- ❌ Menor precisión en extremos (muy alto/muy bajo)
- ❌ Algunas preguntas "desperdiciadas" para alumnos de nivel muy diferente
- ❌ Correlación más baja (r = 0.80-0.85)

---

### Opción 2: MST - Multistage Test (16 preguntas)

**Descripción:** Prueba en 2 etapas. La Etapa 1 determina qué módulo recibe el alumno en Etapa 2.

**Arquitectura:**

```
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 1: ROUTING (8 preguntas iguales para todos)          │
│  - 2 Álgebra, 2 Números, 2 Geometría, 2 Prob/Est            │
│  - Dificultad: 60% Medium, 40% Low                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
         Según puntaje Etapa 1 (0-3, 4-6, 7-8 correctas)
                              ↓
┌─────────────────┬─────────────────┬─────────────────────────┐
│  RUTA A (bajo)  │  RUTA B (medio) │  RUTA C (medio-alto)    │
│  8 preguntas    │  8 preguntas    │  8 preguntas            │
│  Low / Low-Med  │  Medium         │  Medium / Medium+       │
└─────────────────┴─────────────────┴─────────────────────────┘
```

**Mapping de Puntajes por Ruta:**

| Ruta | Correctas | Nivel | Puntaje | Rango |
|------|-----------|-------|---------|-------|
| A | 0-3 | Muy Inicial | 420 | 380-460 |
| A | 4-5 | Inicial | 470 | 440-500 |
| A | 6-7 | Inicial | 495 | 460-525 |
| B | 7-8 | Intermedio Bajo | 525 | 500-555 |
| B | 9-10 | Intermedio | 565 | 540-595 |
| B | 11-12 | Intermedio | 590 | 560-620 |
| B | 13 | Intermedio Alto | 620 | 595-650 |
| C | 12-13 | Intermedio Alto | 635 | 600-670 |
| C | 14 | Alto | 665 | 630-700 |
| C | 15 | Alto | 690 | 650-730 |
| C | 16 | Muy Alto | 715 | 670-760 |

**Ventajas:**
- ✅ Mejor precisión que Forma Fija (especialmente en extremos)
- ✅ 16 preguntas vs 18
- ✅ Control curricular explícito por ruta
- ✅ Experiencia personalizada sin complejidad de CAT

**Limitaciones:**
- ⚠️ Requiere seleccionar 32 preguntas (8 + 8×3)
- ⚠️ Implementar lógica de routing
- ⚠️ Tiempo: 1-2 semanas

---

### Opción 3: CAT - Computerized Adaptive Testing (12-18 preguntas)

**Descripción:** Cada pregunta se selecciona en tiempo real según respuestas anteriores.

**Blueprint CAT:**

| Eje | Mínimo | Máximo |
|-----|--------|--------|
| ALG | 4 | 6 |
| NUM | 3 | 5 |
| GEO | 2 | 4 |
| PROB | 3 | 5 |

**Algoritmo (heurístico sin IRT):**

1. Empezar con pregunta de dificultad media
2. Por cada respuesta:
   - Si correcta: θ += step (aumentar habilidad estimada)
   - Si incorrecta: θ -= step
   - step *= 0.85 (decae con cada pregunta)
3. Seleccionar siguiente pregunta:
   - Que mejor mida θ actual
   - Penalizar ejes ya cubiertos
   - Prohibir ejes sobre su máximo
4. Terminar cuando:
   - N ≥ 12 Y θ estable Y mínimos cumplidos
   - O N == 18 (hard stop)

**Mapping θ → PAES:**

| Rango θ | Nivel | Puntaje | Rango |
|---------|-------|---------|-------|
| ≤ -1.0 | Muy Inicial | 420 | 380-460 |
| -1.0 a -0.5 | Inicial | 470 | 440-500 |
| -0.5 a 0.0 | Intermedio Bajo | 525 | 500-555 |
| 0.0 a 0.5 | Intermedio | 585 | 560-620 |
| 0.5 a 0.9 | Intermedio Alto | 635 | 600-670 |
| 0.9 a 1.2 | Alto | 690 | 650-730 |
| > 1.2 | Muy Alto | 715 | 670-760 |

**Ventajas:**
- ✅ Máxima eficiencia (menos preguntas para igual precisión)
- ✅ Excelente precisión en todos los niveles
- ✅ Experiencia rápida (~15-20 min)

**Limitaciones:**
- ❌ Sin IRT real, es similar en complejidad a MST
- ❌ Control curricular requiere penalizaciones complejas
- ❌ Mayor riesgo de sesgo con banco imperfecto
- ❌ Sin ítems High, el beneficio se reduce
- ❌ Tiempo: 2-3 semanas

---

## 4. Comparativa Completa

| Criterio | Forma Fija | MST | CAT |
|----------|------------|-----|-----|
| **Preguntas al alumno** | 18 | 16 | 12-18 |
| **Preguntas a seleccionar** | 18 | 32 | Todo banco |
| **Correlación esperada (r)** | 0.80-0.85 | 0.82-0.87 | 0.85-0.90 |
| **Error estándar (SEE)** | ±60-70 pts | ±55-65 pts | ±50-60 pts |
| **Precisión extremos** | Limitada | Mejorada | Excelente |
| **Control curricular** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Complejidad técnica** | Baja | Media | Alta |
| **Tiempo implementación** | 3-5 días | 1-2 semanas | 2-3 semanas |
| **Requiere IRT** | No | No | Ideal sí |

---

## 5. Tratamiento del Azar (Guessing)

- **Probabilidad de acertar al azar:** 25% (4 opciones)
- **Penalización:** No (igual que PAES real)

**Cómo se mitiga en cada opción:**

| Tipo | Tratamiento |
|------|-------------|
| Forma Fija | 18 preguntas diluyen impacto estadísticamente |
| MST | 8 preguntas de routing reducen error de clasificación |
| CAT | Algoritmo ajusta θ; aciertos al azar se "limpian" después |

---

## 6. Diagnóstico por Átomo (Nuevo)

### El Problema
La predicción del puntaje global maneja bien el azar, pero ¿cómo marcamos átomos individuales? Con 25% de chance de acertar al azar, algunos aciertos pueden ser falsos.

### Solución: Enfoque Conservador + Botón "No lo sé"

**Principio:** El costo de enseñar algo ya sabido es **bajo**. El costo de no enseñar algo necesario es **alto**. Si hay duda → enseñar.

**Feature recomendada:** Botón "No lo sé" en lugar de forzar una respuesta.

### Sistema de 3 Estados por Átomo

| Resultado | Estado | Acción en plan de estudio |
|-----------|--------|---------------------------|
| ✅ Correcto | `dominado` | No incluir |
| ❓ "No lo sé" | `gap` | Enseñar desde cero |
| ❌ Incorrecto | `misconception` | Corregir + enseñar |

**Valor:** Permite instrucción diferenciada: no es lo mismo enseñar algo nuevo que corregir algo mal aprendido.

---

## 7. Requisitos para Lanzar

### Forma Fija
- [ ] Seleccionar 18 preguntas según blueprint
- [ ] Implementar lógica de scoring ponderado
- [ ] UI de prueba (1 pregunta/pantalla, timer)
- **Tiempo:** 3-5 días

### MST
- [ ] Seleccionar 32 preguntas (8 routing + 8×3 rutas)
- [ ] Implementar routing (cortes 0-3/4-6/7-8)
- [ ] UI con transición entre etapas
- **Tiempo:** 1-2 semanas

### CAT
- [x] Banco etiquetado (202 preguntas con eje/habilidad/dificultad)
- [ ] Motor de selección adaptativa
- [ ] Sistema de penalización por cuotas
- [ ] Control de exposición
- **Tiempo:** 2-3 semanas

---

## 8. Validación Futura

### Fase 1: Pilotaje (N = 30-50 alumnos)
- Verificar inteligibilidad
- α Cronbach ≥ 0.80

### Fase 2: Calibración (N > 200 alumnos)
- Dificultad (p-value): 0.30-0.70
- Discriminación (DI): ≥ 0.30
- Correlación ítem-total: > 0.15

### Fase 3: Equiparación (Post-PAES real)
- Regresión: diagnóstica → PAES
- Ajustar tablas de conversión
- Estrechar rangos de error

---

## 9. Niveles de Competencia

| Nivel | Código | Rango PAES | Descripción |
|-------|--------|------------|-------------|
| Inicial | CM0 | < 450 | Manejo parcial de básicos |
| Básico | CM1A | 450-550 | Básicos con errores |
| Intermedio | CM1B | 550-650 | Buen dominio M1 |
| Avanzado | CM2 | 650-750 | Dominio sólido |
| Superior | CM3 | 750+ | Alto desempeño |

---

## 10. Output al Alumno

### Resultado Principal
```
Puntaje estimado: 620 - 680 puntos
Nivel: Intermedio Alto
```

### Diagnóstico por Eje
```
Números:      ████████████░░░░  75% ✓
Álgebra:      ██████████░░░░░░  62%
Geometría:    ████████░░░░░░░░  50% ⚠️
Prob/Est:     ████████████████  100% ⭐

⚠️ Reforzar: Geometría
```

### Diagnóstico por Habilidad
```
Resolver:     ██████████████░░  87% ✓
Representar:  ████████████░░░░  75% ✓
Modelar:      ██████░░░░░░░░░░  40% ⚠️
Argumentar:   ████████░░░░░░░░  50%

💡 Trabaja más ejercicios de modelación
```

---

## 11. Camino de Migración Recomendado

```
Fase 1: MST (16 ítems)
    ↓ Recolectar datos (2-3 meses)
Fase 2: Calibrar IRT (parámetros a, b, c)
    ↓ Crear ítems High (20-40 nuevos)
Fase 3: CAT completo (10-12 ítems)
```

---

## 12. Decisión Final

| Si tu prioridad es... | Elige | Preguntas | Tiempo |
|----------------------|-------|-----------|--------|
| Lanzar YA | Forma Fija | 18 | 3-5 días |
| **Mejor balance calidad/esfuerzo** | **MST** | **16** | **1-2 semanas** |
| Mínimas preguntas posible | CAT | 12-18 | 2-3 semanas |

---

*Documento completo: [research_prueba_diagnostica.md](./research_prueba_diagnostica.md)*

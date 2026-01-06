# Research Profundo: Prueba Diagnóstica PAES M1

**Fecha:** 2025-12-29  
**Versión:** 2.0 (Research Profundo)

---

## 1. Contexto y Objetivo

### 1.1 Prueba PAES M1 Real
| Parámetro | Valor |
|-----------|-------|
| Total preguntas | 65 |
| Duración | 2h 20min (140 min) |
| Tiempo/pregunta | ~2.15 min |
| Escala de puntaje | 100-1000 |

### 1.2 Objetivo de la Prueba Diagnóstica
Crear una prueba corta que:
1. **Prediga** el puntaje PAES con r ≥ 0.85
2. **Diagnostique** fortalezas/debilidades por eje
3. **Minimice** el tiempo de onboarding (~30 min)

---

## 2. Nuestro Banco de Preguntas

### 2.1 Inventario Actual

| Métrica | Valor |
|---------|-------|
| Preguntas taggeadas | **202** |
| Átomos en alcance M1 | **199** |
| Dificultad Low | 85 (42%) |
| Dificultad Medium | 117 (58%) |
| Dificultad High | 0 (0%) |

### 2.2 Distribución por Habilidad PAES

| Habilidad | Código | Cantidad | % |
|-----------|--------|----------|---|
| Resolver problemas | **RES** | 99 | 49% |
| Modelar | **MOD** | 33 | 16% |
| Representar | **REP** | 28 | 14% |
| Argumentar | **ARG** | 27 | 13% |

> [!NOTE]
> RES domina porque la PAES M1 prioriza aplicación de procedimientos. Las 4 habilidades están representadas.

### 2.3 Distribución por Eje

| Eje | Preguntas (átomos) | % Real PAES* |
|-----|-------------------|--------------|
| Álgebra y Funciones | 152 | ~35% |
| Números | 110 | ~24% |
| Probabilidad y Estadística | 72 | ~22% |
| Geometría | 47 | ~19% |

*Proporción aproximada basada en temario oficial.

### 2.4 Matriz Eje × Dificultad

|  | Low | Medium |
|--|-----|--------|
| **Números** | 48 | 62 |
| **Álgebra** | 68 | 84 |
| **Geometría** | 8 | 39 |
| **Prob/Est** | 24 | 48 |

> [!NOTE]
> Geometría tiene pocas preguntas fáciles (8). La prueba diagnóstica debe considerar esto.

---

## 3. Fundamentos Psicométricos

### 3.1 Discriminación de Ítems

La **correlación point-biserial** mide qué tan bien un ítem diferencia entre estudiantes de alto y bajo rendimiento:

| rpbi | Interpretación |
|------|---------------|
| ≥ 0.40 | Excelente discriminación |
| 0.30-0.39 | Buena discriminación |
| 0.20-0.29 | Aceptable |
| < 0.20 | Pobre, considerar eliminar |
| < 0 | Problemático, eliminar |

**Para nuestra prueba diagnóstica:** Seleccionar ítems con dificultad entre 0.30-0.70 (no muy fáciles ni muy difíciles) que maximicen discriminación.

### 3.2 Ejemplos de Screening Tests Exitosos

| Instrumento | Full Test | Short Form | Proporción | Validez |
|-------------|----------|------------|------------|---------|
| AQ (Autism) | 50 items | 10 items | 20% | r = 0.95 |
| ASRS (ADHD) | 18 items | 6 items | 33% | Sens=90% |
| DAST (Drugs) | 28 items | 10 items | 36% | α = 0.86 |
| EPDS (Depression) | 10 items | 2-5 items | 20-50% | Válido |

**Conclusión:** Una proporción de **20-30% de ítems** puede mantener validez excelente.

### 3.3 Aplicación a PAES M1

| | PAES Real | Diagnóstica Propuesta |
|--|-----------|----------------------|
| Preguntas | 65 | **18** (28%) |
| Tiempo | 140 min | **~40 min** |
| Correlación esperada | — | r ≈ 0.85-0.88 |

---

## 4. Modelo de Predicción de Puntaje

### 4.1 Enfoque: Regresión Lineal Ponderada

El puntaje predicho se calcula mediante:

```
Puntaje_predicho = α + β × (Score_diagnóstica_ponderado)
```

Donde:
- **α** = intercepto (puntaje base)
- **β** = pendiente (factor de escalamiento)
- **Score_diagnóstica_ponderado** = Σ(correctas × peso_dificultad)

### 4.2 Pesos por Dificultad

| Dificultad | Peso | Justificación |
|------------|------|---------------|
| Low | 1.0 | Pregunta base |
| Medium | 1.8 | Mayor valor informativo |
| High | 2.5 | (No tenemos, pero reservar) |

### 4.3 Cálculo del Score Ponderado

```python
def calcular_score_ponderado(respuestas, preguntas):
    """
    respuestas: dict {pregunta_id: True/False}
    preguntas: list con metadata de cada pregunta
    """
    score = 0
    max_score = 0
    
    pesos = {"Low": 1.0, "Medium": 1.8, "High": 2.5}
    
    for p in preguntas:
        peso = pesos[p["difficulty"]]
        max_score += peso
        if respuestas.get(p["id"]):
            score += peso
    
    return score / max_score  # Normalizado 0-1
```

### 4.4 Transformación a Escala PAES

```python
def score_a_paes(score_normalizado):
    """
    Transforma score 0-1 a escala PAES 100-1000
    
    Supuestos iniciales (calibrar con datos reales):
    - Score 0.20 ≈ 350 PAES (percentil bajo)
    - Score 0.50 ≈ 550 PAES (promedio)
    - Score 0.80 ≈ 750 PAES (percentil alto)
    """
    # Regresión lineal simple
    # PAES = 100 + 800 × score
    paes = 100 + 800 * score_normalizado
    
    # Limitar a rango válido
    return max(100, min(1000, round(paes)))
```

### 4.5 Error Estándar de Estimación

Basado en la literatura, con r = 0.85:

$$SEE = SD_{PAES} × \sqrt{1 - r^2}$$

Con SD_PAES ≈ 110 puntos y r = 0.85:
$$SEE = 110 × \sqrt{1 - 0.72} = 110 × 0.53 ≈ 58 \text{ puntos}$$

**Resultado:** El puntaje predicho tiene un error de ±58 puntos (1 desviación estándar).

---

## 5. Arquitecturas de Prueba: 3 Opciones

> [!IMPORTANT]
> Se presentan 3 modelos de arquitectura, ordenados de menor a mayor complejidad técnica. Cada uno tiene trade-offs específicos.

---

### 5.1 Comparativa Rápida

| Criterio | Opción 1: Forma Fija | Opción 2: MST | Opción 3: CAT |
|----------|---------------------|---------------|---------------|
| **Preguntas al alumno** | 18 fijas | 16 (8+8 adaptadas) | 10-15 variables |
| **Preguntas a seleccionar** | 18 | 32 | Todo el banco |
| **Complejidad técnica** | Baja | Media | Alta |
| **Precisión teórica** | Buena | Mejor | Óptima |
| **Precisión en extremos** | Limitada | Mejorada | Excelente |
| **Requiere calibración IRT** | No | No (inicial) | Sí |
| **Lógica de enrutamiento** | No | Sí (simple) | Sí (compleja) |
| **Tiempo implementación** | Días | 1-2 semanas | Meses |

---

### 5.2 Opción 1: Forma Fija (18 preguntas)

**Descripción:** Todos los alumnos responden las mismas 18 preguntas, seleccionadas para cubrir proporcionalmente los 4 ejes temáticos.

**Distribución por Eje:**

| Eje | % PAES | Preguntas | Desglose |
|-----|--------|-----------|----------|
| Álgebra y Funciones | 35% | **6** | 2 Low + 4 Med |
| Números | 24% | **5** | 2 Low + 3 Med |
| Probabilidad y Estadística | 22% | **4** | 1 Low + 3 Med |
| Geometría | 19% | **3** | 1 Low + 2 Med |
| **Total** | 100% | **18** | 6 Low + 12 Med |

**Criterios de Selección:**
1. Cubrir átomos "núcleo" (alta frecuencia, muchos prerrequisitos)
2. Tener validez diagnóstica (identifican déficits específicos)
3. Evitar dependencia visual compleja (facilita UI mobile)
4. No ser redundantes (máximo 1 pregunta por átomo)

**Ventajas:**
- ✅ Implementación inmediata
- ✅ Sin lógica condicional
- ✅ Fácil de mantener

**Limitaciones:**
- ⚠️ Menor precisión en extremos (muy alto/muy bajo)
- ⚠️ Algunas preguntas "desperdiciadas" para alumnos de nivel muy diferente

---

### 5.3 Opción 2: MST - Multistage Test (16 preguntas)

**Descripción:** Prueba en 2 etapas. La Etapa 1 (8 preguntas) determina qué módulo de Etapa 2 recibe el alumno.

```
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 1: ROUTING (8 preguntas iguales para todos)          │
│  - 2 Álgebra, 2 Números, 2 Geometría, 2 Prob/Est           │
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

**Distribución por Módulo:**

| Módulo | ALG | NUM | GEO | PROB | Total |
|--------|-----|-----|-----|------|-------|
| R1 (Routing) | 2 | 2 | 2 | 2 | 8 |
| A2/B2/C2 (Etapa 2) | 3 | 2 | 1 | 2 | 8 |
| **Total por alumno** | 5 | 4 | 3 | 4 | **16** |

**Regla de Enrutamiento:**
- 0-3 correctas en R1 → Ruta A (bajo)
- 4-6 correctas en R1 → Ruta B (medio)
- 7-8 correctas en R1 → Ruta C (alto)

**Ventajas:**
- ✅ Mejor precisión que forma fija (especialmente en extremos)
- ✅ 16 preguntas vs 18 (experiencia más corta)
- ✅ Experiencia personalizada sin complejidad de CAT

**Limitaciones:**
- ⚠️ Requiere 32 preguntas seleccionadas (8 + 8×3)
- ⚠️ Lógica de enrutamiento a implementar
- ⚠️ Requiere taggear habilidades (RES/MOD/REP/ARG) en preguntas

**Blueprint JSON (arquitectura):**
```json
{
  "test_id": "paes_m1_mst16_diagnostic",
  "total_items": 16,
  "structure": {
    "stage_1": {
      "module_id": "R1",
      "num_items": 8,
      "axes_distribution": {"ALG": 2, "NUM": 2, "GEO": 2, "PROB": 2}
    },
    "stage_2": {
      "modules": [
        {"module_id": "A2", "route": "low", "num_items": 8},
        {"module_id": "B2", "route": "medium", "num_items": 8},
        {"module_id": "C2", "route": "high", "num_items": 8}
      ]
    }
  },
  "routing_rule": {
    "cuts": {"low": "0-3", "medium": "4-6", "high": "7-8"}
  }
}
```

#### Mapping de Puntajes PAES por Ruta (MST)

> [!IMPORTANT]
> Este mapping es **provisional**. Se calibrará con datos reales post-PAES.

**Niveles Pedagógicos:**

| Nivel | Descripción | Rango PAES |
|-------|-------------|------------|
| Muy Inicial | Manejo parcial de contenidos básicos | < 450 |
| Inicial | Contenidos básicos con errores frecuentes | 450 – 500 |
| Intermedio Bajo | Resuelve lo esencial, falla en integración | 500 – 550 |
| Intermedio | Buen dominio de M1 | 550 – 600 |
| Intermedio Alto | Dominio sólido y consistente | 600 – 650 |
| Alto | Alto desempeño dentro de M1 | 650 – 700 |
| Muy Alto | Tope del banco actual | 700+ (con cautela) |

**Ruta A (desempeño bajo):**

| Correctas /16 | Nivel | Puntaje Estimado | Rango |
|---------------|-------|------------------|-------|
| 0–3 | Muy Inicial | 420 | 380–460 |
| 4–5 | Inicial | 470 | 440–500 |
| 6–7 | Inicial | 495 | 460–525 |

**Ruta B (desempeño medio) — Zona de máxima precisión:**

| Correctas /16 | Nivel | Puntaje Estimado | Rango |
|---------------|-------|------------------|-------|
| 7–8 | Intermedio Bajo | 525 | 500–555 |
| 9–10 | Intermedio | 565 | 540–595 |
| 11–12 | Intermedio | 590 | 560–620 |
| 13 | Intermedio Alto | 620 | 595–650 |

**Ruta C (desempeño medio-alto) — Mayor incertidumbre por falta de ítems High:**

| Correctas /16 | Nivel | Puntaje Estimado | Rango |
|---------------|-------|------------------|-------|
| 12–13 | Intermedio Alto | 635 | 600–670 |
| 14 | Alto | 665 | 630–700 |
| 15 | Alto | 690 | 650–730 |
| 16 | Muy Alto* | 715 | 670–760 |

*"Muy Alto" debe comunicarse con disclaimer: "Tu nivel es alto dentro del contenido evaluado. El rango puede ajustarse cuando trabajes contenidos avanzados."

---

### 5.4 Opción 3: CAT - Computerized Adaptive Testing

**Descripción:** Cada pregunta se selecciona en tiempo real según las respuestas anteriores. El test termina cuando se alcanza precisión suficiente.

```
┌─────────────────────────────────────────────────────────────┐
│  Pregunta 1 → Respuesta → Estimar θ₁                        │
│       ↓                                                      │
│  Seleccionar pregunta óptima para θ₁                        │
│       ↓                                                      │
│  Pregunta 2 → Respuesta → Estimar θ₂                        │
│       ↓                                                      │
│  ... (repetir hasta SEM < 0.30 o máximo 18 preguntas)       │
└─────────────────────────────────────────────────────────────┘
```

#### ¿Por qué CAT es la opción más corta?

CAT puede lograr con **10-15 ítems** lo que una prueba fija necesita con 25-40:
- Cada ítem aporta **máxima información** cerca del θ estimado
- No "desperdicia" preguntas demasiado fáciles o difíciles
- Se detiene cuando **ya sabe lo suficiente**

#### El problema: CAT sin control ignora el currículum

Sin restricciones, CAT puede hacer 7 ítems de álgebra, 0 de geometría, y aún estimar θ bien. Eso es válido psicométricamente pero **inaceptable para PAES**.

**Solución: Penalización por cuotas**

En cada paso, el CAT penaliza ítems de ejes que ya cumplieron su cuota:
- Si ya tenemos 4 de ALG y el mínimo es 4 → penalizar más ALG
- Si ya tenemos 6 de ALG y el máximo es 6 → prohibir más ALG

#### Blueprint CAT (12-18 ítems)

**Mínimos por eje (para 12 ítems):**

| Eje | Mínimo |
|-----|--------|
| ALG | 4 |
| NUM | 3 |
| GEO | 2 |
| PROB | 3 |
| **Total** | **12** |

**Máximos (hard caps para 18 ítems):**

| Eje | Máximo |
|-----|--------|
| ALG | 6 |
| NUM | 5 |
| GEO | 4 |
| PROB | 5 |

**Mínimos por habilidad:**

| Habilidad | Mínimo |
|-----------|--------|
| REP | 2 |
| MOD | 2 |
| ARG | 1 |
| RES | (resto) |

#### Algoritmo CAT Heurístico (sin IRT)

Mientras no tengamos parámetros IRT calibrados, usamos un enfoque heurístico:

```python
# Estado interno
θ_est = 0.0      # Habilidad estimada (inicia en medio)
step = 0.6       # Tamaño de ajuste
decay = 0.85     # Factor de decaimiento

# Loop principal
while N < max_items and not stable:
    # 1. Filtrar candidatos válidos
    candidates = filter(
        exclude=used_items,
        exclude=forbidden_atoms,
        exclude=axis_over_cap
    )
    
    # 2. Calcular score base (match de dificultad)
    for item in candidates:
        item.score = difficulty_match(θ_est, item.difficulty)
    
    # 3. Aplicar penalizaciones
    for item in candidates:
        if axis_count[item.axis] >= blueprint_min:
            item.score -= 0.3  # Penalización suave
        if skill_count[item.skill] >= soft_cap:
            item.score -= 0.25
    
    # 4. Seleccionar (con randomización)
    selected = random_from_top_k(candidates, k=5)
    
    # 5. Actualizar θ
    if correct:
        θ_est += step
    else:
        θ_est -= step
    step *= decay  # Decaer step
```

#### Regla de término

El CAT se detiene cuando:
1. `N >= 12` Y estabilidad (θ cambia < 0.15 en últimas 4 preguntas) Y mínimos cumplidos
2. O `N == 18` (hard stop)

#### Mapping θ → Puntaje PAES (CAT)

| Rango θ | Nivel | Puntaje Estimado | Rango |
|---------|-------|------------------|-------|
| ≤ -1.0 | Muy Inicial | 420 | 380–460 |
| -1.0 a -0.5 | Inicial | 470 | 440–500 |
| -0.5 a 0.0 | Intermedio Bajo | 525 | 500–555 |
| 0.0 a 0.5 | Intermedio | 585 | 560–620 |
| 0.5 a 0.9 | Intermedio Alto | 635 | 600–670 |
| 0.9 a 1.2 | Alto | 690 | 650–730 |
| > 1.2 | Muy Alto* | 715 | 670–760 |

#### Comparación CAT vs MST (honesta)

| Criterio | CAT | MST |
|----------|-----|-----|
| Largo mínimo | ⭐⭐⭐⭐⭐ (10-12) | ⭐⭐⭐⭐ (16) |
| Precisión | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Control curricular | ⭐⭐ (requiere penalizaciones) | ⭐⭐⭐⭐ (explícito) |
| Facilidad de implementación | ⭐⭐ | ⭐⭐⭐⭐ |
| Robustez con banco imperfecto | ⭐⭐ | ⭐⭐⭐⭐ |
| Requiere IRT calibrado | Sí (ideal) / Heurístico (MVP) | No |

> [!WARNING]
> **Conclusión:** CAT es superior **cuando el banco está maduro**. MST es superior **cuando estás construyendo el sistema**.

**Ventajas CAT:**
- ✅ Máxima eficiencia (menos preguntas, igual precisión)
- ✅ Excelente precisión en todos los niveles
- ✅ Experiencia rápida (~15-20 min)

**Limitaciones CAT:**
- ⚠️ Sin IRT, el "CAT heurístico" es similar en complejidad a MST
- ⚠️ Control curricular requiere penalizaciones complejas
- ⚠️ Mayor riesgo de sesgo con banco imperfecto
- ⚠️ Sin ítems High, techo de medición igual que MST

**Estado:** 🔶 Viable como alternativa a MST, pero con trade-offs. Considerar si se prioriza menos preguntas sobre control curricular.

#### Camino de migración recomendado

```
Fase 1: MST (16 ítems)
    ↓ Recolectar datos
Fase 2: Calibrar IRT (parámetros a, b, c)
    ↓ Crear ítems High
Fase 3: CAT completo (10-12 ítems)
```

---

### 5.5 Recomendación

| Escenario | Opción Recomendada |
|-----------|-------------------|
| MVP inmediato (1-2 semanas) | **Opción 1: Forma Fija** |
| V2 con más tiempo (1 mes) | **Opción 2: MST** |
| Largo plazo con datos | **Opción 3: CAT** |

> [!NOTE]
> Las 3 opciones son **incrementales**: se puede empezar con Forma Fija, migrar a MST cuando se tenga más tiempo, y eventualmente a CAT cuando se tengan datos de calibración.

---

## 5.6 Átomos Prioritarios por Eje (Aplica a Opciones 1 y 2)

#### Números (4-5 preguntas)
| Prioridad | Átomo | Justificación |
|-----------|-------|---------------|
| 1 | NUM-01-25 | Resolución de problemas (integrador) |
| 2 | NUM-02-11 | Porcentajes contextualizados |
| 3 | NUM-03-17 | Potencias y raíces en contexto |
| 4 | NUM-01-09 | Problemas con enteros |
| 5 | NUM-02-06 | Cálculo directo de porcentaje |

#### Álgebra y Funciones (5-6 preguntas)
| Prioridad | Átomo | Justificación |
|-----------|-------|---------------|
| 1 | ALG-03-06 | Problemas con ecuaciones lineales |
| 2 | ALG-05-11 | Modelos lineales y afines |
| 3 | ALG-02-06 | Proporcionalidad directa |
| 4 | ALG-04-08 | Sistemas 2x2 en contexto |
| 5 | ALG-01-17 | Modelado geométrico algebraico |
| 6 | ALG-06-11 | Función cuadrática |

#### Geometría (3 preguntas)
| Prioridad | Átomo | Justificación |
|-----------|-------|---------------|
| 1 | GEO-01-13 | Problemas integrados (perímetro/área) |
| 2 | GEO-02-15 | Volumen en contexto |
| 3 | GEO-03-13 | Isometrías (transformaciones) |

#### Probabilidad y Estadística (4 preguntas)
| Prioridad | Átomo | Justificación |
|-----------|-------|---------------|
| 1 | PROB-01-18 | Evaluación de afirmaciones (gráficos) |
| 2 | PROB-02-11 | Comparación con medidas centrales |
| 3 | PROB-04-02 | Cálculo de probabilidad |
| 4 | PROB-01-15 | Promedio aritmético |

---

## 6. Output para el Alumno

### 6.1 Resultado Principal

```
┌──────────────────────────────────────────────────────┐
│           TU PUNTAJE ESTIMADO PAES M1                │
├──────────────────────────────────────────────────────┤
│                                                      │
│               620 - 680 puntos                       │
│                                                      │
│   Rango probable basado en tu desempeño             │
│   en la prueba diagnóstica                          │
└──────────────────────────────────────────────────────┘
```

### 6.2 Diagnóstico por Eje

```
┌─────────────────────────────────────────────────────┐
│              FORTALEZAS Y DEBILIDADES               │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Números            ████████████░░░░  75% ✓         │
│  Álgebra            ██████████░░░░░░  62%           │
│  Geometría          ████████░░░░░░░░  50% ⚠️        │
│  Prob/Estadística   ████████████████  100% ⭐       │
│                                                     │
│  ⚠️ Recomendamos reforzar: Geometría                │
└─────────────────────────────────────────────────────┘
```

### 6.3 Diagnóstico por Habilidad

```
┌─────────────────────────────────────────────────────┐
│               HABILIDADES PAES M1                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Resolver problemas   ██████████████░░  87% ✓       │
│  Representar          ████████████░░░░  75% ✓       │
│  Modelar              ██████░░░░░░░░░░  40% ⚠️      │
│  Argumentar           ████████░░░░░░░░  50%         │
│                                                     │
│  💡 Trabaja más ejercicios de modelación:           │
│     plantear ecuaciones desde contextos reales      │
└─────────────────────────────────────────────────────┘
```

> [!TIP]
> El diagnóstico por habilidad permite dar recomendaciones más específicas: "Practica plantear ecuaciones desde contextos reales" vs solo "refuerza Álgebra".

### 6.4 Comunicación de Incertidumbre

> "Este es un **estimado** basado en 18 preguntas representativas. Tu puntaje real puede variar ±60 puntos. A medida que practiques más, afinaremos tu predicción."

### 6.5 Diagnóstico por Átomo (Datos Internos)

Además del puntaje y diagnóstico por eje, el sistema debe **registrar internamente** qué átomos domina el alumno y cuáles no. Esto permite:

1. **Planes de estudio personalizados**: Priorizar contenido donde el alumno falló
2. **Seguimiento de progreso**: Medir mejora átomo por átomo
3. **Recomendaciones inteligentes**: "Debes reforzar: Ecuaciones Lineales"

**Estructura de datos sugerida:**

```python
{
    "alumno_id": "abc123",
    "fecha_diagnostico": "2026-01-06",
    "puntaje_predicho": {"min": 620, "max": 680},
    "atomos": {
        "A-M1-NUM-01-25": {"correcto": True, "dominio": "alto"},
        "A-M1-ALG-03-06": {"correcto": False, "dominio": "bajo"},
        "A-M1-GEO-01-13": {"correcto": True, "dominio": "alto"},
        # ... más átomos
    },
    "ejes": {
        "numeros": {"correctas": 4, "total": 5, "porcentaje": 80},
        "algebra_y_funciones": {"correctas": 3, "total": 6, "porcentaje": 50},
        # ...
    },
    "recomendaciones": [
        "Reforzar: Ecuaciones Lineales (ALG-03)",
        "Reforzar: Función Cuadrática (ALG-06)"
    ]
}
```

> [!IMPORTANT]
> Este diagnóstico por átomo es la base para ofrecer **aprendizaje adaptativo** en el futuro.

---

## 7. Validación y Calibración Futura

### 7.1 Fase Piloto (Sin datos)
- Usar fórmulas teóricas (Spearman-Brown, regresión estimada)
- Comunicar al alumno que es "predicción preliminar"

### 7.2 Post-PAES Real
- Recolectar puntajes PAES reales de usuarios
- Calcular correlación empírica
- Ajustar coeficientes α, β
- Actualizar pesos de dificultad

### 7.3 Métricas de Éxito

| Métrica | Objetivo Mínimo | Objetivo Ideal |
|---------|-----------------|----------------|
| Correlación r | 0.80 | 0.90 |
| Error medio | < 80 pts | < 50 pts |
| Tiempo promedio | < 45 min | 30 min |

---

## 8. Próximos Pasos

1. **[INMEDIATO]** Seleccionar las 18 preguntas específicas del banco
2. **[CORTO PLAZO]** Implementar lógica de cálculo de puntaje y almacenamiento de diagnóstico por átomo
3. **[MEDIANO PLAZO]** Diseñar UI de prueba diagnóstica
4. **[LARGO PLAZO]** Validar con datos reales post-PAES

---

## 9. Roadmap de Mejoras Futuras

> [!NOTE]
> Las siguientes mejoras no son prioritarias para la versión inicial, pero deben considerarse para iteraciones futuras.

### 9.1 Tests Adaptativos Computarizados (CAT)

**¿Qué es?**  
En lugar de 18 preguntas fijas, cada alumno recibe preguntas personalizadas en tiempo real según sus respuestas.

**Beneficios potenciales:**
- Reducir de 18 a ~10-12 preguntas manteniendo precisión
- Mejor experiencia de usuario (menos frustración)
- Mayor precisión en extremos (muy alto/muy bajo rendimiento)

**Requisitos para implementar:**
- Motor de cálculo TRI en tiempo real
- Banco de ítems calibrado con parámetros a, b, c
- Datos de respuestas de ~500+ alumnos por ítem

**Estado:** ❌ No prioritario. Considerar cuando tengamos datos suficientes.

---

### 9.2 Actualización de Contenidos por Cambios Curriculares

**Contexto:**  
El DEMRE actualiza periódicamente el temario PAES. Algunos contenidos que hoy incluimos podrían salir del temario oficial en procesos futuros.

**Cambios conocidos (2025-2026):**
- Cilindros: Posible eliminación, foco en paralelepípedos y cubos
- Mediana, moda, rango: Integrados en representación de datos, no como unidades independientes

**Decisión actual:**  
Mantener estos contenidos en el banco (mejor que sobre a que falte). Marcar con flag `revision_futura: true` para facilitar ajustes posteriores.

**Acción futura:**  
Antes de cada proceso de admisión, revisar temario oficial y desactivar átomos obsoletos.

**Estado:** 🔶 Documentado, no activo. Revisar anualmente.

---

## Apéndice: Fórmulas Clave

### A.1 Regresión Lineal Simple
```
ŷ = α + βx

donde:
  β = Σ(xᵢ - x̄)(yᵢ - ȳ) / Σ(xᵢ - x̄)²
  α = ȳ - βx̄
```

### A.2 Error Estándar de Estimación
```
SEE = √(Σ(yᵢ - ŷᵢ)² / (n - 2))
```

### A.3 Intervalo de Confianza del Puntaje
```
IC₉₅% = ŷ ± 1.96 × SEE
       ≈ Puntaje ± 114 puntos (95% confianza)
```

### A.4 Spearman-Brown (Referencia)
```
r_nuevo = (n × r_viejo) / (1 + (n-1) × r_viejo)

Para n = 0.28 (18/65 preguntas), r_viejo = 0.90:
r_nuevo = (0.28 × 0.90) / (1 + (0.28-1) × 0.90)
        = 0.252 / 0.352
        ≈ 0.72 (solo Spearman-Brown)

Pero con selección optimizada: r_efectivo ≈ 0.85
```

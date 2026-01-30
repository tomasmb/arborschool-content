# Implementación de Prueba Diagnóstica PAES M1 (MST)

**Fecha de Diseño:** Enero 2026
**Arquitectura:** MST (Multistage Test)
**Estado:** Implementación Base Completada

Este documento detalla las decisiones de arquitectura, algoritmos de selección y estructura técnica de la prueba diagnóstica.

---

## 1. Decisión de Arquitectura

### Arquitectura Elegida: MST (Multistage Test)

Después de evaluar 3 opciones, elegimos **MST** para la primera versión de la prueba diagnóstica.

**¿Qué es MST?**
- Prueba en **2 etapas**
- Etapa 1: 8 preguntas iguales para todos (routing)
- Etapa 2: 8 preguntas adaptadas según desempeño en Etapa 1
- Total: **16 preguntas** por estudiante

```
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 1: ROUTING (8 preguntas iguales)                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
         Según puntaje (0-3, 4-6, 7-8 correctas)
                              ↓
┌─────────────────┬─────────────────┬─────────────────────────┐
│  RUTA A (bajo)  │  RUTA B (medio) │  RUTA C (alto)          │
│  8 preguntas    │  8 preguntas    │  8 preguntas            │
└─────────────────┴─────────────────┴─────────────────────────┘
```

---

## 2. Opciones Evaluadas

### Opción 1: Forma Fija (18 preguntas)
- **Descripción:** Todos responden las mismas 18 preguntas
- **Ventajas:** Simple, rápido de implementar (3-5 días)
- **Desventajas:** Menor precisión en extremos, preguntas "desperdiciadas"
- **Correlación esperada:** r = 0.80-0.85
- **Decisión:** ❌ Rechazada por menor precisión

### Opción 2: MST (16 preguntas) ✅ ELEGIDA
- **Descripción:** 2 etapas con routing adaptativo
- **Ventajas:** Mejor precisión, control curricular explícito
- **Desventajas:** Requiere 32 preguntas (8 + 8×3)
- **Correlación esperada:** r = 0.82-0.87
- **Decisión:** ✅ Elegida por balance precisión/complejidad

### Opción 3: CAT (12-18 preguntas)
- **Descripción:** Cada pregunta se elige en tiempo real
- **Ventajas:** Máxima eficiencia (menos preguntas)
- **Desventajas:** Requiere IRT calibrado, mayor complejidad
- **Correlación esperada:** r = 0.85-0.90 (con IRT)
- **Decisión:** ❌ Rechazada para MVP, planificada para futuro

### Opción 4: CAT basado en Grafo (KG-CAT) 🆕
- **Descripción:** Navegación por prerrequisitos en el Knowledge Graph. Si fallas un átomo, el sistema evalúa su prerrequisito directo.
- **Lógica:** Determinística (no estadística). "Si no sabes Ecuación Cuadrática, verifico Ecuación Lineal".
- **Ventajas:** No requiere 500 datos para calibrar IRT. Diagnóstico remedial inmediato.
- **Desventajas:** Requiere grafo de prerrequisitos 100% validado. Puede ser más lento para estimar puntaje global.
- **Estado:** 🔶 Alternativa estratégica a evaluar post-MVP.

---

## 3. Por qué MST y no CAT

| Factor | MST | CAT (heurístico) |
|--------|-----|------------------|
| Control curricular | ⭐⭐⭐⭐⭐ (por diseño) | ⭐⭐ (por penalizaciones) |
| Complejidad | Media | Alta |
| Riesgo de sesgo | Bajo | Medio-Alto |
| Requiere IRT | No | Ideal sí |
| Preguntas | 16 fijas | 12-18 variables |

**Conclusión:** CAT sin IRT calibrado tiene complejidad similar a MST pero menos control. El beneficio real de CAT (10-12 preguntas) solo aparece con IRT.

---

## 4. ¿Qué es IRT?

**IRT = Item Response Theory (Teoría de Respuesta al Ítem)**

Modelo matemático que describe la probabilidad de acertar una pregunta según la habilidad del estudiante.

### Parámetros de cada pregunta:

| Parámetro | Símbolo | Significado |
|-----------|---------|-------------|
| Dificultad | b | ¿Qué tan difícil es? |
| Discriminación | a | ¿Qué tan bien distingue saber de no saber? |
| Pseudo-azar | c | Probabilidad de acertar adivinando (~0.25) |

### ¿Por qué no lo tenemos?

Para calibrar IRT se necesitan **200-500 respuestas por pregunta** de estudiantes reales. No tenemos esos datos todavía.

### Beneficio futuro:

Con IRT calibrado, CAT puede:
- Elegir la pregunta óptima para cada estudiante
- Terminar en 10-12 preguntas con igual precisión
- Medir extremos con mayor exactitud

---

## 5. Roadmap: MST → CAT

```
FASE 1: MST (Ahora)
├── Implementar MST con 32 preguntas
├── Lanzar prueba diagnóstica
└── Recolectar respuestas reales
         │
         ▼ (3-6 meses, N > 500 respuestas)
         
FASE 2: Calibración IRT
├── Calcular parámetros a, b, c por pregunta
├── Identificar preguntas problemáticas
└── Crear 20-40 ítems de dificultad High
         │
         ▼ (6-12 meses)
         
FASE 3: Migración a CAT
├── Implementar motor de selección con IRT
├── Probar con banco calibrado
└── Reducir a 10-12 preguntas
```

### Qué se reutiliza de MST en CAT:

| Componente | Reutilización |
|------------|---------------|
| Banco de preguntas | ✅ Se expande |
| Mapping de puntajes | ✅ Se refina |
| Blueprint por eje | ✅ Se convierte en restricciones |
| Datos de respuestas | ✅ Para calibrar IRT |
| UI de prueba | ✅ Se adapta |

---

## 6. Checklist de Implementación

### Fase 1: Selección de Preguntas
- [x] Seleccionar 8 preguntas para Routing (R1)
- [x] Seleccionar 8 preguntas para Ruta A (bajo)
- [x] Seleccionar 8 preguntas para Ruta B (medio)
- [x] Seleccionar 8 preguntas para Ruta C (alto)
- [x] Verificar cobertura de ejes en cada módulo
- [x] Verificar cobertura de habilidades

### Fase 2: Implementación Técnica
- [x] Implementar lógica de routing (cortes 0-3/4-6/7-8)
- [x] Implementar cálculo de puntaje ponderado
- [x] Implementar mapping a escala PAES
- [x] Implementar diagnóstico por átomo (3 estados)
- [x] Agregar soporte para botón "No lo sé"

### Fase 3: UI/UX
- [x] Diseñar UI de prueba (1 pregunta/pantalla)
- [x] Implementar transición entre etapas
- [x] Diseñar pantalla de resultados
- [x] Diseñar diagnóstico visual por eje/habilidad
- [x] Implementar Skill Tree de átomos

### Fase 4: Validación
- [ ] Pilotaje interno (N=10-20)
- [ ] Ajustar redacción si necesario
- [ ] Lanzar versión beta
- [ ] Recolectar datos para calibración futura

### Fase 5: Skill Tree Visualization ✅ (2026-01-08)

**Objetivo:** Visualización tipo "árbol de habilidades" de videojuego mostrando átomos dominados vs no dominados.

**Archivos creados:**
| Archivo | Descripción |
|---------|-------------|
| `app/atoms/scripts/export_skill_tree.py` | Exporta grafo de átomos a JSON |
| `app/diagnostico/data/skill_tree.json` | 229 nodos, 317 edges, profundidad máx 6 |
| `app/diagnostico/data/question_atoms.json` | Mapeo 32 preguntas → 61 átomos únicos |
| `app/diagnostico/web/skill_tree.js` | Componente D3.js para visualización |
| `app/diagnostico/web/tree_viewer.html` | Vista standalone del árbol completo |
| `app/diagnostico/scripts/extract_question_atoms.py` | Extrae mapeo pregunta→átomo |

**Estadísticas de cobertura (v3.0 optimizada):**
- Total átomos en banco: 229
- Átomos directos por MST: 61 (26.6%)
- **Átomos transitivos: 190 (83.0%)** ← Optimizado desde 58%
- Profundidad máxima del grafo: 6 niveles

**Estados de dominio por respuesta:**
| Respuesta | Estado del átomo |
|-----------|------------------|
| ✅ Correcta (átomo primary) | `dominated` (verde) |
| ↻ Inferido por prerrequisito | `transitiveDominated` (cyan) |
| ❌ Incorrecta (átomo primary) | `misconception` (naranja) |
| ❌ Incorrecta (átomo secondary) | `notDominated` (rojo) |
| ❓ "No lo sé" | `notEvaluated` (gris) |

### Fase 6: Optimización de Selección ✅ (2026-01-09)

**Objetivo:** Maximizar cobertura de átomos sin cambiar número de preguntas.

**Resultado:**
| Métrica | v1.0 | v3.0 | Mejora |
|---------|------|------|--------|
| Cobertura transitiva | 58% | **83%** | +25% |
| Átomos directos | 47 | 61 | +14 |
| Preguntas | 32 | 32 | = |

**Validación vs blueprint:**
- ✅ Distribución de ejes: R1=2-2-2-2, A2/B2/C2=3-2-1-2
- ✅ Dificultad A2: 100% Low
- ✅ Dificultad B2/C2: 100% Medium
- ✅ 4 habilidades cubiertas por módulo

### Fase 7: Fórmula Ponderada de Predicción ✅ (2026-01-09)

**Objetivo:** Mejorar precisión de predicción PAES usando fórmula ponderada.

**Fórmula implementada:**
```
PAES = 100 + 900 × score_ponderado × factor_ruta × factor_cobertura

Donde:
- score_ponderado = Σ(correcto × peso) / Σ(peso_max)
- peso = 1.0 (Low) | 1.8 (Medium)
- factor_ruta = 0.70 (A) | 0.85 (B) | 1.00 (C)
- factor_cobertura = 0.90 (10% de átomos no inferibles)
```

**Archivos modificados:**
| Archivo | Cambio |
|---------|--------|
| `app/diagnostico/web/app.js` | `calculatePAESScore()` reescrito |
| `app/diagnostico/config.py` | Nueva función `get_paes_score_weighted()` |

**Resultados (16/16 correctas):**
| Ruta | Puntaje | Rango |
|------|---------|-------|
| A | 667 | 617-717 |
| B | 789 | 739-839 |
| C | 910 | 860-960 |

## 7. Especificaciones Técnicas

### Distribución por Módulo

| Módulo | ALG | NUM | GEO | PROB | Total |
|--------|-----|-----|-----|------|-------|
| R1 (Routing) | 2 | 2 | 2 | 2 | 8 |
| A2 (bajo) | 3 | 2 | 1 | 2 | 8 |
| B2 (medio) | 3 | 2 | 1 | 2 | 8 |
| C2 (alto) | 3 | 2 | 1 | 2 | 8 |

### Routing

| Correctas en R1 | Ruta |
|-----------------|------|
| 0-3 | A (bajo) |
| 4-6 | B (medio) |
| 7-8 | C (alto) |

### Diagnóstico por Átomo

| Resultado | Estado | Acción |
|-----------|--------|--------|
| ✅ Correcto | `dominado` | No incluir en plan |
| ❓ "No lo sé" | `gap` | Enseñar desde cero |
| ❌ Incorrecto | `misconception` | Corregir + enseñar |

---

## 8. Documentación Relacionada

- [Research completo](./research_prueba_diagnostica.md)
- [Resumen ejecutivo](./research_prueba_diagnostica_resumen.md)
- [Feedback del socio](./feedback_prueba_diagnostica.md)
- [Análisis de cobertura de átomos](./analisis_cobertura_atomos.md)

---

## 9. Historial de Decisiones

### Decisiones de Arquitectura

| Fecha | Decisión | Justificación |
|-------|----------|---------------|
| 2026-01-08 | Elegir MST sobre CAT | CAT sin IRT = complejidad similar, menos control |
| 2026-01-08 | Elegir MST sobre Forma Fija | MST mejor precisión en extremos, 2 menos preguntas |
| 2026-01-08 | Agregar botón "No lo sé" | Reduce guessing, mejora diagnóstico por átomo |
| 2026-01-08 | Sistema de 3 estados | Permite instrucción diferenciada (gap vs misconception) |

### Evolución de la Selección de Preguntas

| Versión | Criterio Principal | Resultado | Problema |
|---------|-------------------|-----------|----------|
| v1.0 | Aleatorio dentro de dificultad | RES=69% | Muy desbalanceado en habilidades |
| v2.0 | Score de dificultad | C2=0.64, RES=69% | Buena dificultad, pero sin diagnóstico válido de MOD/REP |
| **v3.0** | Balance de habilidades | C2=0.62, RES=38% | ✅ Diagnóstico válido de todas las habilidades |

### Decisión Clave: Score vs Balance

**Pregunta:** ¿Priorizar dificultad máxima en C2 o balance de habilidades?

**Análisis:**
- Selección por score: C2=0.64, pero 69% RES → no podemos diagnosticar MOD/REP/ARG
- Selección balanceada: C2=0.62 (-4%), pero 38% RES → diagnóstico válido de todas las habilidades

**Decisión (2026-01-08):** Selección balanceada (v3.0)

**Justificación:** 
> "El objetivo principal es diagnosticar qué sabe el alumno. Si solo usamos RES, solo podemos diagnosticar RES. La diferencia de score (0.64 vs 0.62) es ~4%, no significativa."

### Investigación que Respaldó la Decisión

**Fuentes consultadas:**
- Literature on "Attribute Balancing" en Cognitive Diagnostic Testing
- Content Balancing en Multistage Tests (MST)
- Bloom's Taxonomy en tests diagnósticos de matemáticas

**Hallazgo clave:** 
> "Attribute Balancing es crítico para diagnóstico válido. Si no medimos una habilidad, no podemos diagnosticarla."

---

## 10. Distribución Final de Habilidades (v3.0)

| Habilidad | Total | % | Comparación PAES Real |
|-----------|-------|---|----------------------|
| RES | 12 | 38% | ~49% → Subrepresentada |
| ARG | 10 | 31% | ~13% → Sobrerepresentada |
| MOD | 6 | 19% | ~16% → OK |
| REP | 4 | 12% | ~14% → OK |

**Nota:** ARG está sobrerepresentada porque las preguntas Medium más difíciles tienden a ser ARG.

---

## 11. Documentación Relacionada

- [Research completo](./research_prueba_diagnostica.md)
- [Resumen ejecutivo](./research_prueba_diagnostica_resumen.md)
- [Feedback del socio](./feedback_prueba_diagnostica.md)
- [Selección de preguntas MST](./seleccion_mst.md)
- [Análisis de cobertura de átomos](./analisis_cobertura_atomos.md)

---

## 12. Requisitos para Migrar a CAT

Una vez que MST esté en producción y se recolecten datos, estos son los 6 requisitos para migrar a CAT:

### 12.1 Datos de Respuestas (~500 por pregunta)

**¿Por qué 500?**
- Con N<100, los errores de estimación IRT son ±0.3 en dificultad (muy alto)
- 200-500 es el mínimo estadístico para parámetros estables
- **Estimación:** Con 500 estudiantes haciendo MST (16 preguntas cada uno), cada pregunta acumula ~250 respuestas

### 12.2 Calibración IRT (parámetros a, b, c)

Cada pregunta se describe con 3 parámetros:

| Parámetro | Símbolo | Significado | Rango típico |
|-----------|---------|-------------|--------------|
| Dificultad | b | ¿Qué tan difícil? | -3 a +3 |
| Discriminación | a | ¿Distingue saber de no saber? | 0.5 a 2.5 |
| Pseudo-azar | c | Prob. de acertar adivinando | ~0.25 |

**Modelo 3PL:**
```
P(correcta | θ) = c + (1-c) / (1 + e^(-a(θ-b)))
```

### 12.3 Motor de Selección Adaptativa

Algoritmo que elige la siguiente pregunta basándose en respuestas anteriores.

**Criterio principal:** Máxima Información de Fisher
```
Siguiente pregunta = argmax I(θ̂, pregunta)
```

**Restricciones para evitar sesgos:**
- Mínimo 2 preguntas por eje
- Mínimo 2 habilidades diferentes
- No repetir átomos ya evaluados

### 12.4 Banco Expandido (60-100 preguntas)

**Problema actual:** Solo 8 preguntas difíciles → no distinguimos entre θ=+1.5 y θ=+2.5

**Necesidad:** Preguntas con b=+1, +1.5, +2, +2.5 para medir precisamente en extremos.

**Distribución ideal:**
```
Cantidad │          ▓▓▓▓▓
         │       ▓▓▓▓▓▓▓▓▓▓▓
         │    ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
         │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
         └─────────────────────────→ b
            -2   -1    0    +1   +2
```

### 12.5 Estimador de Habilidad (θ)

**Método recomendado:** Expected A Posteriori (EAP)
```
θ̂ = ∫ θ × P(θ | respuestas) dθ
```

**Ventajas de EAP:**
- Funciona con 0% o 100% correctas
- Estable desde la primera respuesta
- Usado en CAT modernos (GRE, GMAT)

**Ejemplo de actualización:**

| Pregunta (b) | Respuesta | θ̂ nuevo |
|--------------|-----------|---------|
| b=0.5 | ✅ | +0.4 |
| b=0.8 | ✅ | +0.9 |
| b=1.2 | ❌ | +0.6 |
| b=0.7 | ✅ | +0.8 |

### 12.6 Criterio de Terminación

**Criterio recomendado:** Híbrido
```
Terminar cuando: SE(θ̂) < 0.30 O preguntas >= 15
```

**Efecto:** Estudiantes típicos terminan en 10-12 preguntas, extremos pueden necesitar hasta 15.

---

### Orden de Implementación CAT

| Paso | Requisito | Dependencia |
|------|-----------|-------------|
| 1 | Datos de respuestas | Lanzar MST primero |
| 2 | Calibración IRT | Depende de (1) |
| 3 | Banco expandido | Paralelo con (1) y (2) |
| 4 | Estimador de θ | Depende de (2) |
| 5 | Motor de selección | Depende de (2) y (4) |
| 6 | Criterio terminación | Depende de (4) |

---

## 13. Validación Empírica Pendiente

> [!IMPORTANT]
> **Sin datos empíricos reales (puntajes PAES de estudiantes que hayan tomado la prueba diagnóstica), es IMPOSIBLE verificar la validez predictiva con certeza.** Todo lo documentado actualmente es teórico.

### 13.1 Estado Actual de Validez

| Aspecto | Estado | Comentario |
|---------|--------|------------|
| **Diseño arquitectónico** | ✅ Validado | MST 1-3 es estándar psicométrico |
| **Proporción de ítems (25%)** | ✅ Adecuada | Literature: 20-36% para short forms |
| **Cobertura curricular** | ✅ Balanceada | 4 ejes, 4 habilidades cubiertas |
| **Validez predictiva probada** | ❌ **NO** | Requiere datos empíricos |
| **Parámetros IRT calibrados** | ❌ **NO** | Requiere N≥200 por pregunta |
| **Correlación con PAES real** | ❌ **Desconocida** | Solo estimación teórica r≈0.82-0.87 |

### 13.2 Limitaciones Conocidas

| Limitación | Impacto | Mitigación Posible |
|------------|---------|-------------------|
| **Sin ítems "High"** | Techo de medición limitado (~700-760 PAES máximo) | Crear/seleccionar preguntas difíciles |
| **Scores de dificultad manuales** | Sin calibración IRT, los pesos son estimaciones | Calibrar con datos reales |
| **Sin datos de discriminación (rpbi)** | No sabemos si las preguntas realmente diferencian entre estudiantes | Calcular rpbi post-recolección |
| **Mapping PAES teórico** | Conversión score→PAES no validada | Ajustar con regresión sobre datos reales |
| **Guessing no modelado** | 25% de acierto al azar no se considera | Incluir parámetro c en IRT futuro |

### 13.3 Estimación Teórica de Precisión

Usando la fórmula Spearman-Brown y literatura psicométrica:

```
Correlación estimada: r ≈ 0.82 - 0.87
Error Estándar (SEE) ≈ ±55-65 puntos

Si predecimos 600 PAES:
- 68% de las veces: puntaje real entre 535-665
- 95% de las veces: puntaje real entre 470-730
```

> [!WARNING]
> Estas correlaciones son **estimaciones teóricas**. La correlación real solo se conocerá después de validar con puntajes PAES reales.

---

## 14. Plan de Validación Empírica

### 14.1 Estudio Piloto (Pre-PAES)

| Fase | Descripción | N Mínimo | Timeline |
|------|-------------|----------|----------|
| **Piloto interno** | Staff/voluntarios prueban el flujo | 10-20 | 1 semana |
| **Piloto beta** | Estudiantes reales pre-PAES | 50-100 | 2-4 semanas |
| **Lanzamiento** | Producción abierta | 500+ | Continuo |

### 14.2 Métricas a Recolectar por Pregunta

| Métrica | Símbolo | Qué mide | Umbral aceptable |
|---------|---------|----------|------------------|
| **Proporción de aciertos** | p | Dificultad empírica | 0.20-0.80 |
| **Correlación point-biserial** | rpbi | Discriminación | ≥0.20 (idealmente ≥0.30) |
| **Tiempo promedio** | t | Carga cognitiva | <3 min |
| **Tasa de "No lo sé"** | pNS | Incertidumbre | <40% |

### 14.3 Métricas a Calcular Post-PAES

| Métrica | Fórmula | Objetivo |
|---------|---------|----------|
| **Correlación con PAES** | r(predicho, real) | ≥0.80 |
| **Error Estándar de Estimación** | SEE = SD × √(1-r²) | <65 puntos |
| **Sesgo por ruta** | media(predicho - real) por ruta | ~0 en cada ruta |
| **Precisión en extremos** | r para PAES<450 y PAES>650 | ≥0.70 |

### 14.4 Calibración IRT Futura

Una vez recolectados N≥200 respuestas por pregunta:

| Acción | Descripción | Herramienta sugerida |
|--------|-------------|---------------------|
| **Estimar parámetros 3PL** | Calcular a, b, c por pregunta | `mirt` (R) o `pyirt` (Python) |
| **Identificar ítems problemáticos** | Eliminar si a<0.5 o rpbi<0.15 | Análisis de residuales |
| **Crear curvas ICC** | Visualizar comportamiento de cada ítem | Gráficos IRT |
| **Recalibrar mapping** | Ajustar θ→PAES con regresión | Datos reales |

### 14.5 Acciones Futuras (TODO)

- [ ] **Corto plazo (1-2 semanas)**
  - [ ] Lanzar piloto interno con 10-20 personas
  - [ ] Verificar flujo técnico completo
  - [ ] Ajustar redacción/UX si necesario

- [ ] **Mediano plazo (1-3 meses)**
  - [ ] Lanzar beta con estudiantes reales
  - [ ] Recolectar primeras 100-500 respuestas
  - [ ] Calcular rpbi inicial por pregunta
  - [ ] Identificar preguntas con bajo poder discriminativo

- [ ] **Largo plazo (post-PAES)**
  - [ ] Obtener puntajes PAES reales de participantes
  - [ ] Calcular correlación empírica (r)
  - [ ] Ajustar mapping de puntajes según datos
  - [ ] Calibrar parámetros IRT (a, b, c)
  - [ ] Evaluar migración a CAT

- [ ] **Expansión del banco**
  - [ ] Crear/seleccionar 20-40 preguntas "High" (b>+1)
  - [ ] Balancear banco para cobertura más uniforme en dificultad
  - [ ] Tagear nuevas preguntas con átomos y habilidades

---

## 15. Criterios de Éxito

### 15.1 Mínimo Viable

| Criterio | Umbral | Estado |
|----------|--------|--------|
| Correlación con PAES | r ≥ 0.75 | ❓ Por validar |
| Error estándar | SEE ≤ 70 puntos | ❓ Por validar |
| Cobertura de ejes | 4/4 ejes en cada estudiante | ✅ Por diseño |

### 15.2 Objetivo Ideal

| Criterio | Umbral | Estado |
|----------|--------|--------|
| Correlación con PAES | r ≥ 0.85 | ❓ Por validar |
| Error estándar | SEE ≤ 55 puntos | ❓ Por validar |
| Discriminación promedio | rpbi ≥ 0.30 | ❓ Por validar |
| IRT calibrado | 3PL para 80%+ de ítems | ❌ Pendiente |

---

## 16. Referencias Psicométricas

| Concepto | Descripción | Uso en nuestro proyecto |
|----------|-------------|------------------------|
| **Spearman-Brown** | Predice confiabilidad si se cambia largo del test | Estimar r para 16 vs 65 ítems |
| **IRT 3PL** | Modelo con dificultad, discriminación y guessing | Calibración futura |
| **Point-biserial (rpbi)** | Correlación ítem-total | Identificar ítems problemáticos |
| **Fisher Information** | Cuánta información aporta un ítem en θ | Selección de ítems para CAT |
| **EAP** | Expected A Posteriori para estimar θ | Estimador para CAT futuro |

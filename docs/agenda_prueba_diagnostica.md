# Agenda: Creación de Prueba Diagnóstica PAES M1

**Fecha inicio:** 2026-01-08  
**Arquitectura elegida:** MST (Multistage Test)  
**Estado:** En progreso

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
- [ ] Diseñar UI de prueba (1 pregunta/pantalla)
- [ ] Implementar transición entre etapas
- [ ] Diseñar pantalla de resultados
- [ ] Diseñar diagnóstico visual por eje/habilidad

### Fase 4: Validación
- [ ] Pilotaje interno (N=10-20)
- [ ] Ajustar redacción si necesario
- [ ] Lanzar versión beta
- [ ] Recolectar datos para calibración futura

---

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

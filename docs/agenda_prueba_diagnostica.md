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
- [ ] Implementar lógica de routing (cortes 0-3/4-6/7-8)
- [ ] Implementar cálculo de puntaje ponderado
- [ ] Implementar mapping a escala PAES
- [ ] Implementar diagnóstico por átomo (3 estados)
- [ ] Agregar botón "No lo sé"

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

| Fecha | Decisión | Justificación |
|-------|----------|---------------|
| 2026-01-08 | Elegir MST sobre CAT | CAT sin IRT = complejidad similar, menos control |
| 2026-01-08 | Agregar botón "No lo sé" | Reduce guessing, mejora diagnóstico por átomo |
| 2026-01-08 | Sistema de 3 estados | Permite instrucción diferenciada (gap vs misconception) |

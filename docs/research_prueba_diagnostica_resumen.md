# Prueba Diagnóstica PAES M1 - Resumen Ejecutivo

**Objetivo:** Predecir puntaje PAES M1 con la menor cantidad de preguntas posible.

---

## El Problema

| PAES Real | Nuestra Diagnóstica |
|-----------|---------------------|
| 65 preguntas | 12-18 preguntas |
| 140 minutos | ~30-40 minutos |
| Escala 100-1000 | Predecir esa escala |

---

## Nuestro Banco

| Métrica | Valor |
|---------|-------|
| Preguntas disponibles | **202** |
| Distribución dificultad | 42% Low, 58% Medium, 0% High |
| Habilidades taggeadas | ✅ RES 49%, MOD 16%, REP 14%, ARG 13% |

**Limitación crítica:** No tenemos preguntas de dificultad High → techo de medición.

---

## 3 Opciones

### Opción 1: Forma Fija (18 preguntas)
- **Todos responden lo mismo**
- Tiempo implementación: 3-5 días
- Correlación esperada: r = 0.80-0.85
- ✅ Simple | ❌ Menos preciso en extremos

### Opción 2: MST (16 preguntas)
- **2 etapas: 8 routing + 8 adaptadas**
- Tiempo implementación: 1-2 semanas
- Correlación esperada: r = 0.82-0.87
- ✅ Balance precisión/control | ❌ Requiere 32 preguntas seleccionadas

### Opción 3: CAT (12-18 preguntas)
- **Cada pregunta se elige según respuestas anteriores**
- Tiempo implementación: 2-3 semanas
- Correlación esperada: r = 0.85-0.90
- ✅ Más eficiente | ❌ Más complejo, menor control curricular

---

## Comparativa

| Criterio | Forma Fija | MST | CAT |
|----------|------------|-----|-----|
| Preguntas al alumno | 18 | 16 | 12-18 |
| Precisión teórica | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Control curricular | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| Facilidad implementar | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Robustez sin IRT | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |

---

## Tratamiento del Azar

- Probabilidad de acertar al azar: **25%** (4 opciones)
- Sin penalización por error (igual que PAES)
- Se mitiga con: más preguntas + ítems discriminativos

---

## Correlación y Error

| Tipo | r esperada | Error ±1σ |
|------|------------|-----------|
| Forma Fija | 0.80-0.85 | ±60-70 pts |
| MST | 0.82-0.87 | ±55-65 pts |
| CAT | 0.85-0.90 | ±50-60 pts |

---

## Requisitos para Lanzar

### Forma Fija
- [ ] Seleccionar 18 preguntas del banco
- [ ] Implementar scoring ponderado
- [ ] UI de prueba

### MST
- [ ] Seleccionar 32 preguntas (8 + 8×3)
- [ ] Implementar routing (0-3/4-6/7-8)
- [ ] UI con transición entre etapas

### CAT
- [x] Banco etiquetado (202 preguntas)
- [ ] Motor de selección adaptativa
- [ ] Sistema de penalización por cuotas
- [ ] Control de exposición

---

## Validación Futura

1. **Fase 1:** Pilotaje (N=30-50) → α Cronbach ≥ 0.80
2. **Fase 2:** Calibración (N>200) → DI ≥ 0.30
3. **Fase 3:** Equiparación con PAES real

---

## Decisión Pendiente

**¿Qué optimizar?**
- Si priorizo **velocidad** → Forma Fija
- Si priorizo **balance** → MST
- Si priorizo **eficiencia máxima** → CAT

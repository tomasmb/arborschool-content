# Métricas Post-Diagnóstico: Opciones y Decisiones Pendientes

**Fecha:** 2026-01-19  
**Propósito:** Documento de trabajo para discutir opciones antes de finalizar `metricas_post_diagnostico.md`

---

## 1. Nombres de Rutas — Opciones

### Opción A: Nombre por Eje (Actual)
Simple y claro, pero genérico.

| Eje | Nombre Actual |
|-----|---------------|
| Álgebra | Ruta: Expresiones Algebraicas |
| Números | Ruta: Dominio de Enteros |
| Geometría | Ruta: Pitágoras y Áreas |
| Prob/Est | Ruta: Probabilidades |

### Opción B: Nombres Creativos/Temáticos
Más engaging, estilo videojuego.

| Eje | Nombre Creativo | Emoji |
|-----|-----------------|-------|
| Álgebra | "El Camino del Álgebra" | 🧮 |
| Álgebra | "Descifrando Ecuaciones" | 🔓 |
| Álgebra | "Maestría Algebraica" | ⚔️ |
| Números | "El Poder de los Números" | 💪 |
| Números | "Dominio Numérico" | 🔢 |
| Geometría | "El Ojo Geométrico" | 📐 |
| Geometría | "Formas y Figuras" | 🔷 |
| Prob/Est | "El Arte de la Probabilidad" | 🎲 |
| Prob/Est | "Datos y Decisiones" | 📊 |

### Opción C: Híbrido — Nombre + Subtítulo
Balance entre claridad y creatividad.

```
🧮 Dominio Algebraico
   "Expresiones, ecuaciones y funciones"
   8 átomos | +45 pts | ~2 hrs
```

### Opción D: Nombres por Objetivo
Enfocados en el beneficio para el alumno.

| Nombre | Descripción |
|--------|-------------|
| "Subir 50 Puntos Rápido" | La ruta más eficiente |
| "Cerrar Brechas Fundamentales" | Átomos base prioritarios |
| "Máximo Potencial" | Ruta completa hacia 1000 pts |

**⏸️ DECISIÓN PENDIENTE**: ¿Cuál opción preferimos? ¿Combinar?

---

## 2. Predicción de Puntaje PAES — Modelo a Mejorar

### Modelo Actual (config.py)
```python
PAES = 100 + 900 × score_ponderado × factor_ruta × factor_cobertura
```

**Limitación**: Basado solo en respuestas del diagnóstico, no en átomos dominados.

### Modelo Propuesto: Basado en Átomos

**Principio**: Si dominas el 100% de los átomos → 1000 pts (máximo teórico)

```python
def calcular_puntaje_por_atomos(atomos_dominados, total_atomos=229):
    """
    Modelo basado en cobertura de átomos.
    
    Fórmula:
    - 100% átomos → 1000 pts
    - 0% átomos → 100 pts (base)
    - Relación no lineal (retornos decrecientes en extremos)
    """
    porcentaje = atomos_dominados / total_atomos
    
    # Curva sigmoide suave para evitar extremos lineales
    # Ajustada para que 50% ≈ 550 pts, 80% ≈ 750 pts
    puntaje = 100 + 900 * (porcentaje ** 0.85)
    
    return round(puntaje)
```

### Consideraciones para Calibrar

1. **Análisis de pruebas reales PAES**:
   - Mapear preguntas PAES históricas a átomos
   - Ver qué % de átomos necesitas para X puntaje
   
2. **Peso diferenciado por átomo**:
   - Átomos de alta frecuencia PAES → más peso
   - Átomos "top" desbloqueadores → bonus
   
3. **Dominio parcial**:
   - No todos los átomos son binarios (sí/no)
   - PP100 da niveles de maestría → usar para puntaje parcial

**⏸️ DECISIÓN PENDIENTE**: Investigar correlación átomos-puntaje con datos reales.

---

## 3. Tiempo por Átomo — Referencia Original

De `learning-atom-granularity-guidelines.md`:
> "An atom should be teachable in an isolated mini-lesson"

De `learning-method-specification.md`:
> "Each atom = 1 lesson + 1 PP100 question set"
> "Lesson: 1-3 worked examples"
> "PP100: minimum 11 questions (3 per level × 3 levels + mastery)"

### Estimación Refinada

| Componente | Tiempo Estimado |
|------------|-----------------|
| Lección (1-3 ejemplos) | 5-10 min |
| PP100 (11-20 preguntas) | 10-15 min |
| **Total por átomo** | **15-25 min** |

### Tiempo por Ruta Actualizado

```python
MINUTOS_POR_ATOMO = 20  # Promedio (lección + PP100)

def estimar_tiempo_ruta(atomos):
    minutos = len(atomos) * MINUTOS_POR_ATOMO
    horas = minutos / 60
    
    # Expresar en días de práctica (30 min/día)
    dias = minutos / 30
    
    return {
        'horas': round(horas, 1),
        'sesiones_30min': round(dias)
    }
    
# Ejemplo: Ruta de 8 átomos
# → 160 min = ~2.5 hrs = ~5-6 sesiones de 30 min
```

**✅ DEFINIDO**: ~15-25 min por átomo (promedio 20 min).

---

## 4. Mensaje de Continuidad — Opciones

### Opción A: Metáfora del Videojuego (Actual)
> "Es como un árbol de habilidades: cada átomo que desbloqueas te sirve para desbloquear más. El objetivo final es tenerlos todos y ser el más poderoso."

### Opción B: Metáfora del Viaje
> "Cada ruta es un tramo del camino. Al completar una, se abren nuevos caminos. No hay solo UNA ruta correcta — todas te llevan hacia adelante."

### Opción C: Enfoque Directo
> "Las rutas no son excluyentes. Puedes completar varias. Cada una te acerca más al dominio total de PAES M1."

### Opción D: Gamificación Explícita
> "🎮 Tu misión: Desbloquear todos los átomos. Cada ruta completada = nivel ganado. ¿Puedes llegar al 100%?"

**⏸️ DECISIÓN PENDIENTE**: ¿Cuál tono preferimos?

---

## 5. Átomos Complementarios — Definición

### Criterio Propuesto

Un átomo es "complementario" si:
1. **Prerrequisitos satisfechos**: El alumno puede aprenderlo ahora
2. **No parte de una ruta activa**: No está en el camino crítico
3. **Bajo valor de desbloqueo**: Solo desbloquea 0-2 átomos
4. **Útil por sí mismo**: Aporta directamente a puntaje PAES

### Ejemplos Típicos
- Átomos "hoja" (sin dependientes)
- Átomos de ejes ya fuertes (refinamiento)
- Habilidades puntuales frecuentes en PAES

**✅ DEFINIDO**: Átomos aprendibles ahora, fuera de ruta, útiles para sesiones cortas.

---

## 6. Ideas Futuras (NO para implementación inmediata)

### 6.1 Carreras y Universidades
- Mostrar carreras alcanzables según puntaje proyectado
- Filtrar por preferencias del alumno (post-contratación)
- Motivar con metas concretas: "Con +50 pts puedes postular a Ingeniería en X"

**Requiere**: Datos de puntajes de corte (web scraping o API)

### 6.2 Puntaje Objetivo Personalizado
- Alumno indica su meta: "Quiero 650 pts"
- Sistema calcula ruta mínima para lograrlo
- Útil para alumnos que no buscan el máximo

**Consideración**: ¿Desmotiva apuntar bajo? ¿O es pragmático?

### 6.3 Múltiples Rutas Activas
- Menú con rutas iniciadas y % de avance
- Alumno elige qué estudiar hoy
- Sistema siempre recomienda la óptima

**Riesgo**: Puede dispersar al alumno. ¿Mejor enfoque secuencial?

---

## 7. Resumen de Decisiones Pendientes

| # | Tema | Opciones | Para discutir con |
|---|------|----------|-------------------|
| 1 | Nombres de rutas | A/B/C/D | Socio |
| 2 | Modelo de predicción PAES | Lineal vs. basado en átomos | Equipo técnico |
| 3 | Tono del mensaje de continuidad | Videojuego/Viaje/Directo/Gamificado | Socio + UX |
| 4 | Carreras y universidades | Implementar o no | Socio (prioridad) |
| 5 | Puntaje objetivo personalizado | Implementar o no | Socio (prioridad) |
| 6 | Múltiples rutas activas | Permitir o no | Socio (UX) |

---

*Documento de trabajo. Decisiones finales se reflejarán en `metricas_post_diagnostico.md`.*

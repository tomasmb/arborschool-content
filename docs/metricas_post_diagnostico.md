# Métricas Post-Diagnóstico: Especificación Completa

**Rama:** `feature/post-diagnostic-metrics`  
**Fecha:** 2026-01-19  
**Versión:** 2.0

---

## Visión General

Al finalizar la prueba diagnóstica, el alumno verá un resumen completo de su situación actual y un plan de acción personalizado. Las métricas están diseñadas para responder:

| Pregunta | Métrica Principal |
|----------|-------------------|
| **¿Dónde estoy?** | Puntaje PAES proyectado + % dominio por eje |
| **¿Qué debo trabajar?** | Rutas de aprendizaje óptimas con nombres descriptivos |
| **¿Cuánto puedo mejorar?** | Puntos PAES ganados + % del eje dominado |
| **¿Cuánto tiempo tomará?** | Horas estimadas por ruta |
| **¿Qué más hay después?** | Rutas alternativas + átomos complementarios |

---

## 1. Puntaje PAES Proyectado + Mensaje Motivacional

La primera métrica que ve el alumno es su puntaje PAES estimado junto con un **mensaje positivo que destaca su fortaleza**:

```
╔════════════════════════════════════════════════════════════════════╗
║                      TU PUNTAJE ESTIMADO                           ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║                    🎯 520 - 560 puntos                             ║
║                                                                    ║
║  ⭐ "Destacas en Números — ¡es tu área más fuerte!"               ║
║                                                                    ║
║  📈 Con trabajo enfocado puedes subir +90 puntos                  ║
║     en pocas semanas de práctica.                                 ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
```

> [!IMPORTANT]
> **Decisión de Diseño**: NO mostramos etiquetas de "nivel" (Inicial, Intermedio, etc.) porque pueden desmotivar. En cambio, siempre destacamos algo positivo primero.

### 1.1 Generación del Mensaje Motivacional

```python
def generar_mensaje_motivacional(perfil_por_eje, puntaje_actual):
    """
    Genera un mensaje positivo personalizado basado en las fortalezas del alumno.
    
    Siempre destaca:
    1. El área más fuerte del alumno
    2. El potencial de mejora (nunca lo que "le falta")
    """
    # Encontrar el eje con mayor % de dominio
    eje_fortaleza = max(perfil_por_eje.items(), key=lambda x: x[1]['porcentaje'])
    eje_nombre = NOMBRES_EJES[eje_fortaleza[0]]
    porcentaje = eje_fortaleza[1]['porcentaje']
    
    # Variantes de mensajes según el área fuerte
    mensajes_fortaleza = {
        'numeros': f"⭐ ¡Destacas en Números! Dominas el {porcentaje}% — es tu superpoder matemático.",
        'algebra_y_funciones': f"⭐ ¡El Álgebra es lo tuyo! Con {porcentaje}% de dominio, tienes una base sólida.",
        'geometria': f"⭐ ¡Tienes ojo para la Geometría! {porcentaje}% de dominio — ves las formas.",
        'probabilidad_y_estadistica': f"⭐ ¡Eres fuerte en Probabilidad y Estadística! {porcentaje}% de dominio."
    }
    
    return mensajes_fortaleza.get(eje_fortaleza[0], f"⭐ ¡Ya dominas el {porcentaje}% de {eje_nombre}!")

NOMBRES_EJES = {
    'numeros': 'Números',
    'algebra_y_funciones': 'Álgebra y Funciones', 
    'geometria': 'Geometría',
    'probabilidad_y_estadistica': 'Probabilidad y Estadística'
}
```

### 1.2 Ejemplos de Mensajes Motivacionales

| Caso | Mensaje |
|------|--------|
| Fortaleza en Números (85%) | "⭐ ¡Destacas en Números! Dominas el 85% — es tu superpoder matemático." |
| Fortaleza en Álgebra (70%) | "⭐ ¡El Álgebra es lo tuyo! Con 70% de dominio, tienes una base sólida." |
| Fortaleza en Geometría (65%) | "⭐ ¡Tienes ojo para la Geometría! 65% de dominio — ves las formas." |
| Todas las áreas similares (55-60%) | "⭐ ¡Tienes un perfil equilibrado! Buen dominio en todas las áreas." |

---

## 2. Perfil de Dominio por Eje

### 2.1 Visualización de Progreso por Eje

Mostramos el porcentaje de átomos dominados en cada eje temático:

```
╔════════════════════════════════════════════════════════════════════╗
║                   TU PERFIL POR EJE TEMÁTICO                       ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  Números               ██████████████████░░  85%  (47/55 átomos)  ⭐ ║
║  Prob. y Estadística   ██████████████░░░░░░  68%  (35/51 átomos)  ║
║  Álgebra y Funciones   ████████████░░░░░░░░  58%  (46/80 átomos)  ║
║  Geometría             ████████░░░░░░░░░░░░  42%  (18/43 átomos)  📈 ║
║                                                                    ║
║  ⭐ = Tu fortaleza     📈 = Mayor oportunidad de mejora            ║
╚════════════════════════════════════════════════════════════════════╝
```

> [!NOTE]
> **Orden de los ejes**: Siempre mostramos las fortalezas primero (de mayor a menor %). Esto refuerza lo positivo antes de mostrar áreas de oportunidad.


### 2.2 Cálculo del Porcentaje por Eje

```python
def calcular_dominio_por_eje(diagnosticos_atomos, skill_tree):
    """
    Calcula el % de átomos dominados en cada eje.
    
    Considera:
    1. Átomos evaluados directamente en la prueba
    2. Átomos inferidos por transitividad (si dominas un átomo avanzado,
       probablemente dominas sus prerrequisitos)
    """
    dominio_por_eje = {}
    
    for eje in ['algebra_y_funciones', 'numeros', 'geometria', 'probabilidad_y_estadistica']:
        atomos_eje = [a for a in skill_tree['nodes'] if a['eje'] == eje]
        total = len(atomos_eje)
        
        # Contar dominados directamente + inferidos
        dominados = contar_dominados_con_transitividad(diagnosticos_atomos, atomos_eje)
        
        dominio_por_eje[eje] = {
            'dominados': dominados,
            'total': total,
            'porcentaje': round(dominados / total * 100)
        }
    
    return dominio_por_eje
```

### 2.3 Inferencia por Transitividad en el Knowledge Graph

> [!IMPORTANT]
> **Regla de Transitividad**: Si un alumno domina un átomo de nivel avanzado (depth 3+), asumimos que probablemente domina sus prerrequisitos (depth 0-2).
> 
> Esto nos permite "extender" el diagnóstico de 20-30 átomos evaluados directamente a ~100+ átomos inferidos.

```python
def inferir_dominados_por_transitividad(atom_dominado, skill_tree):
    """
    Dado un átomo dominado, retorna todos sus prerrequisitos (recursivamente)
    que se pueden marcar como 'probablemente dominados'.
    """
    prerrequisitos_inferidos = set()
    
    def dfs(atom_id):
        atom = buscar_atom(atom_id, skill_tree)
        for prereq_id in atom.get('prerequisites', []):
            prerrequisitos_inferidos.add(prereq_id)
            dfs(prereq_id)  # Recursivo
    
    dfs(atom_dominado['id'])
    return prerrequisitos_inferidos
```

---

## 3. Rutas de Aprendizaje Óptimas

### 3.1 Concepto de Ruta

Una **Ruta de Aprendizaje** es una secuencia ordenada de átomos que:
1. Respeta el orden de prerrequisitos del Knowledge Graph
2. Maximiza el número de átomos desbloqueados por unidad de esfuerzo
3. Se agrupa temáticamente (por eje o subárea)

### 3.2 Algoritmo de Generación de Rutas Óptimas

Usamos un enfoque basado en **Topological Sort + Utility Maximization**:

```python
def generar_rutas_optimas(diagnostico, skill_tree, top_n=3):
    """
    Genera las top N rutas de aprendizaje más eficientes.
    
    Algoritmo:
    1. Identificar todos los átomos no dominados
    2. Para cada átomo, calcular su 'valor de desbloqueo' 
       (cuántos átomos se pueden aprender después de dominarlo)
    3. Agrupar por eje temático
    4. Ordenar por valor de desbloqueo descendente
    5. Generar secuencias respetando prerrequisitos
    """
    atomos_no_dominados = obtener_atomos_no_dominados(diagnostico, skill_tree)
    
    rutas = []
    for eje in EJES:
        atomos_eje = [a for a in atomos_no_dominados if a['eje'] == eje]
        
        if not atomos_eje:
            continue
        
        # Calcular valor de desbloqueo para cada átomo
        for atom in atomos_eje:
            atom['valor_desbloqueo'] = calcular_cascada(atom, skill_tree)
        
        # Ordenar por valor de desbloqueo
        atomos_ordenados = sorted(atomos_eje, key=lambda x: -x['valor_desbloqueo'])
        
        # Generar secuencia respetando prerrequisitos
        secuencia = generar_secuencia_valida(atomos_ordenados, skill_tree)
        
        rutas.append({
            'nombre': generar_nombre_ruta(eje, secuencia),
            'eje': eje,
            'atomos': secuencia,
            'metricas': calcular_metricas_ruta(secuencia)
        })
    
    return sorted(rutas, key=lambda r: -r['metricas']['impacto_total'])[:top_n]
```

### 3.3 Cálculo del Valor de Desbloqueo (Cascada)

```python
def calcular_cascada(atom, skill_tree, dominados_actuales):
    """
    Calcula cuántos átomos se desbloquean en cascada si dominas este átomo.
    
    Un átomo A 'desbloquea' a B si:
    - A es el único prerrequisito faltante de B
    - O A es prerrequisito de algún átomo que desbloquea a B (recursivo)
    """
    desbloqueados = set()
    
    def puede_desbloquearse(atom_id, con_nuevo_dominado):
        atom = buscar_atom(atom_id, skill_tree)
        prereqs = atom.get('prerequisites', [])
        
        # Todos los prereqs deben estar dominados o ser el nuevo
        for prereq in prereqs:
            if prereq not in con_nuevo_dominado and prereq != con_nuevo_dominado:
                return False
        return True
    
    # Simular qué pasa si dominamos este átomo
    nuevo_estado = dominados_actuales | {atom['id']}
    
    for nodo in skill_tree['nodes']:
        if nodo['id'] not in nuevo_estado:
            if puede_desbloquearse(nodo['id'], nuevo_estado):
                desbloqueados.add(nodo['id'])
    
    return len(desbloqueados)
```

### 3.4 Nombres Descriptivos para Rutas

Las rutas llevan nombres que comunican claramente su contenido:

```python
NOMBRES_RUTAS = {
    'algebra_y_funciones': {
        'ALG-01': "Ruta: Expresiones Algebraicas",
        'ALG-03': "Ruta: Ecuaciones e Inecuaciones",
        'ALG-04': "Ruta: Sistemas de Ecuaciones",
        'ALG-05': "Ruta: Funciones Lineales",
        'ALG-06': "Ruta: Funciones Cuadráticas",
    },
    'numeros': {
        'NUM-01': "Ruta: Dominio de Enteros",
        'NUM-02': "Ruta: Fracciones y Racionales", 
        'NUM-03': "Ruta: Potencias y Raíces",
    },
    'geometria': {
        'GEO-01': "Ruta: Pitágoras y Áreas",
        'GEO-02': "Ruta: Geometría Analítica",
        'GEO-03': "Ruta: Transformaciones Isométricas",
    },
    'probabilidad_y_estadistica': {
        'PROB-01': "Ruta: Análisis de Datos",
        'PROB-02': "Ruta: Medidas de Tendencia Central",
        'PROB-04': "Ruta: Probabilidades",
    }
}

def generar_nombre_ruta(eje, secuencia):
    """Genera un nombre amigable basado en el estándar predominante."""
    # Detectar el estándar más común en la secuencia
    standards = [atom['id'].split('-')[2] + '-' + atom['id'].split('-')[3] 
                 for atom in secuencia]
    standard_principal = Counter(standards).most_common(1)[0][0]
    
    return NOMBRES_RUTAS.get(eje, {}).get(standard_principal, f"Ruta: {eje.title()}")
```

---

## 4. Métricas por Ruta

Cada ruta muestra métricas clave que ayudan al alumno a decidir cuál tomar:

### 4.1 Estructura de Métricas

```
╔════════════════════════════════════════════════════════════════════╗
║  🎯 RUTA RECOMENDADA: Expresiones Algebraicas                      ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  📚 8 átomos a aprender                                            ║
║  🔓 +12 átomos desbloqueados (cascada)                            ║
║                                                                    ║
║  📈 +45 puntos PAES estimados                                      ║
║  📊 Álgebra: 58% → 78% (+20%)                                      ║
║                                                                    ║
║  ⏱️ ~6-8 horas de estudio                                          ║
║                                                                    ║
║  [Ver átomos de esta ruta]                                        ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
```

### 4.2 Cálculo de Puntos PAES Estimados por Ruta

```python
def estimar_puntos_paes_ruta(ruta, puntaje_actual):
    """
    Estima cuántos puntos PAES ganaría el alumno al completar la ruta.
    
    Modelo simplificado:
    - Base: ~5-8 pts por átomo aprendido/corregido
    - Bonus por cascada: +2 pts por átomo desbloqueado indirectamente
    - Ajuste por eje: ejes con más peso en PAES dan más puntos
    """
    PESO_EJE_PAES = {
        'algebra_y_funciones': 0.35,  # ~35% del examen
        'numeros': 0.24,
        'probabilidad_y_estadistica': 0.22,
        'geometria': 0.19
    }
    
    pts_base_por_atomo = 6
    pts_cascada_por_atomo = 2
    
    atomos_directos = len(ruta['atomos'])
    atomos_cascada = ruta['metricas']['atomos_desbloqueados']
    peso_eje = PESO_EJE_PAES.get(ruta['eje'], 0.25)
    
    # Fórmula de puntos
    puntos = (atomos_directos * pts_base_por_atomo + 
              atomos_cascada * pts_cascada_por_atomo)
    
    # Ajustar por peso del eje en PAES
    puntos *= (1 + peso_eje)
    
    # Cap realista: máximo ~80 pts por ruta individual
    return min(round(puntos), 80)
```

### 4.3 Estimación de Tiempo por Ruta

Basado en `learning-method-specification.md`:
- Lección: 1-3 ejemplos trabajados (~5-10 min)
- PP100: 11-20 preguntas de maestría (~10-15 min)
- **Total por átomo: ~15-25 min (promedio 20 min)**

```python
def estimar_tiempo_ruta(ruta):
    """
    Estima el tiempo de estudio para completar la ruta.
    
    Basado en la granularidad de átomos definida:
    - Cada átomo = 1 lección + PP100
    - Tiempo promedio: ~20 minutos por átomo
    """
    MINUTOS_POR_ATOMO = 20
    
    minutos_total = len(ruta['atomos']) * MINUTOS_POR_ATOMO
    horas = minutos_total / 60
    sesiones_30min = round(minutos_total / 30)
    
    return {
        'horas': round(horas, 1),
        'sesiones_30min': sesiones_30min,
        'descripcion': f"~{sesiones_30min} sesiones de 30 min"
    }
    
# Ejemplo: Ruta de 8 átomos
# → 160 min = ~2.5 hrs = ~5-6 sesiones de 30 min
```


---

## 5. Rutas Alternativas

Además de la ruta recomendada, mostramos 2-3 alternativas para dar flexibilidad al alumno:

```
╔════════════════════════════════════════════════════════════════════╗
║                    OTRAS RUTAS DISPONIBLES                         ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  ┌──────────────────────────────────────────────────────────────┐ ║
║  │ 📐 Ruta: Pitágoras y Áreas                                    │ ║
║  │    6 átomos | +35 pts | ~4-6 hrs | Geometría: 42% → 60%      │ ║
║  │    "Ideal si te gustan los problemas visuales"               │ ║
║  └──────────────────────────────────────────────────────────────┘ ║
║                                                                    ║
║  ┌──────────────────────────────────────────────────────────────┐ ║
║  │ 🎲 Ruta: Probabilidades                                       │ ║
║  │    5 átomos | +28 pts | ~3-4 hrs | Prob/Est: 68% → 80%       │ ║
║  │    "Rápida de completar, buen balance esfuerzo/resultado"    │ ║
║  └──────────────────────────────────────────────────────────────┘ ║
║                                                                    ║
║  💡 Puedes hacer más de una ruta. Al terminar una, desbloqueas   ║
║     nuevos caminos de aprendizaje.                                ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
```

### 5.1 Mensaje de Continuidad

> [!IMPORTANT]
> **Filosofía del Sistema**: El plan de estudio óptimo para cualquier alumno es aprender TODOS los átomos no conocidos. Las rutas son el camino personalizado para llegar ahí — no el destino final.

**Mensaje para el alumno:**

```
🎮 ¡Esto es como un árbol de habilidades de videojuego!

• Cada átomo que dominas desbloquea nuevos átomos
• Cada ruta completada abre más caminos
• Tu objetivo final: desbloquear TODO y alcanzar el máximo potencial

🇺 Las rutas NO son excluyentes. Al terminar una, puedes empezar otra.
El verdadero poder está en dominar todos los átomos — ¿puedes llegar al 100%?
```


---

## 6. Átomos Complementarios

Átomos que el alumno puede aprender **ahora mismo** (prerrequisitos satisfechos) pero que no forman parte del camino crítico de una ruta.

### Criterios para ser "Complementario"

| Criterio | Descripción |
|----------|-------------|
| ✅ Prerrequisitos satisfechos | El alumno ya domina todo lo necesario |
| ✅ Bajo valor de desbloqueo | Solo desbloquea 0-2 átomos adicionales |
| ✅ Fuera de ruta activa | No está en el camino crítico actual |
| ✅ Útil para PAES | Aparece frecuentemente en exámenes |

### Uso Recomendado

> **Ideales para**: Sesiones cortas de 15-20 min cuando el alumno quiere avanzar pero no tiene tiempo para una lección completa de ruta.

```
╔════════════════════════════════════════════════════════════════════╗
║                   ÁTOMOS COMPLEMENTARIOS                           ║
╠════════════════════════════════════════════════════════════════════╣
║  💡 Átomos listos para aprender ahora (fuera de rutas):           ║
║                                                                    ║
║  • Simplificación de fracciones (NUM) - 20 min - +8 pts           ║
║  • Cálculo del área de círculos (GEO) - 20 min - +6 pts           ║
║  • Interpretación de gráficos (ALG) - 20 min - +5 pts             ║
║                                                                    ║
║  ⏱️ Ideales para sesiones cortas de práctica                      ║
╚════════════════════════════════════════════════════════════════════╝
```

---

## 7. Gamificación y Motivación

### 7.1 Sistema de Progreso Visual

Inspirado en Duolingo y Khan Academy:

```
╔════════════════════════════════════════════════════════════════════╗
║                     TU CAMINO AL ÉXITO                             ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║   AHORA               1ª META              2ª META            🏆   ║
║    520     ─────────▶   565    ──────────▶   610    ──────▶  700+ ║
║                                                                    ║
║  🏃 Ruta 1: Expresiones Algebraicas (+45 pts)                     ║
║  🏃 Ruta 2: Probabilidades (+28 pts)                              ║
║  🎯 Átomos sueltos (+17 pts)                                      ║
║  ═══════════════════════════════════════════════                  ║
║                                    TOTAL: +90 pts alcanzables     ║
║                                                                    ║
║  💪 "Con tu fortaleza en Números, ya tienes una base sólida.      ║
║      Cada ruta te acerca más a tu máximo potencial."              ║
╚════════════════════════════════════════════════════════════════════╝
```

> [!TIP]
> **Sin etiquetas de nivel**: No usamos "Inicial", "Intermedio", etc. Solo mostramos el puntaje y las metas alcanzables. El mensaje siempre menciona la fortaleza del alumno.


### 7.2 Métricas de Engagement (Backend)

Para tracking interno (no visible al alumno necesariamente):

| Métrica | Descripción |
|---------|-------------|
| `atomos_completados` | Átomos marcados como dominados post-diagnóstico |
| `rutas_iniciadas` | Cuántas rutas empezó el alumno |
| `rutas_completadas` | Cuántas terminó |
| `tiempo_en_plataforma` | Minutos totales de estudio |
| `streak` | Días consecutivos de práctica |
| `mejora_puntaje` | Diferencia entre diagnósticos |

---

## 8. Estructura de Datos Final

### 8.1 Output Completo del Sistema de Métricas

```json
{
  "resumen_diagnostico": {
    "puntaje_estimado": {
      "valor": 540,
      "rango": [520, 560]
    },
    
    "mensaje_motivacional": {
      "fortaleza": "numeros",
      "mensaje": "⭐ ¡Destacas en Números! Dominas el 85% — es tu superpoder matemático.",
      "potencial": "Con trabajo enfocado puedes subir +90 puntos en pocas semanas."
    },

    
    "perfil_por_eje": {
      "algebra_y_funciones": {
        "dominados": 46,
        "total": 80,
        "porcentaje": 58,
        "status": "en_desarrollo"
      },
      "numeros": {
        "dominados": 47,
        "total": 55,
        "porcentaje": 85,
        "status": "fortaleza"
      },
      "geometria": {
        "dominados": 18,
        "total": 43,
        "porcentaje": 42,
        "status": "reforzar"
      },
      "probabilidad_y_estadistica": {
        "dominados": 35,
        "total": 51,
        "porcentaje": 68,
        "status": "en_desarrollo"
      }
    },
    
    "rutas_recomendadas": [
      {
        "id": "ruta-alg-expresiones",
        "nombre": "Ruta: Expresiones Algebraicas",
        "eje": "algebra_y_funciones",
        "descripcion": "Domina las bases del álgebra para desbloquear ecuaciones y funciones",
        "atomos": [
          {
            "id": "A-M1-ALG-01-03",
            "title": "Reducción de términos semejantes",
            "tipo": "aprender",
            "depth": 0
          },
          {
            "id": "A-M1-ALG-01-05",
            "title": "Multiplicación de monomios y polinomios",
            "tipo": "corregir",
            "depth": 1
          }
          // ... más átomos
        ],
        "metricas": {
          "atomos_directos": 8,
          "atomos_desbloqueados": 12,
          "puntos_paes_estimados": 45,
          "tiempo_horas": {
            "min": 6,
            "max": 8,
            "promedio": 7
          },
          "mejora_eje": {
            "actual": 58,
            "proyectado": 78,
            "diferencia": 20
          }
        },
        "prioridad": 1
      },
      // ... más rutas
    ],
    
    "atomos_complementarios": [
      {
        "id": "A-M1-NUM-01-11",
        "title": "Simplificación de fracciones",
        "eje": "numeros",
        "tiempo_minutos": 30,
        "puntos_estimados": 8
      }
      // ... más átomos
    ],
    
    "proyeccion_mejora": {
      "con_ruta_1": {
        "puntaje_proyectado": 585,
        "mejora_puntos": 45
      },
      "con_todas_rutas": {
        "puntaje_proyectado": 630,
        "mejora_puntos": 90
      },
      "potencial_maximo": {
        "puntaje_proyectado": 700,
        "nota": "Si dominas todos los átomos evaluables"
      }
    },
    
    "mensaje_motivacional": "¡Gran trabajo completando el diagnóstico! Tienes una base sólida en Números. Enfocándote en Álgebra y Geometría, puedes subir ~90 puntos en pocas semanas."
  }
}
```

---

## 9. Top 15 Átomos "Desbloqueadores" (Referencia)

Basado en el análisis del Knowledge Graph, estos son los átomos que desbloquean más contenido:

| # | Átomo | Dependientes | Eje |
|---|-------|--------------|-----|
| 1 | Multiplicación de números enteros (NUM-01-06) | 6 | Números |
| 2 | Multiplicación de monomios y polinomios (ALG-01-05) | 5 | Álgebra |
| 3 | Concepto de Sistema 2x2 (ALG-04-01) | 5 | Álgebra |
| 4 | Concepto de números enteros (NUM-01-01) | 5 | Números |
| 5 | Concepto de números racionales (NUM-01-10) | 5 | Números |
| 6 | Potencias de exponente negativo (NUM-03-02) | 5 | Números |
| 7 | Conversión potencia-raíz (NUM-03-08) | 5 | Números |
| 8 | Probabilidad de evento simple (PROB-04-02) | 5 | Prob/Est |
| 9 | Ecuaciones lineales (ALG-03-01) | 4 | Álgebra |
| 10 | Inecuaciones lineales (ALG-03-07) | 4 | Álgebra |
| 11 | Concepto de Pendiente (ALG-05-06) | 4 | Álgebra |
| 12 | Transformación isométrica (GEO-03-01) | 4 | Geometría |
| 13 | Adición de enteros (NUM-01-04) | 4 | Números |
| 14 | División de enteros (NUM-01-07) | 4 | Números |
| 15 | Simplificación de fracciones (NUM-01-11) | 4 | Números |

> [!NOTE]
> Estos átomos son **puntos de alto ROI** (retorno sobre inversión). Si un alumno tiene problemas con alguno de ellos, priorizarlos tiene efecto cascada significativo.

---

## 10. Consideraciones de UX

### 10.1 Principios de Diseño

| Principio | Aplicación |
|-----------|------------|
| **Accionable** | Cada métrica lleva a una acción concreta |
| **Positivo** | Lenguaje de oportunidad, no de fracaso |
| **Gamificado** | Progreso visible, metas alcanzables |
| **Transparente** | El alumno entiende por qué se recomienda algo |
| **Flexible** | Múltiples rutas, el alumno decide |

### 10.2 Tono de Comunicación

| ❌ Evitar | ✅ Preferir |
|-----------|-------------|
| "Nivel: Inicial" o "Intermedio Bajo" | "⭐ Destacas en [área más fuerte]" |
| "Te falta dominar 50 átomos" | "Ya dominas 100+ átomos, y tienes 50 oportunidades de mejora" |
| "Debes estudiar Álgebra" | "La Ruta de Expresiones Algebraicas te puede dar +45 pts" |
| "Tu área débil es Geometría" | "📈 Geometría es tu mayor oportunidad de mejora" |
| "Esta ruta toma 8 horas" | "~6-8 horas de estudio (1-2 semanas de práctica de 30 min/día)" |


---

## 11. Próximos Pasos de Implementación

1. **Crear `app/diagnostico/metrics.py`**: Módulo con todas las funciones de cálculo
2. **Actualizar `scorer.py`**: Integrar generación de rutas
3. **Crear `app/diagnostico/routes.py`**: Algoritmo de generación de rutas óptimas
4. **Endpoint API**: `/api/diagnostic-summary` con el JSON completo
5. **Frontend**: Componentes visuales para mostrar las métricas

---

*Documento vivo. Actualizar según feedback del equipo.*

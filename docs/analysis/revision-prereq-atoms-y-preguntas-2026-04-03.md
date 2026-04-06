# Revisión de prereq atoms y hard variants

**Encargado:** Franco Solari
**Fecha de inicio:** 2026-04-03
**Última actualización:** 2026-04-05
**Estado:** Revisión completa — pendientes de acción documentados

---

## 1. Prerequisite atoms

### 1.1 Inventario y conteos verificados

| Métrica | Valor |
|---------|------:|
| Total atoms en `atoms.json` | 1,135 |
| Total reportado en `validation_result.json` | 1,095 |
| Diferencia | `validation_result` = pre-fix (1,095); `atoms.json` = post-fix (1,135) |
| Connections (M1 atoms con prereqs) | 52 |
| Layer 1 (prereq IDs únicos referenciados) | 55 |
| Layer 1 IDs que existen en `atoms.json` | 55 |

### 1.2 Integridad de `connections.json`

**Había 1 referencia rota:** `A-EB8-NUM-01-09` aparecía como prerequisito de `A-M1-NUM-03-01`, pero no existía en `atoms.json`. En `fix_results/fix_run_20260331_180606.json` constaba el reemplazo `A-EB8-NUM-01-09 → A-EB8-NUM-01-15`, pero `connections.json` no se había actualizado.

> [!NOTE]
> **Ya corregido** en esta revisión: `connections.json` ahora apunta a `A-EB8-NUM-01-15`. Se verificó que no hay más referencias rotas.

### 1.3 Consistencia `validation_result.json` vs estado actual

- `validation_result.json` reporta 1,095 atoms — coincide con el estado **previo al fix pipeline**.
- El fix pipeline procesó 140 estándares exitosamente: removió 56 IDs únicos y generó 205 atoms (48 truly removed + 197 truly new + 8 updated in place → neto +149 IDs, pero muchos reemplazan IDs preexistentes fuera del set removido).
- El cruce verificable es: `atoms.json` = 1,135 y `validation_result.total_prereq_atoms` = 1,095. Comparando IDs, hay 56 IDs que ya no están y un bloque de atoms actuales que no aparecen en los bloques LLM de validación.

**Acción requerida:** re-correr validación sobre el `atoms.json` actual (1,135 atoms post-fix).

### 1.4 Distribución de criterios atómicos

**Todo el set (1,135 atoms):**

| Criterios | Atoms | % |
|----------:|------:|:---:|
| 1 | 44 | 3.9% |
| 2 | 696 | 61.3% |
| 3 | 355 | 31.3% |
| 4 | 37 | 3.3% |
| 6 | 1 | — |
| 7 | 1 | — |
| 8 | 1 | — |

- Atoms con < 3 criterios: **740/1,135 (65%)**.
- 44 atoms con exactamente 1 criterio, repartidos en todos los ejes/grados (EB1–EM1). 36 de esos 44 traen 2+ ejemplos → subdesagregación, no falta de contenido.
- Gap notable: **0 atoms con 5 criterios** (salto de 4 a 6).

**Layer 1 (55 atoms presentes):**

| Criterios | Atoms |
|----------:|------:|
| 1 | 1 (`A-EB8-ALG-02-02`) |
| 2 | 27 |
| 3 | 22 |
| 4 | 5 |

- Layer 1 con < 3 criterios: **28/55 (51%)**.

### 1.5 Atoms sobrecargados (6+ criterios)

| Atom | Criterios | Observación |
|------|----------:|-------------|
| `A-EB3-PROB-01-01` | 6 | Evaluar si conviene re-split |
| `A-EB4-ALG-01-01` | 7 | Evaluar si conviene re-split |
| `A-EB7-GEO-01-01` | 8 | Evaluar si conviene re-split |

### 1.6 Consistencia estructural de `atoms.json`

Verificaciones automatizadas — todas limpias:

| Check | Resultado |
|-------|-----------|
| Self-prerrequisitos | 0 |
| Prerrequisitos internos rotos | 0 |
| Atoms sin ejemplos | 0 |
| Atoms sin notas de alcance | 0 |
| Títulos duplicados exactos | 0 |

### 1.7 Muestra manual de atoms Layer 1

Se revisaron 14 atoms de Layer 1 manualmente. No aparecieron problemas graves de coherencia pedagógica. El patrón dominante es compresión (pocos criterios), no incoherencia.

| Atom | Crit. | Resultado |
|------|------:|-----------|
| `A-EB3-GEO-03-05` | 2 | OK — revisar si mínimo debería ser 3 |
| `A-EB4-PROB-01-02` | 2 | OK — evaluar agregar criterio |
| `A-EB4-GEO-02-15` | 2 | OK — evaluar separar clasificación/justificación |
| `A-EB5-NUM-01-15` | 2 | OK — evaluar mayor desagregación |
| `A-EB5-GEO-01-15` | 4 | ✓ Referencia positiva |
| `A-EB6-ALG-01-15` | 3 | ✓ Referencia positiva |
| `A-EB7-NUM-02-06` | 2 | OK — evaluar separar reconocimiento/cálculo |
| `A-EB8-ALG-01-02` | 2 | OK — evaluar separar identificación/simplificación |
| `A-EB8-ALG-02-02` | 1 | ⚠️ Subespecificado para EB8; necesita al menos 1 criterio más |
| `A-EB8-ALG-03-05` | 3 | ✓ Referencia positiva |
| `A-EM1-PROB-02-02` | 2 | OK — evaluar separar espacio muestral/equiprobabilidad |
| `A-EM1-PROB-02-03` | 2 | OK — evaluar separar identificación/representación |
| `A-EM1-ALG-01-03` | 2 | OK — evaluar desagregar extracción/reescritura |
| `A-EM1-ALG-01-06` | 2 | OK — evaluar separar planteamiento/resolución |

**Muestra complementaria (layers 2+):** `A-EB2-NUM-01-09` (1 criterio, 2 ejemplos) confirma el patrón de subdesagregación en layers más profundas.

---

## 2. Question generation para prereq atoms

### Estado: nunca se ejecutó

- **0 directorios** `A-EB*` / `A-EM*` en `app/data/question-generation/`. Solo existen 205 carpetas `A-M1-*`.
- **0 rastros en git** de esos prefijos en el historial de `app/data/question-generation/`.
- El handoff describe los pasos de generación como **instrucciones futuras** con estimaciones de costo ($324–$540 para Layer 1).
- El pipeline sync ya soporta prereq atoms (`load_atom()` en `helpers.py` tiene fallback a `atoms.json` de prerequisites). El código está listo; simplemente no se ejecutó.

**Conclusión:** la generación de preguntas para prereq atoms quedó pendiente de correr. No se guardó en otra ruta ni fuera de git.

---

## 3. Hard variants

> [!IMPORTANT]
> Scan completo de **1,951 variantes aprobadas** en `app/data/pruebas/hard_variants/`. Los números reportados a continuación amplían la muestra inicial.

### 3.1 Imagen S3 duplicada entre choices (hallazgo crítico)

**15 variantes aprobadas** tienen la misma imagen S3 reutilizada en choices distintos, haciendo las preguntas visualmente ambiguas.

| Variante | Imagen duplicada usada en |
|----------|--------------------------|
| `prueba-invierno-2025/Q50/Q50_v6` | 2 choices comparten imagen |
| `prueba-invierno-2025/Q65/Q65_v6` | 2 choices comparten imagen |
| `prueba-invierno-2025/Q65/Q65_v8` | 2 imágenes duplicadas, c/u en 2 choices |
| `prueba-invierno-2026/Q38/Q38_v1` | 2 choices comparten imagen |
| `prueba-invierno-2026/Q38/Q38_v3` | 2 choices comparten imagen |
| `prueba-invierno-2026/Q48/Q48_v1` | 2 choices comparten imagen |
| `prueba-invierno-2026/Q48/Q48_v7` | 2 choices comparten imagen |
| `prueba-invierno-2026/Q50/Q50_v1` | 2 choices comparten imagen |
| `prueba-invierno-2026/Q50/Q50_v4` | 2 choices comparten imagen |
| `prueba-invierno-2026/Q50/Q50_v6` | 2 choices comparten imagen |
| `prueba-invierno-2026/Q50/Q50_v7` | placeholder duplicado (`requiere_nueva_imagen.png`) |
| `prueba-invierno-2026/Q50/Q50_v8` | 2 choices comparten imagen |
| `prueba-invierno-2026/Q7/Q7_v6` | 2 choices comparten imagen |
| `seleccion-regular-2025/Q63/Q63_v4` | 2 imágenes duplicadas, c/u en 2 choices |
| `seleccion-regular-2025/Q63/Q63_v15` | 2 choices comparten imagen |

**Concentración:** Q50 acumula 7/15, Q48 y Q63 suman 4 más. Las preguntas Q38 y Q65 de prueba-invierno aportan el resto.

### 3.2 Imágenes pendientes (src no-HTTP)

**15 variantes aprobadas** con **23 tags `<img>` pendientes** (se excluye `seleccion-regular-2026/Q60/Q60_v3` que tiene un `<img />` vacío sin atributo src — caso anómalo diferente):

| Variante | Pend. | Detalle |
|----------|------:|---------|
| `prueba-invierno-2025/Q33/Q33_v10` | 1 | `q33.png` |
| `prueba-invierno-2025/Q50/Q50_v10` | 1 | `requiere_nueva_imagen.png` |
| `prueba-invierno-2026/Q48/Q48_v8` | 1 | `requiere_nueva_imagen_Q48_v8_1.png` |
| `prueba-invierno-2026/Q50/Q50_v1` | 1 | imagen base del stem |
| `prueba-invierno-2026/Q50/Q50_v3` | 3 | opciones A, C, D |
| `prueba-invierno-2026/Q50/Q50_v4` | 1 | opción D |
| `prueba-invierno-2026/Q50/Q50_v6` | 1 | opción B |
| `prueba-invierno-2026/Q50/Q50_v7` | 2 | 2× `requiere_nueva_imagen.png` |
| `prueba-invierno-2026/Q50/Q50_v8` | 2 | opciones B, C |
| `prueba-invierno-2026/Q6/Q6_v9` | 1 | stem (ítem depende de infografía) |
| `prueba-invierno-2026/Q7/Q7_v10` | 1 | opción D |
| `prueba-invierno-2026/Q7/Q7_v3` | 2 | opciones A, C |
| `seleccion-regular-2025/Q62/Q62_v2` | 1 | stem |
| `seleccion-regular-2025/Q63/Q63_v1` | 4 | las 4 opciones |
| `seleccion-regular-2025/Q65/Q65_v2` | 1 | `attached_image_1.png` (patrón distinto) |

**Q50** concentra **11/23** tags pendientes; `Q63_v1` y `Q7` suman 7 más.

### 3.3 Hallazgos positivos

- Integridad QTI básica OK en las 1,951 variantes: no aparecieron variantes con número incorrecto de choices ni claves correctas ausentes.
- Spot-check manual de `seleccion-regular-2026/Q30/Q30_v13` y `prueba-invierno-2026/Q38/Q38_v10` muestra variantes limpias que preservan el constructo del source.

---

## 4. Acciones requeridas

| # | Acción | Estado | Prioridad |
|---|--------|--------|-----------|
| 1 | ~~Actualizar `connections.json`: `A-M1-NUM-03-01` → `A-EB8-NUM-01-15`~~ | ✅ Hecho | — |
| 2 | Re-correr validación sobre `atoms.json` actual (1,135 post-fix) | Pendiente | Media |
| 3 | Decidir si el mínimo de criterios por atom debe ser 2–3 (740/1,135 tienen < 3) | Pendiente | Media |
| 4 | Revisar los 3 atoms sobrecargados (6–8 criterios) y evaluar re-split | Pendiente | Baja |
| 5 | Corregir las 15 variantes aprobadas con imagen S3 duplicada entre choices | Pendiente | Alta |
| 6 | Completar los 23 tags de imagen pendientes en 15 variantes (priorizar Q50 y Q6_v9) | Pendiente | Media |
| 7 | Correr question generation para prereq atoms Layer 1 (55 atoms, 0 outputs hoy) | Pendiente | Alta |

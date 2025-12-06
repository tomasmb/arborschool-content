# TODO: Mejoras al Prompt de Generación de Átomos

**Fecha**: 2025-12-05  
**Estado**: Pendiente para mañana

## Evaluaciones Realizadas

### Gemini (v12)
- **Calidad general**: Excellent
- **Átomos con issues**: 2
- **Problemas identificados**:
  - A-M1-NUM-01-14: Combina estrategias cognitivamente distintas (fracciones vs decimales)
  - A-M1-NUM-01-22: Menciona dos algoritmos muy diferentes (transformación vs división directa)

### OpenAI (v12)
- **Calidad general**: Good
- **Átomos con issues**: 3
- **Problemas identificados**:
  - A-M1-NUM-01-08: Integra varias micro-habilidades, falta prerrequisito A-03
  - A-M1-NUM-01-14: Menciona "multiplicación cruzada" (solapamiento con proporcionalidad)
  - A-M1-NUM-01-18: Menciona "multiplicación cruzada" (inusual, puede confundir)
  - A-M1-NUM-01-22: Dos algoritmos distintos en un solo átomo

## Tareas Pendientes

### 1. Refuerzo del Prompt
- [ ] Separar algoritmos distintos cuando requieren estrategias cognitivas diferentes
- [ ] Eliminar referencias a "multiplicación cruzada" del prompt
- [ ] Aclarar límites de complejidad en `notas_alcance`
- [ ] Reforzar la separación de procedimientos con estrategias cognitivas diferentes

### 2. Áreas Faltantes (según OpenAI)
- [ ] Considerar si agregar representación explícita de porcentajes como forma equivalente de racionales
- [ ] Considerar problemas que integren Z y Q en un mismo contexto (más allá de átomos separados)

### 3. Ajustes Específicos
- [ ] A-M1-NUM-01-08: Agregar prerrequisito A-03 (comparación de enteros)
- [ ] A-M1-NUM-01-14: Separar comparación de fracciones vs decimales, o aclarar estrategia preferente
- [ ] A-M1-NUM-01-18: Eliminar mención a "multiplicación cruzada", dejar solo algoritmo estándar
- [ ] A-M1-NUM-01-22: Definir algoritmo preferente o separar en dos átomos

### 4. Próximos Pasos
- [ ] Ajustar el prompt en `app/atoms/prompts.py`
- [ ] Ejecutar nuevo test (v13)
- [ ] Evaluar con Gemini y OpenAI
- [ ] Comparar resultados y decidir si es necesario otro ajuste

## Notas
- El prompt actual (v12) ya tiene prerrequisitos exhaustivos funcionando bien
- La granularidad general es apropiada según ambos evaluadores
- Los issues son menores y específicos, no problemas estructurales
- Mantener el enfoque genérico (sin overfitting) al hacer ajustes


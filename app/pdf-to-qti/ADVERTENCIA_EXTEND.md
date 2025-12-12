# ⚠️ ADVERTENCIA IMPORTANTE: Uso de Extend.ai

## 💰 Créditos Limitados

**Extend.ai tiene créditos gratuitos limitados.** Usa la API con cuidado.

## 🔄 Parsing es Determinístico

**El parsing de Extend.ai es 100% determinístico.** Esto significa:

- ✅ El mismo PDF siempre produce el mismo resultado
- ✅ **NO necesitas parsear el mismo PDF más de una vez**
- ❌ Re-parsear es **gastar créditos innecesariamente**

## ✅ Buenas Prácticas

### 1. Parsear UNA SOLA VEZ por PDF

```bash
# Primera vez: Parsear el PDF
python run.py mi-prueba.pdf --step parse --output ./output

# ✅ Guarda el parsed.json generado
# ✅ Este archivo es tu "caché" - reutilízalo siempre
```

### 2. Reutilizar parsed.json

```bash
# Para trabajos futuros, usa el parsed.json guardado
python run.py ./output/parsed.json --step segment --output ./output
python run.py ./output/segmented.json --step generate --output ./output
```

### 3. Organizar tus archivos

```
mis-pruebas/
├── prueba-1.pdf
├── prueba-1-parsed.json    # ← Guarda esto!
├── prueba-2.pdf
├── prueba-2-parsed.json    # ← Guarda esto!
└── ...
```

## 🛡️ Protecciones en el Código

El módulo ya tiene protecciones:

1. **Detección automática**: Si `parsed.json` existe, **NO re-parsea**
2. **Advertencia clara**: Te avisa si intentas re-parsear
3. **Skip automático**: Usa el archivo existente en lugar de gastar créditos

## ❌ NO HAGAS ESTO

```bash
# ❌ MAL: Parsear el mismo PDF múltiples veces
python run.py prueba.pdf --step parse --output ./output1
python run.py prueba.pdf --step parse --output ./output2  # ¡Gastaste créditos!
python run.py prueba.pdf --step parse --output ./output3  # ¡Gastaste créditos!

# ✅ BIEN: Parsear una vez, reutilizar después
python run.py prueba.pdf --step parse --output ./output
python run.py ./output/parsed.json --step segment --output ./output
python run.py ./output/segmented.json --step generate --output ./output
```

## 📋 Checklist Antes de Parsear

Antes de ejecutar `--step parse`:

- [ ] ¿Ya tengo un `parsed.json` para este PDF?
- [ ] ¿Estoy seguro de que necesito parsear este PDF ahora?
- [ ] ¿Guardé el `parsed.json` de parseos anteriores?

## 💡 Recomendación

**Parsear solo cuando:**
- Es un PDF nuevo que nunca has procesado
- Necesitas el resultado inmediatamente
- Tienes créditos disponibles

**NO parsear si:**
- Ya tienes el `parsed.json` guardado
- Solo quieres probar otros pasos del pipeline
- El PDF ya fue procesado antes

---

**Recuerda: Un parse = créditos gastados. Reutiliza siempre que sea posible.**

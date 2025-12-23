# Setup Guide - PDF to QTI

## ✅ Verificación Rápida

Ejecuta el script de verificación:

```bash
cd app/pdf-to-qti
python check_setup.py
```

## 📦 Dependencias

Las dependencias están definidas en `pyproject.toml` como optional dependencies:

```bash
# Instalar todas las dependencias del módulo
pip install -e ".[pdf-to-qti]"

# O instalar manualmente:
pip install click requests google-genai openai boto3 Pillow pydantic python-dotenv
```

## 🔑 Variables de Entorno

El módulo busca el archivo `.env` en la raíz del proyecto (`/Users/francosolari/Arbor/arborschool-content/.env`).

### Mínimo Requerido

Para usar el módulo necesitas **al menos uno** de estos proveedores de IA:

```bash
# Opción 1: Gemini (recomendado)
GEMINI_API_KEY=tu-api-key-aqui

# Opción 2: OpenAI GPT
OPENAI_API_KEY=tu-api-key-aqui

# Opción 3: Claude via AWS Bedrock
AWS_ACCESS_KEY_ID=tu-access-key
AWS_SECRET_ACCESS_KEY=tu-secret-key
AWS_REGION=us-east-1
```

### Para Parsing de PDFs (Opcional)

Solo necesario si quieres parsear PDFs desde cero:

```bash
EXTEND_API_KEY=tu-extend-api-key
```

**Nota:** Si ya tienes un `parsed.json`, no necesitas `EXTEND_API_KEY`.

## 🚀 Uso Básico

### Desde el directorio del módulo:

```bash
cd app/pdf-to-qti

# Pipeline completo
python run.py input.pdf --output ./output --provider gemini

# Paso por paso (recomendado)
python run.py input.pdf --step parse --output ./output
python run.py ./output/parsed.json --step segment --output ./output
python run.py ./output/segmented.json --step generate --output ./output
python run.py ./output/qti --step validate --output ./output
```

### Desde la raíz del proyecto:

```bash
# Usando Python path
PYTHONPATH=app/pdf-to-qti python -m app.pdf-to-qti.run input.pdf --output ./output
```

## 📝 Estado Actual

Según la última verificación:

- ✅ Dependencias instaladas
- ✅ GEMINI_API_KEY configurada
- ⚠️  EXTEND_API_KEY no configurada (solo necesaria para parsear PDFs nuevos)

## 🔍 Troubleshooting

### Error: "No AI provider credentials found"

- Verifica que el `.env` esté en la raíz del proyecto
- Verifica que al menos una API key esté configurada
- Ejecuta `python check_setup.py` para diagnóstico

### Error: "Module not found"

- Asegúrate de ejecutar desde `app/pdf-to-qti/` o ajusta el PYTHONPATH
- Verifica que las dependencias estén instaladas: `pip list | grep click`

### Error: "EXTEND_API_KEY required"

- Solo necesario para el paso `parse`
- Si ya tienes `parsed.json`, omite el paso parse y empieza desde `segment`

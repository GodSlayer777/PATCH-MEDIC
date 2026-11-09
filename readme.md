# 🩹 patch-medic

> **Autonomous CLI & GitHub Action for pytest test triage, AST-based token pruning, and sandboxed self-healing patches using LLMs.**

`patch-medic` ejecuta tu suite de pruebas con `pytest`, intercepta los fallos en tiempo de ejecución, aísla mediante análisis estático (AST) únicamente la función responsable para minimizar el consumo de tokens y utiliza un LLM para generar y aplicar parches `git diff` atómicos y tolerantes a regresiones.

---

## 🚀 Características

- **Zero-Noise AST Token-Pruner**: Recorta el código fuente para enviar únicamente el nodo de la función culpable al modelo, no archivos completos.
- **Fail-Safe Regression Verification**: Valida primero la prueba unitaria afectada y luego la suite completa. Si se detectan efectos secundarios, revierte los cambios automáticamente.
- **Git-Native Tolerant Diffing**: Aplica parches mediante `git apply` con compatibilidad multiplataforma (Windows/Linux/macOS) y flags de tolerancia a saltos de línea y numeración.
- **CI Ready**: Incluye una GitHub Composite Action (`action.yml`) que aísla parches en ramas temporales (`patch/auto-fix-...`) sin tocar `main`.

---

## 📦 Instalación

Requiere **Python 3.10+**.

```bash
# Clonar el repositorio
git clone [https://github.com/GodSlayer777/PATCH-MEDIC.git](https://github.com/GodSlayer777/PATCH-MEDIC.git)
cd PATCH-MEDIC

# Crear y activar entorno virtual
python -m venv env

# En Windows (CMD/PowerShell):
.\env\Scripts\activate
# En Git Bash / Linux / macOS:
source env/Scripts/activate

# Instalar dependencias y registrar el CLI en modo editable
pip install -r requirements.txt
pip install -e .
```

---

## ⚙️ Configuración

Configura tu clave de API para el modelo:

```bash
# Git Bash / Linux / macOS
export GEMINI_API_KEY="tu_api_key_aqui"
export LLM_MODEL="gemini-1.5-flash"

# Windows CMD
set GEMINI_API_KEY=tu_api_key_aqui
set LLM_MODEL=gemini-1.5-flash

# Windows PowerShell
$env:GEMINI_API_KEY="tu_api_key_aqui"
$env:LLM_MODEL="gemini-1.5-flash"
```

---

## 🛠️ Uso

### Reparar un archivo de pruebas específico
```bash
patch-medic heal --target tests/test_sample_broken.py
```

### Ejecutar sobre toda la suite del proyecto
```bash
patch-medic heal
```

### Opciones disponibles
- `--target <ruta>`: Especifica un archivo o test puntual a evaluar.
- `--max-retries <n>`: Número máximo de intentos de reparación por fallo (por defecto: `2`).

---

## 🤖 Uso en GitHub Actions

Agrega `patch-medic` a tus workflows de CI:

```yaml
steps:
  - uses: actions/checkout@v4
  - uses: GodSlayer777/PATCH-MEDIC@main
    with:
      llm_api_key: ${{ secrets.GEMINI_API_KEY }}
      github_token: ${{ secrets.GITHUB_TOKEN }}
```

---

## 📄 Licencia

Distribuido bajo la licencia MIT.
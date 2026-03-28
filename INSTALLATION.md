# 📦 Guía de Instalación - Abliterador Studio

**Versión:** `0.4.0` | **Última actualización:** 2026-03-28

Abliterador Studio se puede instalar de varias formas dependiendo de tu sistema y necesidades.

---

## Requisitos Mínimos Globales

- **Sistema Operativo:** Windows 10+, macOS 10.14+, o Linux (Ubuntu 18.04+, Debian 11+, etc.)
- **RAM:** 4 GB mínimo (8 GB recomendado para 4B+ modelos)
- **Espacio disco:** 10 GB mínimo (20+ GB si usarás modelos HF pesados)
- **Internet:** Conexión requerida para primera descarga de modelos

---

## Opción 1: Ejecutable Precompilado (Más Fácil)

**Ideal para:** Usuarios finales sin Python instalado

### Windows

1. **Descarga el instalador:**
   - Ve a [Releases](https://github.com/Azrael-Hagen/abliterador/releases)
   - Descarga `AbliteradorStudio_v0.4.0_Windows.zip`

2. **Instala:**
   ```cmd
   # Descomprime el ZIP
   # Haz doble clic en AbliteradorStudio.exe
   ```
   
3. **¡Listo!** No requiere Python ni dependencias adicionales.

**Tamaño:** ~350 MB (contiene todo bundled)

### macOS

1. **Descarga:**
   - Ve a [Releases](https://github.com/Azrael-Hagen/abliterador/releases)
   - Descarga `AbliteradorStudio_v0.4.0_macOS.tar.gz`

2. **Instala:**
   ```bash
   tar -xzf AbliteradorStudio_v0.4.0_macOS.tar.gz
   cd AbliteradorStudio
   ./AbliteradorStudio
   ```

### Linux

1. **Descarga:**
   - Ve a [Releases](https://github.com/Azrael-Hagen/abliterador/releases)
   - Descarga `AbliteradorStudio_v0.4.0_Linux.tar.gz`

2. **Instala:**
   ```bash
   tar -xzf AbliteradorStudio_v0.4.0_Linux.tar.gz
   cd AbliteradorStudio
   ./AbliteradorStudio
   ```

---

## Opción 2: Instalación desde Código Fuente (Recomendado para Desarrollo)

**Requisitos previos:**
- Python 3.10+ ([Descarga aquí](https://www.python.org/downloads/))
- Git ([Descarga aquí](https://git-scm.com/))

### Pasos Comunes (Windows, macOS, Linux)

1. **Clona el repositorio:**
   ```bash
   git clone https://github.com/Azrael-Hagen/abliterador.git
   cd abliterador
   ```

2. **Crea un entorno virtual** (altamente recomendado):
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   # macOS / Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Instala dependencias:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Ejecuta la aplicación:**
   ```bash
   python abliterador_studio.py
   ```

**Alternativa con setup.py (Instalación "global" en venv):**
```bash
pip install -e .
abliterador-studio  # Comando disponible en cualquier ruta del terminal
```

---

## Opción 3: Compilar Tu Propio Ejecutable

**Ideal para:** Publicar a otros usuarios o crear distribuciones customizadas

**Requisitos previos:**
- Python 3.10+
- Código fuente clonado (ver Opción 2, pasos 1-2)

### Pasos

1. **Instala herramientas de build:**
   ```bash
   pip install -e ".[dev]"
   ```
   Esto instala todas las dependencias + PyInstaller

2. **Compila el ejecutable:**
   ```bash
   python build_installer.py
   ```
   
   **Opciones:**
   ```bash
   python build_installer.py --onefile     # Single .exe/binary (+ gran tamaño ~400MB)
   python build_installer.py --windows     # Target Windows
   python build_installer.py --linux       # Target Linux
   ```

3. **Resultado:**
   ```
   dist/
   ├── AbliteradorStudio/              # Carpeta con ejecutable y librerías
   │   ├── AbliteradorStudio.exe       # (Windows) o AbliteradorStudio (Linux/macOS)
   │   ├── _internal/                  # Dependencias bundled
   │   └── ...
   └── AbliteradorStudio.exe           # O .exe integrado si usaste --onefile
   ```

4. **Distribuye:**
   - ZIP la carpeta `dist/AbliteradorStudio/` para otros usuarios
   - O el `.exe` único si compilaste con `--onefile`
   - Sube a releases en GitHub

---

## Verificación Post-Instalación

Después de instalar por cualquier método, verifica que funcione:

```bash
# Si ejecutable:
./AbliteradorStudio          # (Linux/macOS)
AbliteradorStudio.exe        # (Windows)

# Si desde código fuente:
python abliterador_studio.py
```

**Deberías ver:**
1. Ventana GUI con título "Abliterador Studio v0.4.0"
2. Sección de búsqueda de modelos
3. Logs iniciales en la consola (si ejecutaste desde terminal)

---

## Instalación de Ollama (Opcional pero Recomendado)

Para usar modelos locales de Ollama con máximo rendimiento:

1. **Descarga e instala** [Ollama](https://ollama.ai/)

2. **Inicia el servicio:**
   ```bash
   ollama serve
   ```

3. **En otra terminal, descarga un modelo:**
   ```bash
   ollama pull qwen2.5:0.5b     # Ultra rápido en CPU
   ```

4. La app detectará automáticamente tus modelos Ollama al abrir.

---

## Troubleshooting

### ❌ "No se encuentra Python 3.10+"
**Solución:**
- Descarga Python desde [python.org](https://www.python.org/downloads/)
- Asegúrate de marcar "Add Python to PATH" durante instalación

### ❌ "ModuleNotFoundError: No module named 'PySide6'"
**Solución:**
```bash
pip install -r requirements.txt
```

### ❌ "Port 11434 already in use" (Ollama)
**Causa:** Ollama ya está corriendo
**Solución:**
```bash
# Detén el proceso anterior
killall ollama      # macOS/Linux
taskkill /IM ollama.exe  # Windows
```

### ❌ "CUDA out of memory"
**Solución:**
- Selecciona modelos más pequeños (≤3.8B params)
- Usa CPU-only mode (sin GPU)
- Aumenta RAM disponible

### ❌ "La app se cuelga al cargar modelo"
**Solución:**
- Revisa `logs/abliterador.log` para errores
- Intenta modelo más pequeño (< 4B)
- Reinicia Ollama o descarga local

---

## Actualización

### Desde Ejecutable
- Descarga nueva versión de [Releases](https://github.com/Azrael-Hagen/abliterador/releases)
- Reemplaza el ejecutable / carpeta anterior

### Desde Código Fuente
```bash
cd abliterador
git pull origin main
pip install --upgrade -r requirements.txt
python abliterador_studio.py
```

---

## Contacto & Soporte

- **Issues:** [GitHub Issues](https://github.com/Azrael-Hagen/abliterador/issues)
- **Logs:** Revisa `logs/abliterador.log` para diagnóstico
- **Documentación:** [README.md](README.md)

---

## Notas de Seguridad

✅ **Datos locales:** Abliterador Studio no envía datos a servidores externos (solo descargas de HF/Ollama)

✅ **Modelos:** Los modelos se descargan y almacenan localmente en tu máquina

✅ **Prompts:** Los prompts y generaciones se procesan 100% localmente

⚠️ **Puertos:** Si usas Ollama, escucha en `localhost:11434` (no accesible remotamente por defecto)

---

**¡Disfruta usando Abliterador Studio! 🚀**

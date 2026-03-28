# 🔨 Building Executables for Abliterador Studio

Este documento proporciona instrucciones detalladas para compilar ejecutables distribucibles para Windows, macOS y Linux.

---

## Requisitos Previos (Todos los Sistemas)

```bash
# 1. Clona el repositorio
git clone https://github.com/Azrael-Hagen/abliterador.git
cd abliterador

# 2. Crea un entorno virtual
python3 -m venv .venv
source .venv/bin/activate     # macOS/Linux
.venv\Scripts\activate        # Windows

# 3. Instala buildtools
pip install --upgrade pip
pip install -e ".[dev]"       # Instala deps + PyInstaller
```

---

## 🪟 Windows Build

### Requisitos Adicionales
- Windows 10 o superior
- Visual C++ Runtime (generalmente preinstalado)

### Pasos

```bash
# Activa el venv
.venv\Scripts\activate

# Compila
python build_installer.py

# Resultado: dist\AbliteradorStudio\AbliteradorStudio.exe (~350MB)
```

**Para single-file executable (más portátil, +100MB):**
```bash
python build_installer.py --onefile
# Resultado: dist\AbliteradorStudio.exe (~400MB, totalmente independiente)
```

**Distribución:**
```bash
# Opción A: Carpeta
Compress-Archive -Path dist\AbliteradorStudio -DestinationPath AbliteradorStudio_v0.4.0_Windows.zip

# Opción B: Single exe  
Compress-Archive -Path dist\AbliteradorStudio.exe -DestinationPath AbliteradorStudio_v0.4.0_Windows.zip
```

---

## 🍎 macOS Build

### Requisitos Adicionales
- Xcode Command Line Tools: `xcode-select --install`
- macOS 10.14+

### Pasos

```bash
# Activa el venv
source .venv/bin/activate

# Compila
python build_installer.py

# Resultado: dist/AbliteradorStudio/AbliteradorStudio (~350MB bundle)
```

**Para single-file (si deseas, though less common on macOS):**
```bash
python build_installer.py --onefile
# Resultado: dist/AbliteradorStudio (~400MB executable)
```

**Distribución (crear dmg o tar.gz):**
```bash
# Tar.gz (más universal)
tar -czf AbliteradorStudio_v0.4.0_macOS.tar.gz -C dist AbliteradorStudio

# O DMG (más "Mac-like", requiere dmgbuild)
pip install dmgbuild
python -m dmgbuild -s dmgbuild_settings.py "Abliterador Studio" AbliteradorStudio.dmg dist/AbliteradorStudio
```

---

## 🐧 Linux Build

### Requisitos Adicionales
Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install python3-dev python3-pip python3-venv libfuse2 -y
```

Arch:
```bash
sudo pacman -S python python-pip fuse2 -y
```

### Pasos

```bash
# Activa el venv
source .venv/bin/activate

# Compila
python build_installer.py

# Resultado: dist/AbliteradorStudio/AbliteradorStudio (~350MB directory)
```

**Distribución (tar.gz):**
```bash
tar -czf AbliteradorStudio_v0.4.0_Linux.tar.gz -C dist AbliteradorStudio
```

**O crear AppImage (distribución universal Linux):**
```bash
pip install appimage-builder
appimage-builder --recipe AppImageBuilder.yml
# (requiere AppImageBuilder.yml setup)
```

---

## ☁️ Cross-Platform Notes

### Limitaciones
- **PyInstaller NO es cross-compiler:**
  - Para Windows .exe, necesitas compilar EN Windows
  - Para macOS app, necesitas compilar EN macOS
  - Para Linux binary, necesitas compilar EN Linux
- Cada binario es específico del OS (no es Unix universal)

### Alternativa: GitHub Actions (CI/CD)
Para automatizar builds en todos los sistemas:

```yaml
# .github/workflows/build-release.yml
name: Build Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -e ".[dev]"
      - run: python build_installer.py --onefile
      - uses: softprops/action-gh-release@v1
        with:
          files: dist/AbliteradorStudio.exe

  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -e ".[dev]"
      - run: python build_installer.py --onefile
      - run: tar -czf AbliteradorStudio_macOS.tar.gz -C dist AbliteradorStudio
      - uses: softprops/action-gh-release@v1

  build-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -e ".[dev]"
      - run: python build_installer.py --onefile
      - run: tar -czf AbliteradorStudio_Linux.tar.gz -C dist AbliteradorStudio
      - uses: softprops/action-gh-release@v1
```

---

## 📦 Distribución a Usuarios

### Opción A: GitHub Releases (Recomendado)

```bash
# 1. Crea GitHub Release en https://github.com/Azrael-Hagen/abliterador/releases
# 2. Sube los archivos:
#    - AbliteradorStudio_v0.4.0_Windows.zip
#    - AbliteradorStudio_v0.4.0_macOS.tar.gz
#    - AbliteradorStudio_v0.4.0_Linux.tar.gz

# 3. Usuarios descargan y descomprimen directamente - ¡Listo!
```

### Opción B: PyPI

```bash
# 1. Instala build tools
pip install wheel twine build

# 2. Construye distribuciones
python -m build

# 3. Upload a PyPI (o TestPyPI para probar)
twine upload dist/abliterador-studio-0.4.0.tar.gz dist/abliterador*-py3-none-any.whl
```

Luego usuarios hacen:
```bash
pip install abliterador-studio
abliterador-studio  # ¡Ejecutar desde cualquier lugar!
```

---

## 🧪 Verificación Pre-Release

Antes de subir a releases, verifica:

```bash
# 1. Test en máquina limpia (sin dev deps)
rm -rf .venv dist build *.egg-info
python -m venv .venv_test
source .venv_test/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python abliterador_studio.py

# 2. Verifica que no haya errores de importación
python -c "import abliterador_app; print('OK')"

# 3. Limpia
deactivate
rm -rf .venv_test

# 4. Compila ejecutable
python build_installer.py

# 5. Prueba el ejecutable
./dist/AbliteradorStudio/AbliteradorStudio  # o .exe en Windows

# 6. Verifica: interfaz aparece, logs funcionan, botones responden
```

---

## 📋 Checklist Final Release

- [ ] Actualizar `APP_VERSION` en `abliterador_studio.py`
- [ ] Actualizar `CHANGELOG.md` con cambios
- [ ] Commit y push a main
- [ ] Compilar en Windows → zip
- [ ] Compilar en macOS → tar.gz
- [ ] Compilar en Linux → tar.gz
- [ ] Crear GitHub Release `vX.Y.Z`
- [ ] Subir los 3 executables a la release
- [ ] Verificar descargas + prueba descomprimir
- [ ] Actualizar README con links a release
- [ ] Anunciar en redes/docs

---

## 🐛 Troubleshooting

### "ImportError: No module named 'heretic'"
```bash
pip install heretic-llm  # O desde source si necesario
python build_installer.py --clean
python build_installer.py
```

### "pyinstaller: command not found"
```bash
pip install -e ".[dev]"  # Reinstala con dev extras
python build_installer.py
```

### Executable no se inicia / error criptográfico
```bash
# Asegúrate que el .venv está limpio
deactivate
rm -rf .venv dist build
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python build_installer.py --clean
python build_installer.py
```

### Archivo muy grande (>500MB)
- Usa `--onefile` para ahorrar repetición de libs
- O con `--onedir` descomprime el .onefile para distribución



---

**¡Listo para distribuir! 🚀**

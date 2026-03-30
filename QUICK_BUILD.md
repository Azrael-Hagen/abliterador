# 🏗️ INSTRUCCIONES PARA COMPILAR EJECUTABLES - v0.7.0

Sigue estos pasos **en cada sistema operativo** para criar los ejecutables precompilados que pueden ser distribuidos.

---

## 📋 Requisitos Previos (En Tu Máquina)

### Todos los sistemas
- Python 3.10+ instalado
- pip funcionando
- Git instalado

### Velocidad esperada
~5-10 minutos por sistema, principalmente descarga + compilación

---

## 🪟 En WINDOWS

```powershell
# 1. Abre PowerShell en la carpeta del proyecto
cd C:\Users\Azrael\OneDrive\Documentos\Herramientas\abliterador

# 2. Crea entorno virtual limpio
python -m venv .venv_build
.venv_build\Scripts\activate

# 3. Instala dependencias
pip install --upgrade pip
pip install -e ".[dev]"

# 4. Compila ejecutable
python build_installer.py --onefile

# 4b. Compila ejecutable servidor all-in-one (IP visible en consola)
python build_installer.py --onefile --all-in-one

# 5. Resultado
# → Busca: dist\AbliteradorStudio.exe (~400MB)
# → Busca también: dist\AbliteradorAllInOne.exe (servidor web LAN)

# 6. Crea ZIP para distribución
# Manualmente: Click derecho → Enviar a → Carpeta comprimida
# Nombra: AbliteradorStudio_v0.4.0_Windows.zip

# 7. Limpia (opcional)
deactivate
Remove-Item .venv_build -Recurse -Force
```

**Verificación:**
```powershell
# Abre una PowerShell NUEVA (sin venv)
# Navega al ZIP extraído
cd AbliteradorStudio
.\AbliteradorStudio.exe
# → Debería abrir GUI sin errores

# O prueba servidor all-in-one:
.\AbliteradorAllInOne.exe
# → Debe mostrar versión + IPs LAN + FTP LAN y habilitar Admin Studio Web

# Ruta exacta del ejecutable en este proyecto
# C:\Users\Azrael\OneDrive\Documentos\Herramientas\abliterador\dist\AbliteradorAllInOne.exe

# Ejecución directa por ruta absoluta
& "C:\Users\Azrael\OneDrive\Documentos\Herramientas\abliterador\dist\AbliteradorAllInOne.exe"

# 8. (Opcional Windows Server) Instala arranque automatico
powershell -ExecutionPolicy Bypass -File .\setup_windows_server_service.ps1 -Action install -Port 8088 -FtpPort 2121
# → Instala servicio (NSSM) o tarea programada ONSTART
```

---

## 🍎 En MACOS

```bash
# 1. Abre Terminal en la carpeta del proyecto
cd ~/OneDrive/Documentos/Herramientas/abliterador

# 2. Crea entorno virtual limpio
python3 -m venv .venv_build
source .venv_build/bin/activate

# 3. Instala dependencias
pip install --upgrade pip
pip install -e ".[dev]"

# 4. Compila ejecutable
python build_installer.py --onefile

# 5. Resultado
# → Busca: dist/AbliteradorStudio (~400MB)

# 6. Crea tar.gz para distribución
cd dist
tar -czf ../AbliteradorStudio_v0.4.0_macOS.tar.gz AbliteradorStudio
ls -lh ../AbliteradorStudio_v0.4.0_macOS.tar.gz

# 7. Limpia (opcional)
cd ..
deactivate
rm -rf .venv_build
```

**Verificación:**
```bash
# En Terminal nueva
cd /tmp
tar -xzf ~/ABLiterador/AbliteradorStudio_v0.4.0_macOS.tar.gz
./AbliteradorStudio/AbliteradorStudio
# → Debería abrir GUI (puede pedir permiso seguridad, permitir)
```

---

## 🐧 En LINUX

```bash
# 1. Abre Terminal en la carpeta del proyecto
cd ~/Documentos/Herramientas/abliterador

# 2. [SOLO PRIMERA VEZ] Instala dependencias del sistema
sudo apt-get update
sudo apt-get install python3-dev python3-pip python3-venv libfuse2 -y
# O en Arch:
# sudo pacman -S python python-pip fuse2 -y

# 3. Crea entorno virtual limpio
python3 -m venv .venv_build
source .venv_build/bin/activate

# 4. Instala dependencias
pip install --upgrade pip
pip install -e ".[dev]"

# 5. Compila ejecutable
python build_installer.py --onefile

# 6. Resultado
# → Busca: dist/AbliteradorStudio (~400MB)

# 7. Crea tar.gz para distribución
cd dist
tar -czf ../AbliteradorStudio_v0.4.0_Linux.tar.gz AbliteradorStudio
ls -lh ../AbliteradorStudio_v0.4.0_Linux.tar.gz

# 8. Limpia (opcional)
cd ..
deactivate
rm -rf .venv_build
```

**Verificación:**
```bash
# En Terminal nueva
cd /tmp
tar -xzf ~/abliterador/AbliteradorStudio_v0.4.0_Linux.tar.gz
./AbliteradorStudio/AbliteradorStudio
# → Debería abrir GUI
```

---

## 📦 Después de Compilar

### Tienes 3 archivos

```
AbliteradorStudio_v0.4.0_Windows.zip  (~350MB)
AbliteradorStudio_v0.4.0_macOS.tar.gz  (~350MB)
AbliteradorStudio_v0.4.0_Linux.tar.gz  (~350MB)
```

### Subirlos a GitHub Release

1. Ve a: https://github.com/Azrael-Hagen/abliterador/releases

2. Click: "Draft a new release"

3. Completa:
   - **Tag:** `v0.4.0` (o selecciona del dropdown)
   - **Title:** `Abliterador Studio v0.4.0 - Professional Distribution`
   - **Description:** (copia de READY_TO_DISTRIBUTE.md)
   - **Assets:** Upload los 3 ZIPs

4. Click: "Publish release"

5. Verifica que aparecen los 3 downloads

---

## ⚡ Comando Rápido (Todos los Pasos)

Si has hecho esto antes, aquí está el mini-resumen:

**Windows:**
```powershell
python -m venv .venv_build; .venv_build\Scripts\activate; pip install -e ".[dev]"; python build_installer.py --onefile
```

**macOS/Linux:**
```bash
python3 -m venv .venv_build && source .venv_build/bin/activate && pip install -e ".[dev]" && python build_installer.py --onefile
```

---

## 🆘 Problemas Comunes

### Windows: "pyinstaller command not found"
```powershell
pip install -e ".[dev]"
python build_installer.py --clean
python build_installer.py --onefile
```

### macOS: "xcrun: error: unable to find utility"
```bash
xcode-select --install
pip install -e ".[dev]"
python build_installer.py --onefile
```

### Linux: "libfuse.so.2 not found"
```bash
sudo apt-get install libfuse2  # Ubuntu/Debian
pip install -e ".[dev]"
python build_installer.py --onefile
```

### Cualquiera: Archivo muy grande (>500MB)"
- Es normal (PySide6 + torch + transformers son grandes)
- Usa `--onedir` si no te importa el tamaño total
- O zip el directorio para comprimir más

---

## ✅ Checklist Pre-Release

- [ ] Compilé en Windows → ZIP
- [ ] Compilé en macOS → tar.gz
- [ ] Compilé en Linux → tar.gz
- [ ] Probé cada ejecutable en máquina LIMPIA (sin venv)
- [ ] GUI abrió sin errores
- [ ] Logs funcionan
- [ ] Botones responden
- [ ] Subí a GitHub Release
- [ ] Descargué desde release para verificar
- [ ] Probé otra vez post-descarga

**Si todo es verde: ¡READY TO SHIP!** 🚀

---

**Si tienes dudas exactas, revisa BUILD_GUIDE.md para más detalle.**

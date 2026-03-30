# Abliterador Studio

**Versión actual:** `v0.9.0` — *2026-03-30* 🎨

Aplicacion GUI en PySide6 para buscar modelos, cargarlos localmente, aplicar abliteración y probar generacion de texto.

### 📥 Instalación Rápida

**La forma más fácil: Descarga el ejecutable**
- Ve a [Releases](https://github.com/Azrael-Hagen/abliterador/releases)
- Descarga `AbliteradorStudio_vX.X.X_[SistemaOperativo].zip`
- No requiere Python instalado ✅

**O instala desde código fuente:**
```bash
git clone https://github.com/Azrael-Hagen/abliterador.git
cd abliterador
pip install -r requirements.txt
python abliterador_studio.py
```

👉 **[Ver guía completa de instalación →](INSTALLATION.md)**

---

## Historial de versiones resumido

| Versión | Fecha | Cambios principales |
|---------|-------|---------------------|
| `0.8.0` | 2026-03-30 | **Web Search Enrichment:** búsqueda internet desde UI servidor, contexto web actualizado en chat y memoria persistente de conocimiento reciente |
| `0.7.0` | 2026-03-30 | **Admin Studio Web:** registro de usuarios, catálogo de roles/permisos, descargas de modelos, auto-recuperación y lanzamiento de GUI de escritorio |
| `0.6.0` | 2026-03-30 | **FTP LAN estilo nube local:** subida/descarga en bibliotecas de Windows, integrado al all-in-one con visibilidad de estado |
| `0.5.0` | 2026-03-29 | **Servidor LAN all-in-one:** hardening web, perfil multiusuario aislado, IP visible, servicio Windows Server, catálogo ampliado |
| `0.4.0` | 2026-03-28 | **Distribución profesional:** setup.py, pyproject.toml, PyInstaller, ejecutables precompilados, INSTALLATION.md 🎁 |
| `0.3.1` | 2026-03-28 | Descarga HF resiliente con reintentos/backoff, auto-recuperación en worker, chip Micro IA durante arranque |
| `0.3.0` | 2026-03-26 | Paquete modular (domain/services/ui), integración real Heretic, factory de backends, GUI profesional |
| `0.2.0` | 2026-03-26 | Worker QThread, controles de generación (tokens, temp, top-p), validaciones de entrada |
| `0.1.0` | 2026-03-26 | Baseline arquitectural: CHECKPOINTS, MODULES, VERSIONING, ENGINEER_LOG |

## Objetivo
Permitir experimentacion local con modelos usando una interfaz simple y segura, priorizando responsividad de GUI y validaciones claras.

## 📦 Cómo Instalar

### Opción 1️⃣: Ejecutable (No requiere Python)
```
Página de Releases → Descargar ZIP → Descomprimir → Ejecutar
```

### Opción 2️⃣: Desde código fuente (Desarrollo)
```bash
git clone https://github.com/Azrael-Hagen/abliterador.git
cd abliterador
pip install -r requirements.txt
python abliterador_studio.py
```

### Opción 3️⃣: Ser instalado con pip
```bash
pip install -e .                # Develop mode
pip install abliterador-studio  # (After PyPI submission)
```

### Opción 4️⃣: Compilar tu propio ejecutable
```bash
pip install -e ".[dev]"
python build_installer.py
```

👉 **[Instrucciones detalladas para cada opción →](INSTALLATION.md)**

---

## Dependencias

### Runtime (Automáticas con cualquier instalación)
- PySide6
- transformers
- heretic-llm (paquete que expone el módulo heretic moderno)
- La app usa backend heretic moderno como primera opción para abliteración real.
- Si ese backend falla, intenta compatibilidad legacy con heretic_llm.
- Como último recurso usa fallback de transformers para mantener operatividad (sin abliteración real).

## Arquitectura modular
- abliterador_studio.py: entrypoint principal de ejecución.
- abliterador_basico.py: compatibilidad temporal con nombre legacy.
- abliterador_app/domain/models.py: contratos de datos (GenerationSettings, WorkerTask).
- abliterador_app/services/backends.py: integración de backends y abliteración real.
- abliterador_app/services/worker.py: ejecución en segundo plano con señales Qt.
- abliterador_app/ui/main_window.py: lógica de interfaz y validaciones.

## Ejecutar
python abliterador_studio.py

## Modo Servidor Web (remoto y multiusuario)

Este proyecto ahora incluye un modo web para acceso remoto desde navegador, con autenticacion y sandbox de archivos.

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Configurar variables de entorno recomendadas antes de arrancar:

```bash
# Credenciales del panel web
set ABLITERADOR_WEB_USER=admin
set ABLITERADOR_WEB_PASSWORD=tu_password_fuerte
set ABLITERADOR_WEB_SECRET=tu_secret_largo_y_aleatorio

# Solo red local (1 = habilitado, recomendado)
set ABLITERADOR_LOCAL_NETWORK_ONLY=1

# Host/puerto del servidor
set ABLITERADOR_WEB_HOST=0.0.0.0
set ABLITERADOR_WEB_PORT=8088

# Rendimiento y anti-flood
set ABLITERADOR_MODELS_CACHE_TTL_S=20
set ABLITERADOR_RATE_LIMIT_PER_MINUTE=120

# FTP LAN (solo red local)
set ABLITERADOR_FTP_ENABLED=1
set ABLITERADOR_FTP_HOST=0.0.0.0
set ABLITERADOR_FTP_PORT=2121
set ABLITERADOR_FTP_USER=lanuser
set ABLITERADOR_FTP_PASSWORD=tu_password_ftp
set ABLITERADOR_FTP_ROOT=C:\Users\Azrael

# Ollama remoto/local (OpenAI-compatible endpoint de Ollama)
set ABLITERADOR_OLLAMA_URL=http://127.0.0.1:11434

# Mini IA de diagnostico/autorreparacion
set ABLITERADOR_DIAGNOSTICS_MEMORY=C:\\data\\abliterador_diagnostics_memory.json

# Busqueda web e inteligencia con informacion actualizada
set ABLITERADOR_WEB_SEARCH_ENABLED=1
set ABLITERADOR_WEB_SEARCH_TIMEOUT_S=8
set ABLITERADOR_WEB_SEARCH_CACHE_TTL_S=600
set ABLITERADOR_WEB_SEARCH_MAX_RESULTS=5
set ABLITERADOR_WEB_KNOWLEDGE_PATH=C:\\data\\abliterador_web_knowledge.json
set ABLITERADOR_WEB_KNOWLEDGE_MAX_QUERIES=200

# Comando opcional para lanzar GUI de escritorio desde web admin
set ABLITERADOR_GUI_LAUNCH_CMD=cmd /c C:\\ruta\\launch_abliterador_studio.bat

# Base de perfiles y espacios de usuario
set ABLITERADOR_USERS_DB=C:\\data\\abliterador_users.json
set ABLITERADOR_USER_WORKSPACES_ROOT=C:\\data\\abliterador_workspaces

# Opcional: sandbox legacy compartido (no recomendado para multiusuario)
set ABLITERADOR_ALLOWED_DIRS=C:\\data\\ia_sandbox
```

Iniciar servidor:

```bash
python abliterador_web_server.py
```

Iniciar launcher all-in-one (muestra IPs LAN en consola y versión):

```bash
python abliterador_all_in_one.py
```

Ruta exacta del ejecutable en este entorno Windows Server:

```powershell
C:\Users\Azrael\OneDrive\Documentos\Herramientas\abliterador\dist\AbliteradorAllInOne.exe
```

Ejecutar desde cualquier consola:

```powershell
& "C:\Users\Azrael\OneDrive\Documentos\Herramientas\abliterador\dist\AbliteradorAllInOne.exe"
```

En Windows Server puedes instalar arranque automatico como servicio/tarea:

```powershell
# Compilar onefile all-in-one
python build_installer.py --onefile --all-in-one

# Ejecutar como Administrador (instala servicio NSSM o tarea ONSTART)
powershell -ExecutionPolicy Bypass -File .\setup_windows_server_service.ps1 -Action install -Port 8088 -FtpPort 2121
```

Eliminar servicio/tarea:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_windows_server_service.ps1 -Action remove
```

Abrir en navegador:

```text
http://<ip-del-servidor>:8088
```

La UI también muestra las URLs LAN detectadas en la sección "Acceso LAN".
También muestra el estado de FTP LAN, rutas de bibliotecas y endpoints FTP disponibles.

Admin Studio Web (solo administradores):
- Gestión de usuarios: crear, cambiar rol, activar/desactivar y eliminar.
- Catálogo de roles usuales y permisos: `admin`, `manager`, `operator`, `viewer`.
- Solicitud de descarga de modelos en servidor (`ollama pull`) con estado por job.
- Diagnóstico y ejecución de auto-recuperación del servidor.
- Mini IA de autodiagnóstico con memoria de incidencias y priorización de acciones de autorreparación.
- Búsqueda web en servidor y enriquecimiento opcional del chat con fuentes recientes.
- Lanzamiento de la GUI de escritorio (`AbliteradorStudio`) desde el panel web admin.

Registro de nuevos usuarios:
- Disponible directamente en la UI web (bloque "Registro").
- Rol inicial por defecto para nuevos registros: `viewer`.

Credenciales iniciales por defecto:
- Usuario admin: `admin`
- Password admin: `change_me_now`
- Cambiar inmediatamente en variables de entorno para producción LAN.

Notas de seguridad para produccion:
- Usa password fuerte y secret unico.
- Publica el servicio detras de Nginx/Caddy con HTTPS.
- Mantén `ABLITERADOR_LOCAL_NETWORK_ONLY=1` para bloquear IPs fuera de LAN.
- Cada usuario tiene su carpeta propia dentro de `ABLITERADOR_USER_WORKSPACES_ROOT`.
- El sandbox bloquea paths absolutos y traversal (`../`) por usuario.

Perfiles LAN:
- El usuario admin inicial se crea con `ABLITERADOR_WEB_USER` + `ABLITERADOR_WEB_PASSWORD`.
- Desde la UI (bloque admin) puedes crear usuarios `user` o `admin`.
- Cada perfil nuevo recibe su workspace aislado automáticamente.

## Launcher (Windows)
- Doble clic en launch_abliterador_studio.bat
- O desde terminal: launch_abliterador_studio.bat

## Uso con Ollama (pruebas locales)
- Si tienes modelos en Ollama (ejemplo: qwen2.5:0.5b), puedes escribir ese nombre en la búsqueda y seleccionarlo.
- El sistema detecta el modelo local y activa backend `ollama` automáticamente.
- En backend `ollama` se prueba generación local rápida, pero no se aplica abliteración Heretic real.
- Para abliteración real, usa un modelo que pase por backend `heretic_modern`.

## Flujos E2E a validar
1. Busqueda de modelo: valida entrada vacia y muestra resultados simulados.
2. Carga + abliteracion: selecciona modelo, ejecuta flujo heretic en segundo plano y reporta estado.
3. Generacion: usa prompt configurable y parametros de generacion sin recargar el modelo.
4. Manejo de error: verifica QMessageBox en fallos de carga o generacion.

## Funcionalidades GUI implementadas
- Busqueda y lista de modelos simulada.
- Detección automática de modelos locales (Ollama) al abrir la app.
- Carga y abliteracion de modelo con worker thread (QThread).
- Prompt editable.
- Controles de generacion: max tokens, temperatura, top-p, sampling.
- Boton de generacion reutilizando el modelo ya cargado.
- Panel de salida con mensajes de progreso y resultados.
- Selector de backend manual: Auto, Heretic Real, Ollama, Fallback.
- Boton de recarga de modelos Ollama e integración visual con estado.
- Tema visual moderno con tarjetas, colores profesionales e iconos nativos Qt.
- Búsqueda de modelos descargables (Ollama + Hugging Face) y descarga directa para modelos de Ollama.

## Resiliencia y auto-reparación
- Descarga Hugging Face con estrategia robusta: limpieza preventiva de locks/temporales, reintentos de red y validación de integridad local.
- Si se detecta error reparable (permisos, locks, dependencia HF, batch Heretic), la Micro IA ejecuta auto-reparación y reintento controlado.
- Registro persistente en `logs/abliterador.log` para diagnóstico posterior.

## Arranque y rendimiento
- Arranque modular con progreso visible (motor interno, extensiones, perfil de hardware, catálogo).
- Operaciones pesadas siguen en `QThread` para evitar bloqueo de interfaz.
- Estrategia conservadora ante offload inestable: fallback seguro para mantener continuidad de uso.

## Checklist E2E v0.3.1 (aprobado/no aprobado)

Ejecuta contra un modelo HF real (ej. `Qwen/Qwen2.5-0.5B-Instruct`) en entorno con venv activado:

| # | Paso | Criterio de aprobado |
|---|------|----------------------|
| 1 | `python abliterador_studio.py` | App arranca, chip Micro IA visible, barra de arranque completa |
| 2 | Buscar modelo por nombre | Lista aparece sin error; validación de entrada vacía muestra aviso |
| 3 | Seleccionar modelo y descargar | Progreso en panel Salida; descarga completa sin crash; integridad confirmada |
| 4 | Cargar + abliterar | Backend seleccionado aparece en chip; flujo termina con ✅ en Salida |
| 5 | Generar con prompt corto | Respuesta aparece en tab Chat Modelo y panel Salida |
| 6 | Provocar error de red (desconectar) | Micro IA muestra estado de recuperación; reintento automático visible |
| 7 | Cerrar y re-abrir app | Modelos cacheados detectados correctamente al arrancar |
| 8 | Revisar `logs/abliterador.log` | Sin trazas ERROR no manejadas |

## Referencias de investigacion
- Qt threading (QThread worker-object pattern): https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html
- Transformers generation strategies: https://huggingface.co/docs/transformers/main/en/generation_strategies
- Transformers GPU inference optimizations: https://huggingface.co/docs/transformers/main/en/perf_infer_gpu_one
- OWASP input validation: https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html

## Stack Decision Log
| Concern | Chosen | Rejected | Reason |
|---|---|---|---|
| GUI | PySide6 Widgets | Web stack | Ya existe base funcional y dependencias instaladas |
| Model runtime | transformers + heretic_llm | Cambio de backend | Mantener continuidad con flujo validado |
| Concurrency | QThread worker-object | Operaciones en hilo UI | Evitar congelamiento al cargar/ejecutar modelos |
| Validation | Allowlist + rangos | Validacion minima | Evitar errores y parametros inseguros |
| Testing | Manual E2E inicial | Sin validacion | Proyecto sin suite previa, se define checklist claro |

## Risk Register
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Congelamiento UI por carga de modelo | Alta | Alta | Worker thread para operaciones pesadas |
| Consumo excesivo de RAM/VRAM | Alta | Alta | Limites de parametros y mensajes de estado |
| Error por modelo remoto no disponible | Media | Media | Manejo de excepciones y feedback en GUI |
| Prompt mal formado o vacio | Media | Media | Validaciones de longitud y contenido |
| Dependencias no instaladas | Media | Alta | Mensajes de error claros y README con setup |

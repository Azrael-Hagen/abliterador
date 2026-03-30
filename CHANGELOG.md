# Changelog

## [Unreleased]

## [0.10.4] - 2026-03-30 🛡 Configurador Inteligente LAN Windows
### Added
- Nuevo módulo `windows_lan_setup.py`: al arrancar el executable verifica y configura automáticamente:
  - Regla inbound de Windows Firewall para el puerto HTTP (8088)
  - Regla inbound de Windows Firewall para el puerto FTP (2121) si habilitado
  - URL ACL con `netsh http` para permitir binding sin admin en Windows Server
  - Detección de conflicto de puerto con proceso responsable (PID + nombre)
- Bandera `--configure-lan` en el ejecutable: solo configura y sale (ideal para GPO/scripts)
- Bandera `--auto-elevate`: relanza con UAC automáticamente si se necesitan permisos admin
- Self-heal de firewall: cada ~5 minutos el watchdog verifica que las reglas sigan activas y las restaura si se eliminaron
- `launch_abliterador_allinone.bat`: lanzador que eleva para configurar LAN y luego arranca el servidor como usuario normal
- Detección de conflicto de puerto al inicio: si el puerto está en uso muestra proceso responsable y aborta con mensaje claro

### Changed
- El all-in-one imprime un resumen de configuración LAN en consola al arrancar
- VERSIONING: 0.10.3 → 0.10.4

## [0.10.3] - 2026-03-30 ✨ UI Polish & File Tools in Streaming
### Added
- Markdown rendering en respuestas IA: code blocks, inline code, bold, listas, links.
- Cursor de streaming animado (`▍`) durante generacion de tokens.
- Botón "Copiar" en mensajes IA al completarse la respuesta.
- Timestamps en cada burbuja de mensaje.
- Tinte de calidad en burbuja IA: verde/amarillo/rojo según score QA.
- Soporte completo de file tools en streaming (`/api/chat/stream`): ya no devuelve 400 si `use_file_tools=true`.
- Estilado mejorado de scrollbars, inputs con focus ring, empty state centrado.

### Fixed
- Error 400 `Streaming no disponible con file tools` eliminado: el endpoint de streaming ahora ejecuta herramientas de archivo de forma síncrona dentro del generador y hace streaming del follow-up.

## [0.10.2] - 2026-03-30 ⚡ Streaming & Performance Hardening
### Added
- Nuevo endpoint `POST /api/chat/stream` con salida NDJSON token a token para feedback inmediato en UI.
- Timeout de chat configurable por request (`chat_timeout_s`) con cancelacion cliente automatica por modo de rendimiento.
- Badge visible de rendimiento en chat (`ms` + resultado de QA) y cache-busting de assets por version.

### Changed
- Refactor del backend de chat para eliminar duplicacion entre `/api/chat` y `/api/chat/quality` con pipeline unificado.
- Llamadas bloqueantes (Ollama, web search, web knowledge) movidas a threadpool para reducir cuelgues por bloqueo del event loop.
- `quality_auto_repair` queda desactivado por defecto para evitar segunda inferencia innecesaria y mejorar latencia.

### Fixed
- Respuestas que quedaban "colgadas" por cadena de inferencias secuenciales y operaciones bloqueantes dentro de endpoints async.
- Falla de runtime por dependencia faltante de formularios: se incorpora `python-multipart` en metadata y requirements.

## [0.10.1] - 2026-03-30 🎨 Chat UX & Branding Polish Release
### Added
- Envio rapido de chat con `Enter` (y `Shift+Enter` para salto de linea).
- Accion `Cancelar` para abortar generacion en curso desde la UI web.
- Badge de conectividad de servidor en vivo y estado vacio informativo del panel de chat.

### Changed
- Estilizado de chat con mejor jerarquia visual: burbujas por rol, espaciado, chips de estado y composer optimizado.
- Branding actualizado: logo Nexus para web y logo normal para GUI (con fallback resiliente).
- Version del proyecto incrementada a `0.10.1`.

### Fixed
- Interaccion de chat mas fluida en uso intensivo, evitando envios duplicados durante generacion.

### References
- LobeHub visuals and layout inspiration: https://github.com/lobehub/lobehub
- NextChat screenshots and chat ergonomics: https://github.com/ChatGPTNextWeb/NextChat
- Open WebUI status-rich patterns: https://github.com/open-webui/open-webui
- UX heuristic for status visibility: https://www.nngroup.com/articles/visibility-system-status/
- Visual hierarchy principles: https://ixdf.org/literature/topics/visual-hierarchy

## [Unreleased]
### Added
- `RELEASE_REQUIREMENTS_V1.md` con criterios de publicacion v1.0.0 y diseno de bootstrap inteligente para autoinstalacion de recursos.
- `RELEASE_AUDIT.md` con evidencia de auditoria de recursos y smoke E2E de endpoints criticos.
- Modularizacion de UI web en modulos reutilizables: `app_core.js`, `app_files.js`, `app_users.js`.

### Changed
- `.gitignore` actualizado para excluir temporales de build (`.pyi_work/`) y ejecutables locales de `release/`.
- Frontend web ahora carga JS como modulo (`type="module"`) para separar responsabilidades.
- Build de PyInstaller ahora incluye carpeta `sources` en el bundle all-in-one.

### Fixed
- Runtime crash del exe all-in-one cuando faltaba directorio de assets en entorno PyInstaller (`/assets` ahora tolera ausencia y usa fallback).

## [0.10.0] - 2026-03-30 🎨 UX Unificada Web Release
### Added
- **Modelo global unificado en UI web**: selección única aplicada a todo el flujo de chat y paneles.
- **Modelo visible en cada respuesta**: el backend ahora reporta `model_used` y el frontend lo muestra en cada salida IA.
- **Catálogo guiado de modelos descargables**: endpoint `/api/models/download-catalog` + UI con descarga directa sin requerir escritura manual del nombre.
- **Transferencias web dedicadas**: endpoints `/api/files/manager/upload` y `/api/files/manager/download` con área visible de transferencias en UI.
- **Branding web aplicado**: logo de proyecto incorporado en cabecera de la interfaz web.

### Changed
- Refactor de frontend para eliminar lógica redundante y centralizar estado de sesión/modelo/archivos.
- Flujo de chat con estados visibles por etapas (preparación, generación, validación, completado).
- `ChatResponse` extendido con campos `model_used`, `quality_score` y `quality_summary`.
- Mini IA de calidad mejorada con un reintento ligero de refinamiento cuando la respuesta cae bajo umbral.
- Versión del proyecto incrementada a `0.10.0`.

### Fixed
- Reducción de duplicación en listeners y sincronización de selectores de modelo.
- Mejor control de presión sobre el servidor con caché y ajustes de rendimiento del lado cliente.

## [0.9.0] - 2026-03-30 🎨 UX Overhaul & Chat Quality Release
### Added
- **Chat Quality Assistant**: Motor ligero para detectar respuestas sin coherencia, repetidas o sin sentido (heurísticas, sin extra LLM).
- **Nuevo endpoint `/api/chat/quality`**: Versión de chat que aplica validación automática y reporta score de calidad (0-100%).
- **File Manager tipo OneDrive**: 6 nuevos endpoints (`list`, `info`, `preview`, `copy`, `move`, `delete`, `mkdir`, `search`) para gestionar archivos del workspace.
- **UI Rediseñada**:
  - Pestañas sideb ar: "Chat IA" (selector de modelo visible, opciones avanzadas) y "Archivos" (file browser con metadatos y acciones rápidas).
  - Indicador de progreso real-time con spinner animado durante generación.
  - Mejor layout del panel de chat con modelo visible, estado de progreso y acciones claras.
- **Nuevas pruebas**: 20 tests unitarios para ChatQualityChecker (8 tests) y FileManager (12 tests).
- **CSS mejorado**: Animaciones, estilos para file browser, mejor contraste y usabilidad.
- **Opciones de chat avanzadas**: Toggle para verificación de calidad, tools, búsqueda web, memoria web reciente.

### Changed
- Versionado del proyecto incrementado a 0.9.0.
- UI del servidor completamente reorganizada en tabs del sidebar para mejor experiencia de usuario.
- Respuestas de chat ahora incluyen evento `tool_events` con score de calidad si está habilitado.
- Panel derecho de chat mejorado con selector de modelo en la cabecera y progreso visible.

### Fixed
- Mejor manejo visual de estados durante generación (progreso, errores, completación).
- Protección contra path traversal en todas las operaciones de file manager.
- Validación más estricta en ChatQualityChecker para detectar patrones sin sentido.

### Deferred (v1.0+)
- Streaming real-time con SSE en lugar de polling.
- Ranking de resultados de búsqueda por relevancia/confianza.
- Estadísticas detalladas de performance en file manager (latencia, throughput).
- Integración de proveedores de search premium (Bing, Serper).

## [0.8.0] - 2026-03-30 🚀 Web Search Enrichment Release
### Added
- Búsqueda por internet desde el servidor con endpoint dedicado (`/api/web/search`) accesible desde la UI web.
- Motor de enriquecimiento de chat con fuentes web recientes para mejorar respuestas con información actualizada.
- Memoria persistente de conocimiento web (`web_knowledge.json`) para reutilizar contexto reciente entre sesiones.
- Controles UI para activar/desactivar búsqueda web en chat, definir query y límite de fuentes.
- Nuevas pruebas unitarias para búsqueda web y almacenamiento de conocimiento reciente.

### Changed
- Versionado del proyecto incrementado a 0.8.0.
- Endpoint `/api/chat` ahora soporta enriquecimiento web opcional con trazabilidad de fuentes en `tool_events`.
- Configuración web ampliada con variables `ABLITERADOR_WEB_SEARCH_*` y `ABLITERADOR_WEB_KNOWLEDGE_*`.

### Fixed
- Búsqueda web ahora aplica fallback entre proveedores y degrada de forma segura cuando un origen externo falla.

## [0.7.0] - 2026-03-30 🚀 Admin Studio Web Release
### Added
- Registro de nuevos usuarios desde la UI web (`/api/signup`).
- Catálogo de roles y permisos usuales (`admin`, `manager`, `operator`, `viewer`).
- Gestión administrativa completa de usuarios: crear, cambiar rol, activar/desactivar y eliminar.
- Descarga de modelos solicitada por administradores con jobs y seguimiento de estado.
- Panel Admin Studio Web con acciones de auto-recuperación y lanzamiento de GUI de escritorio.

### Changed
- Versionado del proyecto incrementado a 0.7.0.
- Endpoints de perfil/usuarios ahora exponen estado activo y permisos.
- All-in-one incorpora watchdog automático para recuperación de Ollama y reinicio FTP.

### Fixed
- Compatibilidad de rutas FTP en Windows para escritura/lectura mediante normalización virtual segura.

---

## [0.6.0] - 2026-03-30 🚀 LAN FTP Release
### Added
- FTP LAN integrado al launcher all-in-one para subir/descargar archivos desde red local.
- Descubrimiento y exposición de bibliotecas usuales de Windows (Desktop, Documents, Downloads, Pictures, Music, Videos).
- Estado y URLs FTP visibles en UI y endpoints de estado del servidor.
- Configuración por entorno para FTP (`ABLITERADOR_FTP_*`).

### Changed
- Versión del proyecto incrementada a 0.6.0.
- Banner de arranque all-in-one muestra versión y estado de FTP LAN.

### Fixed
- Validación de integración all-in-one con servicios simultáneos (web + FTP) sin romper el flujo LAN-only.

---

## [0.5.0] - 2026-03-29 🚀 LAN All-in-One Release
### Added
- All-in-one server launcher executable path and startup flow documented for Windows Server.
- Visible version in all-in-one startup banner.
- Windows Server service setup script with NSSM/task fallback.
- Runtime guard tests for local-network detection, rate limiting and model cache reuse.

### Changed
- Web server hardening: model list cache TTL, IP-based rate limiting and resilient Ollama HTTP session.
- Expanded curated abliterated model catalog with additional lightweight, coding and high-capacity options.
- Project version bumped to 0.5.0.

### Fixed
- PyInstaller all-in-one packaging now includes web static/template assets and uses active interpreter.
- Cleaned redundant generated artifacts from workspace before release.

---

## [0.4.0] - 2026-03-28 🚀 Distribution Release
### Added
- **Setup Infrastructure:** `setup.py` for pip installation support (all platforms).
- **Modern Packaging:** `pyproject.toml` with PEP 517/518 build backend configuration.
- **Dependency Pinning:** `requirements.txt` with exact versions for reproducible builds.
- **Executable Builder:** `build_installer.py` script to generate standalone executables via PyInstaller.
  - Supports Windows (.exe), macOS, and Linux binaries
  - One-file and directory-bundle modes
  - No Python installation required on target systems
- **Installation Guide:** `INSTALLATION.md` with step-by-step instructions for all platforms.
- **Cross-platform Support:** Verified builds for Windows 10+, macOS 10.14+, Linux (Ubuntu 18.04+, Debian 11+).
- **GitHub Release Assets:** Pre-built executables for Windows, macOS, and Linux.

### Changed
- README updated with references to INSTALLATION.md and executable downloads.
- Project version bumped to 0.4.0 (MINOR: distribution features don't change existing flows).
- Windows launcher (launch_abliterador_studio.bat) now references official release notes.

### Fixed
- Model auto-replacement bug on CPU-only systems (from v0.3.1) fully tested before release.
- Download cancellation and model deletion features validated across all backends.

### Infrastructure
- Prepared CI/CD hooks for automated executable builds on release tags.
- Validated dependency tree for cross-architecture compatibility (x86_64, ARM64 ready for macOS).

---

## [0.3.1] - 2026-03-28
### Added
- Resilient HF download flow with transient-network retry backoff and post-download integrity validation.
- Worker-level auto-recovery retries for repairable HF download errors and Heretic batch configuration failures.
- Explicit micro-IA visibility chip during startup and recovery flows.
- `APP_VERSION = "0.3.1"` constant in entrypoint; version displayed in window title bar and footer chip.
- E2E validation checklist table in README for release sign-off.

### Changed
- Heretic load path now retries with conservative CPU mapping when disk-offload strategy fails.
- Startup panel now surfaces modular boot-step status more clearly.
- Assistant guidance wording aligned with current UI tab naming.

### Fixed
- Reduced recurrence of permission/lock-related HF download failures by cleaning lock and partial artifacts before retry.
- Hardened handling for `range() arg 3 must not be zero` style batch errors in the load/abliteration path.

## [0.3.0] - 2026-03-26
### Added
- Modular package structure: domain, services, and UI layers under abliterador_app.
- Real Heretic integration backend using heretic.model.Model with residual-direction abliteration.
- Backend factory with priority order: modern heretic, legacy heretic_llm, fallback transformers.
- Manual backend selector (Auto/Heretic/Ollama/Fallback).
- Modernized GUI with professional stylesheet, grouped panels, and native Qt icons.
- Ollama model refresh action and improved local-model discovery.
- New professional entrypoint: abliterador_studio.py.
- Windows launcher: launch_abliterador_studio.bat.

### Changed
- Previous entrypoint abliterador_basico.py now acts as compatibility shim.
- Entry script kept as stable launcher and moved GUI orchestration to package modules.
- Worker now reports active backend and keeps runtime logic outside widget handlers.

## [0.2.0] - 2026-03-26
### Added
- Worker-thread execution with QThread to keep GUI responsive during model loading and generation.
- Generation controls in GUI: max tokens, temperature, top-p, sampling toggle.
- Dedicated prompt editor and explicit generate action with loaded model reuse.
- Input validation for model name and prompt, with consistent QMessageBox errors.

### Changed
- Load/abliterate flow now dispatches heavy tasks to background worker.
- Output panel now receives progress messages and operation results asynchronously.

## [0.1.0] - 2026-03-26
### Added
- Architecture governance files: CHECKPOINTS, MODULES, VERSIONING, ENGINEER_LOG.
- Expanded GUI plan for local model testing with HereticLLM.

### Notes
- Initial structured release baseline.

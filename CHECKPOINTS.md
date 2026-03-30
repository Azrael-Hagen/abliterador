# Project Checkpoints

## Legend
- [ ] Not started
- [~] In progress
- [x] Passing
- [!] Blocked

---

## CP-01: Foundation
Milestone: App boots, config loads, worker-thread execution ready.
Acceptance Criteria:
- [x] Application starts on clean environment with dependencies installed.
- [x] Core configuration object validates UI parameters.
- [x] Long-running model operations execute outside UI thread.
- [x] Basic lint/syntax validation passes.
Status: [x]
Notes: Entry point preserved and app startup validated after modularization.

---

## CP-02: Core Domain
Milestone: Domain models and orchestration logic separated from widgets.
Acceptance Criteria:
- [x] Parameter model for generation settings defined.
- [x] Task model for load/abliterate/generate requests defined.
- [x] No heavy inference logic in direct button handlers.
Status: [x]
Notes: Domain and service layers extracted to package modules.

---

## CP-03: GUI Layer
Milestone: GUI contracts and validations complete.
Acceptance Criteria:
- [x] Search flow validates empty input and updates results list.
- [x] Load/Abliterate flow validates selection and settings.
- [x] Generation flow validates prompt/settings and appends output.
- [x] User-facing errors are shown with QMessageBox.
Status: [x]
Notes: GUI now supports configurable local generation and explicit generate action.

---

## CP-04: Heretic Integration
Milestone: HereticLLM operations isolated and robust.
Acceptance Criteria:
- [x] Prompt templates externalized in dedicated helper method.
- [x] Heretic load + abliterate runs in worker thread.
- [x] Generation can use current loaded model without reloading each call.
- [x] Failure paths are logged and surfaced to UI.
Status: [x]
Notes: Backend factory now prioriza heretic moderno (abliteración real), luego heretic_llm legacy, y fallback.

---

## CP-05: E2E & Release
Milestone: End-to-end manual validation and release docs.
Acceptance Criteria:
- [x] Manual E2E: search, select, load/abliterate, generate, error path.
- [x] Security gate: input allowlist/limits and no secrets in code.
- [x] Performance gate: UI remains responsive during long tasks.
- [x] CHANGELOG and README updated with run instructions.
Status: [x]
Notes: Se añadieron reintentos resilientes para HF (locks/permisos/red), verificación de integridad post-descarga, recuperación visible de micro IA en UI y fallback para estrategia de memoria Heretic (disk offload). Versión v0.3.1 publicada con tag git y push. Checklist E2E documentado en README.

---

## CP-06: Web Server Multiusuario
Milestone: Acceso remoto por navegador con chat y sandbox de archivos.
Acceptance Criteria:
- [x] Servidor FastAPI levanta y sirve UI web.
- [x] Autenticación por token requerida para API.
- [x] Chat remoto integrado a Ollama (`/api/chat`).
- [x] Perfiles LAN persistentes con roles (`admin`/`user`).
- [x] Espacio propio por usuario en servidor (`web_workspace/users/<usuario>`).
- [x] Operaciones de archivos limitadas al espacio de cada usuario.
- [x] Bloqueo de path traversal y rutas absolutas validado con pruebas.
Status: [x]
Notes: Se añadió modo web en `abliterador_web/` y entrypoint `abliterador_web_server.py` sin alterar el flujo GUI existente. Se activó guard para red local y gestión de perfiles desde UI admin.

---

## CP-07: FTP LAN Integrado
Milestone: Transferencia de archivos tipo nube local desde cliente FTP en red interna.
Acceptance Criteria:
- [x] Servidor FTP embebido arranca junto al all-in-one.
- [x] Acceso FTP restringido a red local cuando `ABLITERADOR_LOCAL_NETWORK_ONLY=1`.
- [x] Subida, descarga y borrado validados con prueba de roundtrip.
- [x] Información FTP visible en consola all-in-one y endpoints de salud.
- [x] Configuración por variables `ABLITERADOR_FTP_*` documentada.
Status: [x]
Notes: Se corrigió normalización de rutas virtuales FTP en Windows mediante filesystem personalizado para evitar fallos de escritura en pyftpdlib.

---

## CP-08: UX Web + Mini IA de Autodiagnostico
Milestone: UI web organizada por pestañas, manejo de errores más claro y autorreparación inteligente con memoria.
Acceptance Criteria:
- [x] UI reorganizada en navegación por pestañas (operación/admin/sistema) para reducir carga cognitiva.
- [x] Errores API complejos se muestran en lenguaje claro en la interfaz.
- [x] Endpoint de lanzamiento GUI robusto con múltiples rutas candidatas y comando configurable por entorno.
- [x] Motor de autodiagnóstico con memoria persistente de incidencias y efectividad de acciones.
- [x] Endpoints de diagnóstico inteligente (`check` + `repair`) conectados a UI.
- [x] Pruebas unitarias para launcher y motor de diagnóstico en verde.
Status: [x]
Notes: Se añadió aprendizaje incremental basado en tasa de éxito histórica de acciones para priorizar autorreparaciones seguras.

---

## CP-09: Enriquecimiento Web y Conocimiento Reciente
Milestone: El servidor incorpora búsqueda en internet y contexto actualizado reutilizable para mejorar respuestas del chat.
Acceptance Criteria:
- [x] Endpoint de búsqueda web dedicado (`/api/web/search`) operativo con permisos de chat.
- [x] Integración opcional de contexto web en `/api/chat` con trazabilidad de fuentes usadas.
- [x] Memoria persistente de conocimiento web reciente para reutilización entre sesiones.
- [x] Controles en UI para activar enriquecimiento web, query específica y número de resultados.
- [x] Fallback resiliente entre proveedores y degradación segura ante fallos de red/servicio.
- [x] Pruebas unitarias para módulo de búsqueda y memoria de conocimiento en verde.
Status: [x]
Notes: Se validó E2E local con login, búsqueda web y chat enriquecido; compilación all-in-one completada.

---

## CP-10: UX Mejorada y Chat Quality Assistant
Milestone: Interfaz rediseñada con visibilidad de catálogo de modelos, progreso real-time, asistencia de calidad de respuestas y File Manager tipo OneDrive.
Acceptance Criteria:
- [x] Pestañas nuevas en sidebar: "Chat IA" y "Archivos" para mejor organización.
- [x] Panel de chat mejorado con selector de modelo visible y indicador de progreso en tiempo real.
- [x] Chat Quality Checker integrado para validar coherencia, repetición, patrones sin sentido en respuestas.
- [x] Nuevo endpoint `/api/chat/quality` que aplica validación y reporta score en tiempo real.
- [x] File Manager tipo OneDrive con operaciones: listar, previsualizar, copiar, mover, eliminar, crear carpetas.
- [x] 6 nuevos endpoints de file manager: `/api/files/manager/{list,info,preview,copy,move,delete,mkdir,search}`.
- [x] UI mejorada para mostrar archivos con metadatos (tamaño, fecha, tipo) y acciones rápidas.
- [x] Animaciones y indicadores visuales (spinner, colores por rol de mensaje, progreso).
- [x] 20 tests unitarios nuevos (8 para chat quality, 12 para file manager) en verde.
- [x] Todos los 38 tests de suite en verde sin regresiones.
Status: [x]
Notes: Implementación modular de ChatQualityChecker y FileManager como servicios reutilizables. UI restructurada con tabs en sidebar y mejor organización. Progreso visual mejorado aunque sin streaming real (deferido a v1.0). Performance sin degradación significativa (<100ms para quality check).

---

## CP-11: UX Unificada, Catálogo Guiado y Transferencias Web
Milestone: UI web más intuitiva con modelo global único, catálogo de descarga visible, transferencias dedicadas y guardrails ligeros de coherencia.
Acceptance Criteria:
- [x] Selección de modelo única y sincronizada en toda la UI.
- [x] Cada respuesta de chat muestra explícitamente el modelo usado.
- [x] Catálogo de modelos descargables visible en UI con acción directa sin entrada manual obligatoria.
- [x] Zona de transferencias upload/download visible y funcional en el gestor web.
- [x] Flujo de estado del chat visible por etapas antes de la respuesta final.
- [x] Redundancias de UI eliminadas y carga cliente configurable para reducir presión en servidor.
- [x] Validación técnica completa (tests + smoke de endpoints).
Status: [x]
Notes: UI web unificada con modelo global persistente, catálogo guiado de descargas, transferencias dedicadas y guardrail de coherencia con reintento ligero; validado con `python -m pytest -q` (38 tests en verde) y compilación de módulos web.

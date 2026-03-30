# Modules Registry

## Reusable Modules

1. GenerationSettings
- Purpose: Canonical contract for text generation controls.
- Public API: max_new_tokens, temperature, top_p, do_sample.

2. WorkerTask
- Purpose: Immutable command object for worker execution.
- Public API: operation, model_name, prompt, settings.

3. ModelTaskWorker
- Purpose: Background execution of expensive operations.
- Public API: run_task(task), progress/success/error signals.

4. BaseAbliterationBackend
- Purpose: Contract for interchangeable inference/abliteration engines.
- Public API: load_and_abliterate(), generate().

5. ModernHereticBackend
- Purpose: Real abliteration with heretic package (residual directions + LoRA adaptation).
- Public API: load_and_abliterate(), generate().

6. LegacyHereticLLMBackend
- Purpose: Compatibility path for environments exposing heretic_llm.HereticLLM.
- Public API: load_and_abliterate(), generate().

7. TransformersFallbackBackend
- Purpose: Safe operational mode when Heretic APIs are unavailable.
- Public API: load_and_abliterate(), generate().

8. ModelSearcher
- Purpose: Main GUI orchestration and user interactions.
- Public API: search_model(), apply_heretic(), generate_text().

9. RuntimeEngine
- Purpose: Declarative modular startup pipeline with weighted progress.
- Public API: steps, total_weight.

10. Auto-repair helpers
- Purpose: Detect and remediate common runtime failures (HF cache locks, dependency drift, memory/network hints).
- Public API: attempt_auto_repair(target, progress_callback).

11. Advisor classifiers
- Purpose: Classify runtime errors and map them to user-facing guidance + automatic recovery decisions.
- Public API: classify_runtime_error(), humanize_runtime_error(), suggest_next_action().

12. WebSettings
- Purpose: Carga declarativa de configuración para modo servidor web (host, puerto, auth, sandbox).
- Public API: load_settings().

13. TokenAuth
- Purpose: Emisión/verificación de token firmado HMAC para API multiusuario.
- Public API: issue_token(), verify_token().

14. FileSandbox
- Purpose: Operaciones de archivos con restricción estricta a directorios permitidos.
- Public API: list_dir(), read_text(), write_text(), delete_file().

15. OllamaClient
- Purpose: Cliente HTTP aislado para listar modelos y generar chat contra servidor Ollama.
- Public API: list_models(), chat().

16. FastAPI web app
- Purpose: Exponer chat remoto, auth y herramientas de archivo desde navegador.
- Public API: create_app(), endpoints `/api/*`.

17. UserStore
- Purpose: Persistencia de perfiles LAN con hash de password y roles.
- Public API: ensure_admin(), create_user(), list_users(), verify_credentials().

18. FTP Server Integration
- Purpose: Exponer transferencia de archivos LAN (upload/download/delete) en all-in-one.
- Public API: start_ftp_server(), stop_ftp_server(), ftp_urls(), discover_windows_libraries().

19. Desktop Launcher Resolver
- Purpose: Resolver y lanzar GUI de escritorio de forma robusta desde el servidor web.
- Public API: find_gui_launch_targets(), launch_desktop_gui().

20. MiniAIDiagnosticsEngine
- Purpose: Diagnóstico inteligente con memoria persistente y priorización de autorreparaciones según efectividad histórica.
- Public API: check(), run_repair().

21. WebSearchService
- Purpose: Búsqueda de información en internet con caché temporal, fallback entre proveedores y normalización de resultados.
- Public API: search().

22. WebKnowledgeStore
- Purpose: Persistencia de hallazgos web recientes para reutilización contextual en el chat.
- Public API: record(), recent().

23. ChatQualityChecker
- Purpose: Validación ligera de respuestas LLM sin requerir LLM adicional (heurísticas para coherencia, repetición, patrones sin sentido).
- Public API: check_response(), get_quality_summary().

24. FileManager
- Purpose: Gestión completa de archivos del workspace con seguridad (protección traverse, operaciones copy/move/delete, preview, búsqueda).
- Public API: list_files(), get_preview(), copy_file(), move_file(), delete_file(), create_folder(), search().

## Reuse Rules
- Any new long-running operation must be routed through ModelTaskWorker.
- Any new generation controls must be added to GenerationSettings first.
- Any new model runtime integration must implement BaseAbliterationBackend.
- Any user-triggered operation must validate through task builders before execution.

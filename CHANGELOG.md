# Changelog

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

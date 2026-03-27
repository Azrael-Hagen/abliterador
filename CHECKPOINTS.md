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
- [ ] Manual E2E: search, select, load/abliterate, generate, error path.
- [x] Security gate: input allowlist/limits and no secrets in code.
- [x] Performance gate: UI remains responsive during long tasks.
- [x] CHANGELOG and README updated with run instructions.
Status: [~]
Notes: Arranque y selección de backend validados; falta cerrar E2E completo con modelo real en carga/generación.

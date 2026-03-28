# Changelog

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

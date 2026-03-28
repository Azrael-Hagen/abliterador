# Engineer Log

## [CP-04/Distribution] 2026-03-28
Status: Passed
Decisions made:
- **Distribution Strategy:** Chose multi-tier approach for maximum adoption:
  1. Pre-built executables via GitHub Releases (zero-config for end users)
  2. pip installation from PyPI (for dev/integration use)
  3. Source + requirements.txt (for developers and CI/CD)
  4. Build script for custom executables (PyInstaller)

- **Dependency Pinning:** Used exact versions in requirements.txt for reproducible builds across systems/architects; setup.py allows flexible ranges for dev installs.

- **Setup.py + pyproject.toml:** Modern dual-layer configuration (backcompat + PEP 517) for compatibility with older pip versions and future PyPI submission.

- **PyInstaller Spec:** Chose onedir + onefile modes to balance portability and distribution size. Hidden imports configured for heretic, transformers, and torch.

- **Documentation:** Consolidated installation paths into INSTALLATION.md (4 options) with troubleshooting and security notes.

- **Versioning Bump:** v0.3.1 → v0.4.0 (MINOR: new distribution infrastructure, no breaking GUI changes).

Trade-offs:
- PyInstaller executables are large (~350-400MB) to avoid requiring Python on target systems; acceptable for GUI apps.
- Cross-compilation (e.g., Windows exe from Linux) not supported; each platform builds on that platform.
- CI/CD automation for release builds deferred to next sprint (manual builds for now).

Debt deferred:
- Automated GitHub Actions workflow to build + sign + upload executables on tag push.
- MSI installer for Windows (WiX toolset integration).
- macOS code signing and notarization for production App Store compliance.
- Auto-update mechanism for distributed executables.

Next steps:
- Commit and push distribution files to main.
- Create GitHub Release v0.4.0 with pre-built executables (manual build on each platform).
- Update project wiki with release notes and upgrade instructions.

## [CP-01] 2026-03-26
Status: In progress
Decisions made:
- Keep single-file app architecture for compatibility with current project scope.
- Introduce worker-thread pattern using Qt signals to avoid UI blocking.
- Expand GUI with configurable generation controls for local model testing.

Trade-offs:
- Single-file keeps onboarding simple but limits strict layer separation.
- Manual E2E used initially because no automated test suite exists.

Debt deferred:
- Full split into src/core/ui modules deferred until feature baseline stabilizes.
- Automated unit/integration tests deferred to next iteration.

Next steps:
- Implement worker-backed load/abliterate/generate flows.
- Validate syntax and run manual E2E checklist.

## [CP-03/CP-04] 2026-03-26
Status: Passed
Decisions made:
- Added GenerationSettings and WorkerTask contracts to normalize GUI-to-worker commands.
- Implemented ModelTaskWorker in QThread with progress/success/error signals.
- Preserved existing search and load flow while extending with reusable generation action.

Trade-offs:
- Kept single-file structure to avoid breaking validated behavior and simplify deployment.
- Runtime dependency checks remain operational (not compile-time), pending packaging step.

Debt deferred:
- Automated unit tests for worker logic and settings validation.
- Optional model quantization controls and memory-aware presets.

Next steps:
- Run full manual E2E with real local model and verify responsiveness under load.
- Add lightweight tests around validation helpers and task construction.

## [CP-02 Refactor] 2026-03-26
Status: Passed
Decisions made:
- Migrated from monolithic script to modular package with explicit domain/services/ui boundaries.
- Implemented backend abstraction to support real heretic integration and backward compatibility.
- Prioritized real Heretic backend (heretic package) to satisfy abliteración real requirement.

Trade-offs:
- Real Heretic backend uses internal API flow (Model + residual directions) to avoid dependency on missing HereticLLM wrapper.
- Full optimization loop from heretic CLI was not embedded to keep GUI latency predictable.

Debt deferred:
- Add configurable good/bad calibration prompt sets from GUI or external files.
- Add integration tests with a small chat-template model fixture.

Next steps:
- Execute full manual E2E on a real instruction model and tune default ablation parameters.
- Add preset profiles (ligero, equilibrado, agresivo) for abliteration intensity.

## [CP-05 Hardening] 2026-03-28
Status: Passed — Release v0.3.1
Decisions made:
- Added resilient Hugging Face download strategy with lock/partial cleanup, transient-network retry backoff, and post-download model completeness verification.
- Added worker-level auto-recovery retries for repairable download and Heretic batch failures to reduce user-blocking crashes.
- Added Heretic load fallback when disk-offload strategy becomes unstable, forcing a conservative CPU mapping retry.
- Improved startup observability by exposing micro-IA state during modular boot and recovery actions.
- Added visible APP_VERSION constant (v0.3.1) in entrypoint, window title, and footer chip for full traceability.
- E2E checklist documented in README for manual validation against any real HF model.

Trade-offs:
- Preferred deterministic recovery and reliability over aggressive load strategy; CPU fallback can be slower but avoids hard failures.
- Kept visual polish lightweight in Qt stylesheets (no heavy effects/animations) to avoid startup/render penalties.

Debt deferred:
- Full automated E2E suite with mocked large-model paths and synthetic cache corruption fixtures.
- Optional telemetry dashboard (structured metrics timeline) beyond current rotating log + assistant feed.
- Preset profiles (ligero/equilibrado/agresivo) for abliteration intensity.

Release notes:
- git tag v0.3.1 published for this checkpoint.
- Version constant APP_VERSION = "0.3.1" in abliterador_studio.py as single source of truth.

# Engineer Log

## [CP-10] 2026-03-30  
Status: Passed
Decisions made:
- Implemented lightweight `ChatQualityChecker` with heuristic scoring (0.0-1.0) for response coherence without requiring extra LLM calls.
- Added new `/api/chat/quality` endpoint that applies quality validation and exposes score in `tool_events`.
- Implemented `FileManager` class as reusable service for secure file operations (list/preview/copy/move/delete/search) with path traversal protection.
- Added 8 new file manager endpoints (`/api/files/manager/*`) accessible behind "files" permission.
- Restructured web UI with new tabs "Chat IA" and "Archivos" in sidebar for better UX organization.
- Improved chat panel with visible model selector, real-time progress spinner and better visual feedback.
- Added CSS animations for spinner and file browser styling.

Trade-offs:
- Chat Quality Checker uses heuristics only (no external classifier or language model) to keep latency <100ms and cost zero.
- File preview limited to 50KB and specific file types (.txt, .md, .py, .json, .csv, etc.) to avoid accidental binary exposure.
- Real-time progress shown via UI state toggle rather than SSE streaming (deferred to v1.0) to reduce complexity.

Debt deferred:
- Implement true streaming with Server-Sent Events (SSE) for step-by-step progress feedback.
- Add citation ranking by relevance score and freshness timestamp in file manager and web results.
- Add telemetry/profiling for file manager operations (throughput, latency percentiles).
- Add support for cloud storage backends (S3, Azure Blob, etc.) beyond local workspace.

Next steps:
- Deploy and validate full UI with real users on production LAN.
- Add optional background indexing for large file repositories.
- Consider full-text search capability for document content.

## [CP-09] 2026-03-30
Status: Passed
Decisions made:
- Added server-side internet search service with provider fallback and TTL cache for low-latency enrichment.
- Added persistent web knowledge memory so newly fetched information can be reused in future prompts.
- Extended `/api/chat` contract to optionally inject fresh web context and include source traceability via `tool_events`.
- Added dedicated `/api/web/search` endpoint and UI controls for explicit web lookups from the browser.

Trade-offs:
- Implemented retrieval-augmented enrichment (RAG ligero) instead of model weight fine-tuning to keep deployment local, safe and fast.
- Chosen public-source snippets (DuckDuckGo + Wikipedia API) to avoid API key dependency for baseline functionality.

Debt deferred:
- Add optional premium search provider adapters (Serper/Bing/etc.) with API keys and ranking strategy.
- Add citation confidence scoring and source freshness metadata in the UI.

Next steps:
- Add integration tests with mocked external HTTP responses for deterministic CI.
- Add scheduled background refresh jobs for configurable topic watchlists.

## [CP-08] 2026-03-30
Status: Passed
Decisions made:
- Reorganized web UI into tabbed sections (Operacion/Admin/Sistema) to improve discoverability and reduce visual overload.
- Added robust desktop GUI launch resolver with multi-path discovery and optional `ABLITERADOR_GUI_LAUNCH_CMD` override.
- Implemented `MiniAIDiagnosticsEngine` with persistent memory (`diagnostics_memory.json`) to learn issue/action outcomes.
- Added intelligent diagnostics API endpoints (`/api/admin/diagnostics/ai/check` and `/api/admin/diagnostics/ai/repair`).
- Added structured API error parsing in frontend to avoid opaque `[object Object]` messages.

Trade-offs:
- Chosen learning approach is heuristic/statistical (success-rate based) instead of remote LLM to keep latency/cost near zero and run fully offline.
- GUI launch from web remains dependent on local availability of desktop artifacts or explicit launch command configuration.

Debt deferred:
- Add optional authenticated remote desktop bridge for environments where GUI binary is not present in server host.
- Add integration tests against running FastAPI app for diagnostics endpoints.

Next steps:
- Validate from real LAN clients on Windows Server service mode.
- Document recommended production values for `ABLITERADOR_GUI_LAUNCH_CMD` and diagnostics memory path.

## [CP-07] 2026-03-30
Status: Passed
Decisions made:
- Integrated FTP LAN service into `abliterador_all_in_one.py` so web + FTP start together in one executable.
- Added `ABLITERADOR_FTP_*` settings for host, port, credentials, root path and enable/disable switch.
- Exposed FTP status/URLs in `/api/health`, `/api/server-info` and sidebar UI.
- Implemented custom FTP filesystem normalization for Windows path semantics to avoid write failures.

Trade-offs:
- Chose pyftpdlib for lightweight embedded FTP over full SMB/WebDAV stack to keep onefile distribution simple.
- FTP credentials are env-driven for operational simplicity; advanced RBAC/audit trail deferred.

Debt deferred:
- Per-user FTP chroot mapping aligned with web profile workspace.
- Optional FTPS/TLS for encrypted LAN deployments.

Next steps:
- Add integration test that boots all-in-one and validates FTP login + file transfer in CI.
- Add optional passive port range config for stricter firewall setups.

## [CP-06] 2026-03-29
Status: Passed
Decisions made:
- Added isolated web mode (`abliterador_web/`) without modifying existing GUI behavior.
- Selected FastAPI + Uvicorn for remote multi-user service and browser UI.
- Implemented token auth with HMAC signed tokens and configurable credentials via environment variables.
- Implemented file sandbox with strict path normalization and root confinement.
- Added model tool-calling pattern (JSON tool response) with explicit server-side validation before file operations.
- Added persistent LAN profiles with role (`admin`/`user`) in `abliterador_users.json` using PBKDF2 password hashing.
- Added per-user workspace isolation under `web_workspace/users/<username>`.
- Added local-network-only guard (private/loopback/link-local IPs) configurable via env.

Trade-offs:
- Kept auth lightweight (single admin credential) for MVP speed; RBAC deferred.
- Chose in-memory sessionless API model (token-only) for simpler deployment.
- Tool-calling follows explicit JSON convention instead of full function-calling framework.

Debt deferred:
- Add RBAC (admin/user roles) and per-user workspaces.
- Add audit trail persistence for file operations.
- Add reverse-proxy hardening templates (Nginx/Caddy) and TLS automation.

Next steps:
- Deploy behind HTTPS reverse proxy on server machine.
- Rotate credentials/secret from environment and disable defaults.
- Add integration tests for `/api/chat` with mocked Ollama.

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

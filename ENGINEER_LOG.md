# Engineer Log

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

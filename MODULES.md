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

## Reuse Rules
- Any new long-running operation must be routed through ModelTaskWorker.
- Any new generation controls must be added to GenerationSettings first.
- Any new model runtime integration must implement BaseAbliterationBackend.
- Any user-triggered operation must validate through task builders before execution.

# Versioning Strategy

## Project SemVer
- Format: MAJOR.MINOR.PATCH.
- MAJOR: Breaking GUI behavior or incompatible runtime requirements.
- MINOR: New user-visible features that preserve existing flows.
- PATCH: Bug fixes and non-breaking improvements.

## App Contract Versioning
- GUI contract version tracked in CHANGELOG under release notes.
- Existing flows (search, select, load/abliterate) must remain backward compatible across MINOR/PATCH.

## Prompt Versioning
- Prompt templates follow suffix naming: default_prompt_v1, default_prompt_v2.
- Breaking prompt behavior changes require version bump and changelog entry.

## Migration Rules
- No silent renames of primary buttons/actions.
- Deprecated controls remain for at least one MINOR version with note in README.

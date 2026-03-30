# Versioning Strategy

## Project SemVer
- Format: MAJOR.MINOR.PATCH.
- **MAJOR:** Breaking GUI behavior or incompatible runtime requirements (e.g., Python 3.10 → 3.12 only).
- **MINOR:** New user-visible features that preserve existing flows (e.g., new backend option, new export format).
- **PATCH:** Bug fixes, security patches, and non-breaking improvements (e.g., faster load, UI polish).

**Current Version:** `0.10.1` (polish UX chat, cancelacion, Enter-to-send y branding Nexus/web + GUI)

## Distribution & Releases

### PyPI Package
- Package name: `abliterador-studio`
- Available via: `pip install abliterador-studio` (after PyPI submission)
- Installation docs: [INSTALLATION.md](INSTALLATION.md)

### GitHub Releases
- Pre-built executables published for each MINOR/MAJOR bump:
  - `AbliteradorStudio_vX.X.X_Windows.zip` → `AbliteradorStudio.exe`
  - `AbliteradorStudio_vX.X.X_macOS.tar.gz` → `AbliteradorStudio` (macOS binary)
  - `AbliteradorStudio_vX.X.X_Linux.tar.gz` → `AbliteradorStudio` (Linux binary)

### Version Consistency
- Entrypoint (`abliterador_studio.py`): `APP_VERSION = "X.Y.Z"`
- setup.py / pyproject.toml: `version = "X.Y.Z"`
- Window title bar: displays `Abliterador Studio vX.Y.Z`
- Footer chip: displays version + build info
- CHANGELOG.md: updated with release notes before tagging

## App Contract Versioning
- GUI contract version tracked in CHANGELOG under release notes.
- Existing flows (search, select, load/abliterate, generate) must remain backward compatible across MINOR/PATCH.
- New flows (e.g., model cancellation, storage relocation) are MINOR (0.3.1 → 0.4.0).

## Prompt Versioning
- Prompt templates follow suffix naming: `default_prompt_v1.txt`, `default_prompt_v2.txt`.
- Breaking prompt behavior changes require MINOR version bump and changelog entry.
- Legacy prompts retained for compatibility (at least one version back).

## Dependency Pinning
- **Production (requirements.txt):** Exact versions pinned (e.g., `PySide6==6.7.1`)
  - Built executables use these exact versions
  - Source installations can use requirements.txt or setup.py (more flexible ranges)
- **Development (setup.py extras):** Relaxed ranges for dev tools
  - `pip install -e ".[dev]"` for PyInstaller, pytest, linters

## Migration Rules & Deprecation
- No silent renames of primary buttons/actions
- Deprecated controls remain for at least one MINOR version with warning note in README
- Breaking API changes require MAJOR version bump and migration guide

## Git Workflow
1. Commit feature/fix to `main`
2. Update CHANGELOG.md with new [VERSION] section
3. Bump version in setup.py + pyproject.toml + abliterador_studio.py
4. Commit: `git commit -m "chore: version bump to X.Y.Z"`
5. Tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z: [short description]"`
6. Push: `git push origin main` + `git push origin vX.Y.Z`
7. Create GitHub Release with pre-built executables (automated or manual)

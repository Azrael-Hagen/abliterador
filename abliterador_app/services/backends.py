import inspect
import os
import re
import shutil
import subprocess
import sys
import time
from abc import ABC, abstractmethod

# Configure Hugging Face caches as early as possible, before importing transformers/heretic.
_EARLY_HF_HOME = os.path.join(os.getcwd(), ".hf_cache")
_EARLY_HF_HUB = os.path.join(_EARLY_HF_HOME, "hub")
_EARLY_HF_TRANSFORMERS = os.path.join(_EARLY_HF_HOME, "transformers")
os.makedirs(_EARLY_HF_HUB, exist_ok=True)
os.makedirs(_EARLY_HF_TRANSFORMERS, exist_ok=True)
os.environ["HF_HOME"] = _EARLY_HF_HOME
os.environ["HF_HUB_CACHE"] = _EARLY_HF_HUB
os.environ["HUGGINGFACE_HUB_CACHE"] = _EARLY_HF_HUB
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from transformers import AutoModelForCausalLM, AutoTokenizer

from abliterador_app.domain.models import GenerationSettings

# Strip ANSI / terminal control sequences (spinners, cursor moves, etc.)
_ANSI_RE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-9;?]*[A-Za-z])|\[\?[0-9]+[hl]|\[[0-9]+[A-Za-z]|\[K')


def _clean_line(line: str) -> str:
    """Remove ANSI escape codes and carriage-returns from a line."""
    return _ANSI_RE.sub('', line).replace('\r', '').strip()

BACKEND_MODE_AUTO = "auto"
BACKEND_MODE_HERETIC = "heretic"
BACKEND_MODE_OLLAMA = "ollama"
BACKEND_MODE_FALLBACK = "fallback"


class BackendError(RuntimeError):
    pass


def _workspace_hf_cache_dir() -> str:
    cache_dir = os.path.join(os.getcwd(), ".hf_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _configure_hf_environment() -> None:
    """Force HF/Transformers caches into workspace to avoid user-profile permission issues."""
    base = _workspace_hf_cache_dir()
    hub_cache = os.path.join(base, "hub")
    transformers_cache = os.path.join(base, "transformers")
    os.makedirs(hub_cache, exist_ok=True)
    os.makedirs(transformers_cache, exist_ok=True)

    os.environ["HF_HOME"] = base
    os.environ["HF_HUB_CACHE"] = hub_cache
    os.environ["HUGGINGFACE_HUB_CACHE"] = hub_cache
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"


def _has_dir_content(path: str) -> bool:
    try:
        with os.scandir(path) as iterator:
            for _ in iterator:
                return True
    except Exception:
        return False
    return False


def _resolve_hf_model_source(model_name: str) -> tuple[str, str, str]:
    cache_dir, model_dir = _local_hf_paths(model_name)
    source = model_dir if _has_dir_content(model_dir) else model_name
    return source, cache_dir, model_dir


def is_hf_model_ready_local(model_name: str) -> bool:
    """Return True when a local downloaded HF model looks complete enough to load offline."""
    _cache_dir, model_dir = _local_hf_paths(model_name)

    config_path = os.path.join(model_dir, "config.json")
    tokenizer_cfg = os.path.join(model_dir, "tokenizer_config.json")
    if not os.path.isfile(config_path) or not os.path.isfile(tokenizer_cfg):
        return False

    shard_index_path = os.path.join(model_dir, "model.safetensors.index.json")
    if os.path.isfile(shard_index_path):
        try:
            import json

            with open(shard_index_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            weight_map = data.get("weight_map", {})
            shard_files = set(weight_map.values())
            if not shard_files:
                return False
            return all(os.path.isfile(os.path.join(model_dir, name)) for name in shard_files)
        except Exception:
            return False

    # Non-sharded formats.
    if os.path.isfile(os.path.join(model_dir, "model.safetensors")):
        return True
    if os.path.isfile(os.path.join(model_dir, "pytorch_model.bin")):
        return True

    return False


def _is_permission_or_lock_error(message: str) -> bool:
    low = (message or "").lower()
    return any(
        token in low
        for token in [
            "permissionerror",
            "check cache directory permissions",
            "access is denied",
            "winerror 5",
            "filelock",
            "lock file",
            "lock needs manual removal",
        ]
    )


def _is_transient_network_error(message: str) -> bool:
    low = (message or "").lower()
    return any(
        token in low
        for token in [
            "read timed out",
            "timed out",
            "connection",
            "temporary failure",
            "name resolution",
            "ssl",
            "proxyerror",
            "remote end closed connection",
            "max retries exceeded",
        ]
    )


def _cleanup_hf_locks(cache_dir: str) -> int:
    removed = 0
    for root, dirs, files in os.walk(cache_dir):
        for filename in files:
            if filename.endswith(".lock"):
                lock_path = os.path.join(root, filename)
                try:
                    os.remove(lock_path)
                    removed += 1
                except Exception:
                    pass
        for dirname in list(dirs):
            if dirname.endswith(".lock"):
                lock_dir = os.path.join(root, dirname)
                try:
                    shutil.rmtree(lock_dir, ignore_errors=True)
                    removed += 1
                except Exception:
                    pass
    return removed


def _cleanup_hf_partial_artifacts(cache_dir: str, model_dir: str) -> int:
    removed = _cleanup_hf_locks(cache_dir)
    for base in [cache_dir, model_dir]:
        if not base or not os.path.isdir(base):
            continue
        for root, _dirs, files in os.walk(base):
            for filename in files:
                if filename.endswith(".incomplete") or filename.endswith(".tmp"):
                    partial_path = os.path.join(root, filename)
                    try:
                        os.remove(partial_path)
                        removed += 1
                    except Exception:
                        pass
    return removed


_configure_hf_environment()


class BaseAbliterationBackend(ABC):
    backend_name = "base"
    supports_abliteration = True

    @abstractmethod
    def load_and_abliterate(
        self,
        model_name: str,
        prompt: str,
        settings: GenerationSettings,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate(self, prompt: str, settings: GenerationSettings) -> str:
        raise NotImplementedError


class TransformersFallbackBackend(BaseAbliterationBackend):
    backend_name = "fallback"

    def __init__(self):
        self.model = None
        self.tokenizer = None

    def load_and_abliterate(self, model_name: str, prompt: str, settings: GenerationSettings) -> str:
        source, cache_dir, _model_dir = _resolve_hf_model_source(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(source, cache_dir=cache_dir)
        self.model = AutoModelForCausalLM.from_pretrained(source, cache_dir=cache_dir)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        return self.generate(prompt, settings)

    def generate(self, prompt: str, settings: GenerationSettings) -> str:
        if self.model is None or self.tokenizer is None:
            raise BackendError("No hay modelo cargado para generar.")

        inputs = self.tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        output_ids = self.model.generate(
            **inputs,
            max_new_tokens=settings.max_new_tokens,
            temperature=settings.temperature,
            top_p=settings.top_p,
            do_sample=settings.do_sample,
            pad_token_id=self.tokenizer.eos_token_id,
        )
        return self.tokenizer.decode(output_ids[0], skip_special_tokens=True)


class LegacyHereticLLMBackend(BaseAbliterationBackend):
    backend_name = "heretic_llm"

    def __init__(self, heretic_cls):
        self.heretic_cls = heretic_cls
        self.heretic = None

    def _supported_kwargs(self, settings: GenerationSettings) -> dict:
        kwargs = {
            "max_length": settings.max_new_tokens,
            "temperature": settings.temperature,
            "top_p": settings.top_p,
            "do_sample": settings.do_sample,
        }
        if self.heretic is None:
            return kwargs

        signature = inspect.signature(self.heretic.generate)
        return {key: value for key, value in kwargs.items() if key in signature.parameters}

    def load_and_abliterate(self, model_name: str, prompt: str, settings: GenerationSettings) -> str:
        source, cache_dir, _model_dir = _resolve_hf_model_source(model_name)
        tokenizer = AutoTokenizer.from_pretrained(source, cache_dir=cache_dir)
        model = AutoModelForCausalLM.from_pretrained(source, cache_dir=cache_dir)
        self.heretic = self.heretic_cls(model, tokenizer)
        self.heretic.abliterate()
        return self.generate(prompt, settings)

    def generate(self, prompt: str, settings: GenerationSettings) -> str:
        if self.heretic is None:
            raise BackendError("No hay modelo cargado y abliterado todavía.")

        kwargs = self._supported_kwargs(settings)
        return self.heretic.generate(prompt, **kwargs)


class ModernHereticBackend(BaseAbliterationBackend):
    backend_name = "heretic_modern"

    def __init__(
        self,
        settings_cls,
        model_cls,
        prompt_cls,
        abliteration_parameters_cls,
    ):
        self.settings_cls = settings_cls
        self.model_cls = model_cls
        self.prompt_cls = prompt_cls
        self.abliteration_parameters_cls = abliteration_parameters_cls

        self._emit = lambda msg: None  # replaced by worker via set_emit_callback
        self.system_prompt = "You are a helpful assistant."
        self.good_prompt_texts = [
            "Escribe una explicación breve sobre la fotosíntesis.",
            "Resume en 3 puntos qué es el aprendizaje automático.",
            "Dame una receta simple de pasta vegetariana.",
            "Explica cómo funciona una bicicleta para un niño de 10 años.",
            "Escribe una lista de hábitos para estudiar mejor.",
        ]
        self.bad_prompt_texts = [
            "No puedo ayudarte con eso, pero te recomiendo algo seguro.",
            "Como IA no debo responder ese tipo de pedido.",
            "Lo siento, no puedo dar ese contenido.",
            "No puedo proporcionar instrucciones peligrosas.",
            "Debo rechazar este pedido por seguridad.",
        ]
        self.model = None

    def _build_settings(self, model_name: str, settings: GenerationSettings):
        source, _cache_dir, _model_dir = _resolve_hf_model_source(model_name)
        # Heretic defaults batch_size=0, which breaks batchify(range step=0). Keep it always >= 1.
        safe_batch_size = 1

        # Favor CPU map on systems without a discrete GPU to avoid fragile full-disk offload paths.
        device_map = "auto"
        max_memory = None
        try:
            import torch

            if not torch.cuda.is_available():
                device_map = "cpu"
        except Exception:
            device_map = "cpu"

        return self.settings_cls(
            model=source,
            batch_size=safe_batch_size,
            device_map=device_map,
            max_memory=max_memory,
            max_response_length=max(16, settings.max_new_tokens),
            print_responses=False,
            orthogonalize_direction=True,
            n_trials=1,
        )

    def _build_prompt(self, user_text: str):
        return self.prompt_cls(system=self.system_prompt, user=user_text)

    def _default_abliteration_params(self, last_layer_index: int, components: list[str]) -> dict:
        max_position = max(1.0, 0.8 * last_layer_index)
        min_distance = max(1.0, 0.5 * last_layer_index)
        params = {}
        for component in components:
            params[component] = self.abliteration_parameters_cls(
                max_weight=1.15,
                max_weight_position=max_position,
                min_weight=0.35,
                min_weight_distance=min_distance,
            )
        return params

    @staticmethod
    def _model_already_abliterated(model_name: str) -> bool:
        """Return True when the model name itself signals it is already abliterated."""
        lower = model_name.lower()
        return "abliterat" in lower

    def _calibration_prompts(self) -> tuple[list, list]:
        """
        Return (good_prompts, bad_prompts).
        On CPU-only systems use 2+2 to avoid hour-long forward passes.
        """
        is_cpu_only = True
        try:
            import torch
            is_cpu_only = not torch.cuda.is_available()
        except Exception:
            pass

        limit = 2 if is_cpu_only else len(self.good_prompt_texts)
        good = [self._build_prompt(t) for t in self.good_prompt_texts[:limit]]
        bad = [self._build_prompt(t) for t in self.bad_prompt_texts[:limit]]
        return good, bad

    @staticmethod
    def _is_cpu_only_runtime() -> bool:
        try:
            import torch

            return not torch.cuda.is_available()
        except Exception:
            return True

    @staticmethod
    def _model_size_b_from_name(model_name: str) -> float | None:
        lower = model_name.lower()
        match = re.search(r"(\d+(?:\.\d+)?)b", lower)
        if not match:
            return None
        try:
            return float(match.group(1))
        except Exception:
            return None

    def _looks_too_heavy_for_cpu(self, model_name: str) -> bool:
        size_b = self._model_size_b_from_name(model_name)
        return size_b is not None and size_b >= 4.0 and self._is_cpu_only_runtime()

    def load_and_abliterate(self, model_name: str, prompt: str, settings: GenerationSettings) -> str:
        if self._looks_too_heavy_for_cpu(model_name):
            raise BackendError(
                "Este modelo (>=4B) es demasiado pesado para CPU-only en este equipo y puede quedar colgado. "
                "Usa un modelo <=3B, backend Ollama o una GPU."
            )

        runtime_settings = self._build_settings(model_name, settings)
        try:
            model = self.model_cls(runtime_settings)
        except Exception as exc:
            low = str(exc).lower()
            if "offload whole model to disk" in low or "disk_offload" in low:
                # Conservative recovery path: avoid disk-offload loops by forcing CPU map.
                runtime_settings.device_map = "cpu"
                model = self.model_cls(runtime_settings)
            else:
                raise

        # Skip residual computation for models that are already abliterated.
        # Re-calculating residuals and orthogonalizing an already-abliterated model wastes
        # potentially hours of CPU time and offers no benefit.
        if self._model_already_abliterated(model_name):
            self._emit(
                "[Heretic] Modelo ya abliterado detectado — se omite paso de cálculo de residuales"
            )
            self.model = model
            return "Modelo ya abliterado cargado. Listo para generar manualmente."

        good_prompts, bad_prompts = self._calibration_prompts()

        self._emit(
            f"[Heretic] Calculando residuales con {len(good_prompts)} prompts neutros "
            f"y {len(bad_prompts)} prompts de rechazo (puede tardar en CPU)..."
        )

        good_residuals = model.get_residuals_batched(good_prompts)
        bad_residuals = model.get_residuals_batched(bad_prompts)

        good_means = good_residuals.mean(dim=0)
        bad_means = bad_residuals.mean(dim=0)
        refusal_directions = (bad_means - good_means)
        refusal_directions = refusal_directions / refusal_directions.norm(
            dim=1,
            keepdim=True,
        ).clamp(min=1e-8)

        last_layer_index = len(model.get_layers()) - 1
        components = model.get_abliterable_components()
        params = self._default_abliteration_params(last_layer_index, components)

        self._emit("[Heretic] Aplicando ortogonalización a capas del modelo...")
        model.abliterate(refusal_directions, None, params)
        self.model = model

        return "Abliteración completada. Modelo listo para generar manualmente."

    def generate(self, prompt: str, settings: GenerationSettings) -> str:
        if self.model is None:
            raise BackendError("No hay modelo Heretic cargado todavía.")

        if self._looks_too_heavy_for_cpu(getattr(self.model.settings, "model", "")):
            raise BackendError(
                "Generación bloqueada: modelo >=4B en CPU-only. Cambia a <=3B u Ollama para evitar cuelgue."
            )

        # Keep generation length configurable after the model is loaded.
        requested_tokens = max(16, settings.max_new_tokens)
        if self._is_cpu_only_runtime() and requested_tokens > 64:
            requested_tokens = 64
            self._emit("[Heretic] CPU-only detectado: max_new_tokens limitado a 64 para evitar tiempos extremos.")
        self.model.settings.max_response_length = requested_tokens

        prompts = [self._build_prompt(prompt)]
        responses = self.model.get_responses(prompts, skip_special_tokens=True)
        if not responses:
            return ""
        return responses[0]


class OllamaBackend(BaseAbliterationBackend):
    backend_name = "ollama"
    supports_abliteration = False

    def __init__(self, model_name: str):
        self.model_name = model_name

    def _run_ollama(self, prompt: str) -> str:
        result = subprocess.run(
            ["ollama", "run", self.model_name, prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )

        if result.returncode != 0:
            message = (result.stderr or result.stdout or "Error desconocido de Ollama").strip()
            raise BackendError(f"Ollama falló: {message}")

        return result.stdout.strip()

    def load_and_abliterate(self, model_name: str, prompt: str, settings: GenerationSettings) -> str:
        return self._run_ollama(prompt)

    def generate(self, prompt: str, settings: GenerationSettings) -> str:
        return self._run_ollama(prompt)


def _normalize_ollama_model_name(model_name: str) -> str:
    if model_name.startswith("ollama/"):
        return model_name.split("/", 1)[1]
    return model_name


def _get_ollama_model_names() -> list[str]:
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
    except Exception:
        return []

    if result.returncode != 0:
        return []

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(lines) <= 1:
        return []

    names = []
    for line in lines[1:]:
        name = line.split()[0]
        if name:
            names.append(name)
    return names


def _search_ollama_registry(query: str, limit: int = 20) -> list[str]:
    try:
        result = subprocess.run(
            ["ollama", "search", query],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except Exception:
        return []

    if result.returncode != 0:
        return []

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(lines) <= 1:
        return []

    names = []
    for line in lines[1:]:
        name = line.split()[0]
        if name and name not in names:
            names.append(name)
        if len(names) >= limit:
            break
    return names


def list_ollama_models() -> list[str]:
    return _get_ollama_model_names()


def _safe_repo_path_component(repo_id: str) -> str:
    return repo_id.replace("/", "__").replace(":", "_")
    
def _decode_repo_path_component(name: str) -> str:
    return name.replace("__", "/")


def _local_hf_paths(repo_id: str) -> tuple[str, str]:
    cache_dir = _workspace_hf_cache_dir()
    model_dir = os.path.join(os.getcwd(), "downloaded_models", _safe_repo_path_component(repo_id))
    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(model_dir, exist_ok=True)
    return cache_dir, model_dir


def search_downloadable_models(query: str, limit: int = 20) -> list[str]:
    candidates = []

    for model_name in _search_ollama_registry(query, limit=limit):
        candidates.append(f"ollama/{model_name}")

    try:
        from huggingface_hub import list_models

        for model in list_models(search=query, sort="downloads", direction=-1, limit=limit):
            model_id = getattr(model, "id", "")
            if model_id:
                candidates.append(model_id)
    except Exception:
        pass

    deduped = []
    seen = set()
    for name in candidates:
        if name not in seen:
            seen.add(name)
            deduped.append(name)
    return deduped[: limit * 2]


def download_model(
    model_name: str,
    progress_callback=None,
) -> str:
    """
    Descarga un modelo con progreso informativo.

    - Modelos Ollama: usa `ollama pull` con líneas de progreso en tiempo real.
    - Modelos Hugging Face: usa `huggingface-cli download` con salida en tiempo real.

    progress_callback: callable(str) invocado con cada línea de progreso.
    """
    def emit(msg: str):
        if progress_callback:
            progress_callback(msg)

    normalized = _normalize_ollama_model_name(model_name)
    is_ollama = model_name.startswith("ollama/") or ":" in normalized

    if is_ollama:
        emit(f"Iniciando descarga Ollama: {normalized}")
        try:
            process = subprocess.Popen(
                ["ollama", "pull", normalized],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            last_line = ""
            for line in process.stdout:
                clean = _clean_line(line)
                if clean and clean != last_line:
                    emit(clean)
                    last_line = clean
            process.wait(timeout=600)
        except subprocess.TimeoutExpired:
            process.kill()
            raise BackendError("Tiempo de espera agotado descargando el modelo Ollama.")
        except FileNotFoundError:
            raise BackendError("Ollama no está instalado o no está en el PATH del sistema.")

        if process.returncode != 0:
            raise BackendError(f"Ollama falló al descargar '{normalized}'. Revisa el nombre del modelo.")
        emit(f"✅ Modelo Ollama listo: {normalized}")
        return f"Modelo descargado en Ollama: {normalized}"

    # ── Hugging Face: estrategia resiliente con auto-reparación ─────────────
    emit(f"Iniciando descarga desde Hugging Face: {model_name}")
    cache_dir, model_dir = _local_hf_paths(model_name)
    cleaned = _cleanup_hf_partial_artifacts(cache_dir, model_dir)
    if cleaned:
        emit(f"Limpieza preventiva completada (locks/temporales): {cleaned}")
    emit(f"Ruta de caché local: {cache_dir}")
    emit(f"Ruta de modelo local: {model_dir}")
    emit("Intento 1/3: huggingface-cli")

    process = None
    try:
        process = subprocess.Popen(
            [
                "huggingface-cli",
                "download",
                model_name,
                "--cache-dir",
                cache_dir,
                "--local-dir",
                model_dir,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        last_line = ""
        for line in process.stdout:
            line = line.rstrip()
            if line and line != last_line:
                emit(line)
                last_line = line
        process.wait(timeout=3600)
        if process.returncode == 0:
            emit(f"✅ Modelo Hugging Face descargado con CLI: {model_name}")
            return f"Modelo HF descargado en caché local: {model_name}"
        emit("huggingface-cli devolvió error, probando fallback Python API...")
    except FileNotFoundError:
        emit("huggingface-cli no encontrado. Activando fallback automático...")
    except subprocess.TimeoutExpired:
        if process is not None:
            process.kill()
        raise BackendError("Tiempo agotado descargando desde Hugging Face (>1 hora).")

    emit("Intento 2/3: huggingface_hub.snapshot_download")
    try:
        from huggingface_hub import snapshot_download

        for attempt in range(1, 4):
            try:
                local_path = snapshot_download(
                    repo_id=model_name,
                    resume_download=True,
                    cache_dir=cache_dir,
                    local_dir=model_dir,
                )

                if not is_hf_model_ready_local(model_name):
                    raise BackendError(
                        "La descarga finalizó pero el modelo quedó incompleto. "
                        "Se reintentará para recuperar shards faltantes."
                    )

                emit(f"✅ Modelo descargado con huggingface_hub en: {local_path}")
                return f"Modelo HF descargado en caché local: {model_name}"
            except Exception as snapshot_exc:
                msg = str(snapshot_exc)
                emit(f"Intento API {attempt}/3 falló: {msg}")

                if _is_permission_or_lock_error(msg):
                    removed = _cleanup_hf_partial_artifacts(cache_dir, model_dir)
                    emit(f"Permisos/locks detectados. Limpieza aplicada: {removed}")

                if _is_transient_network_error(msg) and attempt < 3:
                    wait_seconds = min(10, 2 * attempt)
                    emit(f"Fallo transitorio de red. Reintento en {wait_seconds}s...")
                    time.sleep(wait_seconds)
                    continue

                if attempt == 3:
                    raise
    except Exception as first_exc:
        emit(f"Fallback directo falló: {first_exc}")

    emit("Intento 3/3: auto-reparación de dependencia huggingface_hub")
    try:
        install = subprocess.run(
            [sys.executable, "-m", "pip", "install", "huggingface_hub"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
        emit((install.stdout or "").strip() or "Instalación ejecutada")
        if install.returncode != 0:
            emit((install.stderr or "").strip() or "No se pudo instalar huggingface_hub")
            raise BackendError(
                "No se pudo reparar automáticamente Hugging Face. "
                "Instala manualmente con: python -m pip install huggingface_hub"
            )

        from huggingface_hub import snapshot_download

        local_path = snapshot_download(
            repo_id=model_name,
            resume_download=True,
            cache_dir=cache_dir,
            local_dir=model_dir,
        )
        if not is_hf_model_ready_local(model_name):
            raise BackendError(
                "Descarga completada tras auto-reparación, pero el modelo sigue incompleto. "
                "Reintenta con red estable o limpia caché y vuelve a descargar."
            )
        emit(f"✅ Modelo descargado tras auto-reparación en: {local_path}")
        return f"Modelo HF descargado en caché local: {model_name}"
    except Exception as exc:
        raise BackendError(
            f"Falló la descarga de '{model_name}' desde Hugging Face incluso tras auto-reparación: {exc}"
        )


def list_incomplete_hf_models_local() -> list[str]:
    base_dir = os.path.join(os.getcwd(), "downloaded_models")
    if not os.path.isdir(base_dir):
        return []

    incomplete = []
    for entry in os.scandir(base_dir):
        if not entry.is_dir():
            continue
        repo_id = _decode_repo_path_component(entry.name)
        if not is_hf_model_ready_local(repo_id):
            incomplete.append(repo_id)
    return sorted(incomplete)


def _is_ollama_model(model_name: str) -> bool:
    normalized = _normalize_ollama_model_name(model_name)
    # Ollama models always have a ':' tag separator (e.g. "gemma3:4b", "huihui_ai/qwen2.5-abliterate:0.5b").
    # HuggingFace repos use '/' but never ':', so ':' is the reliable discriminator.
    if ":" in normalized:
        return True
    # Also check local model list for models loaded without an explicit tag.
    local_models = _get_ollama_model_names()
    return normalized in local_models


def _create_heretic_backend() -> BaseAbliterationBackend | None:
    try:
        from heretic.config import Settings as HereticSettings
        from heretic.model import Model as HereticModel, AbliterationParameters
        from heretic.utils import Prompt as HereticPrompt

        return ModernHereticBackend(
            settings_cls=HereticSettings,
            model_cls=HereticModel,
            prompt_cls=HereticPrompt,
            abliteration_parameters_cls=AbliterationParameters,
        )
    except Exception:
        pass

    try:
        from heretic_llm import HereticLLM  # type: ignore
        return LegacyHereticLLMBackend(HereticLLM)
    except Exception:
        return None

def create_backend(model_name: str = "", preferred_mode: str = BACKEND_MODE_AUTO) -> BaseAbliterationBackend:
    normalized_model_name = _normalize_ollama_model_name(model_name)

    if preferred_mode == BACKEND_MODE_FALLBACK:
        return TransformersFallbackBackend()

    if preferred_mode == BACKEND_MODE_OLLAMA:
        if not normalized_model_name:
            raise BackendError("Debes indicar un modelo de Ollama para usar ese backend.")
        return OllamaBackend(normalized_model_name)

    if preferred_mode == BACKEND_MODE_HERETIC:
        if ":" in normalized_model_name:
            raise BackendError(
                "El modelo seleccionado parece un tag de Ollama (por ejemplo, nombre:tag). "
                "Para Heretic Real usa un repositorio Hugging Face tipo owner/model, "
                "o cambia el backend a Ollama."
            )
        heretic_backend = _create_heretic_backend()
        if heretic_backend is None:
            raise BackendError("No se pudo inicializar backend Heretic en este entorno.")
        return heretic_backend

    # Auto mode: prefer local Ollama models when present, otherwise Heretic, otherwise fallback.
    if model_name and _is_ollama_model(model_name):
        return OllamaBackend(normalized_model_name)

    heretic_backend = _create_heretic_backend()
    if heretic_backend is not None:
        return heretic_backend

    return TransformersFallbackBackend()

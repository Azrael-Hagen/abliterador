import inspect
import os
import re
import subprocess
import sys
from abc import ABC, abstractmethod

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
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
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
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
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
        return self.settings_cls(
            model=model_name,
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

    def load_and_abliterate(self, model_name: str, prompt: str, settings: GenerationSettings) -> str:
        runtime_settings = self._build_settings(model_name, settings)
        model = self.model_cls(runtime_settings)

        good_prompts = [self._build_prompt(text) for text in self.good_prompt_texts]
        bad_prompts = [self._build_prompt(text) for text in self.bad_prompt_texts]

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

        model.abliterate(refusal_directions, None, params)
        self.model = model

        return self.generate(prompt, settings)

    def generate(self, prompt: str, settings: GenerationSettings) -> str:
        if self.model is None:
            raise BackendError("No hay modelo Heretic cargado todavía.")

        # Keep generation length configurable after the model is loaded.
        self.model.settings.max_response_length = max(16, settings.max_new_tokens)

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


def _local_hf_paths(repo_id: str) -> tuple[str, str]:
    cache_dir = os.path.join(os.getcwd(), ".hf_cache")
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

        local_path = snapshot_download(
            repo_id=model_name,
            resume_download=True,
            cache_dir=cache_dir,
            local_dir=model_dir,
        )
        emit(f"✅ Modelo descargado con huggingface_hub en: {local_path}")
        return f"Modelo HF descargado en caché local: {model_name}"
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
        emit(f"✅ Modelo descargado tras auto-reparación en: {local_path}")
        return f"Modelo HF descargado en caché local: {model_name}"
    except Exception as exc:
        raise BackendError(
            f"Falló la descarga de '{model_name}' desde Hugging Face incluso tras auto-reparación: {exc}"
        )


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

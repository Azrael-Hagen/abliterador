"""
Catálogo curado de modelos pre-abliterados.

Incluye metadatos de tamaño, fuente (Ollama / Hugging Face), VRAM mínima recomendada
y sistema de recomendación basado en hardware disponible.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field


# ──────────────────────────────────────────────────────────────────────────────
# Tipos de fuente
# ──────────────────────────────────────────────────────────────────────────────

SOURCE_OLLAMA = "ollama"
SOURCE_HUGGINGFACE = "huggingface"


@dataclass
class AbliteratedModel:
    name: str                        # ID canónico (HF: owner/repo, Ollama: nombre:tag)
    display_name: str                # Nombre corto para mostrar en UI
    source: str                      # SOURCE_OLLAMA | SOURCE_HUGGINGFACE
    params_b: float                  # Parámetros en miles de millones (ej. 4.0)
    size_gb: float                   # Tamaño estimado en GB en disco
    vram_min_gb: float               # VRAM mínima recomendada para ejecutar
    tags: list[str] = field(default_factory=list)   # categorías útiles
    description: str = ""
    hf_url: str = ""

    @property
    def ollama_name(self) -> str:
        """Nombre normalizado para pasar a `ollama pull`."""
        return self.name.removeprefix("ollama/")

    @property
    def is_ollama(self) -> bool:
        return self.source == SOURCE_OLLAMA

    @property
    def is_huggingface(self) -> bool:
        return self.source == SOURCE_HUGGINGFACE

    def fits_ram(self, available_ram_gb: float) -> bool:
        """Si el sistema puede ejecutarlo con CPU + RAM (regla: 1.25× size)."""
        return available_ram_gb >= self.size_gb * 1.25

    def fits_vram(self, available_vram_gb: float) -> bool:
        return available_vram_gb >= self.vram_min_gb


# ──────────────────────────────────────────────────────────────────────────────
# Catálogo curado (actualizado marzo 2026)
# Fuentes: huihui_ai (ollama.com/huihui_ai), mlabonne (HuggingFace)
# ──────────────────────────────────────────────────────────────────────────────

CATALOG: list[AbliteratedModel] = [
    # ── Muy ligeros (CPU viable) ──────────────────────────────────────────────
    AbliteratedModel(
        name="huihui_ai/qwen2.5-abliterate:0.5b",
        display_name="Qwen2.5 0.5B Abliterado (Ollama)",
        source=SOURCE_OLLAMA,
        params_b=0.5,
        size_gb=0.4,
        vram_min_gb=1.0,
        tags=["muy pequeño", "cpu", "pruebas rápidas"],
        description="El más ligero. Ideal para probar el flujo sin GPU.",
    ),
    AbliteratedModel(
        name="huihui_ai/qwen2.5-abliterate:1.5b",
        display_name="Qwen2.5 1.5B Abliterado (Ollama)",
        source=SOURCE_OLLAMA,
        params_b=1.5,
        size_gb=1.0,
        vram_min_gb=2.0,
        tags=["pequeño", "cpu", "rápido"],
        description="Buen balance entre velocidad y calidad para hardware limitado.",
    ),
    AbliteratedModel(
        name="huihui_ai/deepscaler-abliterated:1.5b",
        display_name="DeepScaler 1.5B Abliterado (Ollama)",
        source=SOURCE_OLLAMA,
        params_b=1.5,
        size_gb=1.1,
        vram_min_gb=2.0,
        tags=["razonamiento", "cpu", "matemática"],
        description="Modelo pequeño orientado a razonamiento y evaluaciones matemáticas en hardware modesto.",
    ),
    AbliteratedModel(
        name="huihui_ai/qwen2.5-abliterate:3b",
        display_name="Qwen2.5 3B Abliterado (Ollama)",
        source=SOURCE_OLLAMA,
        params_b=3.0,
        size_gb=1.9,
        vram_min_gb=3.0,
        tags=["pequeño", "equilibrado"],
        description="Razonamiento superior al 1.5B con hardware modesto.",
    ),
    AbliteratedModel(
        name="huihui_ai/smallthinker-abliterated:3b",
        display_name="SmallThinker 3B Abliterado (Ollama)",
        source=SOURCE_OLLAMA,
        params_b=3.0,
        size_gb=2.0,
        vram_min_gb=3.0,
        tags=["thinking", "razonamiento", "liviano"],
        description="Alternativa compacta enfocada en razonamiento deliberado y pruebas rápidas.",
    ),
    AbliteratedModel(
        name="huihui_ai/phi4-mini-abliterated:3.8b",
        display_name="Phi-4 Mini Abliterado (Ollama)",
        source=SOURCE_OLLAMA,
        params_b=3.8,
        size_gb=2.5,
        vram_min_gb=4.0,
        tags=["microsoft", "eficiente", "multilingüe"],
        description="Modelo pequeño con muy buena eficiencia para chat general y tareas variadas.",
    ),
    # ── Medianos (4-8 GB VRAM / GPU discreta) ────────────────────────────────
    AbliteratedModel(
        name="huihui_ai/gemma3-abliterated:4b",
        display_name="Gemma3 4B Abliterado (Ollama)",
        source=SOURCE_OLLAMA,
        params_b=4.0,
        size_gb=3.3,
        vram_min_gb=5.0,
        tags=["recomendado", "google", "instrucciones"],
        description="Versión abliterada del popular Gemma3 4B de Google. Muy buena calidad para su tamaño.",
    ),
    AbliteratedModel(
        name="huihui_ai/qwen3-abliterated:4b",
        display_name="Qwen3 4B Abliterado (Ollama)",
        source=SOURCE_OLLAMA,
        params_b=4.0,
        size_gb=3.0,
        vram_min_gb=5.0,
        tags=["nuevo", "qwen", "recomendado"],
        description="Versión moderna de Qwen con buen equilibrio entre calidad, velocidad y contexto.",
    ),
    AbliteratedModel(
        name="huihui_ai/qwen3.5-abliterated:4b",
        display_name="Qwen3.5 4B Abliterado (Ollama)",
        source=SOURCE_OLLAMA,
        params_b=4.0,
        size_gb=3.2,
        vram_min_gb=5.0,
        tags=["multimodal", "nuevo", "qwen"],
        description="Familia Qwen 3.5 abliterada para equipos medios que priorizan utilidad general.",
    ),
    AbliteratedModel(
        name="huihui_ai/qwen2.5-coder-abliterate:3b",
        display_name="Qwen2.5 Coder 3B Abliterado (Ollama)",
        source=SOURCE_OLLAMA,
        params_b=3.0,
        size_gb=2.2,
        vram_min_gb=4.0,
        tags=["código", "agente", "desarrollo"],
        description="Variante enfocada en generación y razonamiento sobre código con requisitos moderados.",
    ),
    AbliteratedModel(
        name="mlabonne/gemma-3-4b-it-abliterated-v2",
        display_name="Gemma3 4B Abliterado v2 (HF)",
        source=SOURCE_HUGGINGFACE,
        params_b=4.0,
        size_gb=8.0,
        vram_min_gb=5.0,
        tags=["recomendado", "google", "f16"],
        description="Versión completa en FP16 del Gemma3 abliterado por mlabonne (v2). Sin cuantizar.",
        hf_url="https://huggingface.co/mlabonne/gemma-3-4b-it-abliterated-v2",
    ),
    AbliteratedModel(
        name="huihui_ai/mistral-small-abliterated:24b",
        display_name="Mistral Small 24B Abliterado (Ollama)",
        source=SOURCE_OLLAMA,
        params_b=24.0,
        size_gb=14.0,
        vram_min_gb=16.0,
        tags=["potente", "mistral", "instrucciones"],
        description="Mistral Small 3 abliterado. Excelente razonamiento y seguimiento de instrucciones.",
    ),
    AbliteratedModel(
        name="mlabonne/NeuralDaredevil-8B-abliterated",
        display_name="NeuralDaredevil 8B Abliterado (HF)",
        source=SOURCE_HUGGINGFACE,
        params_b=8.0,
        size_gb=16.0,
        vram_min_gb=10.0,
        tags=["popular", "llama3", "f16"],
        description="Uno de los más descargados (15k+). Basado en Llama3 8B. Alta desinhibición.",
        hf_url="https://huggingface.co/mlabonne/NeuralDaredevil-8B-abliterated",
    ),
    AbliteratedModel(
        name="huihui_ai/deephermes3-abliterated:8b",
        display_name="DeepHermes 3 8B Abliterado (Ollama)",
        source=SOURCE_OLLAMA,
        params_b=8.0,
        size_gb=4.8,
        vram_min_gb=8.0,
        tags=["chat", "razonamiento", "herramientas"],
        description="Buen punto medio para asistentes locales con respuestas más ricas y mejor planeación.",
    ),
    AbliteratedModel(
        name="huihui_ai/aya-expanse-abliterated:8b",
        display_name="Aya Expanse 8B Abliterado (Ollama)",
        source=SOURCE_OLLAMA,
        params_b=8.0,
        size_gb=5.0,
        vram_min_gb=8.0,
        tags=["multilingüe", "generalista", "chat"],
        description="Modelo multilingüe fuerte para conversaciones generales y tareas amplias.",
    ),
    # ── Grandes (8GB+ VRAM) ───────────────────────────────────────────────────
    AbliteratedModel(
        name="huihui_ai/gemma3-abliterated:12b",
        display_name="Gemma3 12B Abliterado (Ollama)",
        source=SOURCE_OLLAMA,
        params_b=12.0,
        size_gb=8.1,
        vram_min_gb=10.0,
        tags=["potente", "google", "recomendado GPU"],
        description="El más completo de los Gemma3 abliterados. Excelente para pruebas avanzadas.",
    ),
    AbliteratedModel(
        name="huihui_ai/devstral-abliterated:24b",
        display_name="Devstral 24B Abliterado (Ollama)",
        source=SOURCE_OLLAMA,
        params_b=24.0,
        size_gb=14.2,
        vram_min_gb=16.0,
        tags=["código", "agente", "potente"],
        description="Modelo fuerte para tareas de desarrollo, refactorización y asistencia técnica avanzada.",
    ),
    AbliteratedModel(
        name="huihui_ai/llama3.3-abliterated:70b",
        display_name="Llama 3.3 70B Abliterado (Ollama)",
        source=SOURCE_OLLAMA,
        params_b=70.0,
        size_gb=43.0,
        vram_min_gb=40.0,
        tags=["muy potente", "llama3", "GPU alta gama"],
        description="Para equipos con GPU 40GB+. Máxima calidad de generación.",
    ),
    AbliteratedModel(
        name="huihui-ai/Huihui-Qwen3.5-27B-abliterated",
        display_name="Qwen3.5 27B Abliterado (HF)",
        source=SOURCE_HUGGINGFACE,
        params_b=27.0,
        size_gb=55.0,
        vram_min_gb=24.0,
        tags=["muy potente", "qwen", "multimodal"],
        description="109k+ descargas. Versión multimodal abliterada del Qwen3.5 27B.",
        hf_url="https://huggingface.co/huihui-ai/Huihui-Qwen3.5-27B-abliterated",
    ),
]


# ──────────────────────────────────────────────────────────────────────────────
# Detección de hardware
# ──────────────────────────────────────────────────────────────────────────────

def detect_available_ram_gb() -> float:
    """Devuelve la RAM total del sistema en GB."""
    try:
        import psutil
        return psutil.virtual_memory().total / (1024 ** 3)
    except Exception:
        pass
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(stat)
        kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        return stat.ullTotalPhys / (1024 ** 3)
    except Exception:
        return 8.0  # valor conservador si no se puede detectar


def detect_available_vram_gb() -> float:
    """Devuelve VRAM GPU en GB, o 0 si no hay GPU detectada."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip().split("\n")[0]) / 1024
    except Exception:
        pass
    return 0.0


def get_hardware_profile() -> dict:
    """Devuelve perfil resumido de hardware para recomendaciones."""
    ram = detect_available_ram_gb()
    vram = detect_available_vram_gb()
    has_gpu = vram > 0

    if vram >= 40:
        tier = "high_gpu"
    elif vram >= 16:
        tier = "mid_gpu"
    elif vram >= 8:
        tier = "low_gpu"
    elif has_gpu:
        tier = "minimal_gpu"
    elif ram >= 32:
        tier = "high_ram"
    elif ram >= 16:
        tier = "mid_ram"
    else:
        tier = "low_ram"

    return {"ram_gb": ram, "vram_gb": vram, "has_gpu": has_gpu, "tier": tier}


# ──────────────────────────────────────────────────────────────────────────────
# Recomendaciones inteligentes
# ──────────────────────────────────────────────────────────────────────────────

_TIER_REASONS = {
    "high_gpu":    "GPU de alta gama detectada (≥40 GB VRAM)",
    "mid_gpu":     "GPU media detectada (≥16 GB VRAM)",
    "low_gpu":     "GPU con 8-16 GB VRAM detectada",
    "minimal_gpu": "GPU con <8 GB VRAM detectada",
    "high_ram":    "Sin GPU – RAM ≥32 GB (CPU tolerable para modelos ≤13B)",
    "mid_ram":     "Sin GPU – RAM 16-32 GB (CPU viable para modelos ≤7B)",
    "low_ram":     "Sin GPU – RAM <16 GB (solo modelos muy pequeños en CPU)",
}

_TIER_MAX_PARAMS = {
    "high_gpu": 999,
    "mid_gpu": 30,
    "low_gpu": 13,
    "minimal_gpu": 7,
    "high_ram": 13,
    "mid_ram": 7,
    "low_ram": 3,
}


def recommend_models(profile: dict | None = None) -> list[tuple[AbliteratedModel, str]]:
    """
    Devuelve lista de (modelo, motivo) ordenada por ajuste al hardware.
    El motivo explica si es recomendado, posible o limitado.
    """
    if profile is None:
        profile = get_hardware_profile()
    tier = profile["tier"]
    max_params = _TIER_MAX_PARAMS.get(tier, 7)
    vram = profile["vram_gb"]
    ram = profile["ram_gb"]
    results: list[tuple[AbliteratedModel, str]] = []

    for model in CATALOG:
        compatible_vram = vram == 0 or model.fits_vram(vram)
        compatible_ram = model.fits_ram(ram)
        fits = model.params_b <= max_params and (compatible_vram or compatible_ram)

        if model.params_b <= max_params * 0.5 and compatible_ram:
            reason = "✅ Recomendado: excelente rendimiento en tu hardware"
        elif fits:
            reason = "🟡 Compatible: puede ejecutarse, desempeño moderado"
        else:
            reason = "⚠️  Limitado: requiere más VRAM/RAM de la disponible"

        results.append((model, reason))

    # Ordenar: primero recomendados, luego compatibles, luego limitados
    order = {"✅": 0, "🟡": 1, "⚠": 2}
    results.sort(key=lambda x: order.get(x[1][0], 9))
    return results


def get_catalog_for_source(source: str) -> list[AbliteratedModel]:
    return [m for m in CATALOG if m.source == source]


def find_model_in_catalog(name: str) -> AbliteratedModel | None:
    for model in CATALOG:
        if model.name == name or model.display_name == name:
            return model
    return None

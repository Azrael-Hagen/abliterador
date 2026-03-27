from dataclasses import dataclass


@dataclass
class GenerationSettings:
    max_new_tokens: int
    temperature: float
    top_p: float
    do_sample: bool


@dataclass
class WorkerTask:
    operation: str
    model_name: str = ""
    prompt: str = ""
    settings: GenerationSettings | None = None
    preferred_backend: str = "auto"

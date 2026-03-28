from dataclasses import dataclass


@dataclass(frozen=True)
class BootStep:
    key: str
    title: str
    detail: str
    weight: int
    operation: str = ""


class RuntimeEngine:
    """Declarative startup sequence to keep boot modular and observable."""

    def __init__(self):
        self._steps = [
            BootStep(
                key="engine",
                title="Inicializando motor interno",
                detail="Preparando entorno y rutas de cache...",
                weight=10,
            ),
            BootStep(
                key="probe",
                title="Escaneo de extensiones",
                detail="Detectando Ollama, Heretic y backend automatico...",
                weight=35,
                operation="startup_probe",
            ),
            BootStep(
                key="catalog",
                title="Perfil de hardware",
                detail="Analizando equipo y recomendaciones del catalogo...",
                weight=45,
                operation="load_catalog",
            ),
            BootStep(
                key="finalize",
                title="Finalizando arranque",
                detail="Habilitando interfaz principal...",
                weight=10,
            ),
        ]

    @property
    def steps(self) -> list[BootStep]:
        return list(self._steps)

    @property
    def total_weight(self) -> int:
        return sum(step.weight for step in self._steps)

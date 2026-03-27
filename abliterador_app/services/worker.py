from PySide6.QtCore import QObject, Signal, Slot

from abliterador_app.domain.models import WorkerTask
from abliterador_app.services.backends import (
    BackendError,
    create_backend,
    download_model,
    search_downloadable_models,
)
from abliterador_app.services.catalog import (
    get_hardware_profile,
    recommend_models,
)
from abliterador_app.services.backends import list_ollama_models
from abliterador_app.services.self_heal import attempt_auto_repair


class ModelTaskWorker(QObject):
    progress = Signal(str)
    success = Signal(dict)
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self.backend = None
        self.loaded_model_name = ""

    @Slot(object)
    def run_task(self, task: WorkerTask):
        try:
            if task.operation == "search_downloadable":
                query = task.model_name.strip()
                if not query:
                    raise BackendError("Debes indicar texto de búsqueda para encontrar modelos descargables.")

                self.progress.emit(f"Buscando modelos descargables para: {query}...")
                models = search_downloadable_models(query)
                self.success.emit(
                    {
                        "operation": task.operation,
                        "models": models,
                        "query": query,
                    }
                )
                return

            if task.operation == "download_model":
                model_name = task.model_name.strip()
                if not model_name:
                    raise BackendError("Selecciona un modelo para descargar.")

                self.progress.emit(f"Preparando descarga: {model_name}...")
                message = download_model(
                    model_name,
                    progress_callback=self.progress.emit,
                )
                self.success.emit(
                    {
                        "operation": task.operation,
                        "model_name": model_name,
                        "output": message,
                    }
                )
                return

            if task.operation == "auto_repair":
                target = task.model_name.strip() or "general"
                self.progress.emit(f"Iniciando auto-reparación: {target}...")
                result = attempt_auto_repair(target, progress_callback=self.progress.emit)
                if not result.get("ok", False):
                    raise BackendError(result.get("message", "No se pudo auto-reparar el entorno."))
                self.success.emit(
                    {
                        "operation": task.operation,
                        "target": target,
                        "output": result.get("message", "Auto-reparación completada."),
                    }
                )
                return

            if task.operation == "load_catalog":
                self.progress.emit("Detectando hardware del sistema...")
                profile = get_hardware_profile()
                self.progress.emit(
                    f"Hardware: RAM={profile['ram_gb']:.1f}GB  "
                    f"VRAM={profile['vram_gb']:.1f}GB  "
                    f"Nivel={profile['tier']}"
                )
                self.progress.emit("Calculando recomendaciones para tu equipo...")
                recommendations = recommend_models(profile)
                local_ollama = list_ollama_models()
                self.success.emit(
                    {
                        "operation": task.operation,
                        "profile": profile,
                        "recommendations": recommendations,
                        "local_ollama": local_ollama,
                    }
                )
                return

            if task.operation == "load_abliterate":
                if task.settings is None:
                    raise BackendError("No se recibieron parámetros de generación.")

                self.progress.emit(f"Cargando modelo: {task.model_name}...")
                self.backend = create_backend(task.model_name, task.preferred_backend)
                self.progress.emit(f"Backend activo: {self.backend.backend_name}")
                if self.backend.supports_abliteration:
                    self.progress.emit("Aplicando abliteración...")
                else:
                    self.progress.emit(
                        "Nota: este backend no aplica abliteración real; se usa para pruebas de generación local."
                    )

                output = self.backend.load_and_abliterate(
                    task.model_name,
                    task.prompt,
                    task.settings,
                )
                self.loaded_model_name = task.model_name
                self.success.emit(
                    {
                        "operation": task.operation,
                        "model_name": task.model_name,
                        "output": output,
                        "backend": self.backend.backend_name,
                    }
                )
                return

            if task.operation == "generate":
                if self.backend is None:
                    raise BackendError("No hay un modelo cargado y abliterado todavía.")

                if task.settings is None:
                    raise BackendError("No se recibieron parámetros de generación.")

                self.progress.emit(f"Generando con modelo: {self.loaded_model_name}...")
                output = self.backend.generate(task.prompt, task.settings)
                self.success.emit(
                    {
                        "operation": task.operation,
                        "model_name": self.loaded_model_name,
                        "output": output,
                        "backend": self.backend.backend_name,
                    }
                )
                return

            raise BackendError(f"Operación no soportada: {task.operation}")

        except Exception as exc:
            self.error.emit(str(exc))

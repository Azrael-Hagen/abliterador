from __future__ import annotations


def _norm(text: str) -> str:
    return (text or "").strip().lower()


def build_assistant_reply(question: str, context: dict) -> str:
    """Respuestas heurísticas para guiar el uso de la app según hardware/estado."""
    q = _norm(question)

    ram = float(context.get("ram_gb", 0.0))
    vram = float(context.get("vram_gb", 0.0))
    tier = context.get("tier", "desconocido")
    backend = context.get("backend_mode", "auto")
    selected_model = context.get("selected_model", "")
    model_ready = bool(context.get("model_ready", False))
    top_recommended = context.get("top_recommended", [])

    if not q:
        if top_recommended:
            return (
                "Te recomiendo empezar por: "
                + ", ".join(top_recommended[:3])
                + ". Luego pulsa 'Descargar seleccionado' y después 'Cargar y Abliterar'."
            )
        return "Empieza cargando el catálogo para que pueda recomendarte modelos según tu hardware."

    if any(k in q for k in ["mejor modelo", "recomend", "cuál uso", "que modelo", "qué modelo"]):
        if top_recommended:
            return (
                f"Según tu hardware (RAM {ram:.0f}GB, VRAM {vram:.0f}GB, perfil {tier}), "
                f"mis mejores opciones son: {', '.join(top_recommended[:3])}."
            )
        return "Carga el catálogo para generar recomendaciones inteligentes para tu equipo."

    if any(k in q for k in ["descarg", "download", "bajar"]):
        return (
            "Para descargar: ve a la pestaña 'Catalogo abliterado', filtra/busca, "
            "selecciona un modelo y pulsa 'Descargar seleccionado'. "
            "Verás progreso en 'Salida y Estado'."
        )

    if any(k in q for k in ["backend", "heretic", "ollama", "fallback"]):
        if ":" in selected_model and backend == "heretic":
            return (
                "Detecto que elegiste Heretic con un modelo tipo Ollama (nombre:tag). "
                "Te conviene cambiar backend a Ollama para evitar errores de compatibilidad."
            )
        return (
            "Regla rápida: Ollama para modelos nombre:tag, Heretic para repos owner/model en HF, "
            "Auto cuando no quieras decidir manualmente."
        )

    if any(k in q for k in ["siguiente", "qué hago", "paso", "ayuda"]):
        if not selected_model:
            return "Paso siguiente: selecciona un modelo en la lista o en el catálogo."
        if not model_ready:
            return "Paso siguiente: pulsa 'Cargar y Abliterar modelo seleccionado'."
        return "Paso siguiente: ajusta parámetros y pulsa 'Generar'."

    if any(k in q for k in ["riesgo", "seguridad", "peligro"]):
        return (
            "La abliteración puede reducir rechazos del modelo y aumentar respuestas inseguras o inestables. "
            "Úsala solo en entorno local de pruebas y evita datos sensibles."
        )

    return (
        "Puedo ayudarte con: recomendación de modelo, backend correcto, descarga, pasos siguientes y riesgos. "
        "Ejemplo: 'que modelo me recomiendas para mi pc'."
    )


def suggest_next_action(context: dict) -> dict:
    """Return an actionable next-step recommendation for the current app state."""
    selected_model = (context.get("selected_model") or "").strip()
    model_ready = bool(context.get("model_ready", False))
    prompt_present = bool((context.get("prompt") or "").strip())
    top_recommended = context.get("top_recommended", [])
    incomplete_hf_models = context.get("incomplete_hf_models", [])

    if incomplete_hf_models:
        model_name = incomplete_hf_models[0]
        return {
            "action": "repair_incomplete_download",
            "message": f"Recuperar descarga incompleta de: {model_name}",
            "model_name": model_name,
        }

    if not selected_model and top_recommended:
        return {
            "action": "select_recommended_model",
            "message": f"Seleccionar mejor recomendado: {top_recommended[0]}",
            "model_name": top_recommended[0],
        }

    if selected_model and not model_ready:
        return {
            "action": "load_selected_model",
            "message": f"Cargar y abliterar modelo seleccionado: {selected_model}",
            "model_name": selected_model,
        }

    if model_ready:
        if prompt_present:
            return {
                "action": "generate_now",
                "message": "Generar respuesta con el modelo cargado.",
            }
        return {
            "action": "set_default_prompt",
            "message": "Cargar prompt sugerido y generar.",
        }

    return {
        "action": "load_catalog",
        "message": "Actualizar catálogo y contexto para continuar.",
    }


def classify_runtime_error(error_message: str) -> dict:
    """Classify backend/runtime errors and suggest auto-recovery action."""
    raw = (error_message or "").strip()
    low = raw.lower()

    if any(x in low for x in ["permissionerror", "cache directory permissions", "lock needs manual removal", "winerror 5"]):
        return {
            "category": "hf_permissions_lock",
            "target": "huggingface",
            "assistant_message": "Detecté un bloqueo de caché/permisos en Hugging Face. Haré limpieza y auto-reparación.",
            "visible_state": "auto-reparando cache hf",
            "retry": True,
        }

    if any(x in low for x in ["read timed out", "connection", "temporary failure", "network", "name resolution"]):
        return {
            "category": "network",
            "target": "download",
            "assistant_message": "Detecté un problema de red. Reintentaré descarga de forma segura.",
            "visible_state": "reintentando descarga",
            "retry": True,
        }

    if any(x in low for x in ["no space left", "not enough space", "espacio", "disk full"]):
        return {
            "category": "disk",
            "target": "storage",
            "assistant_message": "Detecté falta de espacio en disco. Haré limpieza de temporales y te avisaré.",
            "visible_state": "revisando almacenamiento",
            "retry": False,
        }

    if any(x in low for x in ["out of memory", "cuda out of memory", "memoryerror", "cublas"]):
        return {
            "category": "memory",
            "target": "memory",
            "assistant_message": "Detecté un error de memoria. Ajustaré parámetros para reducir consumo y reintentar.",
            "visible_state": "ajustando parametros por memoria",
            "retry": True,
        }

    if "huggingface-cli no encontrado" in low or "huggingface_hub" in low:
        return {
            "category": "hf_dependency",
            "target": "huggingface",
            "assistant_message": "Detecté dependencia faltante de Hugging Face. Intento auto-reparación.",
            "visible_state": "auto-reparando hf",
            "retry": True,
        }

    if "ollama no está instalado" in low or "ollama no esta" in low:
        return {
            "category": "ollama_missing",
            "target": "ollama",
            "assistant_message": "Detecté que Ollama no está disponible. Cambiaré backend para continuar.",
            "visible_state": "cambiando backend",
            "retry": False,
        }

    if "backend heretic" in low or "heretic" in low:
        return {
            "category": "heretic",
            "target": "heretic",
            "assistant_message": "Detecté error de Heretic. Intento auto-reparación y reintento.",
            "visible_state": "auto-reparando heretic",
            "retry": True,
        }

    if any(x in low for x in ["not a valid model identifier", "can't load", "tokenizer_config", "config.json"]):
        return {
            "category": "model_incomplete",
            "target": "download",
            "assistant_message": "El modelo parece incompleto/corrupto. Reintentaré descarga para recuperarlo.",
            "visible_state": "recuperando modelo",
            "retry": True,
        }

    return {
        "category": "unknown",
        "target": "general",
        "assistant_message": "Detecté un error no clasificado. Intentaré auto-reparación general.",
        "visible_state": "auto-reparando",
        "retry": False,
    }


def humanize_runtime_error(error_message: str) -> dict:
    diagnosis = classify_runtime_error(error_message)
    category = diagnosis.get("category", "unknown")

    if category == "hf_permissions_lock":
        return {
            "title": "Problema de permisos o bloqueo en cache",
            "summary": "No se pudo acceder a la cache de Hugging Face. El sistema intentará limpiar locks y recuperar.",
            "hint": "Si persiste, ejecuta la app como administrador o revisa permisos de la carpeta .hf_cache.",
        }

    if category == "network":
        return {
            "title": "Problema de red",
            "summary": "La descarga o consulta al repositorio no respondió correctamente.",
            "hint": "Revisa conexión, VPN/proxy y vuelve a intentar.",
        }

    if category == "disk":
        return {
            "title": "Espacio en disco insuficiente",
            "summary": "No hay suficiente espacio para completar la descarga o cache del modelo.",
            "hint": "Libera espacio y vuelve a intentar; los modelos grandes pueden requerir varios GB.",
        }

    if category == "memory":
        return {
            "title": "Memoria insuficiente",
            "summary": "El modelo o generación superó la memoria disponible del sistema.",
            "hint": "Reduce max tokens o usa un modelo más pequeño.",
        }

    if category == "heretic":
        return {
            "title": "Error de backend Heretic",
            "summary": "El backend Heretic no pudo inicializar o completar la operación.",
            "hint": "La app intentará auto-reparación; si falla, revisa dependencias heretic/torch.",
        }

    if category == "model_incomplete":
        return {
            "title": "Modelo incompleto",
            "summary": "El modelo parece descargado parcialmente o con archivos faltantes.",
            "hint": "Se recomienda relanzar la descarga para recuperar archivos faltantes.",
        }

    return {
        "title": "Error de ejecución",
        "summary": "Ocurrió un error no clasificado durante la operación.",
        "hint": "Consulta el log para más detalles técnicos y vuelve a intentar.",
    }

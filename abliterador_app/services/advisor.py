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

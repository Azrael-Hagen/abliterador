# Abliterador Basico

Aplicacion GUI en PySide6 para buscar modelos, cargarlos localmente, aplicar abliteración y probar generacion de texto.

## Objetivo
Permitir experimentacion local con modelos usando una interfaz simple y segura, priorizando responsividad de GUI y validaciones claras.

## Dependencias
- Python 3.10+
- PySide6
- transformers
- heretic-llm (paquete que expone el módulo heretic moderno)

Instalacion sugerida:

pip install PySide6 transformers heretic-llm

Nota importante sobre Heretic:
- La app usa backend heretic moderno como primera opción para abliteración real.
- Si ese backend falla, intenta compatibilidad legacy con heretic_llm.
- Como último recurso usa fallback de transformers para mantener operatividad (sin abliteración real).

## Arquitectura modular
- abliterador_studio.py: entrypoint principal de ejecución.
- abliterador_basico.py: compatibilidad temporal con nombre legacy.
- abliterador_app/domain/models.py: contratos de datos (GenerationSettings, WorkerTask).
- abliterador_app/services/backends.py: integración de backends y abliteración real.
- abliterador_app/services/worker.py: ejecución en segundo plano con señales Qt.
- abliterador_app/ui/main_window.py: lógica de interfaz y validaciones.

## Ejecutar
python abliterador_studio.py

## Launcher (Windows)
- Doble clic en launch_abliterador_studio.bat
- O desde terminal: launch_abliterador_studio.bat

## Uso con Ollama (pruebas locales)
- Si tienes modelos en Ollama (ejemplo: qwen2.5:0.5b), puedes escribir ese nombre en la búsqueda y seleccionarlo.
- El sistema detecta el modelo local y activa backend `ollama` automáticamente.
- En backend `ollama` se prueba generación local rápida, pero no se aplica abliteración Heretic real.
- Para abliteración real, usa un modelo que pase por backend `heretic_modern`.

## Flujos E2E a validar
1. Busqueda de modelo: valida entrada vacia y muestra resultados simulados.
2. Carga + abliteracion: selecciona modelo, ejecuta flujo heretic en segundo plano y reporta estado.
3. Generacion: usa prompt configurable y parametros de generacion sin recargar el modelo.
4. Manejo de error: verifica QMessageBox en fallos de carga o generacion.

## Funcionalidades GUI implementadas
- Busqueda y lista de modelos simulada.
- Detección automática de modelos locales (Ollama) al abrir la app.
- Carga y abliteracion de modelo con worker thread (QThread).
- Prompt editable.
- Controles de generacion: max tokens, temperatura, top-p, sampling.
- Boton de generacion reutilizando el modelo ya cargado.
- Panel de salida con mensajes de progreso y resultados.
- Selector de backend manual: Auto, Heretic Real, Ollama, Fallback.
- Boton de recarga de modelos Ollama e integración visual con estado.
- Tema visual moderno con tarjetas, colores profesionales e iconos nativos Qt.
- Búsqueda de modelos descargables (Ollama + Hugging Face) y descarga directa para modelos de Ollama.

## Referencias de investigacion
- Qt threading (QThread worker-object pattern): https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html
- Transformers generation strategies: https://huggingface.co/docs/transformers/main/en/generation_strategies
- Transformers GPU inference optimizations: https://huggingface.co/docs/transformers/main/en/perf_infer_gpu_one
- OWASP input validation: https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html

## Stack Decision Log
| Concern | Chosen | Rejected | Reason |
|---|---|---|---|
| GUI | PySide6 Widgets | Web stack | Ya existe base funcional y dependencias instaladas |
| Model runtime | transformers + heretic_llm | Cambio de backend | Mantener continuidad con flujo validado |
| Concurrency | QThread worker-object | Operaciones en hilo UI | Evitar congelamiento al cargar/ejecutar modelos |
| Validation | Allowlist + rangos | Validacion minima | Evitar errores y parametros inseguros |
| Testing | Manual E2E inicial | Sin validacion | Proyecto sin suite previa, se define checklist claro |

## Risk Register
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Congelamiento UI por carga de modelo | Alta | Alta | Worker thread para operaciones pesadas |
| Consumo excesivo de RAM/VRAM | Alta | Alta | Limites de parametros y mensajes de estado |
| Error por modelo remoto no disponible | Media | Media | Manejo de excepciones y feedback en GUI |
| Prompt mal formado o vacio | Media | Media | Validaciones de longitud y contenido |
| Dependencias no instaladas | Media | Alta | Mensajes de error claros y README con setup |

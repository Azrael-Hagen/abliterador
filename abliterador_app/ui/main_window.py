from datetime import datetime
from html import escape
import os
from pathlib import Path
import re
import subprocess

from PySide6.QtCore import QThread, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont, QGuiApplication, QIcon, QPixmap, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QStyle,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from abliterador_app.domain.models import GenerationSettings, WorkerTask
from abliterador_app.services.advisor import (
    build_assistant_reply,
    classify_runtime_error,
    humanize_runtime_error,
    suggest_next_action,
)
from abliterador_app.services.backends import (
    BACKEND_MODE_AUTO,
    BACKEND_MODE_FALLBACK,
    BACKEND_MODE_HERETIC,
    BACKEND_MODE_OLLAMA,
    create_backend,
    list_ollama_models,
)
from abliterador_app.services.catalog import SOURCE_HUGGINGFACE, SOURCE_OLLAMA
from abliterador_app.services.logger import get_log_path, get_logger
from abliterador_app.services.runtime_engine import RuntimeEngine
from abliterador_app.services.worker import ModelTaskWorker

MODEL_NAME_ALLOWLIST = re.compile(r"^[a-zA-Z0-9._\-\/:]{3,128}$")


class ModelSearcher(QWidget):
    task_requested = Signal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Abliterador Studio")
        self.setMinimumSize(980, 680)
        self._logo_path = self._resolve_logo_path()
        if self._logo_path is not None:
            self.setWindowIcon(QIcon(str(self._logo_path)))

        self.model_ready = False
        self.current_model_name = ""
        self._ollama_models = []
        self._catalog_recommendations = []
        self._catalog_card_buttons = []
        self._hardware_profile = {}
        self._local_ollama_models: list = []
        self._incomplete_hf_models: list[str] = []
        self._assistant_autopilot_enabled = True
        self._pending_generate_after_load = False
        self._last_failed_operation = ""
        self._last_failed_model = ""
        self._prefer_real_abliteration = True
        self._recovery_attempts: dict[str, int] = {}
        self._max_recovery_attempts = 2
        self._extensions_heretic_ok = "?"
        self._extensions_auto_name = "pendiente"
        self._boot_engine = RuntimeEngine()
        self._boot_step_index = -1
        self._boot_completed_weight = 0
        self._boot_waiting_operation = ""
        self._boot_started = False
        self._log_path = get_log_path()
        self._logger = get_logger()

        self.worker_thread = QThread(self)
        self.worker = ModelTaskWorker()
        self.worker.moveToThread(self.worker_thread)
        self.task_requested.connect(self.worker.run_task)
        self.worker.progress.connect(self._append_output)
        self.worker.success.connect(self._on_task_success)
        self.worker.error.connect(self._on_task_error)
        self.worker_thread.start()

        self._apply_theme()

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(20, 16, 20, 16)
        root_layout.setSpacing(10)

        header_row = QHBoxLayout()
        if self._logo_path is not None:
            logo_label = QLabel()
            logo_pixmap = QPixmap(str(self._logo_path))
            logo_label.setPixmap(logo_pixmap.scaled(76, 76, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            logo_label.setObjectName("headerLogo")
            header_row.addWidget(logo_label)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title = QLabel("Abliterador Studio")
        title.setObjectName("titleLabel")
        subtitle = QLabel("Interfaz guiada para descargar, abliterar y probar modelos con asistencia inteligente")
        subtitle.setObjectName("subtitleLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header_row.addLayout(title_box, 1)
        root_layout.addLayout(header_row)

        self.steps_bar = QLabel("Paso 1 Modelo  |  Paso 2 Cargar/Abliterar  |  Paso 3 Generar")
        self.steps_bar.setObjectName("stepsLabel")
        root_layout.addWidget(self.steps_bar)

        self._build_startup_panel(root_layout)

        self.main_tabs = QTabWidget()
        self.main_tabs.setDocumentMode(True)
        root_layout.addWidget(self.main_tabs, 1)

        self._build_workflow_tab()
        self._build_catalog_tab()
        self._build_model_chat_tab()
        self._build_assistant_tab()
        self._build_output_tab()

        footer = QHBoxLayout()
        self.extensions_label = QLabel("Extensiones: cargando...")
        self.extensions_label.setObjectName("extensionsLabel")
        footer.addWidget(self.extensions_label, 1)

        self.status_label = QLabel("Listo")
        self.status_label.setObjectName("statusLabel")
        footer.addWidget(self.status_label)
        root_layout.addLayout(footer)

        self.setLayout(root_layout)
        self._fit_and_center_window()

        self.refresh_extensions_status()
        self._assistant_set_recovery_state("monitoreo activo", "Esperando eventos")
        self._assistant_append("Asistente listo. Puedo recomendarte modelos y siguiente paso.")
        QTimer.singleShot(0, self._start_boot_sequence)

    def _fit_and_center_window(self):
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(1220, 880)
            return

        geo = screen.availableGeometry()
        target_w = max(self.minimumWidth(), min(1320, int(geo.width() * 0.94)))
        target_h = max(self.minimumHeight(), min(940, int(geo.height() * 0.90)))
        self.resize(target_w, target_h)

        center_x = geo.x() + (geo.width() - target_w) // 2
        center_y = geo.y() + (geo.height() - target_h) // 2
        self.move(center_x, center_y)

    def showEvent(self, event):
        super().showEvent(event)
        self._fit_and_center_window()

    def _build_startup_panel(self, root_layout: QVBoxLayout):
        self.startup_panel = QFrame()
        self.startup_panel.setObjectName("outputHero")
        startup_layout = QVBoxLayout(self.startup_panel)
        startup_layout.setContentsMargins(14, 10, 14, 10)
        startup_layout.setSpacing(6)

        self.startup_title = QLabel("Inicializando motor interno...")
        self.startup_title.setObjectName("outputHeroTitle")
        startup_layout.addWidget(self.startup_title)

        self.startup_detail = QLabel("Preparando módulos y diagnóstico del entorno")
        self.startup_detail.setObjectName("outputHeroSubtitle")
        self.startup_detail.setWordWrap(True)
        startup_layout.addWidget(self.startup_detail)

        self.startup_progress = QProgressBar()
        self.startup_progress.setRange(0, 100)
        self.startup_progress.setValue(0)
        startup_layout.addWidget(self.startup_progress)

        root_layout.addWidget(self.startup_panel)

    def _start_boot_sequence(self):
        if self._boot_started:
            return
        self._boot_started = True
        self._set_busy(True)
        self._append_output("▶ Inicio: secuencia de arranque modular")
        self._run_next_boot_step()

    def _run_next_boot_step(self):
        self._boot_step_index += 1
        steps = self._boot_engine.steps

        if self._boot_step_index >= len(steps):
            self._finish_boot_sequence()
            return

        step = steps[self._boot_step_index]
        self.startup_title.setText(step.title)
        self.startup_detail.setText(step.detail)
        self._append_output(f"Proceso de inicio: {step.title}")

        if step.operation:
            self._boot_waiting_operation = step.operation
            self.task_requested.emit(WorkerTask(operation=step.operation))
            return

        self._boot_completed_weight += step.weight
        self._update_boot_progress()
        QTimer.singleShot(20, self._run_next_boot_step)

    def _update_boot_progress(self):
        total = max(1, self._boot_engine.total_weight)
        pct = int((self._boot_completed_weight / total) * 100)
        self.startup_progress.setValue(max(0, min(100, pct)))

    def _mark_boot_operation_completed(self, operation: str):
        if operation != self._boot_waiting_operation:
            return

        step = self._boot_engine.steps[self._boot_step_index]
        self._boot_completed_weight += step.weight
        self._boot_waiting_operation = ""
        self._update_boot_progress()
        QTimer.singleShot(20, self._run_next_boot_step)

    def _finish_boot_sequence(self):
        self.startup_title.setText("Arranque completado")
        self.startup_detail.setText("La interfaz está lista para trabajar.")
        self.startup_progress.setValue(100)
        self._append_output("✅ Motor interno listo")
        self._set_busy(False)
        QTimer.singleShot(500, lambda: self.startup_panel.setVisible(False))

    def _build_workflow_tab(self):
        self.tab_workflow = QWidget()
        layout = QVBoxLayout(self.tab_workflow)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        backend_box = QGroupBox("Configuracion")
        backend_layout = QHBoxLayout(backend_box)
        backend_layout.addWidget(QLabel("Modo de ejecucion:"))

        self.backend_selector = QComboBox()
        self.backend_selector.addItem("Auto", BACKEND_MODE_AUTO)
        self.backend_selector.addItem("Heretic Real", BACKEND_MODE_HERETIC)
        self.backend_selector.addItem("Ollama", BACKEND_MODE_OLLAMA)
        self.backend_selector.addItem("Fallback", BACKEND_MODE_FALLBACK)
        backend_layout.addWidget(self.backend_selector)

        self.prefer_real_abliteration_chk = QCheckBox("Preferir abliteracion real")
        self.prefer_real_abliteration_chk.setChecked(True)
        backend_layout.addWidget(self.prefer_real_abliteration_chk)

        self.reload_ollama_button = QPushButton("Actualizar modelos locales")
        self.reload_ollama_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.reload_ollama_button.clicked.connect(self.load_ollama_models)
        backend_layout.addWidget(self.reload_ollama_button)
        backend_layout.addStretch(1)
        layout.addWidget(backend_box)

        model_box = QGroupBox("Paso 1 Seleccion de modelo")
        model_layout = QVBoxLayout(model_box)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filtrar modelos locales o escribir modelo manual (ej: meta-llama/...)")
        model_layout.addWidget(self.search_input)

        model_row = QHBoxLayout()
        self.search_button = QPushButton("Filtrar")
        self.search_button.clicked.connect(self.search_model)
        model_row.addWidget(self.search_button)

        self.search_downloadable_button = QPushButton("Buscar descargables en Ollama")
        self.search_downloadable_button.clicked.connect(self.search_downloadable)
        model_row.addWidget(self.search_downloadable_button)

        self.download_button = QPushButton("Descargar seleccionado")
        self.download_button.clicked.connect(self.download_selected_model)
        model_row.addWidget(self.download_button)
        model_layout.addLayout(model_row)

        self.results_list = QListWidget()
        self.results_list.setAlternatingRowColors(True)
        model_layout.addWidget(self.results_list)

        layout.addWidget(model_box)

        generation_box = QGroupBox("Paso 2 y 3 Abliterar y generar")
        generation_layout = QVBoxLayout(generation_box)

        self.prompt_input = QTextEdit()
        self.prompt_input.setMaximumHeight(140)
        self.prompt_input.setPlaceholderText("Escribe el prompt para probar el modelo")
        self.prompt_input.setPlainText(self.default_prompt_v1())
        generation_layout.addWidget(self.prompt_input)

        params = QHBoxLayout()
        params.addWidget(QLabel("Max tokens"))
        self.max_tokens_input = QSpinBox()
        self.max_tokens_input.setRange(10, 4096)
        self.max_tokens_input.setValue(128)
        params.addWidget(self.max_tokens_input)

        params.addWidget(QLabel("Temperatura"))
        self.temperature_input = QDoubleSpinBox()
        self.temperature_input.setRange(0.0, 2.0)
        self.temperature_input.setSingleStep(0.1)
        self.temperature_input.setValue(0.7)
        params.addWidget(self.temperature_input)

        params.addWidget(QLabel("Top-p"))
        self.top_p_input = QDoubleSpinBox()
        self.top_p_input.setRange(0.1, 1.0)
        self.top_p_input.setSingleStep(0.05)
        self.top_p_input.setValue(0.9)
        params.addWidget(self.top_p_input)

        self.do_sample_input = QCheckBox("Sampling")
        self.do_sample_input.setChecked(True)
        params.addWidget(self.do_sample_input)
        params.addStretch(1)
        generation_layout.addLayout(params)

        action_row = QHBoxLayout()
        self.heretic_button = QPushButton("Paso 2 Cargar y abliterar")
        self.heretic_button.clicked.connect(self.apply_heretic)
        action_row.addWidget(self.heretic_button)

        self.generate_button = QPushButton("Paso 3 Generar")
        self.generate_button.clicked.connect(self.generate_text)
        action_row.addWidget(self.generate_button)

        self.clear_button = QPushButton("Limpiar salida")
        self.clear_button.clicked.connect(self.output_area_clear)
        action_row.addWidget(self.clear_button)

        self.smart_action_button = QPushButton("Siguiente accion inteligente")
        self.smart_action_button.clicked.connect(self.run_smart_next_action)
        action_row.addWidget(self.smart_action_button)
        action_row.addStretch(1)
        generation_layout.addLayout(action_row)

        layout.addWidget(generation_box)
        layout.addStretch(1)

        self.main_tabs.addTab(self.tab_workflow, "Flujo")

    def _build_catalog_tab(self):
        self.tab_catalog = QWidget()
        layout = QVBoxLayout(self.tab_catalog)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._hw_label = QLabel("Analizando hardware...")
        self._hw_label.setObjectName("hwLabel")
        self._hw_label.setWordWrap(True)
        layout.addWidget(self._hw_label)

        filters = QHBoxLayout()
        self._catalog_search_input = QLineEdit()
        self._catalog_search_input.setPlaceholderText("Buscar en catalogo (nombre, tags, fuente)")
        self._catalog_search_input.textChanged.connect(self._refresh_catalog_view)
        filters.addWidget(self._catalog_search_input)

        self._catalog_source_filter = QComboBox()
        self._catalog_source_filter.addItem("Todas", "all")
        self._catalog_source_filter.addItem("Ollama", SOURCE_OLLAMA)
        self._catalog_source_filter.addItem("Hugging Face", SOURCE_HUGGINGFACE)
        self._catalog_source_filter.currentIndexChanged.connect(self._refresh_catalog_view)
        filters.addWidget(self._catalog_source_filter)

        self._catalog_quality_filter = QComboBox()
        self._catalog_quality_filter.addItem("Todos", "all")
        self._catalog_quality_filter.addItem("Recomendados", "recommended")
        self._catalog_quality_filter.addItem("Recomendados + Compatibles", "compatible")
        self._catalog_quality_filter.currentIndexChanged.connect(self._refresh_catalog_view)
        filters.addWidget(self._catalog_quality_filter)
        layout.addLayout(filters)

        self._catalog_list = QListWidget()
        self._catalog_list.setAlternatingRowColors(False)
        self._catalog_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._catalog_list.setSpacing(8)
        layout.addWidget(self._catalog_list, 1)

        self._catalog_count_label = QLabel("0 modelos")
        self._catalog_count_label.setObjectName("catalogCountLabel")
        layout.addWidget(self._catalog_count_label)

        actions = QHBoxLayout()
        self._catalog_reload_btn = QPushButton("Actualizar recomendaciones")
        self._catalog_reload_btn.clicked.connect(self.load_catalog)
        actions.addWidget(self._catalog_reload_btn)

        self._catalog_best_btn = QPushButton("Usar mejor sugerido")
        self._catalog_best_btn.clicked.connect(self._catalog_use_best_recommended)
        actions.addWidget(self._catalog_best_btn)

        self._catalog_dl_btn = QPushButton("Descargar seleccionado")
        self._catalog_dl_btn.clicked.connect(self._catalog_download)
        actions.addWidget(self._catalog_dl_btn)

        self._catalog_use_btn = QPushButton("Usar seleccionado")
        self._catalog_use_btn.clicked.connect(self._catalog_use_and_abliterate)
        actions.addWidget(self._catalog_use_btn)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.main_tabs.addTab(self.tab_catalog, "Catalogo")

    def _build_model_chat_tab(self):
        self.tab_model_chat = QWidget()
        layout = QVBoxLayout(self.tab_model_chat)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        chat_context_box = QGroupBox("Contexto del chat")
        chat_context_layout = QHBoxLayout(chat_context_box)
        self.chat_model_chip = QLabel("Modelo activo: sin cargar")
        self.chat_model_chip.setObjectName("outputMetaChip")
        chat_context_layout.addWidget(self.chat_model_chip)

        self.chat_backend_chip = QLabel("Backend: auto")
        self.chat_backend_chip.setObjectName("outputMetaChip")
        chat_context_layout.addWidget(self.chat_backend_chip)
        chat_context_layout.addStretch(1)
        layout.addWidget(chat_context_box)

        model_chat_box = QGroupBox("Conversación con modelo")
        model_chat_layout = QVBoxLayout(model_chat_box)

        model_chat_actions = QHBoxLayout()
        self.model_chat_clear_button = QPushButton("Limpiar chat modelo")
        self.model_chat_clear_button.clicked.connect(self._clear_model_chat)
        model_chat_actions.addWidget(self.model_chat_clear_button)

        self.model_chat_copy_button = QPushButton("Copiar chat modelo")
        self.model_chat_copy_button.clicked.connect(self._copy_model_chat)
        model_chat_actions.addWidget(self.model_chat_copy_button)
        model_chat_actions.addStretch(1)
        model_chat_layout.addLayout(model_chat_actions)

        self.model_chat_output = QTextEdit()
        self.model_chat_output.setReadOnly(True)
        self.model_chat_output.setObjectName("modelChatOutput")
        self.model_chat_output.setPlaceholderText("Aquí aparecerán exclusivamente tus mensajes y respuestas del modelo.")
        model_chat_layout.addWidget(self.model_chat_output)

        model_chat_input_row = QHBoxLayout()
        self.model_chat_input = QLineEdit()
        self.model_chat_input.setPlaceholderText("Escribe un mensaje al modelo y presiona Enter...")
        self.model_chat_input.returnPressed.connect(self._model_chat_send)
        model_chat_input_row.addWidget(self.model_chat_input)

        self.model_chat_send_button = QPushButton("Enviar al modelo")
        self.model_chat_send_button.clicked.connect(self._model_chat_send)
        model_chat_input_row.addWidget(self.model_chat_send_button)
        model_chat_layout.addLayout(model_chat_input_row)

        layout.addWidget(model_chat_box, 1)
        self.main_tabs.addTab(self.tab_model_chat, "Chat Modelo")

    def _build_assistant_tab(self):
        self.tab_assistant = QWidget()
        layout = QVBoxLayout(self.tab_assistant)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        risk_box = QGroupBox("Que es la abliteracion y riesgos")
        risk_layout = QVBoxLayout(risk_box)
        self.abliteration_info_label = QLabel(
            "La abliteracion reduce patrones de rechazo del modelo para pruebas.\n"
            "Riesgos: respuestas mas inseguras, perdida de alineacion, errores e inestabilidad.\n"
            "Usar solo en entorno local y nunca con datos sensibles o en produccion."
        )
        self.abliteration_info_label.setWordWrap(True)
        self.abliteration_info_label.setObjectName("abliterationInfoLabel")
        risk_layout.addWidget(self.abliteration_info_label)
        layout.addWidget(risk_box)

        assistant_box = QGroupBox("Micro IA de ayuda")
        assistant_layout = QVBoxLayout(assistant_box)

        ops_row = QHBoxLayout()
        self.assistant_autopilot = QCheckBox("Autopiloto de asistente")
        self.assistant_autopilot.setChecked(True)
        self.assistant_autopilot.toggled.connect(self._toggle_assistant_autopilot)
        ops_row.addWidget(self.assistant_autopilot)

        self.assistant_repair_button = QPushButton("Auto-reparar entorno")
        self.assistant_repair_button.clicked.connect(self._assistant_auto_repair_now)
        ops_row.addWidget(self.assistant_repair_button)
        ops_row.addStretch(1)
        assistant_layout.addLayout(ops_row)

        status_row = QHBoxLayout()
        self.assistant_state_chip = QLabel("Micro IA: monitoreo activo")
        self.assistant_state_chip.setObjectName("outputMetaChip")
        status_row.addWidget(self.assistant_state_chip)

        self.assistant_action_chip = QLabel("Ultima accion: esperando")
        self.assistant_action_chip.setObjectName("outputMetaChip")
        status_row.addWidget(self.assistant_action_chip)
        status_row.addStretch(1)
        assistant_layout.addLayout(status_row)

        self.assistant_output = QTextEdit()
        self.assistant_output.setReadOnly(True)
        self.assistant_output.setObjectName("assistantOutput")
        self.assistant_output.setPlaceholderText("El asistente dejará aquí recomendaciones, alertas y siguientes pasos.")
        assistant_layout.addWidget(self.assistant_output)

        ask_row = QHBoxLayout()
        self.assistant_input = QLineEdit()
        self.assistant_input.setPlaceholderText("Pregunta: que modelo me conviene, que backend uso, siguiente paso...")
        self.assistant_input.returnPressed.connect(self._assistant_ask)
        ask_row.addWidget(self.assistant_input)

        self.assistant_send_button = QPushButton("Preguntar")
        self.assistant_send_button.clicked.connect(self._assistant_ask)
        ask_row.addWidget(self.assistant_send_button)
        assistant_layout.addLayout(ask_row)

        quick_row = QHBoxLayout()
        self.assistant_recommend_button = QPushButton("Recomiendame modelo")
        self.assistant_recommend_button.clicked.connect(self._assistant_quick_recommend)
        quick_row.addWidget(self.assistant_recommend_button)

        self.assistant_next_button = QPushButton("Dime siguiente paso")
        self.assistant_next_button.clicked.connect(self._assistant_quick_next)
        quick_row.addWidget(self.assistant_next_button)
        quick_row.addStretch(1)
        assistant_layout.addLayout(quick_row)

        layout.addWidget(assistant_box, 1)
        self.main_tabs.addTab(self.tab_assistant, "Asistente")

    def _build_output_tab(self):
        self.tab_output = QWidget()
        layout = QVBoxLayout(self.tab_output)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        hero = QFrame()
        hero.setObjectName("outputHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(14, 12, 14, 12)
        hero_layout.setSpacing(8)

        hero_title = QLabel("Consola de sesion")
        hero_title.setObjectName("outputHeroTitle")
        hero_layout.addWidget(hero_title)

        hero_subtitle = QLabel("Actividad técnica del flujo: progreso, diagnósticos, errores y eventos del backend. El chat vive en la pestaña Chat Modelo.")
        hero_subtitle.setObjectName("outputHeroSubtitle")
        hero_subtitle.setWordWrap(True)
        hero_layout.addWidget(hero_subtitle)

        hero_meta = QHBoxLayout()
        self.output_model_chip = QLabel("Modelo: sin seleccionar")
        self.output_model_chip.setObjectName("outputMetaChip")
        hero_meta.addWidget(self.output_model_chip)

        self.output_backend_chip = QLabel("Backend: auto")
        self.output_backend_chip.setObjectName("outputMetaChip")
        hero_meta.addWidget(self.output_backend_chip)

        self.output_state_chip = QLabel("Estado: listo")
        self.output_state_chip.setObjectName("outputMetaChipActive")
        hero_meta.addWidget(self.output_state_chip)
        hero_meta.addStretch(1)
        hero_layout.addLayout(hero_meta)
        layout.addWidget(hero)

        box = QGroupBox("Salida y progreso")
        box_layout = QVBoxLayout(box)

        output_actions = QHBoxLayout()
        self.output_copy_button = QPushButton("Copiar salida")
        self.output_copy_button.clicked.connect(self._copy_output_to_clipboard)
        output_actions.addWidget(self.output_copy_button)

        self.output_jump_button = QPushButton("Volver al flujo")
        self.output_jump_button.clicked.connect(lambda: self.main_tabs.setCurrentWidget(self.tab_workflow))
        output_actions.addWidget(self.output_jump_button)

        self.output_open_log_button = QPushButton("Abrir log")
        self.output_open_log_button.clicked.connect(self._open_log_file)
        output_actions.addWidget(self.output_open_log_button)

        self.output_copy_diag_button = QPushButton("Copiar diagnostico")
        self.output_copy_diag_button.clicked.connect(self._copy_diagnostics)
        output_actions.addWidget(self.output_copy_diag_button)
        output_actions.addStretch(1)
        box_layout.addLayout(output_actions)

        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setObjectName("outputFeed")
        self.output_area.setPlaceholderText("La actividad aparecerá aquí en formato de conversación.")
        box_layout.addWidget(self.output_area)
        layout.addWidget(box, 1)

        self.main_tabs.addTab(self.tab_output, "Salida")

    def _apply_theme(self):
        self.setFont(QFont("Segoe UI Semibold", 10))
        self.setStyleSheet(
            """
            QWidget {
                background: #090d14;
                color: #e7edf3;
            }
            QGroupBox {
                border: 1px solid #29384a;
                border-radius: 16px;
                margin-top: 14px;
                background: #101723;
                font-weight: 700;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #f2f6f8;
            }
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QListWidget {
                border: 1px solid #283443;
                border-radius: 12px;
                background: #0b131d;
                color: #e7edf3;
                padding: 8px;
                selection-background-color: #1e5f8f;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #ff8f33;
            }
            QListWidget::item:selected {
                background: #1c2733;
                color: #edf4f8;
                border-radius: 8px;
            }
            QListWidget::item:hover {
                background: #151e27;
            }
            QPushButton {
                background: #ff8a2b;
                color: #1e0f06;
                border: 1px solid #ffae64;
                border-radius: 12px;
                padding: 9px 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #ff9f4e;
            }
            QPushButton:disabled {
                background: #40505f;
                color: #9cadbc;
                border: 1px solid #485866;
            }
            #titleLabel {
                font-size: 30px;
                color: #f7fbff;
                font-weight: 800;
            }
            #headerLogo {
                background: transparent;
                padding-right: 10px;
            }
            #subtitleLabel {
                color: #8bb9d8;
                margin-bottom: 4px;
            }
            #stepsLabel {
                background: #101923;
                border: 1px solid #274059;
                border-radius: 14px;
                padding: 10px 14px;
                color: #dbe9f5;
                font-weight: 700;
            }
            #statusLabel {
                background: #1f2e3d;
                border: 1px solid #2d6998;
                border-radius: 12px;
                padding: 6px 10px;
                color: #c9e7ff;
                font-weight: 700;
            }
            #extensionsLabel {
                background: #111b27;
                border: 1px solid #23435f;
                border-radius: 12px;
                padding: 6px 10px;
                color: #abc8df;
            }
            #hwLabel {
                background: #102027;
                border: 1px solid #23414f;
                border-radius: 14px;
                padding: 10px 12px;
                color: #d7eef7;
                font-weight: 700;
            }
            #catalogCountLabel {
                background: #111821;
                border: 1px solid #24313d;
                border-radius: 12px;
                padding: 6px 10px;
                color: #93aab9;
            }
            #catalogCard {
                border: 1px solid #24313d;
                border-radius: 16px;
                background: #10161d;
            }
            #catalogCardTitle {
                font-weight: 800;
                color: #f3f7fa;
            }
            #catalogCardDesc {
                color: #92a5b7;
            }
            #chip {
                background: #151e27;
                border: 1px solid #2a3947;
                border-radius: 11px;
                padding: 3px 8px;
                color: #afc0ce;
            }
            #chipOk {
                background: #1f2f3f;
                border: 1px solid #2d668f;
                border-radius: 11px;
                padding: 3px 8px;
                color: #c8e8ff;
            }
            #chipWarn {
                background: #2f1f10;
                border: 1px solid #ad6e2e;
                border-radius: 11px;
                padding: 3px 8px;
                color: #ffd7a4;
            }
            #assistantOutput, #outputFeed, #abliterationInfoLabel, #modelChatOutput {
                background: #0b1015;
                border: 1px solid #26313c;
                border-radius: 14px;
                padding: 10px;
            }
            #chipInstalled {
                background: #112b1b;
                border: 1px solid #2c8450;
                border-radius: 11px;
                padding: 3px 8px;
                color: #bcffd1;
                font-weight: 700;
            }
            #outputHero {
                background: #10161d;
                border: 1px solid #24313d;
                border-radius: 18px;
            }
            #outputHeroTitle {
                font-size: 18px;
                font-weight: 800;
                color: #f4f7fa;
            }
            #outputHeroSubtitle {
                color: #90a5b8;
            }
            #outputMetaChip {
                background: #151e27;
                border: 1px solid #293645;
                border-radius: 12px;
                padding: 4px 10px;
                color: #b9c8d5;
            }
            #outputMetaChipActive {
                background: #26384a;
                border: 1px solid #2f6b95;
                border-radius: 12px;
                padding: 4px 10px;
                color: #d1ebff;
                font-weight: 700;
            }
            QTabWidget::pane {
                border: 1px solid #24313d;
                border-radius: 16px;
                background: #10161d;
            }
            QTabBar::tab {
                background: #121922;
                border: 1px solid #24313d;
                border-bottom: none;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                padding: 10px 16px;
                color: #90a2b3;
                font-weight: 700;
            }
            QTabBar::tab:selected {
                background: #182a3d;
                color: #eff4f7;
                border-color: #2f5370;
            }
            QScrollBar:vertical {
                background: #10161d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #314150;
                min-height: 24px;
                border-radius: 6px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            """
        )

    def _resolve_logo_path(self) -> Path | None:
        base_dir = Path(__file__).resolve().parents[2]
        candidate = base_dir / "sources" / "Copilot_20260327_161839.png"
        return candidate if candidate.exists() else None

    def _selected_backend_mode(self):
        return self.backend_selector.currentData()

    def load_ollama_models(self):
        self._ollama_models = list_ollama_models()
        self._local_ollama_models = list(self._ollama_models)
        self._populate_local_models()
        if self._catalog_recommendations:
            self._refresh_catalog_view()
        self.status_label.setText(f"Modelos Ollama detectados: {len(self._ollama_models)}")
        self.refresh_extensions_status()

    def refresh_extensions_status(self):
        self.extensions_label.setText(
            f"Extensiones -> Heretic Real: {self._extensions_heretic_ok} | "
            f"Ollama local: {len(self._ollama_models)} | Auto: {self._extensions_auto_name}"
        )

    def _populate_local_models(self):
        self.results_list.clear()
        candidates = list(self._ollama_models)
        if not candidates:
            candidates = ["qwen2.5:0.5b", "gemma3:4b", "meta-llama/Llama-2-7b-chat-hf"]
        for model_name in candidates:
            self.results_list.addItem(model_name)

    def default_prompt_v1(self):
        return "Escribe un poema breve sobre un angel solitario."

    def output_area_clear(self):
        self.output_area.clear()
        self._update_output_meta(state="listo")

    def _copy_output_to_clipboard(self):
        text = self.output_area.toPlainText().strip()
        if not text:
            self.status_label.setText("No hay salida para copiar.")
            return
        QApplication.clipboard().setText(text)
        self.status_label.setText("Salida copiada al portapapeles.")

    def _open_log_file(self):
        try:
            if os.path.exists(self._log_path):
                if os.name == "nt":
                    os.startfile(self._log_path)
                else:
                    subprocess.Popen(["xdg-open", self._log_path])
                self.status_label.setText("Log abierto en el sistema.")
                return
            self.status_label.setText("Log no encontrado todavía.")
        except Exception as exc:
            self._append_output(f"Error abriendo log: {exc}")

    def _copy_diagnostics(self):
        diag = (
            f"Modelo activo: {self.current_model_name or 'ninguno'}\n"
            f"Backend seleccionado: {self._selected_backend_mode()}\n"
            f"Estado UI: {self.output_state_chip.text()}\n"
            f"Log: {self._log_path}\n"
            f"Modelo listo: {self.model_ready}\n"
            f"Ollama local: {len(self._ollama_models)}"
        )
        QApplication.clipboard().setText(diag)
        self.status_label.setText("Diagnóstico copiado al portapapeles.")

    def _clear_model_chat(self):
        self.model_chat_output.clear()

    def _copy_model_chat(self):
        text = self.model_chat_output.toPlainText().strip()
        if not text:
            self.status_label.setText("No hay chat del modelo para copiar.")
            return
        QApplication.clipboard().setText(text)
        self.status_label.setText("Chat del modelo copiado al portapapeles.")

    def _model_chat_append(self, speaker: str, text: str, tone: str):
        self._append_feed(self.model_chat_output, speaker, text, tone)

    def _update_chat_context_meta(self, model: str | None = None, backend: str | None = None):
        if model is not None:
            shown_model = model if len(model) <= 42 else f"{model[:39]}..."
            self.chat_model_chip.setText(f"Modelo activo: {shown_model}")
        if backend is not None:
            self.chat_backend_chip.setText(f"Backend: {backend}")

    def _model_chat_send(self):
        prompt = self.model_chat_input.text().strip()
        if not prompt:
            return
        self.model_chat_input.clear()
        self.generate_text(prompt_override=prompt)

    def _update_output_meta(self, state: str | None = None, model: str | None = None, backend: str | None = None):
        if model is not None:
            shown_model = model if len(model) <= 42 else f"{model[:39]}..."
            self.output_model_chip.setText(f"Modelo: {shown_model}")
        if backend is not None:
            self.output_backend_chip.setText(f"Backend: {backend}")
        if state is not None:
            self.output_state_chip.setText(f"Estado: {state}")

    def _feed_html(self, speaker: str, text: str, tone: str = "system") -> str:
        palette = {
            "system": {"bg": "#131b22", "border": "#2a3643", "fg": "#dfe8ef", "meta": "#8fa3b5"},
            "progress": {"bg": "#102027", "border": "#274450", "fg": "#dcf2f6", "meta": "#8fb9c2"},
            "success": {"bg": "#122219", "border": "#2d6d49", "fg": "#daf7e5", "meta": "#91c9a8"},
            "error": {"bg": "#2a1417", "border": "#7d3941", "fg": "#ffd8dd", "meta": "#e1a3ac"},
            "action": {"bg": "#1e1828", "border": "#51406f", "fg": "#eee3ff", "meta": "#b1a4d4"},
            "assistant": {"bg": "#111920", "border": "#344555", "fg": "#e9f1f6", "meta": "#95a8ba"},
            "user": {"bg": "#163023", "border": "#367153", "fg": "#dcf7e5", "meta": "#9ed0b2"},
            "model": {"bg": "#17201a", "border": "#4b845d", "fg": "#effbf2", "meta": "#a5d9b4"},
        }
        colors = palette.get(tone, palette["system"])
        align = "right" if tone == "user" else "left"
        body = escape(text).replace("\n", "<br>")
        stamp = datetime.now().strftime("%H:%M")
        return (
            f'<table width="100%" cellspacing="0" cellpadding="0" style="margin: 0 0 10px 0;">'
            f'<tr><td align="{align}">'
            f'<div style="display:inline-block; max-width: 840px; background:{colors["bg"]}; '
            f'border:1px solid {colors["border"]}; border-radius:16px; padding:10px 12px;">'
            f'<div style="font-size:10px; color:{colors["meta"]}; font-weight:700; margin-bottom:4px;">'
            f'{escape(speaker)} · {stamp}</div>'
            f'<div style="color:{colors["fg"]}; line-height:1.45;">{body}</div>'
            f'</div></td></tr></table>'
        )

    def _append_feed(self, editor: QTextEdit, speaker: str, text: str, tone: str = "system"):
        if not text.strip():
            return
        editor.moveCursor(QTextCursor.End)
        editor.insertHtml(self._feed_html(speaker, text, tone))
        editor.moveCursor(QTextCursor.End)
        editor.ensureCursorVisible()

    def _classify_output(self, message: str) -> tuple[str, str, str]:
        raw = message.strip()
        low = raw.lower()
        if low.startswith("error:"):
            return "Error", raw, "error"
        if raw.startswith("▶") or "reintentando" in low:
            return "Accion", raw, "action"
        if raw.startswith("✅") or "listo" in low or "complet" in low or "cargado" in low:
            return "Sistema", raw, "success"
        if "generando" in low or "descargando" in low or "buscando" in low or "aplicando" in low:
            return "Proceso", raw, "progress"
        return "Sistema", raw, "system"

    def _append_output(self, message):
        speaker, raw, tone = self._classify_output(message)
        self._append_feed(self.output_area, speaker, raw, tone)
        self.status_label.setText(raw.splitlines()[0][:120])
        if tone == "error":
            self._logger.error(raw)
        elif tone in {"action", "progress"}:
            self._logger.info(raw)
        else:
            self._logger.info(raw)
        if tone == "error":
            self._update_output_meta(state="error")
        elif tone in {"action", "progress"}:
            self._update_output_meta(state="trabajando")
        elif tone == "success":
            self._update_output_meta(state="listo")

    def _set_busy(self, busy):
        self.search_button.setEnabled(not busy)
        self.search_downloadable_button.setEnabled(not busy)
        self.heretic_button.setEnabled(not busy)
        self.download_button.setEnabled(not busy)
        self.generate_button.setEnabled(not busy)
        self.reload_ollama_button.setEnabled(not busy)
        self._catalog_reload_btn.setEnabled(not busy)
        self._catalog_best_btn.setEnabled(not busy)
        self._catalog_dl_btn.setEnabled(not busy)
        self._catalog_use_btn.setEnabled(not busy)
        self.assistant_send_button.setEnabled(not busy)
        self.assistant_recommend_button.setEnabled(not busy)
        self.assistant_next_button.setEnabled(not busy)
        self.assistant_repair_button.setEnabled(not busy)
        self.model_chat_clear_button.setEnabled(not busy)
        self.model_chat_copy_button.setEnabled(not busy)
        self.model_chat_send_button.setEnabled(not busy)
        self.model_chat_input.setEnabled(not busy)
        self.output_copy_button.setEnabled(not busy)
        self.output_open_log_button.setEnabled(True)
        self.output_copy_diag_button.setEnabled(True)
        self.output_jump_button.setEnabled(True)
        for button in self._catalog_card_buttons:
            button.setEnabled(not busy)

    def _validate_model_name(self, model_name):
        return bool(MODEL_NAME_ALLOWLIST.match(model_name))

    def _build_settings(self):
        return GenerationSettings(
            max_new_tokens=self.max_tokens_input.value(),
            temperature=self.temperature_input.value(),
            top_p=self.top_p_input.value(),
            do_sample=self.do_sample_input.isChecked(),
        )

    def search_model(self):
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Error", "Introduce un nombre de modelo.")
            return

        if not self._validate_model_name(query):
            QMessageBox.warning(self, "Error", "Nombre invalido. Usa letras, numeros, '.', '_', '-', '/', ':'")
            return

        self.results_list.clear()
        candidates = [query, "meta-llama/Llama-2-7b-chat-hf", "tiiuae/falcon-7b-instruct"]
        for model_name in self._ollama_models:
            if query.lower() in model_name.lower() and model_name not in candidates:
                candidates.insert(0, model_name)

        for model_name in candidates:
            self.results_list.addItem(model_name)

        self.status_label.setText(f"Modelos filtrados para: {query}")

    def load_catalog(self):
        self._hw_label.setText("Analizando hardware y calculando recomendaciones...")
        self._catalog_list.clear()
        self._catalog_count_label.setText("Cargando catalogo...")
        self._update_output_meta(state="analizando equipo")
        self._set_busy(True)
        self.task_requested.emit(WorkerTask(operation="load_catalog"))

    def _populate_catalog(self, recommendations: list):
        self._catalog_recommendations = recommendations
        self._refresh_catalog_view()

    def _refresh_catalog_view(self):
        self._catalog_list.clear()
        self._catalog_card_buttons.clear()

        text_filter = self._catalog_search_input.text().strip().lower()
        source_filter = self._catalog_source_filter.currentData()
        quality_filter = self._catalog_quality_filter.currentData()

        visible_count = 0
        for model, reason in self._catalog_recommendations:
            if source_filter != "all" and model.source != source_filter:
                continue
            if quality_filter == "recommended" and not reason.startswith("✅"):
                continue
            if quality_filter == "compatible" and reason.startswith("⚠"):
                continue

            searchable = " ".join([
                model.display_name,
                model.name,
                model.source,
                " ".join(model.tags),
                reason,
            ]).lower()
            if text_filter and text_filter not in searchable:
                continue

            item = QListWidgetItem()
            item.setData(Qt.UserRole, model.name)
            self._catalog_list.addItem(item)
            card = self._build_catalog_card(model, reason)
            hint = card.sizeHint()
            hint.setHeight(hint.height() + 8)
            item.setSizeHint(hint)
            self._catalog_list.setItemWidget(item, card)
            visible_count += 1

        self._catalog_count_label.setText(f"Mostrando {visible_count} de {len(self._catalog_recommendations)} modelos")

    def _build_catalog_card(self, model, reason):
        source_tag = "Ollama" if model.is_ollama else "Hugging Face"
        is_installed = model.is_ollama and model.name in self._local_ollama_models

        card = QFrame()
        card.setObjectName("catalogCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 9, 10, 9)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        title = QLabel(model.display_name)
        title.setObjectName("catalogCardTitle")
        top_row.addWidget(title, 1)

        if is_installed:
            installed_chip = QLabel("✔ Instalado")
            installed_chip.setObjectName("chipInstalled")
            top_row.addWidget(installed_chip)

        status_chip = QLabel(reason.split(":", 1)[0])
        if reason.startswith("✅"):
            status_chip.setObjectName("chipOk")
        elif reason.startswith("⚠"):
            status_chip.setObjectName("chipWarn")
        else:
            status_chip.setObjectName("chip")
        top_row.addWidget(status_chip)
        layout.addLayout(top_row)

        chips_row = QHBoxLayout()
        for text in [f"{model.params_b:g}B", f"{model.size_gb:.1f} GB", f"VRAM min {model.vram_min_gb:g} GB", source_tag]:
            chip = QLabel(text)
            chip.setObjectName("chip")
            chips_row.addWidget(chip)
        chips_row.addStretch(1)
        layout.addLayout(chips_row)

        desc = QLabel(model.description)
        desc.setWordWrap(True)
        desc.setObjectName("catalogCardDesc")
        layout.addWidget(desc)

        actions = QHBoxLayout()
        download_btn = QPushButton("Descargar")
        download_btn.clicked.connect(lambda _=False, n=model.name: self._catalog_download_by_name(n))
        actions.addWidget(download_btn)
        self._catalog_card_buttons.append(download_btn)

        use_btn = QPushButton("Usar")
        use_btn.clicked.connect(lambda _=False, n=model.name: self._catalog_use_by_name(n))
        actions.addWidget(use_btn)
        self._catalog_card_buttons.append(use_btn)
        actions.addStretch(1)
        layout.addLayout(actions)

        return card

    def _select_catalog_item_by_name(self, model_name: str):
        for i in range(self._catalog_list.count()):
            item = self._catalog_list.item(i)
            if item and item.data(Qt.UserRole) == model_name:
                self._catalog_list.setCurrentItem(item)
                break

    def _select_workflow_item_by_name(self, model_name: str):
        exact_items = self.results_list.findItems(model_name, Qt.MatchExactly)
        if exact_items:
            self.results_list.setCurrentItem(exact_items[0])
        else:
            self.results_list.insertItem(0, model_name)
            self.results_list.setCurrentRow(0)
        self.search_input.setText(model_name)

    def _catalog_selected_model_name(self) -> str | None:
        item = self._catalog_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _current_selected_model_name(self) -> str | None:
        if self.main_tabs.currentWidget() == self.tab_catalog:
            return self._catalog_selected_model_name()
        selected = self.results_list.currentItem()
        if selected is not None:
            return selected.text().strip()
        if self.current_model_name:
            return self.current_model_name
        typed = self.search_input.text().strip()
        return typed or None

    def _assistant_context(self) -> dict:
        top_recommended = [model.display_name for model, reason in self._catalog_recommendations if reason.startswith("✅")]
        return {
            "ram_gb": self._hardware_profile.get("ram_gb", 0.0),
            "vram_gb": self._hardware_profile.get("vram_gb", 0.0),
            "tier": self._hardware_profile.get("tier", "desconocido"),
            "backend_mode": self._selected_backend_mode(),
            "selected_model": self._current_selected_model_name() or "",
            "model_ready": self.model_ready,
            "top_recommended": top_recommended,
            "prompt": self.prompt_input.toPlainText().strip(),
            "incomplete_hf_models": list(self._incomplete_hf_models),
        }

    def run_smart_next_action(self):
        plan = suggest_next_action(self._assistant_context())
        action = plan.get("action", "")
        message = plan.get("message", "")
        target_model = (plan.get("model_name") or "").strip()

        if message:
            self._assistant_append(f"Siguiente accion inteligente: {message}")
        self._assistant_set_recovery_state("asistencia activa", action or "sin accion")

        if action == "repair_incomplete_download" and target_model:
            self._catalog_download_by_name(target_model)
            return

        if action == "select_recommended_model" and target_model:
            self._catalog_use_by_name(target_model)
            return

        if action == "load_selected_model":
            self.apply_heretic()
            return

        if action == "set_default_prompt":
            self.prompt_input.setPlainText(self.default_prompt_v1())
            self.generate_text()
            return

        if action == "generate_now":
            self.generate_text()
            return

        self.load_catalog()

    def _pick_preferred_hf_model_name(self) -> str | None:
        for model, reason in self._catalog_recommendations:
            if model.source == SOURCE_HUGGINGFACE and reason.startswith("✅"):
                return model.name
        for model, _reason in self._catalog_recommendations:
            if model.source == SOURCE_HUGGINGFACE:
                return model.name
        return None

    def _assistant_append(self, text: str):
        self._append_feed(self.assistant_output, "Asistente", text, "assistant")

    def _assistant_set_recovery_state(self, state: str, action: str):
        self.assistant_state_chip.setText(f"Micro IA: {state}")
        self.assistant_action_chip.setText(f"Ultima accion: {action}")

    def _consume_recovery_attempt(self, key: str) -> bool:
        attempts = self._recovery_attempts.get(key, 0)
        if attempts >= self._max_recovery_attempts:
            return False
        self._recovery_attempts[key] = attempts + 1
        return True

    def _auto_adjust_after_memory_error(self):
        original_tokens = self.max_tokens_input.value()
        reduced_tokens = max(32, original_tokens // 2)
        self.max_tokens_input.setValue(reduced_tokens)
        self.do_sample_input.setChecked(False)
        self.temperature_input.setValue(min(self.temperature_input.value(), 0.5))
        self.top_p_input.setValue(min(self.top_p_input.value(), 0.8))
        self._assistant_append(
            "Ajuste anti-memoria aplicado: menos tokens, sampling desactivado y parámetros más conservadores."
        )
        self._append_output(
            f"Ajuste por memoria: max_tokens {original_tokens} -> {reduced_tokens}, sampling=off, temperatura<=0.5"
        )

    def _toggle_assistant_autopilot(self, enabled: bool):
        self._assistant_autopilot_enabled = enabled
        state = "activado" if enabled else "desactivado"
        self._assistant_append(f"Autopiloto {state}.")

    def _assistant_auto_repair_now(self):
        self._last_failed_operation = ""
        self._last_failed_model = ""
        self._append_output("\n▶ Asistente inició auto-reparación general...")
        self._set_busy(True)
        self.main_tabs.setCurrentWidget(self.tab_output)
        self._update_output_meta(state="auto-reparando")
        self.task_requested.emit(WorkerTask(operation="auto_repair", model_name="general"))

    def _assistant_try_recover_error(self, error_message: str):
        if not self._assistant_autopilot_enabled:
            return False
        diagnosis = classify_runtime_error(error_message)
        category = diagnosis.get("category", "unknown")
        target = diagnosis.get("target", "general")
        assistant_message = diagnosis.get("assistant_message", "Intento recuperar el error.")
        visible_state = diagnosis.get("visible_state", "auto-reparando")

        recovery_key = f"{category}:{self._last_failed_operation}:{self._last_failed_model}".lower()
        if not self._consume_recovery_attempt(recovery_key):
            self._assistant_set_recovery_state("requiere intervención", f"Sin más reintentos para {category}")
            self._assistant_append(
                "Ya intenté auto-recuperar este error varias veces. Te recomiendo revisar red/permisos/espacio y reintentar."
            )
            return False

        self._assistant_append(assistant_message)
        self._assistant_set_recovery_state("autorecuperando", visible_state)

        if category == "ollama_missing":
            self.backend_selector.setCurrentIndex(self.backend_selector.findData(BACKEND_MODE_FALLBACK))
            self._assistant_set_recovery_state("degradado", "Cambio automático a backend Fallback")
            return True

        if category == "memory":
            self._auto_adjust_after_memory_error()
            if self._last_failed_operation == "generate":
                self._set_busy(True)
                self.main_tabs.setCurrentWidget(self.tab_model_chat)
                self.generate_text()
                return True
            if self._last_failed_operation == "load_abliterate":
                self._set_busy(True)
                self.main_tabs.setCurrentWidget(self.tab_output)
                self.apply_heretic()
                return True

        self._set_busy(True)
        self.main_tabs.setCurrentWidget(self.tab_output)
        self.task_requested.emit(WorkerTask(operation="auto_repair", model_name=target))
        return True

    def _assistant_ask(self):
        question = self.assistant_input.text().strip() or "que modelo me conviene"
        self._append_feed(self.assistant_output, "Tu", question, "user")
        reply = build_assistant_reply(question, self._assistant_context())
        self._assistant_append(reply)
        self.assistant_input.clear()

    def _assistant_quick_recommend(self):
        self.assistant_input.setText("que modelo me recomiendas")
        self._assistant_ask()

    def _assistant_quick_next(self):
        self.assistant_input.setText("cual es mi siguiente paso")
        self._assistant_ask()

    def _catalog_download_by_name(self, model_name: str):
        self._select_catalog_item_by_name(model_name)
        self._last_failed_operation = "download_model"
        self._last_failed_model = model_name
        self.main_tabs.setCurrentWidget(self.tab_output)
        self._update_output_meta(state="descargando", model=model_name)
        self._append_output(f"\n▶ Iniciando descarga: {model_name}")
        self._set_busy(True)
        self.task_requested.emit(WorkerTask(operation="download_model", model_name=model_name))

    def _catalog_use_by_name(self, model_name: str):
        self._select_catalog_item_by_name(model_name)
        self._select_workflow_item_by_name(model_name)
        self.main_tabs.setCurrentWidget(self.tab_workflow)
        # Ollama models always have ':' in the name — auto-force Ollama backend
        if ":" in model_name:
            self.backend_selector.setCurrentIndex(
                self.backend_selector.findData(BACKEND_MODE_OLLAMA)
            )
        self.apply_heretic()

    def _catalog_use_best_recommended(self):
        for model, reason in self._catalog_recommendations:
            if reason.startswith("✅"):
                self._catalog_use_by_name(model.name)
                return
        if self._catalog_recommendations:
            self._catalog_use_by_name(self._catalog_recommendations[0][0].name)
            return
        QMessageBox.warning(self, "Catalogo vacio", "No hay recomendaciones disponibles todavía.")

    def _catalog_download(self):
        model_name = self._catalog_selected_model_name()
        if not model_name:
            QMessageBox.warning(self, "Seleccion requerida", "Selecciona un modelo del catalogo para descargar.")
            return
        self._catalog_download_by_name(model_name)

    def _catalog_use_and_abliterate(self):
        model_name = self._catalog_selected_model_name()
        if not model_name:
            QMessageBox.warning(self, "Seleccion requerida", "Selecciona un modelo del catalogo primero.")
            return
        self._catalog_use_by_name(model_name)

    def search_downloadable(self):
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Error", "Introduce un texto para buscar modelos en Ollama.")
            return
        self._set_busy(True)
        self.main_tabs.setCurrentWidget(self.tab_output)
        self._update_output_meta(state="buscando")
        self.task_requested.emit(WorkerTask(operation="search_downloadable", model_name=query))

    def download_selected_model(self):
        model_name = self._current_selected_model_name()
        if not model_name:
            QMessageBox.warning(self, "Error", "Selecciona un modelo para descargar.")
            return
        self._last_failed_operation = "download_model"
        self._last_failed_model = model_name
        self._set_busy(True)
        self.main_tabs.setCurrentWidget(self.tab_output)
        self._update_output_meta(state="descargando", model=model_name)
        self.task_requested.emit(WorkerTask(operation="download_model", model_name=model_name))

    def apply_heretic(self):
        model_name = self._current_selected_model_name()
        if not model_name:
            QMessageBox.warning(self, "Error", "Selecciona un modelo.")
            return

        self._last_failed_operation = "load_abliterate"
        self._last_failed_model = model_name

        selected_mode = self._selected_backend_mode()

        if self.prefer_real_abliteration_chk.isChecked() and selected_mode in {BACKEND_MODE_AUTO, BACKEND_MODE_OLLAMA}:
            if ":" in model_name:
                preferred_hf = self._pick_preferred_hf_model_name()
                if preferred_hf:
                    self._assistant_append(
                        "Preferencia de abliteración real activa: cambio a Heretic usando un modelo HF recomendado."
                    )
                    self._append_output(
                        f"Preferencia de abliteración real: se usará Heretic con {preferred_hf} en lugar de {model_name}."
                    )
                    self._select_workflow_item_by_name(preferred_hf)
                    self.backend_selector.setCurrentIndex(self.backend_selector.findData(BACKEND_MODE_HERETIC))
                    model_name = preferred_hf
                    selected_mode = BACKEND_MODE_HERETIC
                else:
                    self._assistant_append(
                        "No encontré modelos HF en el catálogo para abliteración real; continúo con el backend seleccionado."
                    )

        if selected_mode == BACKEND_MODE_HERETIC and ":" in model_name:
            answer = QMessageBox.question(
                self,
                "Modelo no compatible con Heretic",
                "El modelo parece de Ollama (nombre:tag).\n\n"
                "Para Heretic usa un repo Hugging Face tipo owner/model.\n"
                "Quieres cambiar a backend Ollama automaticamente?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if answer == QMessageBox.Yes:
                self.backend_selector.setCurrentIndex(self.backend_selector.findData(BACKEND_MODE_OLLAMA))
            else:
                return

        prompt = self.prompt_input.toPlainText().strip() or self.default_prompt_v1()
        settings = self._build_settings()
        self._set_busy(True)
        self.main_tabs.setCurrentWidget(self.tab_output)
        self._update_output_meta(state="cargando modelo", model=model_name, backend=selected_mode)
        self.task_requested.emit(
            WorkerTask(
                operation="load_abliterate",
                model_name=model_name,
                prompt=prompt,
                settings=settings,
                preferred_backend=selected_mode,
            )
        )

    def generate_text(self, prompt_override: str | None = None):
        if not self.model_ready:
            if self._assistant_autopilot_enabled:
                selected = self._current_selected_model_name()
                if selected:
                    self._assistant_append("No había modelo cargado. Lo cargaré automáticamente y luego generaré.")
                    self._pending_generate_after_load = True
                    self.apply_heretic()
                    return
            QMessageBox.warning(self, "Error", "Primero carga y ablitera un modelo.")
            return

        prompt = (prompt_override or "").strip() or self.prompt_input.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "Error", "Introduce un prompt para generar texto.")
            return

        settings = self._build_settings()
        self._last_failed_operation = "generate"
        self._last_failed_model = self.current_model_name or self._current_selected_model_name()
        self._set_busy(True)
        self.main_tabs.setCurrentWidget(self.tab_model_chat)
        self._model_chat_append("Tu", prompt, "user")
        self._update_output_meta(state="generando", backend=self._selected_backend_mode())
        self.task_requested.emit(
            WorkerTask(
                operation="generate",
                prompt=prompt,
                settings=settings,
                preferred_backend=self._selected_backend_mode(),
            )
        )

    @Slot(dict)
    def _on_task_success(self, payload):
        self._set_busy(False)
        operation = payload.get("operation", "")
        model_name = payload.get("model_name", "")
        output = payload.get("output", "")
        backend = payload.get("backend", "")
        log_path = payload.get("log_path", "")

        if log_path:
            self._log_path = log_path

        if operation == "startup_probe":
            self._ollama_models = payload.get("local_ollama", [])
            self._local_ollama_models = list(self._ollama_models)
            self._populate_local_models()
            self._extensions_heretic_ok = "Si" if payload.get("heretic_ok", False) else "No"
            self._extensions_auto_name = payload.get("auto_backend", "desconocido")
            self.refresh_extensions_status()
            self._append_output(
                "Startup probe: "
                f"Ollama={len(self._ollama_models)} | Heretic={self._extensions_heretic_ok} | Auto={self._extensions_auto_name}"
            )
            self._mark_boot_operation_completed(operation)
            return

        if operation == "load_abliterate":
            self.model_ready = True
            self.current_model_name = model_name
            self._update_output_meta(state="modelo listo", model=model_name, backend=backend)
            self._update_chat_context_meta(model=model_name, backend=backend)
            self._append_output(f"Modelo listo para pruebas: {model_name}")
            self._append_output(f"Backend: {backend}")
            self.refresh_extensions_status()
            self._assistant_append("Modelo cargado. Ya puedes generar texto.")
            if output:
                self._model_chat_append("Modelo", output, "model")
                output = ""
            if self._pending_generate_after_load:
                self._pending_generate_after_load = False
                self._assistant_append("Continuo automáticamente con la generación pendiente.")
                self.generate_text()
                return

        if operation == "generate":
            self._update_output_meta(state="respuesta lista", model=model_name, backend=backend)
            self._update_chat_context_meta(model=model_name, backend=backend)
            self._last_failed_operation = ""
            self._last_failed_model = ""
            self._assistant_set_recovery_state("estable", "Generación completada")
            if output:
                self._model_chat_append("Modelo", output, "model")
                output = ""

        if operation == "search_downloadable":
            models = payload.get("models", [])
            query = payload.get("query", "")
            self.results_list.clear()
            for candidate in models:
                self.results_list.addItem(candidate)
            self._update_output_meta(state="resultados listos")
            self._append_output(f"Resultados descargables para '{query}': {len(models)}")

        if operation == "load_catalog":
            profile = payload.get("profile", {})
            recommendations = payload.get("recommendations", [])
            self._local_ollama_models = payload.get("local_ollama", [])
            self._incomplete_hf_models = payload.get("incomplete_hf", [])
            self._hardware_profile = profile
            ram = profile.get("ram_gb", 0)
            vram = profile.get("vram_gb", 0)
            tier = profile.get("tier", "desconocido")
            gpu_text = f"GPU: {vram:.1f} GB VRAM" if vram > 0 else "Sin GPU detectada"
            self._hw_label.setText(
                f"Hardware detectado · RAM: {ram:.0f} GB · {gpu_text} · Perfil: {tier}\n"
                "Los modelos con ✅ son los mas recomendados para tu equipo."
            )
            self._populate_catalog(recommendations)
            self._update_output_meta(state="catalogo listo")
            self._append_output(f"Catalogo cargado: {len(recommendations)} modelos.")
            self._assistant_append(build_assistant_reply("que modelo me recomiendas", self._assistant_context()))
            if self._incomplete_hf_models:
                short_list = ", ".join(self._incomplete_hf_models[:2])
                extra = "" if len(self._incomplete_hf_models) <= 2 else f" (+{len(self._incomplete_hf_models) - 2} más)"
                self._assistant_append(
                    "Detecté descargas HF incompletas (posible cierre inesperado): "
                    f"{short_list}{extra}. Haré recuperación automática al intentar cargar esos modelos."
                )
                self._assistant_set_recovery_state("atención", "Modelos incompletos detectados")
            else:
                self._assistant_set_recovery_state("estable", "Catalogo listo")
            self._mark_boot_operation_completed(operation)

        if operation == "download_model":
            self._update_output_meta(state="modelo descargado", model=model_name)
            self._append_output(payload.get("output", "Descarga completada."))
            self.load_ollama_models()
            self._assistant_append("Descarga finalizada. Puedo recomendarte backend para usarlo.")
            self._last_failed_operation = ""
            self._last_failed_model = ""
            self._assistant_set_recovery_state("estable", "Descarga completada")

        if operation == "load_abliterate":
            self._last_failed_operation = ""
            self._last_failed_model = ""
            self._assistant_set_recovery_state("estable", "Modelo cargado y listo")

        if operation == "auto_repair":
            self._update_output_meta(state="entorno reparado")
            self._append_output(payload.get("output", "Auto-reparación completada."))
            self._assistant_append("Auto-reparación completada. Reintento la operación fallida si aplica.")
            self._assistant_set_recovery_state("estable", "Auto-reparación finalizada")
            if self._last_failed_operation == "download_model" and self._last_failed_model:
                self._append_output(f"Reintentando descarga: {self._last_failed_model}")
                self._set_busy(True)
                self.task_requested.emit(
                    WorkerTask(operation="download_model", model_name=self._last_failed_model)
                )
                return
            if self._last_failed_operation == "load_abliterate":
                self._append_output("Reintentando carga y abliteración...")
                self.apply_heretic()
                return
            if self._last_failed_operation == "generate":
                self._append_output("Reintentando generación tras auto-reparación...")
                self.generate_text()
                return

        if output:
            self._append_output("\n--- Salida ---\n")
            self._append_output(output)

    @Slot(str)
    def _on_task_error(self, error_message):
        self._set_busy(False)
        if self._boot_waiting_operation:
            self.startup_title.setText("Arranque con incidencias")
            self.startup_detail.setText("Se detectó un problema durante el inicio. Puedes continuar y revisar el log.")
            self.startup_progress.setValue(max(self.startup_progress.value(), 75))
            self._boot_waiting_operation = ""
            QTimer.singleShot(1200, lambda: self.startup_panel.setVisible(False))
        self._update_output_meta(state="error")
        self._append_output(f"Error: {error_message}")
        self._assistant_set_recovery_state("error detectado", "Evaluando auto-recovery")
        recovered = self._assistant_try_recover_error(error_message)
        if recovered:
            return
        self._assistant_set_recovery_state("bloqueado", "Se requiere intervención manual")
        friendly = humanize_runtime_error(error_message)
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle(friendly.get("title", "Error"))
        msg.setText(friendly.get("summary", "No se pudo completar la operación."))
        msg.setInformativeText(f"Sugerencia: {friendly.get('hint', 'Revisa el log y reintenta.')}\nLog: {self._log_path}")
        msg.setDetailedText(error_message)
        msg.exec()

    def closeEvent(self, event):
        self.worker_thread.quit()
        self.worker_thread.wait(3000)
        super().closeEvent(event)

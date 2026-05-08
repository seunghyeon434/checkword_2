from pathlib import Path

from PyQt5.QtCore import QPoint, QRectF, QSize, Qt, QVariantAnimation, QTimer
from PyQt5.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QStackedLayout,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ResultPanel(QWidget):
    LIGHT_THEME = {
        "window_bg": "#00000000",
        "card_bg": "#f7efe5",
        "card_border": "#e2d4c3",
        "title": "#2f241f",
        "text": "#43332b",
        "muted": "#7b6658",
        "editor_bg": "#fffaf4",
        "editor_border": "#dccbbb",
        "tab_bg": "#efe0d0",
        "tab_selected": "#ffffff",
        "tab_text": "#4a382f",
        "button_bg": "#e8d4bf",
        "button_hover": "#dcc1a7",
        "button_text": "#3f2f26",
        "accent": "#b86a3c",
        "accent_hover": "#9f5730",
        "accent_text": "#fff8f2",
        "danger_bg": "#ead7cf",
        "danger_hover": "#dfc3b7",
        "score_bg": "#f1e1d0",
        "input_bg": "#fffaf4",
        "settings_panel_bg": "#ffffff",
        "settings_panel_border": "#00ffffff",
        "settings_text": "#2f241f",
        "settings_notice_text": "#2f241f",
        "settings_check_bg": "#fffaf4",
        "settings_check_border": "#dccbbb",
        "settings_check_checked": "#b86a3c",
    }

    DARK_THEME = {
        "window_bg": "#00000000",
        "card_bg": "#1f2329",
        "card_border": "#303741",
        "title": "#f4efe8",
        "text": "#d6dce5",
        "muted": "#98a1ad",
        "editor_bg": "#14181d",
        "editor_border": "#39414c",
        "tab_bg": "#2b3139",
        "tab_selected": "#39414c",
        "tab_text": "#f4efe8",
        "button_bg": "#2e3640",
        "button_hover": "#3a4451",
        "button_text": "#edf2f7",
        "accent": "#c77747",
        "accent_hover": "#df8a57",
        "accent_text": "#fff7f1",
        "danger_bg": "#3a3134",
        "danger_hover": "#4a3b3f",
        "score_bg": "#2b3139",
        "input_bg": "#14181d",
        "settings_panel_bg": "#ffffff",
        "settings_panel_border": "#00ffffff",
        "settings_text": "#2f241f",
        "settings_notice_text": "#ffffff",
        "settings_check_bg": "#fffaf4",
        "settings_check_border": "#dccbbb",
        "settings_check_checked": "#b86a3c",
    }

    def __init__(self, initial_dark_mode=False):
        super().__init__()

        self.last_original_text = ""
        self._showing_placeholder = True
        self.is_dark_mode = initial_dark_mode
        self.saved_default_dark_mode = False
        self.saved_input_mode = "realtime"
        self.drag_active = False
        self.drag_position = QPoint()
        self._centered_once = False
        self._theme_mix = 1.0 if initial_dark_mode else 0.0

        self.setWindowTitle("Writing Assistant")
        self.setFixedSize(760, 520)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.theme_animation = QVariantAnimation(self)
        self.theme_animation.setDuration(280)
        self.theme_animation.valueChanged.connect(self._on_theme_mix_changed)

        self.settings_notice_timer = QTimer(self)
        self.settings_notice_timer.setSingleShot(True)
        self.settings_notice_timer.timeout.connect(self._start_settings_notice_fade)

        self.settings_notice_animation = QVariantAnimation(self)
        self.settings_notice_animation.setDuration(900)
        self.settings_notice_animation.valueChanged.connect(self._update_settings_notice_opacity)
        self.settings_notice_animation.finished.connect(self._hide_settings_notice)

        self.build_ui()
        self.apply_shadow()
        self.apply_theme()
        self.reset_text_tab()
        self.clear_spell_result()
        self.clear_summary_result()
        self.clear_tone_result()
        self.clear_evaluation_score()
        self.clear_title_recommendation()

    def build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)

        self.card = QFrame()
        self.card.setObjectName("panelCard")
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(24, 20, 24, 24)
        self.card_layout.setSpacing(18)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        title_block = QVBoxLayout()
        title_block.setSpacing(6)
        title_block.setContentsMargins(0, 2, 0, 0)

        self.title_label = QLabel("Writing Assistant")
        self.title_label.setObjectName("titleLabel")

        self.subtitle_label = QLabel("문장을 다듬고 핵심 내용을 빠르게 정리합니다.")
        self.subtitle_label.setObjectName("subtitleLabel")

        self.active_window_label = QLabel("")
        self.active_window_label.setObjectName("activeWindowLabel")
        title_block.addWidget(self.title_label)
        title_block.addWidget(self.subtitle_label)
        title_block.addWidget(self.active_window_label)

        header_layout.addLayout(title_block)
        header_layout.addStretch()

        self.settings_btn = QPushButton("설정")
        self.settings_btn.setObjectName("iconButton")
        self.settings_btn.setToolTip("설정")
        self.settings_btn.setCheckable(True)
        self.settings_icon_path = self._find_settings_icon_path()
        if self.settings_icon_path:
            self.settings_btn.setIconSize(QSize(18, 18))
            self.settings_btn.setText("")
        self.settings_btn.clicked.connect(self.open_settings_tab)

        self.dark_mode_btn = QPushButton("다크 모드 켜기")
        self.dark_mode_btn.setObjectName("secondaryButton")
        self.dark_mode_btn.setCheckable(True)
        self.dark_mode_btn.clicked.connect(self.toggle_theme)

        self.hide_btn = QPushButton("숨기기")
        self.hide_btn.setObjectName("ghostButton")
        self.hide_btn.clicked.connect(self.hide)

        header_layout.addWidget(self.settings_btn)
        header_layout.addWidget(self.dark_mode_btn)
        header_layout.addWidget(self.hide_btn)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("resultTabs")
        self.input_mode_status_label = QLabel("")
        self.input_mode_status_label.setObjectName("inputModeStatusLabel")

        self.text_box = self._create_text_box("복사한 텍스트가 여기에 뜹니다.")
        self.spell_box = self._create_text_box("")
        self.summary_box = self._create_text_box("")
        self.tone_box = self._create_text_box("")

        self.evaluate_btn = QPushButton("평가")
        self.evaluate_btn.setObjectName("secondaryButton")
        self.recommend_title_btn = QPushButton("추천")
        self.recommend_title_btn.setObjectName("secondaryButton")
        self.refresh_btn = QPushButton("다시 분석")
        self.refresh_btn.setObjectName("secondaryButton")
        self.run_summary_btn = QPushButton("글 요약")
        self.run_summary_btn.setObjectName("secondaryButton")
        self.run_tone_btn = QPushButton("변경")
        self.run_tone_btn.setObjectName("secondaryButton")
        self.save_settings_btn = QPushButton("저장")
        self.save_settings_btn.setObjectName("secondaryButton")
        self.close_settings_btn = QPushButton("X")
        self.close_settings_btn.setObjectName("ghostButton")

        self.score_label = QLabel("점수")
        self.score_label.setObjectName("scoreLabel")
        self.score_label.setAlignment(Qt.AlignCenter)
        self.score_label.setMinimumWidth(92)

        self.title_label_box = QLabel("제목")
        self.title_label_box.setObjectName("titleValueLabel")
        self.title_label_box.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.title_label_box.setMinimumWidth(220)
        self.title_label_box.setFixedHeight(40)

        self.tone_input = QLineEdit()
        self.tone_input.setObjectName("toneInput")
        self.tone_input.setPlaceholderText("원하는 문체/말투")

        self.default_dark_mode_checkbox = QCheckBox("기본 다크 모드")
        self.default_dark_mode_checkbox.setObjectName("settingsCheck")
        self.clipboard_mode_checkbox = QCheckBox("클립보드 인식 사용")
        self.clipboard_mode_checkbox.setObjectName("settingsCheck")
        self.realtime_mode_checkbox = QCheckBox("실시간 인식 사용")
        self.realtime_mode_checkbox.setObjectName("settingsCheck")
        self.clipboard_mode_checkbox.toggled.connect(self._sync_input_mode_checks)
        self.realtime_mode_checkbox.toggled.connect(self._sync_input_mode_checks)

        self.settings_notice_label = QLabel("저장되었습니다.")
        self.settings_notice_label.setObjectName("settingsNotice")
        self.settings_notice_label.hide()
        self.settings_notice_effect = QGraphicsOpacityEffect(self.settings_notice_label)
        self.settings_notice_effect.setOpacity(0.0)
        self.settings_notice_label.setGraphicsEffect(self.settings_notice_effect)

        self.tabs.addTab(self._create_text_tab(), "텍스트")
        self.tabs.addTab(self._create_spell_tab(), "맞춤법")
        self.tabs.addTab(self._create_action_tab(self.summary_box, self.run_summary_btn), "요약")
        self.tabs.addTab(self._create_tone_tab(), "문체/말투")

        self.settings_page = self._create_settings_tab()
        self.content_container = QWidget()
        self.content_stack = QStackedLayout(self.content_container)
        self.content_stack.setContentsMargins(0, 0, 0, 0)
        self.content_stack.addWidget(self.tabs)
        self.content_stack.addWidget(self.settings_page)
        self.content_stack.setCurrentIndex(0)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.copy_btn = QPushButton("복사")
        self.copy_btn.setObjectName("primaryButton")

        self.quit_btn = QPushButton("종료")
        self.quit_btn.setObjectName("secondaryButton")

        button_layout.addWidget(self.copy_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.input_mode_status_label)
        button_layout.addStretch()
        button_layout.addWidget(self.quit_btn)

        self.card_layout.addLayout(header_layout)
        self.card_layout.addWidget(self.content_container)
        self.card_layout.addLayout(button_layout)
        root_layout.addWidget(self.card)

    def _find_settings_icon_path(self):
        base_dir = Path(__file__).resolve().parent.parent
        for name in ("settings.png", "settings.svg"):
            candidate = base_dir / name
            if candidate.exists():
                return candidate
        return None

    def _update_settings_icon(self, color_value):
        if not self.settings_icon_path:
            return

        base_icon = QIcon(str(self.settings_icon_path))
        base_pixmap = base_icon.pixmap(QSize(18, 18))
        if base_pixmap.isNull():
            return

        tinted_pixmap = QPixmap(base_pixmap.size())
        tinted_pixmap.fill(Qt.transparent)

        painter = QPainter(tinted_pixmap)
        painter.drawPixmap(0, 0, base_pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(tinted_pixmap.rect(), QColor(color_value))
        painter.end()

        self.settings_btn.setIcon(QIcon(tinted_pixmap))

    def _create_text_box(self, placeholder):
        text_box = QTextEdit()
        text_box.setReadOnly(True)
        text_box.setPlaceholderText(placeholder)
        text_box.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        text_box.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        text_box.setLineWrapMode(QTextEdit.WidgetWidth)
        text_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return text_box

    def _create_text_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 8, 0)
        title_row.setSpacing(10)
        title_row.addWidget(self.title_label_box, 1)
        title_row.addWidget(self.recommend_title_btn)
        layout.addLayout(title_row)

        layout.addWidget(self.text_box, 1)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 8, 0)
        action_row.setSpacing(10)
        action_row.addStretch()
        action_row.addWidget(self.score_label)
        action_row.addWidget(self.evaluate_btn)
        layout.addLayout(action_row)
        return page

    def _create_spell_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)
        layout.addWidget(self.spell_box, 1)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 8, 0)
        button_row.addStretch()
        button_row.addWidget(self.refresh_btn)
        layout.addLayout(button_row)
        return page

    def _create_action_tab(self, text_box, action_button):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)
        layout.addWidget(text_box, 1)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 8, 0)
        button_row.addStretch()
        button_row.addWidget(action_button)
        layout.addLayout(button_row)
        return page

    def _create_tone_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        control_row = QHBoxLayout()
        control_row.setContentsMargins(0, 0, 0, 0)
        control_row.setSpacing(10)
        control_row.addWidget(self.tone_input, 1)
        control_row.addWidget(self.run_tone_btn)

        layout.addLayout(control_row)
        layout.addWidget(self.tone_box, 1)
        return page

    def _create_settings_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(0)

        panel = QFrame()
        panel.setObjectName("settingsPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(22, 18, 22, 18)
        panel_layout.setSpacing(16)

        section = QVBoxLayout()
        section.setContentsMargins(10, 4, 0, 0)
        section.setSpacing(12)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        section_title = QLabel("설정")
        section_title.setObjectName("sectionTitle")
        top_row.addWidget(section_title)
        top_row.addStretch()
        top_row.addWidget(self.close_settings_btn)

        section.addLayout(top_row)
        section.addSpacing(10)
        section.addWidget(self.default_dark_mode_checkbox)
        section.addSpacing(10)
        section.addWidget(self.clipboard_mode_checkbox)
        section.addSpacing(10)
        section.addWidget(self.realtime_mode_checkbox)
        section.addStretch()

        panel_layout.addLayout(section, 1)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 2, 0)
        button_row.addWidget(self.settings_notice_label, 0, Qt.AlignLeft | Qt.AlignBottom)
        button_row.addStretch()
        button_row.addWidget(self.save_settings_btn)
        panel_layout.addLayout(button_row)

        layout.addWidget(panel)
        return page

    def apply_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(35)
        shadow.setOffset(0, 16)
        shadow.setColor(QColor(0, 0, 0, 70))
        self.card.setGraphicsEffect(shadow)

    def _blended_colors(self):
        return {
            key: self._blend_color(self.LIGHT_THEME[key], self.DARK_THEME[key], self._theme_mix)
            for key in self.LIGHT_THEME
        }

    def _blend_color(self, start, end, mix):
        start_color = QColor(start)
        end_color = QColor(end)
        r = round(start_color.red() + (end_color.red() - start_color.red()) * mix)
        g = round(start_color.green() + (end_color.green() - start_color.green()) * mix)
        b = round(start_color.blue() + (end_color.blue() - start_color.blue()) * mix)
        a = round(start_color.alpha() + (end_color.alpha() - start_color.alpha()) * mix)
        return QColor(r, g, b, a).name(QColor.HexArgb if a < 255 else QColor.HexRgb)

    def _on_theme_mix_changed(self, value):
        self._theme_mix = float(value)
        self.apply_theme()

    def apply_theme(self):
        colors = self._blended_colors()
        self.dark_mode_btn.setText("다크 모드 끄기" if self.is_dark_mode else "다크 모드 켜기")
        self.dark_mode_btn.setChecked(self.is_dark_mode)

        self.setStyleSheet(
            f"""
            QWidget {{
                background: {colors["window_bg"]};
                color: {colors["text"]};
                font-size: 14px;
            }}
            QFrame#panelCard {{
                background: {colors["card_bg"]};
                border: 1px solid {colors["card_border"]};
                border-radius: 28px;
            }}
            QFrame#settingsPanel {{
                background: {colors["settings_panel_bg"]};
                border: 1px solid {colors["settings_panel_border"]};
                border-radius: 22px;
            }}
            QLabel#titleLabel {{
                color: {colors["title"]};
                font-size: 28px;
                font-weight: 700;
                letter-spacing: 0.4px;
            }}
            QLabel#subtitleLabel {{
                color: {colors["muted"]};
                font-size: 13px;
            }}
            QLabel#inputModeStatusLabel {{
                color: {colors["muted"]};
                font-size: 12px;
                font-weight: 600;
                padding: 8px 4px 0 10px;
            }}
            QLabel#activeWindowLabel {{
                color: {colors["muted"]};
                font-size: 12px;
                font-weight: 600;
            }}
            QLabel#sectionTitle {{
                color: {colors["settings_text"]};
                font-size: 18px;
                font-weight: 700;
            }}
            QLabel#scoreLabel {{
                background: {colors["score_bg"]};
                color: {colors["text"]};
                border-radius: 12px;
                padding: 6px 14px;
                font-size: 13px;
                font-weight: 700;
            }}
            QLabel#titleValueLabel {{
                background: {colors["score_bg"]};
                color: {colors["text"]};
                border-radius: 12px;
                padding: 0 14px;
                font-size: 13px;
                font-weight: 700;
            }}
            QLabel#settingsNotice {{
                background: {colors["score_bg"]};
                color: {colors["settings_notice_text"]};
                border-radius: 12px;
                border: 1px solid {colors["settings_panel_border"]};
                padding: 7px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QCheckBox#settingsCheck {{
                color: {colors["settings_text"]};
                spacing: 10px;
                font-size: 14px;
            }}
            QCheckBox#settingsCheck::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 5px;
                border: 1px solid {colors["settings_check_border"]};
                background: {colors["settings_check_bg"]};
            }}
            QCheckBox#settingsCheck::indicator:checked {{
                background: {colors["settings_check_checked"]};
                border: 1px solid {colors["settings_check_checked"]};
            }}
            QLineEdit#toneInput {{
                background: {colors["input_bg"]};
                color: {colors["text"]};
                border: 1px solid {colors["editor_border"]};
                border-radius: 14px;
                padding: 10px 14px;
            }}
            QLineEdit#toneInput::placeholder {{
                color: {colors["muted"]};
            }}
            QTabWidget::pane {{
                border: 1px solid {colors["editor_border"]};
                border-radius: 20px;
                background: {colors["editor_bg"]};
                top: -1px;
            }}
            QTabWidget::tab-bar {{
                left: 20px;
            }}
            QTabBar::tab {{
                background: {colors["tab_bg"]};
                color: {colors["tab_text"]};
                padding: 10px 18px;
                margin-right: 8px;
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
                min-width: 88px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background: {colors["tab_selected"]};
            }}
            QTextEdit {{
                background: {colors["editor_bg"]};
                color: {colors["text"]};
                border: none;
                border-radius: 18px;
                padding: 14px;
                selection-background-color: {colors["accent"]};
                selection-color: {colors["accent_text"]};
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 10px;
                margin: 12px 6px 12px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {colors["button_bg"]};
                border-radius: 5px;
                min-height: 28px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {colors["button_hover"]};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: transparent;
                height: 0px;
            }}
            QPushButton {{
                border: none;
                border-radius: 14px;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton#primaryButton {{
                background: {colors["accent"]};
                color: {colors["accent_text"]};
            }}
            QPushButton#primaryButton:hover {{
                background: {colors["accent_hover"]};
            }}
            QPushButton#secondaryButton {{
                background: {colors["button_bg"]};
                color: {colors["button_text"]};
            }}
            QPushButton#secondaryButton:hover {{
                background: {colors["button_hover"]};
            }}
            QPushButton#ghostButton {{
                background: {colors["danger_bg"]};
                color: {colors["button_text"]};
                padding-left: 14px;
                padding-right: 14px;
            }}
            QPushButton#ghostButton:hover {{
                background: {colors["danger_hover"]};
            }}
            QPushButton#iconButton {{
                background: {colors["button_bg"]};
                color: {colors["button_text"]};
                min-width: 40px;
                max-width: 40px;
                min-height: 40px;
                max-height: 40px;
                padding: 0px;
                border-radius: 14px;
            }}
            QPushButton#iconButton:hover {{
                background: {colors["button_hover"]};
            }}
            """
        )
        self._update_settings_icon(colors["button_text"])
        self._refresh_text_box()

    def _refresh_text_box(self):
        if self._showing_placeholder:
            self._render_placeholder_text()
        else:
            self._render_original_text()

    def toggle_theme(self):
        self.set_dark_mode(not self.is_dark_mode)

    def set_dark_mode(self, enabled, animate=True):
        self.is_dark_mode = enabled
        if not animate:
            self._theme_mix = 1.0 if enabled else 0.0
            self.apply_theme()
            return

        start = self._theme_mix
        end = 1.0 if enabled else 0.0
        self.theme_animation.stop()
        self.theme_animation.setStartValue(start)
        self.theme_animation.setEndValue(end)
        self.theme_animation.start()

    def center_on_screen(self):
        screen = self.screen() or self.windowHandle().screen()
        if not screen:
            return

        geometry = screen.availableGeometry()
        x = geometry.x() + (geometry.width() - self.width()) // 2
        y = geometry.y() + (geometry.height() - self.height()) // 2
        self.move(x, y)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._centered_once:
            self.center_on_screen()
            self._centered_once = True

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.pos().y() <= 90:
            self.drag_active = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_active and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_active = False
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        outline = QPainterPath()
        outline.addRoundedRect(QRectF(self.rect().adjusted(8, 8, -8, -8)), 30, 30)
        painter.setPen(QPen(QColor(0, 0, 0, 0)))
        painter.drawPath(outline)

        super().paintEvent(event)

    def open_settings_tab(self):
        showing_settings = self.content_stack.currentIndex() == 1
        if not showing_settings:
            self.default_dark_mode_checkbox.setChecked(self.saved_default_dark_mode)
            self.set_input_mode(self.saved_input_mode)
        self.content_stack.setCurrentIndex(0 if showing_settings else 1)
        self.settings_btn.setChecked(not showing_settings)

    def close_settings_page(self):
        self.default_dark_mode_checkbox.setChecked(self.saved_default_dark_mode)
        self.set_input_mode(self.saved_input_mode)
        self.content_stack.setCurrentIndex(0)
        self.settings_btn.setChecked(False)

    def show_settings_saved_notice(self):
        self.settings_notice_timer.stop()
        self.settings_notice_animation.stop()
        self.settings_notice_label.show()
        self.settings_notice_label.raise_()
        self.settings_notice_effect.setOpacity(1.0)
        self.settings_notice_label.updateGeometry()
        self.settings_notice_label.repaint()
        QApplication.processEvents()
        self.settings_notice_timer.start(3000)

    def _start_settings_notice_fade(self):
        self.settings_notice_animation.setStartValue(1.0)
        self.settings_notice_animation.setEndValue(0.0)
        self.settings_notice_animation.start()

    def _update_settings_notice_opacity(self, value):
        self.settings_notice_effect.setOpacity(float(value))

    def _hide_settings_notice(self):
        if self.settings_notice_effect.opacity() <= 0.01:
            self.settings_notice_label.hide()

    def set_default_dark_mode_checked(self, enabled):
        checked = bool(enabled)
        self.saved_default_dark_mode = checked
        self.default_dark_mode_checkbox.setChecked(checked)

    def get_default_dark_mode_checked(self):
        return self.default_dark_mode_checkbox.isChecked()

    def set_input_mode(self, mode):
        normalized = "clipboard" if mode == "clipboard" else "realtime"
        self.saved_input_mode = normalized
        self.clipboard_mode_checkbox.blockSignals(True)
        self.realtime_mode_checkbox.blockSignals(True)
        self.clipboard_mode_checkbox.setChecked(normalized == "clipboard")
        self.realtime_mode_checkbox.setChecked(normalized == "realtime")
        self.clipboard_mode_checkbox.blockSignals(False)
        self.realtime_mode_checkbox.blockSignals(False)
        mode_text = "클립보드 모드" if normalized == "clipboard" else "실시간 모드"
        self.input_mode_status_label.setText(f"{mode_text} 인식 사용중")

    def get_input_mode(self):
        return "clipboard" if self.clipboard_mode_checkbox.isChecked() else "realtime"

    def set_active_window_title(self, title):
        normalized = str(title).strip()
        self.active_window_label.setText(f"인식 중: {normalized}" if normalized else "")

    def _sync_input_mode_checks(self):
        sender = self.sender()
        if sender is self.clipboard_mode_checkbox and self.clipboard_mode_checkbox.isChecked():
            self.realtime_mode_checkbox.blockSignals(True)
            self.realtime_mode_checkbox.setChecked(False)
            self.realtime_mode_checkbox.blockSignals(False)
        elif sender is self.realtime_mode_checkbox and self.realtime_mode_checkbox.isChecked():
            self.clipboard_mode_checkbox.blockSignals(True)
            self.clipboard_mode_checkbox.setChecked(False)
            self.clipboard_mode_checkbox.blockSignals(False)

        if not self.clipboard_mode_checkbox.isChecked() and not self.realtime_mode_checkbox.isChecked():
            default_checkbox = (
                self.realtime_mode_checkbox if self.saved_input_mode == "realtime" else self.clipboard_mode_checkbox
            )
            default_checkbox.blockSignals(True)
            default_checkbox.setChecked(True)
            default_checkbox.blockSignals(False)

    def reset_text_tab(self):
        self._showing_placeholder = True
        self.last_original_text = ""
        self.set_active_window_title("")
        self._render_placeholder_text()
        self.clear_evaluation_score()
        self.clear_title_recommendation()

    def _render_placeholder_text(self):
        self.text_box.clear()
        self.text_box.setHtml(
            '<div style="color: #9b8a7f;">'
            '<div>복사한 텍스트가 여기에 뜹니다.</div>'
            "</div>"
        )

    def show_text_unavailable_placeholder(self):
        muted_color = self._blended_colors()["muted"]
        self._showing_placeholder = True
        self.last_original_text = ""
        self.text_box.clear()
        self.text_box.setHtml(
            f'<div style="color: {muted_color};">'
            "<div>텍스트가 인식되지 않습니다.</div>"
            "</div>"
        )
        self.clear_summary_result()
        self.clear_evaluation_score()
        self.clear_title_recommendation()
        self.clear_tone_result()
        self.clear_spell_result()

    def set_original_text(self, text):
        previous_text = self.last_original_text
        self._showing_placeholder = False
        self.last_original_text = text
        self._render_original_text(previous_text=previous_text)
        self.clear_summary_result()
        self.clear_evaluation_score()
        self.clear_title_recommendation()
        self.clear_tone_result()

    def _render_original_text(self, previous_text=""):
        text_color = self._blended_colors()["text"]
        safe_text = (
            self.last_original_text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )
        scrollbar = self.text_box.verticalScrollBar()
        previous_value = scrollbar.value()
        previous_maximum = scrollbar.maximum()
        was_near_bottom = previous_maximum - previous_value <= 24
        is_appending = bool(previous_text) and self.last_original_text.startswith(previous_text)

        self.text_box.clear()
        self.text_box.setHtml(
            f'<div style="color: {text_color};">'
            f"<div>{safe_text}</div>"
            "</div>"
        )

        if is_appending or was_near_bottom:
            scrollbar.setValue(scrollbar.maximum())
        elif previous_maximum > 0:
            ratio = previous_value / previous_maximum
            scrollbar.setValue(round(scrollbar.maximum() * ratio))

    def clear_evaluation_score(self):
        self.score_label.setText("점수")

    def set_evaluation_score(self, score_text):
        self.score_label.setText(score_text)

    def clear_title_recommendation(self):
        self.title_label_box.setText("제목")

    def set_title_recommendation(self, title_text):
        self.title_label_box.setText(title_text)

    def clear_spell_result(self):
        self.spell_box.clear()
        self.spell_box.setHtml(
            '<div style="color: #9b8a7f;">'
            '<div>맞춤법 검사한 게 여기에 뜹니다.</div>'
            "</div>"
        )

    def clear_summary_result(self):
        self.summary_box.clear()
        self.summary_box.setHtml(
            '<div style="color: #9b8a7f;">'
            '<div>글을 요약한 게 여기에 뜹니다.</div>'
            "</div>"
        )

    def clear_tone_result(self):
        self.tone_box.clear()
        self.tone_box.setHtml(
            '<div style="color: #9b8a7f;">'
            '<div>문체/말투 변경 결과가 여기에 뜹니다.</div>'
            "</div>"
        )

    def set_spell_result(self, text):
        self.spell_box.setPlainText(text)

    def set_summary_result(self, text):
        self.summary_box.setPlainText(text)

    def set_tone_result(self, text):
        self.tone_box.setPlainText(text)

    def get_current_text(self):
        current_tab = self.tabs.currentIndex()
        if current_tab == 0:
            return self.text_box.toPlainText()
        if current_tab == 1:
            return self.spell_box.toPlainText()
        if current_tab == 2:
            return self.summary_box.toPlainText()
        if current_tab == 3:
            return self.tone_box.toPlainText()
        return ""

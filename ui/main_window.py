import sys
import threading
from pathlib import Path

import pyperclip
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import QAction, QApplication, QMenu, QStyle, QSystemTrayIcon

from app_settings import load_app_settings, save_app_settings
from core.analyzer import TextAnalyzer
from input.clipboard_monitor import monitor_clipboard
from input.realtime_text_monitor import monitor_realtime_text
from ui.result_panel import ResultPanel


class SignalBridge(QObject):
    text_signal = pyqtSignal(object)


class App:
    def __init__(self):
        self.qt_app = QApplication(sys.argv)
        self.load_app_font()
        self.settings = load_app_settings()
        self.startup_clipboard_text = pyperclip.paste()

        self.panel = ResultPanel(
            initial_dark_mode=self.settings.get("default_dark_mode", False)
        )
        self.panel.set_default_dark_mode_checked(
            self.settings.get("default_dark_mode", False)
        )

        self.analyzer = TextAnalyzer()
        self.last_input = ""
        self.active_input_mode = self.settings.get("input_mode", "realtime")

        self.signals = SignalBridge()
        self.signals.text_signal.connect(self.handle_input_event)

        self.panel.set_input_mode(self.active_input_mode)
        self.reset_session_state()

        self.panel.copy_btn.clicked.connect(self.copy_result)
        self.panel.refresh_btn.clicked.connect(self.run_spell_check)
        self.panel.quit_btn.clicked.connect(self.quit_app)
        self.panel.evaluate_btn.clicked.connect(self.run_evaluation)
        self.panel.recommend_title_btn.clicked.connect(self.run_title_recommendation)
        self.panel.run_summary_btn.clicked.connect(self.run_summary)
        self.panel.run_tone_btn.clicked.connect(self.run_tone_change)
        self.panel.save_settings_btn.clicked.connect(self.save_settings)
        self.panel.close_settings_btn.clicked.connect(self.panel.close_settings_page)

        self.init_tray()

    def load_app_font(self):
        font_path = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "A2Z-Medium.ttf"
        font_id = QFontDatabase.addApplicationFont(str(font_path))
        if font_id == -1:
            return

        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            self.qt_app.setFont(QFont(families[0], 10))

    def init_tray(self):
        tray_icon = self.qt_app.style().standardIcon(QStyle.SP_FileDialogInfoView)
        self.tray = QSystemTrayIcon(tray_icon, self.qt_app)
        self.tray.setToolTip("Writing Assistant 실행 중")
        self.tray.activated.connect(self.handle_tray_activation)

        menu = QMenu()
        show_action = QAction("열기")
        quit_action = QAction("종료")

        show_action.triggered.connect(self.show_panel)
        quit_action.triggered.connect(self.quit_app)

        menu.addAction(show_action)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.show()

    def start(self):
        self.reset_session_state()
        self.show_panel()

        clipboard_thread = threading.Thread(
            target=self.run_monitor,
            args=(self.startup_clipboard_text,),
            daemon=True,
        )
        clipboard_thread.start()

        realtime_thread = threading.Thread(
            target=self.run_realtime_monitor,
            daemon=True,
        )
        realtime_thread.start()

        sys.exit(self.qt_app.exec_())

    def run_monitor(self, initial_text):
        def callback(text):
            self.signals.text_signal.emit(
                {
                    "source": "clipboard",
                    "window_title": "",
                    "text": text,
                }
            )

        monitor_clipboard(callback, initial_text=initial_text)

    def run_realtime_monitor(self):
        def callback(event):
            self.signals.text_signal.emit(event)

        monitor_realtime_text(callback)

    def handle_input_event(self, event):
        if not isinstance(event, dict):
            return

        source = event.get("source", "")
        if source != self.active_input_mode:
            return

        self.panel.set_active_window_title(event.get("window_title", ""))
        text = event.get("text", "")
        if source == "realtime" and not text:
            self.last_input = ""
            self.panel.show_text_unavailable_placeholder()
            return

        if not text or text == self.last_input:
            return

        self.last_input = text
        self.panel.set_original_text(text)
        self.run_spell_check()

    def reset_session_state(self):
        self.last_input = ""
        self.panel.reset_text_tab()
        self.panel.clear_spell_result()
        self.panel.clear_summary_result()
        self.panel.clear_tone_result()
        self.panel.set_active_window_title("")

    def copy_result(self):
        text = self.panel.get_current_text()
        if text:
            pyperclip.copy(text)

    def show_panel(self):
        self.panel.showNormal()
        self.panel.show()
        self.panel.raise_()
        self.panel.activateWindow()

    def handle_tray_activation(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_panel()

    def run_spell_check(self):
        if not self.last_input:
            return
        result = self.analyzer.analyze_spelling(self.last_input)
        self.panel.set_spell_result(result)

    def run_summary(self):
        if not self.last_input:
            return
        result = self.analyzer.analyze_summary(self.last_input)
        self.panel.set_summary_result(result)

    def run_evaluation(self):
        if not self.last_input:
            return
        result = self.analyzer.analyze_evaluation(self.last_input)
        self.panel.set_evaluation_score(result)

    def run_title_recommendation(self):
        if not self.last_input:
            return
        result = self.analyzer.analyze_title_recommendation(self.last_input)
        self.panel.set_title_recommendation(result)

    def run_tone_change(self):
        if not self.last_input:
            return
        tone = self.panel.tone_input.text().strip()
        result = self.analyzer.analyze_tone_change(self.last_input, tone)
        self.panel.set_tone_result(result)

    def save_settings(self):
        self.settings["default_dark_mode"] = self.panel.get_default_dark_mode_checked()
        self.settings["input_mode"] = self.panel.get_input_mode()
        save_app_settings(self.settings)
        self.panel.set_default_dark_mode_checked(self.settings["default_dark_mode"])
        self.panel.set_input_mode(self.settings["input_mode"])
        mode_changed = self.active_input_mode != self.settings["input_mode"]
        self.active_input_mode = self.settings["input_mode"]
        if self.active_input_mode != "realtime":
            self.panel.set_active_window_title("")
        if mode_changed:
            self.reset_session_state()
        self.panel.show_settings_saved_notice()

    def quit_app(self):
        self.reset_session_state()
        self.tray.hide()
        self.qt_app.quit()

import os

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from config import PRESETS, ROOT

STATE_COLORS = {
    "loading": QColor(200, 180, 60),
    "idle": QColor(120, 160, 220),
    "recording": QColor(220, 60, 60),
    "processing": QColor(240, 150, 40),
    "error": QColor(150, 40, 40),
}

STATE_LABELS = {
    "loading": "loading models...",
    "idle": "idle — tap mic button or hold F9",
    "recording": "recording",
    "processing": "processing",
    "error": "error (see log)",
}


def _dot_icon(color: QColor) -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QColor(0, 0, 0, 0))
    p.setBrush(color)
    p.drawEllipse(8, 8, 48, 48)
    p.end()
    return QIcon(pm)


class Tray(QObject):
    """System tray icon. set_state()/notify() are thread-safe via signals."""

    _stateSig = Signal(str)
    _notifySig = Signal(str)
    _attachSig = Signal(object)

    def __init__(self, on_quit):
        super().__init__()
        self._icons = {state: _dot_icon(c) for state, c in STATE_COLORS.items()}
        self.icon = QSystemTrayIcon(self._icons["loading"])
        self.icon.setToolTip("Prompt Wizard — loading...")

        self._menu = QMenu()
        for label, target in (
            ("Open config", ROOT / "config.yaml"),
            ("Edit rewrite prompt", ROOT / "prompts" / "rewrite_system.md"),
            ("Open log", ROOT / "logs" / "prompt-wizard.log"),
        ):
            action = QAction(label, self._menu)
            action.triggered.connect(lambda _=False, t=target: os.startfile(t))
            self._menu.addAction(action)
        self._sep = self._menu.addSeparator()
        quit_action = QAction("Quit", self._menu)
        quit_action.triggered.connect(on_quit)
        self._menu.addAction(quit_action)
        self.icon.setContextMenu(self._menu)

        self._stateSig.connect(self._apply_state)
        self._notifySig.connect(self._show_message)
        self._attachSig.connect(self._apply_attach)
        self.icon.show()

    def attach(self, controls: dict):
        """Add wizard-dependent menu items once the app has finished loading.

        controls: {"preset": str, "set_preset": fn(name),
                   "startup_enabled": fn() -> bool, "set_startup": fn(bool)}
        Thread-safe.
        """
        self._attachSig.emit(controls)

    def _apply_attach(self, c: dict):
        preset_menu = QMenu("Style preset", self._menu)
        group = QActionGroup(preset_menu)
        group.setExclusive(True)
        for name in PRESETS:
            action = QAction(name.capitalize(), preset_menu)
            action.setCheckable(True)
            action.setChecked(name == c["preset"])
            action.triggered.connect(lambda _=False, n=name: c["set_preset"](n))
            group.addAction(action)
            preset_menu.addAction(action)
        self._menu.insertMenu(self._sep, preset_menu)

        startup_action = QAction("Start with Windows", self._menu)
        startup_action.setCheckable(True)
        startup_action.setChecked(c["startup_enabled"]())
        startup_action.triggered.connect(lambda checked: c["set_startup"](checked))
        self._menu.insertAction(self._sep, startup_action)

    def set_state(self, state: str):
        self._stateSig.emit(state)

    def notify(self, message: str):
        self._notifySig.emit(message)

    def _apply_state(self, state: str):
        self.icon.setIcon(self._icons[state])
        self.icon.setToolTip(f"Prompt Wizard — {STATE_LABELS[state]}")

    def _show_message(self, message: str):
        self.icon.showMessage("Prompt Wizard", message, self.icon.icon(), 4000)

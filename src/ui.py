import math

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QApplication, QWidget

DOT_COLORS = {
    "recording": QColor(255, 92, 92),
    "processing": QColor(255, 178, 77),
    "done": QColor(99, 214, 139),
    "error": QColor(255, 92, 92),
}

BAR_TOP = QColor(122, 162, 255)
BAR_BOTTOM = QColor(181, 122, 255)

N_BARS = 18
BAR_W = 3.0
BAR_GAP = 4.5


class Bubble(QWidget):
    """Small glassy speech-bubble popup shown while dictating.

    Never takes focus, so the paste target keeps it. Public set_state()
    is thread-safe (routed through a signal to the UI thread).
    """

    W, H = 320, 74
    _stateSig = Signal(str, str)

    def __init__(self):
        super().__init__(
            None,
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.resize(self.W, self.H)

        self._state = "hidden"
        self._label = ""
        self._phase = 0.0
        self._level = 0.0
        self._level_source = lambda: 0.0
        self._bars = [0.1] * N_BARS

        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)

        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setEasingCurve(QEasingCurve.OutCubic)

        self._stateSig.connect(self._apply_state)

    # -- public, callable from any thread --------------------------------

    def set_state(self, state: str, label: str = ""):
        self._stateSig.emit(state, label)

    def set_level_source(self, fn):
        """fn() -> current mic RMS level, read by the UI timer."""
        self._level_source = fn

    # -- UI thread --------------------------------------------------------

    def _apply_state(self, state: str, label: str):
        self._state = state
        self._label = label
        self._hide_timer.stop()
        if state == "hidden":
            self._fade_out()
            return
        if not self.isVisible():
            self._place()
            self.setWindowOpacity(0.0)
            self.show()
            self._animate_opacity(1.0, 160)
            self._timer.start()
        if state == "done":
            self._hide_timer.start(1000)
        elif state == "error":
            self._hide_timer.start(2000)
        self.update()

    def _place(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.center().x() - self.W // 2,
            screen.bottom() - self.H - 28,
        )

    def _animate_opacity(self, end: float, ms: int):
        self._fade.stop()
        self._fade.setDuration(ms)
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(end)
        self._fade.start()

    def _fade_out(self):
        self._animate_opacity(0.0, 280)
        QTimer.singleShot(300, self._finish_hide)

    def _finish_hide(self):
        if self._fade.endValue() == 0.0:
            self._timer.stop()
            self.hide()
            self._state = "hidden"

    def _tick(self):
        self._phase += 0.22
        if self._state == "recording":
            raw = min(1.0, float(self._level_source()) * 14.0)
            # fast attack, slow release, so the wave feels alive
            self._level = max(raw, self._level * 0.88)
            for i in range(N_BARS):
                ripple = 0.4 + 0.6 * abs(math.sin(self._phase * 0.9 + i * 0.62))
                target = 0.12 + 0.88 * self._level * ripple
                self._bars[i] += (target - self._bars[i]) * 0.45
        elif self._state == "processing":
            for i in range(N_BARS):
                self._bars[i] = 0.22 + 0.42 * (
                    0.5 + 0.5 * math.sin(self._phase - i * 0.55)
                )
        else:  # done / error: let the wave settle
            for i in range(N_BARS):
                self._bars[i] += (0.1 - self._bars[i]) * 0.25
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        pill = QRectF(6, 5, self.W - 12, self.H - 22)
        radius = pill.height() / 2
        path = QPainterPath()
        path.addRoundedRect(pill, radius, radius)

        # speech-bubble tail, flowing out of the bottom
        cx = pill.center().x()
        tail = QPainterPath()
        tail.moveTo(cx - 11, pill.bottom() - 2)
        tail.quadTo(cx - 2, pill.bottom() + 13, cx + 9, pill.bottom() - 2)
        path = path.united(tail)

        glass = QLinearGradient(0, pill.top(), 0, pill.bottom())
        glass.setColorAt(0.0, QColor(44, 48, 66, 214))
        glass.setColorAt(1.0, QColor(22, 24, 36, 236))
        p.fillPath(path, glass)
        p.setPen(QPen(QColor(255, 255, 255, 52), 1.2))
        p.drawPath(path)

        # top inner highlight for the glassy sheen
        sheen = QLinearGradient(pill.left(), 0, pill.right(), 0)
        sheen.setColorAt(0.0, QColor(255, 255, 255, 0))
        sheen.setColorAt(0.5, QColor(255, 255, 255, 60))
        sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(QPen(sheen, 1))
        p.drawLine(int(pill.left()) + 24, int(pill.top()) + 2,
                   int(pill.right()) - 24, int(pill.top()) + 2)

        # state dot, pulsing
        dot = DOT_COLORS.get(self._state, QColor(140, 140, 150))
        pulse = 0.65 + 0.35 * math.sin(self._phase * 1.6)
        dot_c = QColor(dot)
        dot_c.setAlpha(int(140 + 100 * pulse) if self._state == "recording" else 230)
        p.setPen(Qt.NoPen)
        p.setBrush(dot_c)
        dot_y = pill.center().y()
        p.drawEllipse(QRectF(pill.left() + 18, dot_y - 4.5, 9, 9))

        # label
        p.setPen(QColor(255, 255, 255, 205))
        p.setFont(QFont("Segoe UI", 10))
        p.drawText(
            QRectF(pill.left() + 34, pill.top(), 84, pill.height()),
            Qt.AlignVCenter | Qt.AlignLeft,
            self._label,
        )

        # waveform bars
        bars_w = N_BARS * BAR_W + (N_BARS - 1) * BAR_GAP
        x = pill.right() - 22 - bars_w
        max_h = pill.height() - 26
        grad = QLinearGradient(0, dot_y - max_h / 2, 0, dot_y + max_h / 2)
        grad.setColorAt(0.0, BAR_TOP)
        grad.setColorAt(1.0, BAR_BOTTOM)
        p.setBrush(grad)
        for i, v in enumerate(self._bars):
            h = max(3.0, v * max_h)
            p.drawRoundedRect(
                QRectF(x + i * (BAR_W + BAR_GAP), dot_y - h / 2, BAR_W, h),
                BAR_W / 2, BAR_W / 2,
            )

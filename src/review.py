import threading

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

STYLE = """
QLabel { color: rgba(255, 255, 255, 170); font: 10pt 'Segoe UI'; background: transparent; }
QTextEdit {
    background: rgba(255, 255, 255, 14); color: rgba(255, 255, 255, 235);
    border: 1px solid rgba(255, 255, 255, 35); border-radius: 10px;
    padding: 8px; font: 11pt 'Segoe UI'; selection-background-color: rgba(122, 162, 255, 140);
}
QPushButton {
    background: rgba(255, 255, 255, 18); color: rgba(255, 255, 255, 220);
    border: 1px solid rgba(255, 255, 255, 40); border-radius: 8px;
    padding: 6px 16px; font: 10pt 'Segoe UI';
}
QPushButton:hover { background: rgba(122, 162, 255, 60); }
QPushButton:disabled { color: rgba(255, 255, 255, 90); }
QPushButton#primary { background: rgba(122, 162, 255, 95); border-color: rgba(122, 162, 255, 150); }
QPushButton#primary:hover { background: rgba(122, 162, 255, 140); }
"""


class ReviewWindow(QWidget):
    """Glassy review card: edit the rewritten prompt before pasting it.

    show_review() is thread-safe. Callbacks are set via configure():
      do_paste(text, hwnd) — paste into the original target window
      do_retry(transcript) -> str — blocking rewrite, called off the UI thread
    """

    _showSig = Signal(str, str, int)
    _retryDoneSig = Signal(str)
    W, H = 620, 340

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(self.W, self.H)
        self.setStyleSheet(STYLE)

        self._transcript = ""
        self._rewrite = ""
        self._hwnd = 0
        self._showing_raw = False
        self.do_paste = lambda text, hwnd: None
        self.do_retry = lambda transcript: transcript

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 16, 22, 18)
        root.setSpacing(10)

        header = QHBoxLayout()
        self._title = QLabel("Review prompt")
        header.addWidget(self._title)
        header.addStretch()
        hint = QLabel("Ctrl+Enter to paste · Esc to dismiss")
        header.addWidget(hint)
        root.addLayout(header)

        self._edit = QTextEdit()
        root.addWidget(self._edit, 1)

        row = QHBoxLayout()
        self._raw_btn = QPushButton("Show raw")
        self._raw_btn.clicked.connect(self._toggle_raw)
        row.addWidget(self._raw_btn)
        self._retry_btn = QPushButton("Retry")
        self._retry_btn.clicked.connect(self._retry)
        row.addWidget(self._retry_btn)
        row.addStretch()
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(self._copy)
        row.addWidget(copy_btn)
        paste_btn = QPushButton("Paste")
        paste_btn.setObjectName("primary")
        paste_btn.clicked.connect(self._paste)
        row.addWidget(paste_btn)
        root.addLayout(row)

        QShortcut(QKeySequence("Ctrl+Return"), self, self._paste)
        QShortcut(QKeySequence("Escape"), self, self.hide)

        self._showSig.connect(self._apply_show)
        self._retryDoneSig.connect(self._apply_retry)

    def configure(self, do_paste, do_retry):
        self.do_paste = do_paste
        self.do_retry = do_retry

    # -- public, callable from any thread --------------------------------

    def show_review(self, transcript: str, rewrite: str, hwnd: int = 0):
        self._showSig.emit(transcript, rewrite, hwnd)

    # -- UI thread --------------------------------------------------------

    def _apply_show(self, transcript: str, rewrite: str, hwnd: int):
        self._transcript = transcript
        self._rewrite = rewrite
        self._hwnd = hwnd
        self._showing_raw = False
        self._raw_btn.setText("Show raw")
        self._retry_btn.setEnabled(True)
        self._edit.setPlainText(rewrite)
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.center().x() - self.W // 2, screen.bottom() - self.H - 40)
        self.show()
        self.raise_()
        self.activateWindow()
        self._edit.setFocus()

    def _toggle_raw(self):
        if self._showing_raw:
            self._edit.setPlainText(self._rewrite)
            self._raw_btn.setText("Show raw")
        else:
            self._rewrite = self._edit.toPlainText()  # keep edits
            self._edit.setPlainText(self._transcript)
            self._raw_btn.setText("Show rewrite")
        self._showing_raw = not self._showing_raw

    def _retry(self):
        self._retry_btn.setEnabled(False)
        self._retry_btn.setText("Retrying...")
        transcript = self._transcript

        def run():
            try:
                self._retryDoneSig.emit(self.do_retry(transcript))
            except Exception as e:
                self._retryDoneSig.emit(f"(retry failed: {e})")

        threading.Thread(target=run, daemon=True).start()

    def _apply_retry(self, text: str):
        self._rewrite = text
        self._showing_raw = False
        self._raw_btn.setText("Show raw")
        self._edit.setPlainText(text)
        self._retry_btn.setEnabled(True)
        self._retry_btn.setText("Retry")

    def _copy(self):
        QApplication.clipboard().setText(self._edit.toPlainText())
        self.hide()

    def _paste(self):
        text = self._edit.toPlainText()
        self.hide()
        self.do_paste(text, self._hwnd)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        card = QRectF(4, 4, self.W - 8, self.H - 8)
        path = QPainterPath()
        path.addRoundedRect(card, 18, 18)
        glass = QLinearGradient(0, card.top(), 0, card.bottom())
        glass.setColorAt(0.0, QColor(44, 48, 66, 232))
        glass.setColorAt(1.0, QColor(22, 24, 36, 244))
        p.fillPath(path, glass)
        p.setPen(QPen(QColor(255, 255, 255, 52), 1.2))
        p.drawPath(path)
        sheen = QLinearGradient(card.left(), 0, card.right(), 0)
        sheen.setColorAt(0.0, QColor(255, 255, 255, 0))
        sheen.setColorAt(0.5, QColor(255, 255, 255, 55))
        sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(QPen(sheen, 1))
        p.drawLine(int(card.left()) + 30, int(card.top()) + 2,
                   int(card.right()) - 30, int(card.top()) + 2)

import threading

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000  # what Whisper expects


class Recorder:
    """Captures mic audio between start() and stop()."""

    def __init__(self):
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self.level = 0.0  # RMS of the latest chunk, for UI visualization

    def start(self):
        with self._lock:
            if self._stream is not None:
                return
            self._chunks = []
            self.level = 0.0
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                callback=self._callback,
            )
            self._stream.start()

    def _callback(self, indata, frames, time_info, status):
        self._chunks.append(indata.copy())
        self.level = float(np.sqrt(np.mean(indata ** 2)))

    def stop(self) -> np.ndarray:
        """Stop recording and return mono float32 audio at 16 kHz."""
        with self._lock:
            if self._stream is None:
                return np.zeros(0, dtype=np.float32)
            self._stream.stop()
            self._stream.close()
            self._stream = None
            if not self._chunks:
                return np.zeros(0, dtype=np.float32)
            return np.concatenate(self._chunks)[:, 0]

    @property
    def recording(self) -> bool:
        return self._stream is not None

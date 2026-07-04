import os
import sys
from pathlib import Path

import numpy as np
import truststore

# Use the Windows certificate store for TLS (model downloads fail otherwise
# on machines where AV/proxy software intercepts HTTPS)
truststore.inject_into_ssl()


def _add_nvidia_dll_dirs():
    """Make pip-installed cuBLAS/cuDNN DLLs visible to ctranslate2 on Windows.

    ctranslate2 resolves these via the PATH search, so add_dll_directory
    alone is not enough.
    """
    base = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    for sub in ("cublas", "cudnn"):
        bin_dir = base / sub / "bin"
        if bin_dir.exists():
            os.add_dll_directory(str(bin_dir))
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ["PATH"]


class Transcriber:
    def __init__(self, model_name: str = "small.en", device: str = "auto"):
        from faster_whisper import WhisperModel

        _add_nvidia_dll_dirs()
        self.device = None
        if device in ("auto", "cuda"):
            try:
                self.model = WhisperModel(model_name, device="cuda", compute_type="float16")
                # Force CUDA init now so failures happen at startup, not first use
                list(self.model.transcribe(np.zeros(1600, dtype=np.float32))[0])
                self.device = "cuda"
            except Exception as e:
                if device == "cuda":
                    raise
                print(f"  GPU unavailable ({type(e).__name__}), using CPU: {e}")
        if self.device is None:
            self.model = WhisperModel(model_name, device="cpu", compute_type="int8")
            self.device = "cpu"

    def transcribe(self, audio: np.ndarray) -> str:
        segments, _info = self.model.transcribe(audio, beam_size=5, vad_filter=True)
        return " ".join(seg.text.strip() for seg in segments).strip()

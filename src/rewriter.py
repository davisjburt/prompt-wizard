import os
import shutil
import subprocess
import time
from pathlib import Path

import requests


def ensure_server(url: str, timeout: float = 30.0) -> bool:
    """Return True if the Ollama server is up, starting it if needed."""
    def alive() -> bool:
        try:
            return requests.get(f"{url}/api/version", timeout=2).ok
        except requests.ConnectionError:
            return False

    if alive():
        return True

    exe = shutil.which("ollama")
    if not exe:
        for candidate in (
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
            Path(os.environ.get("ProgramFiles", "")) / "Ollama" / "ollama.exe",
        ):
            if candidate.exists():
                exe = str(candidate)
                break
    if not exe:
        return False

    subprocess.Popen(
        [exe, "serve"],
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if alive():
            return True
        time.sleep(0.5)
    return False


class Rewriter:
    def __init__(self, url: str, model: str, system_prompt: str,
                 keep_alive: str = "30m", temperature: float = 0.3):
        self.url = url.rstrip("/")
        self.model = model
        self.system_prompt = system_prompt
        self.keep_alive = keep_alive
        self.temperature = temperature

    def check(self):
        """Raise if the Ollama server isn't reachable or the model is missing."""
        r = requests.get(f"{self.url}/api/tags", timeout=5)
        r.raise_for_status()
        names = [m["name"] for m in r.json().get("models", [])]
        if not any(n == self.model or n.split(":")[0] == self.model for n in names):
            raise RuntimeError(
                f"Model '{self.model}' not found in Ollama. Available: {', '.join(names) or 'none'}"
            )

    def warm_up(self):
        """Load the model into VRAM so the first real request is fast."""
        r = requests.post(
            f"{self.url}/api/generate",
            json={"model": self.model, "prompt": "", "stream": False,
                  "keep_alive": self.keep_alive},
            timeout=120,
        )
        r.raise_for_status()

    def rewrite(self, transcript: str) -> str:
        r = requests.post(
            f"{self.url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": transcript},
                ],
                "stream": False,
                "keep_alive": self.keep_alive,
                "options": {"temperature": self.temperature},
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["message"]["content"].strip()

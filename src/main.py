import json
import sys
import threading
import time
import winsound

import keyboard
from PySide6.QtWidgets import QApplication

from config import ROOT, load_config, load_system_prompt
from injector import copy_text, paste_text
from recorder import SAMPLE_RATE, Recorder
from rewriter import Rewriter, ensure_server
from transcriber import Transcriber
from tray import Tray
from ui import Bubble

# Windows consoles default to cp1252, which can't print ● or many
# characters Whisper produces (curly quotes etc.)
if sys.stdout:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LOG_FILE = ROOT / "logs" / "prompt-wizard.log"
HISTORY_FILE = ROOT / "logs" / "history.jsonl"


def log(msg: str):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}" if msg.strip() else msg
    if sys.stdout:  # absent when launched with pythonw
        print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


class PromptWizard:
    def __init__(self, tray: Tray, bubble: Bubble):
        self.tray = tray
        self.bubble = bubble
        self.cfg = load_config()
        log("Prompt Wizard starting...")

        log(f"  Loading Whisper ({self.cfg['whisper']['model']})...")
        self.transcriber = Transcriber(
            self.cfg["whisper"]["model"], self.cfg["whisper"]["device"]
        )
        log(f"  Whisper ready on {self.transcriber.device.upper()}")

        o = self.cfg["ollama"]
        if not ensure_server(o["url"]):
            raise RuntimeError(
                f"Ollama server is not reachable at {o['url']} and could not be started."
            )
        self.rewriter = Rewriter(
            o["url"], o["model"], load_system_prompt(),
            o.get("keep_alive", "30m"), o.get("temperature", 0.3),
        )
        self.rewriter.check()
        log(f"  Loading {o['model']} into Ollama...")
        self.rewriter.warm_up()
        log("  Ollama ready")

        self.recorder = Recorder()
        self.bubble.set_level_source(lambda: self.recorder.level)
        self.raw_mode = False
        self._busy = threading.Lock()
        self._toggle_armed = True

    def beep(self, freq: int, ms: int = 120):
        if self.cfg.get("sounds", True):
            threading.Thread(target=winsound.Beep, args=(freq, ms), daemon=True).start()

    def on_press(self, raw: bool):
        if self.recorder.recording or self._busy.locked():
            return
        self.raw_mode = raw
        try:
            self.recorder.start()
        except Exception as e:
            log(f"  ERROR: could not start recording: {e}")
            self.tray.notify(f"Could not start recording: {e}")
            self.tray.set_state("error")
            self.bubble.set_state("error", "No mic")
            self.beep(220, 400)
            return
        self.tray.set_state("recording")
        self.bubble.set_state("recording", "Listening" + (" ·raw" if raw else ""))
        self.beep(880)
        log(f"● Recording{' (raw)' if raw else ''}...")

    def on_release(self):
        if not self.recorder.recording:
            return
        audio = self.recorder.stop()
        self.beep(660)
        duration = len(audio) / SAMPLE_RATE
        if duration < self.cfg.get("min_duration", 0.5):
            log(f"  Too short ({duration:.2f}s), ignored")
            self.tray.set_state("idle")
            self.bubble.set_state("hidden")
            return
        self.tray.set_state("processing")
        self.bubble.set_state("processing", "Polishing")
        threading.Thread(target=self.process, args=(audio, self.raw_mode), daemon=True).start()

    def process(self, audio, raw: bool):
        with self._busy:
            try:
                t0 = time.perf_counter()
                transcript = self.transcriber.transcribe(audio)
                t1 = time.perf_counter()
                if not transcript:
                    log("  (heard nothing)")
                    self.bubble.set_state("error", "Heard nothing")
                    self.beep(220, 300)
                    return
                log(f"  Heard   ({t1 - t0:.1f}s): {transcript}")

                if raw:
                    result = transcript
                else:
                    result = self.rewriter.rewrite(transcript)
                    t2 = time.perf_counter()
                    log(f"  Rewrote ({t2 - t1:.1f}s): {result}")
                    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                        f.write(json.dumps({
                            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "transcript": transcript,
                            "rewrite": result,
                        }, ensure_ascii=False) + "\n")

                if self.cfg.get("output", "paste") == "paste":
                    paste_text(result)
                    self.bubble.set_state("done", "Pasted")
                else:
                    copy_text(result)
                    self.bubble.set_state("done", "Copied")
                self.beep(1320)
                log(f"  Done in {time.perf_counter() - t0:.1f}s total")
            except Exception as e:
                log(f"  ERROR: {e}")
                self.tray.notify(f"Processing failed: {e}")
                self.bubble.set_state("error", "Error")
                self.beep(220, 400)
            finally:
                self.tray.set_state("idle")

    def on_toggle(self, combo_has_win: bool):
        if not self._toggle_armed:  # ignore keyboard auto-repeat while held
            return
        self._toggle_armed = False
        if combo_has_win:
            # The suppressed combo leaves a bare Win press behind, which would
            # open the Start menu; a dummy key while Win is down cancels that.
            keyboard.press_and_release("f24")
        if self.recorder.recording:
            self.on_release()
        else:
            self.on_press(raw=False)

    def _resolve_key(self, key):
        # config value may be a key name ("f9") or a scan code (91)
        return key if isinstance(key, int) else str(key)

    def register_hotkeys(self):
        hotkey = self._resolve_key(self.cfg["hotkey"])
        keyboard.on_press_key(hotkey, lambda e: self.on_press(raw=False), suppress=True)
        keyboard.on_release_key(hotkey, lambda e: self.on_release(), suppress=True)
        log(f"Hold [{self.cfg['hotkey']}] to dictate a prompt.")

        raw_key = self.cfg.get("raw_hotkey")
        if raw_key:
            rk = self._resolve_key(raw_key)
            keyboard.on_press_key(rk, lambda e: self.on_press(raw=True), suppress=True)
            keyboard.on_release_key(rk, lambda e: self.on_release(), suppress=True)
            log(f"Hold [{raw_key}] for raw dictation (no rewrite).")

        toggle = self.cfg.get("toggle_hotkey")
        if toggle:
            has_win = "windows" in toggle
            keyboard.add_hotkey(toggle, lambda: self.on_toggle(has_win), suppress=True)
            last_key = toggle.split("+")[-1].strip()
            keyboard.on_release_key(
                last_key, lambda e: setattr(self, "_toggle_armed", True)
            )
            log(f"Tap [{toggle}] (mic button) to start/stop dictation.")

        log("Ready. Quit from the tray icon (or Ctrl+C in this window).")


def main():
    LOG_FILE.parent.mkdir(exist_ok=True)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    tray = Tray(on_quit=app.quit)
    bubble = Bubble()

    def start_logic():
        try:
            wizard = PromptWizard(tray, bubble)
            wizard.register_hotkeys()
            tray.set_state("idle")
        except Exception as e:
            log(f"STARTUP FAILED: {e}")
            tray.set_state("error")
            tray.notify(f"Startup failed: {e}")

    threading.Thread(target=start_logic, daemon=True).start()
    app.exec()
    keyboard.unhook_all()


if __name__ == "__main__":
    main()

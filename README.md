# Prompt Wizard

Voice-to-prompt tool: hold a hotkey, speak your rambling thoughts, release — a local
Ollama model rewrites them into a clean, structured LLM prompt and pastes it at your
cursor. Fully local: audio and text never leave your machine.

## Run it

- **`run_hidden.vbs`** — no console, just a tray icon (recommended for daily use).
  Activity is logged to `logs\prompt-wizard.log`.
- **`run.bat`** — same thing with a console window showing live transcripts.

While dictating, a small glassy speech bubble floats above the taskbar with a live
waveform of your voice — it shows Listening → Polishing → Pasted, then fades away.
It never takes focus, so your text lands where your cursor was.

The tray icon shows state: yellow = loading, blue = idle, red = recording,
orange = processing. Right-click it to open the config, edit the rewrite prompt,
view the log, or quit. If Ollama isn't running, the app starts it automatically.

- Tap the **mic/Copilot button** to start recording, tap again to stop → rewritten
  prompt pastes into the focused window (the button sends Win+C, which is intercepted
  so Copilot doesn't open)
- Hold **F9**, speak, release → same thing, push-to-talk style
- Hold **F10** → raw dictation (no rewrite), like a plain dictation tool
- Beeps: high = recording started, mid = processing, higher = pasted, low = error

## Configure

Everything lives in [config.yaml](config.yaml): hotkeys, Whisper model size, Ollama
model, paste vs copy-only. The rewrite style is controlled by
[prompts/rewrite_system.md](prompts/rewrite_system.md) — edit it freely, no code changes needed.

### Binding a special key (e.g. mic/Copilot button)

Run `.venv\Scripts\python.exe tools\detect_key.py`, press the key once, and note the
`name` / `scan_code` it prints. Put either value in `config.yaml` as `hotkey`
(scan codes go in as plain numbers, no quotes).

## Requirements

- Windows, Python 3.12 venv in `.venv` (`pip install -r requirements.txt`)
- [Ollama](https://ollama.com) running with the model from `config.yaml` pulled
- NVIDIA GPU recommended (works on CPU, slower)

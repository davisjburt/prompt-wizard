# Prompt Wizard — Plan

## Concept

A Wispr Flow–style dictation tool with a twist: instead of just transcribing what you say, it runs your speech through a **local Ollama model** that rewrites it into a clear, well-structured LLM prompt, then drops the result into whatever app you're focused on (Claude, ChatGPT, Cursor, a terminal, anywhere).

**The loop:**

```
Hold hotkey → speak → release
      │
      ▼
1. Record mic audio
      ▼
2. Local speech-to-text (Whisper, on-device)
      ▼
3. Ollama rewrites transcript → structured prompt
      ▼
4. Result pasted into the active window (or shown for review first)
```

Everything runs locally. No audio or text leaves your machine.

---

## Example of what it does

**You say (rambling):**
> "uh okay so I want you to look at my python script and like there's this bug where when I pass in a list it sometimes crashes, I think it's something with empty lists maybe? fix it and also can you add some tests"

**It outputs:**
> Review my Python script for a bug: passing a list sometimes causes a crash, possibly related to empty-list handling.
>
> 1. Identify the root cause of the crash.
> 2. Fix the bug.
> 3. Add unit tests covering the fix, including the empty-list edge case.

---

## Architecture

### Stack recommendation: Python

Fastest path to a working tool, and every piece has a mature Python library. A Tauri/Electron app can come later if you want a polished UI, but the MVP doesn't need one.

| Component | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Best ecosystem for audio + ML glue code |
| Hotkey listener | `keyboard` (or `pynput`) | Global hotkeys on Windows, simple API |
| Audio capture | `sounddevice` | Low-latency mic recording to numpy buffer |
| Speech-to-text | `faster-whisper` | Local Whisper, 4x faster than openai-whisper, runs well on CPU or GPU |
| Rewrite engine | Ollama HTTP API (`localhost:11434`) | You already run Ollama; simple REST call |
| Output injection | `pyperclip` + simulated Ctrl+V | Most reliable cross-app text insertion on Windows |
| Feedback | System tray icon + sound cues (`pystray`, `winsound`) | Know when it's listening / thinking / done |

### Component breakdown

```
prompt-wizard/
├── src/
│   ├── main.py            # Entry point, wires everything together
│   ├── hotkey.py          # Global hotkey: push-to-talk (hold) or toggle
│   ├── recorder.py        # Mic capture → WAV/numpy buffer
│   ├── transcriber.py     # faster-whisper wrapper
│   ├── rewriter.py        # Ollama client + the rewrite system prompt
│   ├── injector.py        # Clipboard save → paste → clipboard restore
│   ├── tray.py            # Tray icon showing state (idle/recording/processing)
│   └── config.py          # Settings loader
├── config.yaml            # Hotkey, models, mode, style options
├── prompts/
│   └── rewrite_system.md  # The system prompt (editable without touching code)
└── PLAN.md
```

---

## Key design decisions (your input wanted)

### 1. Interaction model: push-to-talk vs toggle
- **Push-to-talk (recommended):** hold a key (e.g. `F9` or `Ctrl+Win`), speak, release. Matches Wispr Flow's feel, no "forgot to stop recording" failure mode.
- **Toggle:** tap to start, tap to stop. Better for long dictations.
- Could support both — hold for push-to-talk, double-tap for toggle.

### 2. Direct paste vs review window
- **Direct paste:** release key → ~2–5s later the rewritten prompt appears at your cursor. Fastest, but you don't see it before it lands.
- **Review popup:** small always-on-top window shows the rewritten prompt with *Paste / Copy / Retry / Raw transcript* buttons. Safer while you're tuning the rewrite quality.
- **Recommendation:** build direct paste as the default, with a config flag for review mode. During early use you'll want review mode on to judge rewrite quality.

### 3. Whisper model size (latency vs accuracy)
| Model | VRAM/RAM | Speed | Accuracy |
|---|---|---|---|
| `tiny.en` | ~1 GB | near-instant | okay, misses jargon |
| `base.en` | ~1 GB | very fast | decent |
| `small.en` | ~2 GB | fast | good — **recommended start** |
| `medium.en` | ~5 GB | slower | very good |

If you have an NVIDIA GPU, `small.en` transcribes a 15-second clip in well under a second. What GPU does your machine have? That also affects the Ollama model choice below.

### 4. Ollama model for rewriting
The rewrite task is easy for modern small models — it's reformatting, not reasoning. Smaller = faster = the whole loop feels snappy.
- **`llama3.1:8b`** or **`qwen2.5:7b`** — great quality, ~1–3s on GPU
- **`llama3.2:3b`** or **`qwen2.5:3b`** — nearly as good for this task, faster, fine on CPU
- Configurable in `config.yaml`; easy to A/B test.

Note: Whisper and the Ollama model share GPU memory if both are on GPU — with 8 GB VRAM, `small.en` + a 7B quantized model fits fine.

### 5. The rewrite system prompt (the heart of the product)
Draft v1 (lives in `prompts/rewrite_system.md`, tweakable anytime):

```
You convert spoken, rambling dictation into a clear, effective prompt
for an LLM. Rules:
- Preserve ALL intent, requirements, and details the speaker mentioned.
- Remove filler ("um", "like", "you know"), false starts, and repetition.
- Structure multi-part requests as numbered steps or bullets.
- Make ambiguous references explicit where the speech makes the meaning
  clear; NEVER invent requirements the speaker didn't state.
- Keep the speaker's first-person voice ("Fix my script", not
  "The user wants...").
- Output ONLY the rewritten prompt. No preamble, no explanation,
  no quotes around it.
```

Possible later addition: **style presets** switchable by voice command or hotkey — e.g. "coding mode" (adds "include file paths, expected behavior, error output" framing) vs "writing mode" vs "raw mode" (skip Ollama entirely, pure dictation like actual Wispr Flow).

### 6. Escape hatch: raw transcription mode
Sometimes you'll want your literal words (dictating a message, not a prompt). A second hotkey (or modifier) that skips the Ollama step turns this into a plain local Wispr Flow clone for free. Cheap to build, big usability win.

---

## Build phases

### Phase 1 — Core pipeline proof (get the loop working end-to-end)
- Record from mic on hotkey hold, stop on release
- Transcribe with faster-whisper
- Send to Ollama with the rewrite system prompt
- Copy result to clipboard + auto-paste into focused window
- Console logging of raw transcript vs rewrite (for judging quality)
- **Deliverable:** working script you launch from a terminal

### Phase 2 — Usability
- System tray icon with state colors (idle / recording / processing)
- Sound cues on record start/stop and paste
- `config.yaml`: hotkey, Whisper model, Ollama model, paste vs review mode
- Raw-transcription mode hotkey
- Clipboard preserved and restored after paste
- Graceful errors (Ollama not running, no mic) with a tray notification

### Phase 3 — Quality & polish
- Review popup window (paste / retry / edit / show raw transcript)
- Style presets (coding / writing / general)
- Start-with-Windows option, single-exe packaging (PyInstaller)
- Optional: streaming transcription while you speak to cut latency
- Optional: history log of transcript→rewrite pairs to tune the system prompt

---

## Expected latency (the make-or-break metric)

For a ~10-second utterance, release-to-paste:

| Step | GPU | CPU only |
|---|---|---|
| Whisper `small.en` | ~0.5 s | ~3–5 s |
| Ollama 7B rewrite | ~1–2 s | ~5–15 s |
| Paste | instant | instant |
| **Total** | **~2–3 s** | **~10–20 s** |

GPU makes this feel magical; CPU-only makes it feel sluggish but usable with 3B models. Hardware info will let me tune the defaults.

---

## Locked decisions (2026-07-04)

1. **Hardware:** RTX 3060 Ti (8 GB), i5-11600K, 32 GB RAM → Whisper `small.en` on CUDA + `qwen2.5:7b-instruct` on GPU. Measured: ~3 s Whisper load, ~2.8 s rewrite.
2. **Interaction:** push-to-talk. Default F9; target is the keyboard's mic/Copilot button once detected via `tools/detect_key.py`.
3. **Output:** direct paste.
4. **Raw dictation mode:** included in Phase 1 (hold F10).

## Status

- ✅ Phase 1 built and pipeline verified end-to-end (Whisper on CUDA, Ollama rewrite on GPU, ~3 s total processing)
- ✅ Mic/Copilot button bound: it emits Win+C, so it works as a **toggle** (tap to start, tap to stop — it can't be held). Win+C is suppressed so Copilot doesn't open; a dummy F24 press stops the stray Win from opening Start. Verified via injected key events; user should confirm no Copilot/Start flicker with the physical button.
- ✅ UTF-8 console fix (Whisper output can contain non-cp1252 characters)
- ⬜ Live voice test by the user (transcription + rewrite quality)
- ✅ Phase 2: tray icon with state colors + menu (config / rewrite prompt / log / quit), file logging, windowless launch via `run_hidden.vbs`, Ollama auto-start, graceful error notifications
- ✅ Glassy bubble UI (Wispr Flow style): frameless translucent pill with speech-bubble tail above the taskbar, live mic-level waveform, state dot + label (Listening / Polishing / Pasted / Error), fade in/out, never steals focus. Frontend moved from pystray to PySide6 (Qt) — tray is now QSystemTrayIcon, models load in a background thread so the tray appears instantly.
- ⬜ Phase 3 remaining (review popup, style presets, start-with-Windows, packaging)

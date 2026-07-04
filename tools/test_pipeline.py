"""Sanity-check the pipeline without a microphone: Whisper init + Ollama rewrite."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import load_config, load_system_prompt
from rewriter import Rewriter
from transcriber import Transcriber

cfg = load_config()

t0 = time.perf_counter()
tr = Transcriber(cfg["whisper"]["model"], cfg["whisper"]["device"])
print(f"Whisper loaded on {tr.device.upper()} in {time.perf_counter() - t0:.1f}s")

o = cfg["ollama"]
rw = Rewriter(o["url"], o["model"], load_system_prompt(), o["keep_alive"], o["temperature"])
rw.check()
rw.warm_up()

sample = (
    "uh okay so I want you to look at my python script and like there's this bug "
    "where when I pass in a list it sometimes crashes, I think it's something with "
    "empty lists maybe? fix it and also can you add some tests"
)
t1 = time.perf_counter()
result = rw.rewrite(sample)
print(f"\nRewrite took {time.perf_counter() - t1:.1f}s")
print(f"\nINPUT:\n{sample}\n\nOUTPUT:\n{result}")

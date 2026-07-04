import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

PRESETS = ("general", "coding", "writing")


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_system_prompt(preset: str = "general") -> str:
    base = (ROOT / "prompts" / "rewrite_system.md").read_text(encoding="utf-8").strip()
    preset_file = ROOT / "prompts" / "presets" / f"{preset}.md"
    if preset != "general" and preset_file.exists():
        base += "\n\n" + preset_file.read_text(encoding="utf-8").strip()
    return base


def save_preset(preset: str):
    """Persist the preset choice in config.yaml without touching its comments."""
    cfg_file = ROOT / "config.yaml"
    text = cfg_file.read_text(encoding="utf-8")
    if re.search(r"(?m)^preset:", text):
        text = re.sub(r"(?m)^preset:.*$", f"preset: {preset}", text)
    else:
        text += f"\npreset: {preset}\n"
    cfg_file.write_text(text, encoding="utf-8")

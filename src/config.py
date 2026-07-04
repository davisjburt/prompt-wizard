from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_system_prompt() -> str:
    return (ROOT / "prompts" / "rewrite_system.md").read_text(encoding="utf-8").strip()

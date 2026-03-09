"""
Saved ratio presets (name -> ratio string like "0.708:1").
Stored in ratio_presets.json next to the app; defaults include "manga".
"""
import json
from pathlib import Path

PRESETS_FILENAME = "ratio_presets.json"
DEFAULT_PRESETS = {"manga": "0.708:1"}


def get_presets_path(base_dir: Path) -> Path:
    return base_dir / PRESETS_FILENAME


def load_presets(base_dir: Path) -> dict[str, str]:
    path = get_presets_path(base_dir)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_PRESETS)


def save_presets(base_dir: Path, presets: dict[str, str]) -> None:
    path = get_presets_path(base_dir)
    path.write_text(json.dumps(presets, indent=2), encoding="utf-8")


def load_presets_list(base_dir: Path) -> list[dict[str, str]]:
    """List of {"name": ..., "ratio": ...} for templates, sorted by name."""
    presets = load_presets(base_dir)
    return sorted([{"name": k, "ratio": v} for k, v in presets.items()], key=lambda x: x["name"].lower())

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


APP_NAME = "EmptySearcher"


@dataclass
class AppConfig:
    root_folder: str = ""
    last_selected_folder: str = ""
    ignored_file_patterns: list[str] = field(default_factory=lambda: ["Thumbs.db", ".DS_Store", "desktop.ini"])
    ignored_dir_patterns: list[str] = field(default_factory=list)
    excluded_patterns: list[str] = field(default_factory=list)


def get_config_dir() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_NAME


def get_config_path() -> Path:
    return get_config_dir() / "config.json"


def load_config() -> AppConfig:
    path = get_config_path()
    if not path.exists():
        return AppConfig()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AppConfig()

    config = AppConfig()
    config.root_folder = str(data.get("root_folder", config.root_folder))
    config.last_selected_folder = str(data.get("last_selected_folder", config.last_selected_folder))
    config.ignored_file_patterns = _normalize_patterns(data.get("ignored_file_patterns", config.ignored_file_patterns))
    config.ignored_dir_patterns = _normalize_patterns(data.get("ignored_dir_patterns", config.ignored_dir_patterns))
    config.excluded_patterns = _normalize_patterns(data.get("excluded_patterns", config.excluded_patterns))
    return config


def save_config(config: AppConfig) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")


def _normalize_patterns(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized

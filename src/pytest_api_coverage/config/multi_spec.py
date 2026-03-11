"""Multi-spec configuration loader."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from pytest_api_coverage.config.settings import SpecConfig


def load_multi_spec_config(path: Path) -> tuple[list[SpecConfig], dict[str, Any]]:
    """Load multi-spec config from YAML or JSON file.

    Returns (valid_specs, top_level_settings).
    Warns and skips invalid entries. Returns ([], {}) on parse failure.
    """
    try:
        text = path.read_text(encoding="utf-8")
        if path.suffix in (".yaml", ".yml"):
            raw = yaml.safe_load(text)
        else:
            raw = json.loads(text)
    except Exception as e:
        print(f"\n[api-coverage] Warning: Failed to load config {path}: {e}")
        return [], {}

    if not isinstance(raw, dict):
        print(f"\n[api-coverage] Warning: Config file {path} is not a mapping, skipping")
        return [], {}

    top_level = {k: v for k, v in raw.items() if k != "specs"}
    entries = raw.get("specs") or []
    specs: list[SpecConfig] = []

    for entry in entries:
        spec = _parse_spec_entry(entry)
        if spec is not None:
            specs.append(spec)

    return specs, top_level


def _parse_spec_entry(entry: dict[str, Any]) -> SpecConfig | None:
    """Parse a single spec entry dict. Returns None and warns on validation failure."""
    name = entry.get("name")
    if not name:
        print("\n[api-coverage] Warning: Spec entry missing 'name', skipping")
        return None
    urls = entry.get("urls")
    if not urls:
        print(f"\n[api-coverage] Warning: Spec '{name}' has empty or missing 'urls', skipping")
        return None
    path = entry.get("path")
    url = entry.get("url")
    if path and url:
        print(f"\n[api-coverage] Warning: Spec '{name}' has both 'path' and 'url', skipping")
        return None
    return SpecConfig(name=name, urls=urls, path=path, url=url)


def _discover_config_file(rootpath: Path) -> Path | None:
    """Probe rootpath for coverage-config.yaml then coverage-config.json.

    Returns Path to discovered file, or None if neither exists.
    Warns and returns YAML if both exist.
    """
    yaml_candidate = rootpath / "coverage-config.yaml"
    json_candidate = rootpath / "coverage-config.json"
    if yaml_candidate.exists() and json_candidate.exists():
        print(
            "\n[api-coverage] Warning: Both coverage-config.yaml and coverage-config.json found; using YAML"
        )
        return yaml_candidate
    if yaml_candidate.exists():
        return yaml_candidate
    if json_candidate.exists():
        return json_candidate
    return None

"""Multi-spec configuration loader."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml

from pytest_api_coverage.config.settings import SpecConfig

logger = logging.getLogger("pytest_api_coverage")


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
        logger.warning("Failed to load config %s: %s", path, e, exc_info=True)
        return [], {}

    if not isinstance(raw, dict):
        logger.warning("Config file %s is not a mapping, skipping", path)
        return [], {}

    top_level = {k: v for k, v in raw.items() if k != "specs"}
    entries = raw.get("specs") or []
    specs: list[SpecConfig] = []

    for index, entry in enumerate(entries):
        spec = _parse_spec_entry(entry, index)
        if spec is not None:
            specs.append(spec)

    return specs, top_level


def _parse_spec_entry(entry: dict[str, Any], index: int) -> SpecConfig | None:
    """Parse a single spec entry dict. Returns None and warns on validation failure."""
    name = entry.get("name")
    if not name:
        logger.warning("Spec entry #%d missing 'name', skipping", index)
        return None
    api_urls = entry.get("api_urls")
    if not api_urls:
        logger.warning("Spec '%s' has empty or missing 'api_urls', skipping", name)
        return None
    if not isinstance(api_urls, list):
        logger.warning(
            "Spec '%s' has invalid 'api_urls': expected a list, got %s. "
            "Use YAML list syntax:\n  api_urls:\n    - \"https://...\"",
            name,
            type(api_urls).__name__,
        )
        return None
    swagger_path = entry.get("swagger_path")
    swagger_url = entry.get("swagger_url")
    if swagger_path and swagger_url:
        logger.warning("Spec '%s' has both 'swagger_path' and 'swagger_url', skipping", name)
        return None
    return SpecConfig(name=name, api_urls=api_urls, swagger_path=swagger_path, swagger_url=swagger_url)


def _discover_config_file(rootpath: Path) -> Path | None:
    """Probe rootpath for coverage-config.yaml, coverage-config.yml, or coverage-config.json.

    Candidates are checked in that order of preference. Returns the Path to the
    first discovered file, or None if none exist. Warns if more than one candidate
    is present and returns the highest-priority match.
    """
    yaml_candidate = rootpath / "coverage-config.yaml"
    yml_candidate = rootpath / "coverage-config.yml"
    json_candidate = rootpath / "coverage-config.json"

    existing = [p for p in [yaml_candidate, yml_candidate, json_candidate] if p.exists()]
    if not existing:
        return None
    if len(existing) > 1:
        logger.warning("Multiple coverage config files found; using %s", existing[0])
        return existing[0]
    return existing[0]

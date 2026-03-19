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
    api_filters = entry.get("api_filters")
    if not api_filters:
        logger.warning("Spec '%s' has empty or missing 'api_filters', skipping", name)
        return None
    if not isinstance(api_filters, list):
        logger.warning(
            "Spec '%s' has invalid 'api_filters': expected a list, got %s. "
            "Use YAML list syntax:\n  api_filters:\n    - \"https://...\"",
            name,
            type(api_filters).__name__,
        )
        return None
    swagger_path = entry.get("swagger_path")
    swagger_url = entry.get("swagger_url")
    if swagger_path and swagger_url:
        logger.warning("Spec '%s' has both 'swagger_path' and 'swagger_url', skipping", name)
        return None
    return SpecConfig(name=name, api_filters=api_filters, swagger_path=swagger_path, swagger_url=swagger_url)



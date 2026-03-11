"""Unit tests for SpecConfig dataclass."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytest_api_coverage.config.settings import SpecConfig


class TestSpecConfigCreation:
    """Tests for SpecConfig construction."""

    def test_spec_config_local_path(self) -> None:
        """SpecConfig with local path sets path as Path, url as None."""
        sc = SpecConfig(name="auth", urls=["https://auth.example.com"], path="./specs/auth.yaml")
        assert sc.name == "auth"
        assert sc.urls == ["https://auth.example.com"]
        assert sc.path == Path("./specs/auth.yaml")
        assert sc.url is None

    def test_spec_config_remote_url(self) -> None:
        """SpecConfig with remote url sets url, path as None."""
        sc = SpecConfig(
            name="orders",
            urls=["https://orders.example.com"],
            url="https://orders.example.com/openapi.json",
        )
        assert sc.url == "https://orders.example.com/openapi.json"
        assert sc.path is None

    def test_spec_config_both_path_and_url_raises(self) -> None:
        """SpecConfig with both path and url raises ValueError."""
        with pytest.raises(ValueError):
            SpecConfig(
                name="x",
                urls=["https://x.com"],
                path="./x.yaml",
                url="https://x.com/openapi.json",
            )

    def test_spec_config_missing_name_raises(self) -> None:
        """SpecConfig with empty name raises ValueError."""
        with pytest.raises(ValueError):
            SpecConfig(name="", urls=["https://x.com"], path="./x.yaml")

    def test_spec_config_empty_urls_raises(self) -> None:
        """SpecConfig with empty urls list raises ValueError."""
        with pytest.raises(ValueError):
            SpecConfig(name="auth", urls=[], path="./auth.yaml")


class TestSpecConfigFromDict:
    """Tests for SpecConfig.from_dict()."""

    def test_spec_config_missing_urls_raises(self) -> None:
        """from_dict without urls key raises ValueError."""
        with pytest.raises(ValueError):
            SpecConfig.from_dict({"name": "auth", "path": "./auth.yaml"})

    def test_spec_config_from_dict_local(self) -> None:
        """from_dict with local path produces correct SpecConfig."""
        sc = SpecConfig.from_dict(
            {"name": "auth", "path": "./auth.yaml", "urls": ["https://auth.example.com"]}
        )
        assert sc.name == "auth"
        assert sc.path == Path("./auth.yaml")
        assert sc.urls == ["https://auth.example.com"]
        assert sc.url is None

    def test_spec_config_from_dict_remote(self) -> None:
        """from_dict with remote url produces correct SpecConfig."""
        sc = SpecConfig.from_dict(
            {
                "name": "orders",
                "url": "https://orders.example.com/openapi.json",
                "urls": ["https://orders.example.com"],
            }
        )
        assert sc.name == "orders"
        assert sc.url == "https://orders.example.com/openapi.json"
        assert sc.path is None


class TestSpecConfigToDict:
    """Tests for SpecConfig.to_dict() and round-trips."""

    def test_spec_config_to_dict_round_trip(self) -> None:
        """to_dict() produces dict that reconstructs via from_dict() correctly."""
        sc = SpecConfig(
            name="auth",
            urls=["https://auth.example.com"],
            path="./specs/auth.yaml",
        )
        round_tripped = SpecConfig.from_dict(sc.to_dict())
        assert round_tripped == sc

    def test_spec_config_to_dict_path_is_str(self) -> None:
        """to_dict()['path'] is str not Path (required for xdist JSON serialisation)."""
        sc = SpecConfig(
            name="auth",
            urls=["https://auth.example.com"],
            path="./specs/auth.yaml",
        )
        result = sc.to_dict()
        assert isinstance(result["path"], str)
        assert not isinstance(result["path"], Path)

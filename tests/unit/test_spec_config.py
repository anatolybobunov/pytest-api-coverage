"""Unit tests for SpecConfig dataclass."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytest_api_coverage.config.settings import SpecConfig


class TestSpecConfigCreation:
    """Tests for SpecConfig construction."""

    def test_spec_config_local_path(self) -> None:
        """SpecConfig with local swagger_path sets swagger_path as Path, swagger_url as None."""
        sc = SpecConfig(name="auth", api_urls=["https://auth.example.com"], swagger_path="./specs/auth.yaml")
        assert sc.name == "auth"
        assert sc.api_urls == ["https://auth.example.com"]
        assert sc.swagger_path == Path("./specs/auth.yaml")
        assert sc.swagger_url is None

    def test_spec_config_remote_url(self) -> None:
        """SpecConfig with remote swagger_url sets swagger_url, swagger_path as None."""
        sc = SpecConfig(
            name="orders",
            api_urls=["https://orders.example.com"],
            swagger_url="https://orders.example.com/openapi.json",
        )
        assert sc.swagger_url == "https://orders.example.com/openapi.json"
        assert sc.swagger_path is None

    def test_spec_config_both_path_and_url_raises(self) -> None:
        """SpecConfig with both swagger_path and swagger_url raises ValueError."""
        with pytest.raises(ValueError):
            SpecConfig(
                name="x",
                api_urls=["https://x.com"],
                swagger_path="./x.yaml",
                swagger_url="https://x.com/openapi.json",
            )

    def test_spec_config_missing_name_raises(self) -> None:
        """SpecConfig with empty name raises ValueError."""
        with pytest.raises(ValueError):
            SpecConfig(name="", api_urls=["https://x.com"], swagger_path="./x.yaml")

    def test_spec_config_empty_api_urls_raises(self) -> None:
        """SpecConfig with empty api_urls list raises ValueError."""
        with pytest.raises(ValueError):
            SpecConfig(name="auth", api_urls=[], swagger_path="./auth.yaml")


class TestSpecConfigFromDict:
    """Tests for SpecConfig.from_dict()."""

    def test_spec_config_missing_api_urls_raises(self) -> None:
        """from_dict without api_urls key raises ValueError."""
        with pytest.raises(ValueError):
            SpecConfig.from_dict({"name": "auth", "swagger_path": "./auth.yaml"})

    def test_spec_config_from_dict_local(self) -> None:
        """from_dict with local swagger_path produces correct SpecConfig."""
        sc = SpecConfig.from_dict(
            {"name": "auth", "swagger_path": "./auth.yaml", "api_urls": ["https://auth.example.com"]}
        )
        assert sc.name == "auth"
        assert sc.swagger_path == Path("./auth.yaml")
        assert sc.api_urls == ["https://auth.example.com"]
        assert sc.swagger_url is None

    def test_spec_config_from_dict_remote(self) -> None:
        """from_dict with remote swagger_url produces correct SpecConfig."""
        sc = SpecConfig.from_dict(
            {
                "name": "orders",
                "swagger_url": "https://orders.example.com/openapi.json",
                "api_urls": ["https://orders.example.com"],
            }
        )
        assert sc.name == "orders"
        assert sc.swagger_url == "https://orders.example.com/openapi.json"
        assert sc.swagger_path is None


class TestSpecConfigToDict:
    """Tests for SpecConfig.to_dict() and round-trips."""

    def test_spec_config_to_dict_round_trip(self) -> None:
        """to_dict() produces dict that reconstructs via from_dict() correctly."""
        sc = SpecConfig(
            name="auth",
            api_urls=["https://auth.example.com"],
            swagger_path="./specs/auth.yaml",
        )
        round_tripped = SpecConfig.from_dict(sc.to_dict())
        assert round_tripped == sc

    def test_spec_config_to_dict_path_is_str(self) -> None:
        """to_dict()['swagger_path'] is str not Path (required for xdist JSON serialisation)."""
        sc = SpecConfig(
            name="auth",
            api_urls=["https://auth.example.com"],
            swagger_path="./specs/auth.yaml",
        )
        result = sc.to_dict()
        assert isinstance(result["swagger_path"], str)
        assert not isinstance(result["swagger_path"], Path)

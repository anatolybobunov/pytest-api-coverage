"""Unit tests for SpecConfig dataclass."""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given

from pytest_api_coverage.config.settings import SpecConfig

from strategies import valid_name, valid_path_str, valid_spec_config, valid_url, valid_url_list


class TestSpecConfigCreation:
    """Tests for SpecConfig construction."""

    def test_spec_config_local_path(self) -> None:
        """SpecConfig with local swagger_path sets swagger_path as Path, swagger_url as None."""
        sc = SpecConfig(name="auth", api_filters=["https://auth.example.com"], swagger_path="./specs/auth.yaml")
        assert sc.name == "auth"
        assert sc.api_filters == ["https://auth.example.com"]
        assert sc.swagger_path == Path("./specs/auth.yaml")
        assert sc.swagger_url is None

    def test_spec_config_remote_url(self) -> None:
        """SpecConfig with remote swagger_url sets swagger_url, swagger_path as None."""
        sc = SpecConfig(
            name="orders",
            api_filters=["https://orders.example.com"],
            swagger_url="https://orders.example.com/openapi.json",
        )
        assert sc.swagger_url == "https://orders.example.com/openapi.json"
        assert sc.swagger_path is None

    def test_spec_config_both_path_and_url_raises(self) -> None:
        """SpecConfig with both swagger_path and swagger_url raises ValueError."""
        with pytest.raises(ValueError):
            SpecConfig(
                name="x",
                api_filters=["https://x.com"],
                swagger_path="./x.yaml",
                swagger_url="https://x.com/openapi.json",
            )

    def test_spec_config_missing_name_raises(self) -> None:
        """SpecConfig with empty name raises ValueError."""
        with pytest.raises(ValueError):
            SpecConfig(name="", api_filters=["https://x.com"], swagger_path="./x.yaml")

    def test_spec_config_empty_api_urls_raises(self) -> None:
        """SpecConfig with empty api_urls list raises ValueError."""
        with pytest.raises(ValueError):
            SpecConfig(name="auth", api_filters=[], swagger_path="./auth.yaml")


class TestSpecConfigFromDict:
    """Tests for SpecConfig.from_dict()."""

    def test_spec_config_missing_api_urls_raises(self) -> None:
        """from_dict without api_urls key raises ValueError."""
        with pytest.raises(ValueError):
            SpecConfig.from_dict({"name": "auth", "swagger_path": "./auth.yaml"})

    def test_spec_config_from_dict_local(self) -> None:
        """from_dict with local swagger_path produces correct SpecConfig."""
        sc = SpecConfig.from_dict(
            {"name": "auth", "swagger_path": "./auth.yaml", "api_filters": ["https://auth.example.com"]}
        )
        assert sc.name == "auth"
        assert sc.swagger_path == Path("./auth.yaml")
        assert sc.api_filters == ["https://auth.example.com"]
        assert sc.swagger_url is None

    def test_spec_config_from_dict_remote(self) -> None:
        """from_dict with remote swagger_url produces correct SpecConfig."""
        sc = SpecConfig.from_dict(
            {
                "name": "orders",
                "swagger_url": "https://orders.example.com/openapi.json",
                "api_filters": ["https://orders.example.com"],
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
            api_filters=["https://auth.example.com"],
            swagger_path="./specs/auth.yaml",
        )
        round_tripped = SpecConfig.from_dict(sc.to_dict())
        assert round_tripped == sc

    def test_spec_config_to_dict_path_is_str(self) -> None:
        """to_dict()['swagger_path'] is str not Path (required for xdist JSON serialisation)."""
        sc = SpecConfig(
            name="auth",
            api_filters=["https://auth.example.com"],
            swagger_path="./specs/auth.yaml",
        )
        result = sc.to_dict()
        assert isinstance(result["swagger_path"], str)
        assert not isinstance(result["swagger_path"], Path)


class TestSpecConfigProperties:
    """Property-based tests for SpecConfig using Hypothesis."""

    @given(valid_spec_config())
    def test_round_trip(self, sc: SpecConfig) -> None:
        """from_dict(to_dict()) round-trip preserves the SpecConfig."""
        assert SpecConfig.from_dict(sc.to_dict()) == sc

    @given(valid_spec_config())
    def test_to_dict_json_safe(self, sc: SpecConfig) -> None:
        """to_dict() swagger_path is str or None, never a Path object."""
        d = sc.to_dict()
        assert isinstance(d["swagger_path"], (str, type(None)))
        assert not isinstance(d["swagger_path"], Path)

    @given(valid_url_list)
    def test_empty_name_always_raises(self, api_filters: list[str]) -> None:
        """SpecConfig with name='' always raises ValueError regardless of other args."""
        with pytest.raises(ValueError):
            SpecConfig(name="", api_filters=api_filters)

    @given(valid_name)
    def test_empty_api_urls_always_raises(self, name: str) -> None:
        """SpecConfig with api_filters=[] always raises ValueError regardless of name."""
        with pytest.raises(ValueError):
            SpecConfig(name=name, api_filters=[])

    @given(valid_name, valid_url_list, valid_path_str, valid_url)
    def test_both_path_and_url_always_raises(self, name: str, api_filters: list[str], path_str: str, url: str) -> None:
        """SpecConfig with both swagger_path and swagger_url always raises ValueError."""
        with pytest.raises(ValueError):
            SpecConfig(name=name, api_filters=api_filters, swagger_path=path_str, swagger_url=url)

    @given(valid_path_str)
    def test_path_normalization(self, path_str: str) -> None:
        """String swagger_path is always normalized to a Path instance."""
        sc = SpecConfig(name="test", api_filters=["https://example.com"], swagger_path=path_str)
        assert isinstance(sc.swagger_path, Path)

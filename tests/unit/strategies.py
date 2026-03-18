"""Shared Hypothesis strategies for pytest-api-coverage unit tests."""

from __future__ import annotations

from hypothesis import strategies as st

from pytest_api_coverage.config.settings import CoverageSettings, SpecConfig

# Non-empty text: letters, digits, hyphens, 1-50 chars
valid_name = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-",
    min_size=1,
    max_size=50,
)

# HTTP/HTTPS URL matching common domain patterns
valid_url = st.from_regex(
    r"https?://[a-z][a-z0-9.-]{1,20}\.[a-z]{2,6}(/[a-z0-9._-]*)*",
    fullmatch=True,
)

# Non-empty list of URLs, 1-5 items
valid_url_list = st.lists(valid_url, min_size=1, max_size=5)

# Relative file path string ending in .yaml or .json
valid_path_str = st.from_regex(
    r"[a-z][a-z0-9_/-]{0,20}\.(yaml|json)",
    fullmatch=True,
)


@st.composite
def valid_spec_config(draw: st.DrawFn) -> SpecConfig:
    """Build a valid SpecConfig with either swagger_path or swagger_url (never both)."""
    name = draw(valid_name)
    api_urls = draw(valid_url_list)
    choice = draw(st.sampled_from(["path", "url", "none"]))
    if choice == "path":
        swagger_path: str | None = draw(valid_path_str)
        swagger_url: str | None = None
    elif choice == "url":
        swagger_path = None
        swagger_url = draw(valid_url)
    else:
        swagger_path = None
        swagger_url = None
    return SpecConfig(name=name, api_urls=api_urls, swagger_path=swagger_path, swagger_url=swagger_url)


@st.composite
def valid_coverage_settings(draw: st.DrawFn) -> CoverageSettings:
    """Build a valid CoverageSettings using URL-based spec only (no filesystem access)."""
    spec = draw(st.one_of(st.none(), valid_url))
    output_dir = draw(
        st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_",
            min_size=1,
            max_size=30,
        )
    )
    formats = draw(st.frozensets(st.sampled_from(["html", "json", "csv"]), min_size=1))
    split_by_origin = draw(st.booleans())
    specs = draw(st.lists(valid_spec_config(), min_size=0, max_size=3))
    return CoverageSettings(
        spec=spec,
        output_dir=output_dir,
        formats=set(formats),
        split_by_origin=split_by_origin,
        specs=specs,
    )

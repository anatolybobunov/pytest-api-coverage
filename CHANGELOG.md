# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-14

### Added

- Initial release of `pytest-api-coverage` plugin
- HTTP interception adapters for `requests` and `httpx` libraries
- Swagger/OpenAPI specification parser supporting:
  - Swagger 2.0 and OpenAPI 3.x formats
  - JSON and YAML file formats
  - Local files and remote URLs
- Coverage collector with thread-safe request recording
- Coverage reporter with path pattern matching (e.g., `/users/{id}` matches `/users/123`)
- Report writers for multiple output formats:
  - JSON — machine-readable format with full details
  - CSV — spreadsheet-friendly format
  - HTML — visual report with sortable tables and color-coded coverage
- pytest-xdist support for parallel test execution
- Multi-spec support: track coverage across multiple API specifications simultaneously
  - `--coverage-spec` CLI flag with optional `--coverage-spec-name`
  - `coverage-config.yaml` config file for declarative multi-spec setup
- `MultiSpecOrchestrator` to manage lifecycle of multiple specs and reporters
- Origin filtering options:
  - `--coverage-strip-prefix` — strip path prefixes before matching
  - `--coverage-split-by-origin` — produce separate coverage report per origin
- Terminal summary output with per-spec coverage statistics
- Activity indicator displayed during `pytest_sessionstart`
- `pytest.exit()` raised on critical CLI configuration errors instead of silently skipping

### Changed

- Renamed CLI options and `SpecConfig` fields for consistency across the public API
- Extracted `normalize_origin` helper to `utils.py`, eliminating duplication across adapters
- Moved terminal summary functions to a dedicated `terminal.py` module
- Replaced ad-hoc `if`-chains for report writers with `WriterProtocol` and `WRITER_REGISTRY`
- Added public `specs` and `reporters` properties to `Orchestrator`; removed direct private-attribute access from plugin and terminal code
- Replaced `print()` warnings with `logging.getLogger('pytest_api_coverage')` throughout

### Fixed

- Spec load failures are now shown in the terminal summary instead of silently ignored
- Warning displayed when a Swagger spec is loaded but zero HTTP requests were captured
- Missing `--coverage-spec-name` now emits a warning instead of raising a raw `ValueError`
- Terminal summary shows the actual output file path instead of a hardcoded fallback
- `output_dir` and `formats` from `coverage-config.yaml` top-level keys are now applied correctly
- Multi-spec terminal summary correctly uses configured formats when building per-spec filenames

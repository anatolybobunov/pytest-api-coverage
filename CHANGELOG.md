# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-12-16

### Added

- Initial release of pytest-api-coverage plugin
- HTTP interception adapters for `requests` and `httpx` libraries
- Swagger/OpenAPI specification parser supporting:
  - Swagger 2.0 and OpenAPI 3.x formats
  - JSON and YAML file formats
  - Local files and remote URLs
- Coverage collector with thread-safe request recording
- Coverage reporter with path pattern matching (e.g., `/users/{id}` matches `/users/123`)
- Report writers for multiple formats:
  - JSON - machine-readable format with full details
  - CSV - spreadsheet-friendly format
  - HTML - visual report with color-coded coverage
- pytest-xdist support for parallel test execution
- Origin filtering options:
  - `--coverage-base-url` - filter to single origin
  - `--coverage-include-base-url` - allowlist of origins
  - `--coverage-strip-prefix` - strip path prefixes
  - `--coverage-split-by-origin` - separate coverage per origin
- Terminal summary output showing coverage statistics
- Grouped endpoints by path in reports (path-first hierarchy)
# pytest-api-coverage

[![PyPI version](https://img.shields.io/pypi/v/pytest-api-coverage.svg)](https://pypi.org/project/pytest-api-coverage/)
[![Python versions](https://img.shields.io/pypi/pyversions/pytest-api-coverage.svg)](https://pypi.org/project/pytest-api-coverage/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/anatolybobunov/pytest-api-coverage/actions/workflows/ci.yml/badge.svg)](https://github.com/anatolybobunov/pytest-api-coverage/actions/workflows/ci.yml)

Pytest plugin for API test coverage analysis. Automatically intercepts HTTP requests during test execution, compares them against Swagger/OpenAPI specifications, and generates detailed coverage reports.

## Features

- **Automatic HTTP interception** — captures requests from `requests` and `httpx` libraries
- **Swagger/OpenAPI support** — works with JSON and YAML specifications (local files or URLs)
- **Multiple report formats** — JSON, CSV, and HTML reports
- **pytest-xdist support** — works with parallel test execution
- **Origin filtering** — filter coverage by base URL or allowlist
- **Split by origin** — generate separate coverage per API origin

## Documentation

- [Installation Guide](docs/installation.md)
- [Usage Guide](docs/usage.md)
- [Architecture](docs/architecture.md)

## Installation

```bash
pip install pytest-api-coverage
```

See [docs/installation.md](docs/installation.md) for detailed installation instructions.

## Quick Start

```bash
# Basic usage with local spec file
pytest tests/ --coverage-spec=swagger.json

# Using remote spec URL
pytest tests/ --coverage-spec=https://api.example.com/swagger.json

# With parallel execution
pytest tests/ -n 4 --coverage-spec=swagger.json
```

## How It Works

1. **Interception**: The plugin monkeypatches `requests.Session.request`, `httpx.Client.request`, and `httpx.AsyncClient.request` to capture all HTTP requests made during test execution.

2. **Collection**: Each request is recorded with HTTP method, URL, path, response status code, and test name.

3. **Matching**: After tests complete, recorded requests are matched against endpoints defined in the Swagger/OpenAPI specification using path pattern matching (e.g., `/users/{id}` matches `/users/123`).

4. **Reporting**: Coverage reports are generated showing which endpoints were hit, response codes received, and overall coverage percentage.

## CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--coverage-spec` | — | Path to a local OpenAPI/Swagger spec file or URL |
| `--coverage-spec-name` | — | Label for the spec; used as filename prefix in reports |
| `--coverage-spec-api-url` | — | Base URL(s) to match requests against (repeatable) |
| `--coverage-config` | — | Path to YAML/JSON config file for multi-spec mode |
| `--coverage-output` | `api-coverage-report` | Output directory for reports |
| `--coverage-format` | `html` | Report formats (comma-separated). Use `all` for json,csv,html |
| `--coverage-strip-prefix` | — | Path prefixes to strip from request URLs (comma-separated) |
| `--coverage-split-by-origin` | `false` | Separate coverage per API origin |

See [docs/usage.md](docs/usage.md) for detailed usage examples.

## Development

```bash
# Install with dev dependencies
uv sync --group dev

# Run tests
uv run pytest tests/ -v

# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type checking
uv run ty check src/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## Build

The package uses [hatchling](https://hatch.pypa.io/) as its build backend.

```bash
# Build source distribution and wheel (recommended)
uv build

# Or using python -m build (requires the build package)
pip install build
python -m build
```

Build artifacts (`.tar.gz` and `.whl`) are placed in the `dist/` directory.

## License

MIT - see [LICENSE](LICENSE) for details.
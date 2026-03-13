# pytest-api-coverage

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

# Using spec URL
pytest tests/ --coverage-spec=https://api.example.com/swagger.json

# With parallel execution
pytest tests/ -n 4 --coverage-spec=swagger.json
```

## How It Works

1. **Interception**: The plugin monkeypatches `requests.Session.request` and `httpx.Client.request` to capture all HTTP requests made during test execution.

2. **Collection**: Each request is recorded with HTTP method, URL, path, response status code, and test name.

3. **Matching**: After tests complete, recorded requests are matched against endpoints defined in the Swagger/OpenAPI specification using path pattern matching (e.g., `/users/{id}` matches `/users/123`).

4. **Reporting**: Coverage reports are generated showing which endpoints were hit, response codes received, and overall coverage percentage.

## CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--coverage-spec` | — | **Required.** Path or URL to OpenAPI spec |
| `--coverage-output` | `coverage-output` | Output directory for reports |
| `--coverage-format` | `json,csv,html` | Report formats (comma-separated) |
| `--coverage-strip-prefix` | — | Path prefixes to strip (comma-separated) |
| `--coverage-split-by-origin` | `false` | Separate coverage per origin |
| `--coverage-config` | — | Multi-spec config file (YAML/JSON) |
| `--coverage-spec-name` | — | Spec name (with `--coverage-spec` + `--coverage-spec-api-url`) |
| `--coverage-spec-api-url` | — | API base URL(s) for the spec (repeatable) |

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
uv run mypy src/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## License

MIT - see [LICENSE](LICENSE) for details.
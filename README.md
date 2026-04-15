# pytest-api-coverage

[![PyPI version](https://img.shields.io/pypi/v/pytest-api-coverage.svg)](https://pypi.org/project/pytest-api-coverage/)
[![Python versions](https://img.shields.io/pypi/pyversions/pytest-api-coverage.svg)](https://pypi.org/project/pytest-api-coverage/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/anatolybobunov/pytest-api-coverage/actions/workflows/ci.yml/badge.svg)](https://github.com/anatolybobunov/pytest-api-coverage/actions/workflows/ci.yml)

Pytest plugin for API test coverage analysis. Automatically intercepts HTTP requests during test execution, compares them against OpenAPI specifications, and generates detailed coverage reports.

## Features

- **Automatic HTTP interception** — captures requests from `requests` and `httpx` libraries
- **Swagger/OpenAPI support** — works with JSON and YAML specifications (local files or URLs)
- **Multiple report formats** — JSON, CSV, and HTML reports
- **pytest-xdist support** — works with parallel test execution
- **Origin filtering** — filter coverage by base URL or allowlist
- **Split by origin** — generate separate coverage per API origin
- **Async support** — intercepts both `requests` and `httpx`, including async httpx clients
- **Multi-spec mode** — measure coverage across multiple APIs in a single test run

## Installation

Requires **Python 3.11+** and **pytest 7.0+**.

```bash
# If your project uses requests
pip install pytest-api-coverage[requests]

# If your project uses httpx
pip install pytest-api-coverage[httpx]

# If your project uses both
pip install pytest-api-coverage[requests,httpx]
```

See [Installation Guide](docs/installation.md) for details.

## Quick Start

> **Note:** The plugin does not activate by default. You must pass `--coverage-spec` or `--coverage-config` to enable it. Without these flags, pytest runs normally with no coverage overhead.

### 1. Single Spec (local file)

```bash
pytest tests/ --coverage-spec=api/swagger.yaml
```

The simplest way to start. Point the plugin at your local OpenAPI spec file (JSON or YAML). The plugin will intercept all HTTP requests made during tests and compare them against the spec.

### 2. Config File (one or many specs)

Create a config file `coverage-config.yaml`:

```yaml
specs:
  - name: users-api
    swagger_url: https://api.example.com/swagger.json
    api_filters:
      - https://api.example.com
```

Then run:

```bash
pytest tests/ --coverage-config=coverage-config.yaml
```

Use this approach when you have multiple APIs or want to store all settings in one file. The config file defines which specs to load, which URLs to track, and where to save reports.

The `--coverage-spec-name` flag is optional. Use it to run only one spec from the config:

```bash
pytest tests/ --coverage-config=coverage-config.yaml --coverage-spec-name=users-api
```

The `api_filters` field in the config file tells the plugin which HTTP requests belong to each spec. This is required in the config file. When using `--coverage-spec` without a config file, you can pass `--coverage-url-filter` on the CLI instead.

See [Configuration Reference](docs/configuration.md#multi-spec-configuration-file) for the full config file format.

### 3. Parallel Test Execution

```bash
pytest tests/ -n 4 --coverage-config=coverage-config.yaml
```

This runs tests in parallel across 4 workers while measuring API coverage. Requires [pytest-xdist](https://pypi.org/project/pytest-xdist/). The plugin coordinates between workers and combines results into a single report.

### Example Terminal Output

After the test run finishes, the plugin prints a summary to the terminal:

```
======================== API Coverage Summary (1 specs) ========================
users-api   12/20 endpoints   60.0%   45 req   users-api-coverage.html
TOTAL        12/20 endpoints   60.0%   45 req   3 unmatched
```

For detailed setup instructions, see [Installation](docs/installation.md). For all available options, see [Usage Guide](docs/usage.md).

## Documentation

| Guide | Description |
|---|---|
| [Installation](docs/installation.md) | Requirements, install options, verification |
| [Usage Guide](docs/usage.md) | CLI options and examples |
| [Configuration Reference](docs/configuration.md) | pytest.ini setup, multi-spec config |
| [Coverage Reports](docs/reports.md) | Report formats and result interpretation |
| [API Reference](docs/api-reference.md) | Public Python API for programmatic access |
| [Architecture](docs/architecture.md) | How the plugin works internally |
| [Troubleshooting](docs/troubleshooting.md) | Common issues and fixes |
| [Changelog](CHANGELOG.md) | Release history |
| [Contributing](CONTRIBUTING.md) | Development setup and guidelines |

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT — see [LICENSE](LICENSE) for details.

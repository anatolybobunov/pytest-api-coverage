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

```bash
# Basic usage with local spec file
pytest tests/ --coverage-spec=swagger.json

# Using remote spec URL
pytest tests/ --coverage-spec=https://api.example.com/swagger.json

# With parallel execution
pytest tests/ -n 4 --coverage-spec=swagger.json
```

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

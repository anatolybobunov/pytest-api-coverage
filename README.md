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

### 1. Using a Config File

```bash
pytest tests/ --coverage-config=coverage-config.yaml --coverage-spec-name={spec name from config}
```

Use this approach when you have multiple APIs or want to centralize settings in a config file. The plugin reads the OpenAPI specification paths, report formats, and other settings from your `coverage-config.yaml` file. 
See [Configuration Reference](docs/configuration.md#multi-spec-configuration-file) for the config file format.
This approach is recommended for continuous integration environments, since all settings are stored in your repository.

### 2. Testing with Remote Spec URL and Origin Filter

```bash
pytest tests/ \
  --coverage-spec={http or https url to the spec without auth} \
  --coverage-url-filter={part of url to filter}
```

Use this approach when you want to load the OpenAPI spec from a remote server and only capture requests that match a specific base URL. 
The `--coverage-url-filter` parameter helps you focus on one API when your tests make requests to multiple endpoints. 
This is useful in microservices environments where your tests talk to different services.
Note: The plugin cannot download the OpenAPI specification if the endpoint requires authentication.

### 3. Running with Config File and Parallel Tests

```bash
pytest tests/ -n 4 --coverage-config=coverage-config.yaml
```

This command runs your tests in parallel across 4 workers while measuring API coverage. The parallel execution with `pytest-xdist` makes your test suite faster without losing coverage insights. The plugin automatically coordinates between workers and combines results into a single report. Perfect for large test suites where speed matters.

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

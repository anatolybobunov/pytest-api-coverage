# Installation

## Requirements

- Python 3.11 or higher
- pytest 7.0.0 or higher

## Install from PyPI

```bash
pip install pytest-api-coverage
```

Or with uv:

```bash
uv add pytest-api-coverage
```

## Install from Source

### Using pip

```bash
pip install git+https://github.com/anatolybobunov/pytest-api-coverage.git
```

### Using uv

```bash
uv add git+https://github.com/anatolybobunov/pytest-api-coverage.git
```

### Local Development Install

```bash
# Clone repository
git clone https://github.com/anatolybobunov/pytest-api-coverage.git
cd pytest-api-coverage

# Install in editable mode
pip install -e .

# Or with uv
uv pip install -e .
```

## Dependencies

The plugin automatically installs the following dependencies:

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=7.0.0 | Test framework |
| pyyaml | >=6.0 | YAML parsing for swagger files |
| requests | >=2.28.0 | HTTP interception (optional) |
| httpx    | >=0.24.0 | Async HTTP interception (optional) |
| jinja2 | >=3.0.0 | HTML report templating |

> **Note:** `requests` and `httpx` are optional adapters. Install only what your test suite needs:
>
> ```bash
> # Enable requests support
> pip install pytest-api-coverage[requests]
>
> # Enable all adapters
> pip install pytest-api-coverage[all]
> ```

## Build Distribution Packages

To build wheel and sdist packages locally:

```bash
# Using hatch (matches the build backend)
pip install hatch
hatch build

# Or using the standard build frontend
pip install build
python -m build
```

Artifacts are placed in the `dist/` directory.

## Verify Installation

After installation, verify the plugin is available:

```bash
pytest --help | grep coverage-spec
```

You should see:

```
--coverage-spec=COVERAGE_SPEC  #  Path or URL to OpenAPI/Swagger spec
```

## Optional: pytest-xdist

For parallel test execution, install pytest-xdist:

```bash
pip install pytest-xdist
```

Then run tests with:

```bash
pytest tests/ -n 4 --coverage-spec=swagger.json
```
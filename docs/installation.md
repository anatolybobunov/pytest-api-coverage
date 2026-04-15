# Installation

## Requirements

- Python 3.11 or higher
- pytest 7.0.0 or higher

## Install from PyPI

Choose the extra matching the HTTP library your project uses:

```bash
# If your project uses requests
pip install pytest-api-coverage[requests]

# If your project uses httpx
pip install pytest-api-coverage[httpx]

# If your project uses both
pip install pytest-api-coverage[requests,httpx]
```

Or with uv:

```bash
uv add pytest-api-coverage[requests]
uv add pytest-api-coverage[httpx]
uv add pytest-api-coverage[requests,httpx]
```

## Install from Source

### Using pip

```bash
pip install "pytest-api-coverage[requests] @ git+https://github.com/anatolybobunov/pytest-api-coverage.git"
pip install "pytest-api-coverage[httpx] @ git+https://github.com/anatolybobunov/pytest-api-coverage.git"
```

### Using uv

```bash
uv add "pytest-api-coverage[requests] @ git+https://github.com/anatolybobunov/pytest-api-coverage.git"
uv add "pytest-api-coverage[httpx] @ git+https://github.com/anatolybobunov/pytest-api-coverage.git"
```

### Local Development Install

```bash
# Clone repository
git clone https://github.com/anatolybobunov/pytest-api-coverage.git
cd pytest-api-coverage

# Install in editable mode with your HTTP library of choice
pip install -e ".[requests]"
pip install -e ".[httpx]"
pip install -e ".[requests,httpx]"

# Or with uv
uv pip install -e ".[requests]"
uv pip install -e ".[httpx]"
uv pip install -e ".[requests,httpx]"
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=7.0.0 | Test framework |
| pyyaml | >=6.0 | YAML parsing for swagger files |
| jinja2 | >=3.0.0 | HTML report templating |
| requests *(optional)* | >=2.28.0 | HTTP interception for `requests`-based code |
| httpx *(optional)* | >=0.24.0 | HTTP interception for `httpx`-based code |

`requests` and `httpx` are optional — install only the one your project uses.

## Verify Installation

After installation, verify the plugin is available:

```bash
pytest --help | grep coverage-spec
```

You should see a help line containing `coverage-spec` with the description of the flag. The exact format may vary depending on your terminal width and pytest version.

## Optional: pytest-xdist

For parallel test execution, install pytest-xdist:

```bash
pip install pytest-xdist
```

Then run tests with:

```bash
pytest tests/ -n 4 --coverage-spec=swagger.json
```

## Next Steps

See the [Usage Guide](usage.md) to start using the plugin.
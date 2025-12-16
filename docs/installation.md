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
pip install git+https://github.com/your-username/pytest-api-coverage.git
```

### Using uv

```bash
uv add git+https://github.com/your-username/pytest-api-coverage.git
```

### Local Development Install

```bash
# Clone repository
git clone https://github.com/your-username/pytest-api-coverage.git
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
| requests | >=2.28.0 | HTTP client interception |
| httpx | >=0.24.0 | Async HTTP client interception |
| pandas | >=2.0.0 | Data processing for reports |
| jinja2 | >=3.0.0 | HTML report templating |

## Verify Installation

After installation, verify the plugin is available:

```bash
pytest --help | grep swagger
```

You should see:

```
--swagger=SWAGGER     Path to swagger.json/yaml file or URL to swagger spec
```

## Optional: pytest-xdist

For parallel test execution, install pytest-xdist:

```bash
pip install pytest-xdist
```

Then run tests with:

```bash
pytest tests/ -n 4 --swagger=swagger.json
```
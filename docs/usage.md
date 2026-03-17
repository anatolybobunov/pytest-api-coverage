# Usage Guide

## Quick Start

```bash
# Basic usage with local spec file
pytest tests/ --coverage-spec=swagger.json

# Using spec URL
pytest tests/ --coverage-spec=https://api.example.com/swagger.json

# With parallel execution
pytest tests/ -n 4 --coverage-spec=swagger.json
```

## CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--coverage-spec` | — | Path or URL to OpenAPI/Swagger spec |
| `--coverage-output` | `coverage-output` | Output directory for reports |
| `--coverage-format` | `html` | Output format(s) (default: `html`) |
| `--coverage-strip-prefix` | — | Strip URL prefix from recorded paths |
| `--coverage-split-by-origin` | `false` | Split coverage by origin URL |
| `--coverage-config` | — | Path to multi-spec config file |
| `--coverage-spec-name` | — | Label for single CLI spec, or filter from config |
| `--coverage-spec-api-url` | — | API base URL(s) to filter recorded requests |

## Examples

### Basic Coverage

```bash
pytest tests/ --coverage-spec=api/swagger.yaml
```

Generates reports in `coverage-output/` directory.

### Custom Output Directory

```bash
pytest tests/ --coverage-spec=swagger.json --coverage-output=reports/api-coverage
```

### Only JSON Report

```bash
pytest tests/ --coverage-spec=swagger.json --coverage-format=json
```

### Strip Path Prefixes

If your API has versioned paths (`/v1/users`) but the spec defines them without prefix (`/users`):

```bash
pytest tests/ --coverage-spec=swagger.json --coverage-strip-prefix=/v1,/api/v2
```

### Split Coverage by Origin

Generate separate coverage statistics for each API origin:

```bash
pytest tests/ --coverage-spec=swagger.json --coverage-split-by-origin
```

### Parallel Execution with pytest-xdist

```bash
pytest tests/ -n 4 --coverage-spec=swagger.json
```

Coverage data is automatically collected from all workers and aggregated.

## Report Formats

### JSON (`coverage.json`)

Machine-readable format with full details:

```json
{
  "format_version": "1.0",
  "generated_at": "2025-01-15T10:30:00+00:00",
  "swagger_source": "api/swagger.yaml",
  "summary": {
    "total_endpoints": 20,
    "covered_endpoints": 15,
    "coverage_percentage": 75.0,
    "total_requests": 150
  },
  "endpoints": [
    {
      "path": "/users/{id}",
      "hit_count": 8,
      "is_covered": true,
      "all_methods_covered": true,
      "methods": [
        {
          "method": "GET",
          "hit_count": 5,
          "is_covered": true,
          "response_codes": {"200": 4, "404": 1},
          "test_names": ["test_get_user", "test_user_not_found"]
        },
        {
          "method": "DELETE",
          "hit_count": 3,
          "is_covered": true,
          "response_codes": {"204": 3},
          "test_names": ["test_delete_user"]
        }
      ]
    }
  ]
}
```

### CSV (`coverage.csv`)

Spreadsheet-friendly format with columns:

| Path | Hit Count | Method | Method Count | Response Codes | Covered |
|------|-----------|--------|--------------|----------------|---------|
| /users/{id} | 8 | GET | 5 | 200(4), 404(1) | Yes |
| | | DELETE | 3 | 204(3) | Yes |
| /users | 10 | GET | 7 | 200(7) | Yes |
| | | POST | 3 | 201(3) | Yes |

### HTML (`coverage.html`)

Visual report with:
- Coverage percentage bar
- Summary statistics
- Color-coded endpoint table (green=covered, gray=once, red=not covered)
- Response code breakdown
- Grouped by path with method details

## Terminal Output

After test execution, a summary is printed:

```
========================= API Coverage Summary =========================
swagger   15/20 endpoints   75.0%   150 req   coverage.html
```

## Configuration via pytest.ini

You can also configure options in `pytest.ini`:

```ini
[pytest]
addopts = --coverage-spec=api/swagger.json --coverage-output=reports
```

Or in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = "--coverage-spec=api/swagger.json --coverage-output=reports"
```

## Multi-Spec Configuration

For projects with multiple APIs, use a config file instead of CLI flags.

### Config File (coverage-config.yaml)

```yaml
output_dir: coverage-output
formats: [html, json]
specs:
  - name: users-api
    swagger_path: docs/users.yaml
    api_urls:
      - http://localhost:8001
  - name: payments-api
    swagger_url: https://payments.internal/openapi.json
    api_urls:
      - http://localhost:8002
```

### Auto-Discovery

The plugin auto-discovers `coverage-config.yaml` or `coverage-config.json` at the project root.

You can also specify the config path explicitly:
```
pytest --coverage-config=path/to/config.yaml
```

### `--coverage-spec-name` Dual Behavior

- With CLI spec (`--coverage-spec`): sets the display label for that spec
- With config file: filters to run only the named spec(s)

### Note on Mocking Libraries

Socket-level mocking libraries (e.g., `responses`, `pytest-httpserver`) intercept HTTP at the socket level and prevent the plugin from recording interactions. Use real HTTP calls or mock at a higher level.
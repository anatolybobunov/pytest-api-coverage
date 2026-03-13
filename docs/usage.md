# Usage Guide

## Quick Start

```bash
# Basic usage with local swagger file
pytest tests/ --swagger=swagger.json

# Using swagger URL
pytest tests/ --swagger=https://api.example.com/swagger.json

# With parallel execution
pytest tests/ -n 4 --swagger=swagger.json
```

## CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--swagger` | — | Path to swagger.json/yaml file or URL (single-spec mode) |
| `--coverage-config` | — | Path to YAML/JSON config file for multi-spec mode |
| `--coverage-spec-name` | — | Name label for a single spec |
| `--coverage-spec-path` | — | Local file path to an OpenAPI spec (single-spec CLI mode) |
| `--coverage-spec-url` | — | Remote URL of an OpenAPI spec (single-spec CLI mode) |
| `--coverage-spec-base-url` | — | Base URL(s) for the spec (repeatable) |
| `--coverage-output` | `coverage-output` | Output directory for coverage reports |
| `--coverage-format` | `json,csv,html` | Report formats (comma-separated): `json`, `csv`, `html` |
| `--coverage-base-url` | — | Filter coverage to single base URL (origin) |
| `--coverage-include-base-url` | — | Allowlist of base URLs (comma-separated) |
| `--coverage-strip-prefix` | — | Additional path prefixes to strip (comma-separated) |
| `--coverage-split-by-origin` | `false` | Generate separate coverage buckets per origin |

## Examples

### Basic Coverage

```bash
pytest tests/ --swagger=api/swagger.yaml
```

Generates reports in `coverage-output/` directory.

### Custom Output Directory

```bash
pytest tests/ --swagger=swagger.json --coverage-output=reports/api-coverage
```

### Only JSON Report

```bash
pytest tests/ --swagger=swagger.json --coverage-format=json
```

### Filter by Base URL

When your tests hit multiple APIs but you only want coverage for one:

```bash
pytest tests/ --swagger=swagger.json --coverage-base-url=https://api.example.com
```

### Multiple Allowed Origins

```bash
pytest tests/ --swagger=swagger.json \
  --coverage-include-base-url=https://api.example.com,https://staging.example.com
```

### Strip Path Prefixes

If your API has versioned paths (`/v1/users`) but swagger defines them without prefix (`/users`):

```bash
pytest tests/ --swagger=swagger.json --coverage-strip-prefix=/v1,/api/v2
```

### Split Coverage by Origin

Generate separate coverage statistics for each API origin:

```bash
pytest tests/ --swagger=swagger.json --coverage-split-by-origin
```

### Parallel Execution with pytest-xdist

```bash
pytest tests/ -n 4 --swagger=swagger.json
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
addopts = --swagger=api/swagger.json --coverage-output=reports
```

Or in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = "--swagger=api/swagger.json --coverage-output=reports"
```
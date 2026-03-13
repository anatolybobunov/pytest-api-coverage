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
| `--coverage-spec` | — | **Required.** Path or URL to OpenAPI spec (swagger.json/yaml or remote URL) |
| `--coverage-output` | `coverage-output` | Output directory for coverage reports |
| `--coverage-format` | `json,csv,html` | Report formats (comma-separated): `json`, `csv`, `html` |
| `--coverage-strip-prefix` | — | Additional path prefixes to strip (comma-separated) |
| `--coverage-split-by-origin` | `false` | Generate separate coverage buckets per origin |
| `--coverage-config` | — | Path to api-coverage config file (YAML/JSON) for multi-spec |
| `--coverage-spec-name` | — | Name for the spec (used with `--coverage-spec` and `--coverage-spec-api-url`) |
| `--coverage-spec-api-url` | — | API base URL(s) for the spec (repeatable) |

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

If your API has versioned paths (`/v1/users`) but swagger defines them without prefix (`/users`):

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

### Single-spec CLI Mode (with origin filtering)

```bash
pytest tests/ \
  --coverage-spec=swagger.json \
  --coverage-spec-name=myapi \
  --coverage-spec-api-url=https://api.example.com
```

### Multi-spec via Config File

```bash
pytest tests/ --coverage-config=coverage-config.yaml
```

See [Multi-spec Configuration](#multi-spec-configuration) below.

## Multi-spec Configuration

Create a `coverage-config.yaml` in your project root:

```yaml
output_dir: reports/api-coverage
formats: [json, html]

specs:
  - name: auth
    swagger_path: ./specs/auth.yaml
    api_urls:
      - https://auth.example.com

  - name: orders
    swagger_url: https://orders.example.com/openapi.json
    api_urls:
      - https://orders.example.com
      - https://staging-orders.example.com
```

### Config File Keys

| Key | Description |
|-----|-------------|
| `name` | Spec identifier (used as file prefix) |
| `swagger_path` | Local path to OpenAPI spec file |
| `swagger_url` | Remote URL of OpenAPI spec |
| `api_urls` | List of API base URLs to match requests against |

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
Endpoints: 15/20 covered (75.0%)
Total HTTP requests: 150

Uncovered endpoints (5):
  - DELETE /users/{id}
  - PATCH /users/{id}
  - POST /admin/reset
  ...
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

# Usage Guide

## CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--coverage-spec` | — | Path or URL to OpenAPI/Swagger spec |
| `--coverage-output` | `api-coverage-report` | Output directory for reports |
| `--coverage-format` | `html` | Comma-separated report format(s). Supported: `json`, `csv`, `html`, `all` (generates all three formats at once) |
| `--coverage-strip-prefix` | — | Comma-separated path prefixes to strip from request URLs before matching against the spec |
| `--coverage-split-by-origin` | `false` | Split coverage by origin URL |
| `--coverage-config` | — | Path to multi-spec config file |
| `--coverage-spec-name` | — | Label for single CLI spec, or filter from config |
| `--coverage-url-filter` | — | Filter string(s) for matching request URLs (substring match, can be specified multiple times) |

> For persisting options via `pytest.ini` or `pyproject.toml`, and for multi-spec configuration, see the [Configuration Reference](configuration.md).

## Examples

### Basic Coverage

```bash
pytest tests/ --coverage-spec={path or url to the swagger.json} --coverage-spec-name={spec name from config}
```

Generates reports in `api-coverage-report/` directory.

### Custom Output Directory

```bash
pytest tests/ --coverage-spec={path or url to the swagger.json} --coverage-output={custom report folder}
```

### Only JSON Report

```bash
pytest tests/ --coverage-spec={path or url to the swagger.json} --coverage-format=json
```

### Strip Path Prefixes

If your API has versioned paths (`/v1/users`) but the spec defines them without prefix (`/users`):

```bash
pytest tests/ --coverage-spec={path or url to the swagger.json} --coverage-strip-prefix=/v1,/api/v2
```

### Split Coverage by Origin

Generate separate coverage statistics for each API origin:

```bash
pytest tests/ --coverage-spec={path or url to the swagger.json} --coverage-split-by-origin
```

### Parallel Execution with pytest-xdist

```bash
pytest tests/ -n 4 --coverage-spec={path or url to the swagger.json}
```

Coverage data is automatically collected from all workers and aggregated.

## Report Formats

For details on HTML, JSON, CSV, and terminal output formats, see [Coverage Reports](reports.md).

## See Also

- [Configuration Reference](configuration.md) — pytest.ini setup, multi-spec config
- [Coverage Reports](reports.md) — report formats and result interpretation
- [Troubleshooting](troubleshooting.md) — common issues and fixes

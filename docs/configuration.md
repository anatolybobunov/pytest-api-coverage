# Configuration Reference

There are two ways to configure pytest-api-coverage. For single-spec projects, pass CLI
flags directly on the command line or persist them via `addopts` in your pytest config
file. For projects with multiple APIs, use a YAML or JSON config file that declares each
spec as a named entry and pass it with `--coverage-config=path/to/config.yaml`.

## Persisting CLI Options (addopts)

CLI flags can be persisted so you do not have to repeat them on every `pytest` invocation.

In `pytest.ini`:

```ini
[pytest]
addopts = --coverage-spec=api/swagger.json --coverage-output=reports
```

In `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = "--coverage-spec=api/swagger.json --coverage-output=reports"
```

The plugin does **not** register custom `ini_options` keys. There is no `[api_coverage]`
section or `coverage_spec = ...` style setting. `addopts` is the only mechanism for
persisting CLI flags into a pytest config file.

## Multi-Spec Configuration File

### File Format

Create a `coverage-config.yaml` (or `coverage-config.yml`) file at the project root:

```yaml
output_dir: api-coverage-report
formats: [html, json]
specs:
  - name: users-api
    swagger_path: docs/users.yaml
    api_filters:
      - users-
  - name: payments-api
    swagger_url: https://payments.internal/openapi.json
    api_filters:
      - payments
```

The file can also be written as JSON (`coverage-config.json`) with the same structure. Both `.yaml` and `.yml` extensions are supported.

### Supported Keys (Schema Reference)

**Top-level keys:**

| Key | Type | Required | Default | Description |
|---|---|---|---|---|
| `output_dir` | string | no | `api-coverage-report` | Directory where reports are written |
| `formats` | list of strings | no | `[html]` | Report formats to generate; valid values: `html`, `json`, `csv`, `all` (`all` expands to all three formats) |
| `specs` | list | yes | — | One or more spec configurations (see below) |

**Per-spec keys (each entry under `specs`):**

> **Note:** These keys apply only to entries in the `specs` list of the config file. In CLI single-spec mode, use `--coverage-url-filter` instead of `api_filters`.

| Key | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Unique identifier for this spec; used in output filenames and terminal summary |
| `api_filters` | list of strings | yes | Filter strings matched against intercepted request URLs (substring match, case-insensitive); only matching requests are attributed to this spec |
| `swagger_path` | string | no | Path to a local OpenAPI/Swagger spec file (mutually exclusive with `swagger_url`) |
| `swagger_url` | string | no | URL to a remote OpenAPI/Swagger spec (mutually exclusive with `swagger_path`) |
| `strip_prefixes` | list of strings | no | Path prefixes to strip before matching request paths to spec endpoints. Defaults to `[]`. Auto-derived from `api_filters` URL paths — e.g. `http://host/symboldb` automatically strips `/symboldb`. Set this explicitly only when auto-derivation is insufficient. |

Each spec entry must provide exactly one of `swagger_path` or `swagger_url`. Entries
missing `name`, `api_filters`, or that supply both `swagger_path` and `swagger_url` are
skipped with a warning and do not abort the run.

**Important:** Only `output_dir`, `formats`, and `specs` are honoured at the top level of
the config file. The global `--coverage-strip-prefix` CLI flag has no top-level config
equivalent. For multi-spec setups, use the per-spec `strip_prefixes` key inside each spec
entry. `--coverage-split-by-origin` has no config file equivalent at all — use `addopts` to
persist it.

**Specifying a config path explicitly:**

```bash
pytest --coverage-config=path/to/config.yaml
```

## `--coverage-spec-name` Behavior

`--coverage-spec-name` has a dual purpose that depends on which other flags are present.

| Scenario | What `--coverage-spec-name` does |
|---|---|
| Used with `--coverage-spec` | Labels the spec; the name appears in the output filename and terminal summary. `--coverage-url-filter` is **required** — omitting it raises a `UsageError`. |
| Used with `--coverage-config` | Filters the config file to run only the spec whose `name` matches; all other specs are ignored. `--coverage-url-filter` is not needed — each spec's `api_filters` in the config file serves that purpose. If `--coverage-url-filter` is passed anyway, it is ignored and a warning is emitted. |
| Used alone (no `--coverage-spec` and no config file) | Error: `--coverage-spec-name requires --coverage-spec` |

**Labelling a single spec via CLI:**

```bash
pytest tests/ \
  --coverage-spec=api/swagger.yaml \
  --coverage-spec-name=users-api \
  --coverage-url-filter=http://localhost:8001
```

**Filtering a config file to one spec:**

```bash
pytest tests/ \
  --coverage-config=coverage-config.yaml \
  --coverage-spec-name=payments-api
```

When filtering by name, the value must exactly match the `name` field of one of the
entries in the config file. If no match is found, pytest exits with a `UsageError`
listing the available spec names.

### Shared domain with path prefixes

When multiple specs share a domain but differ by path prefix, set the full URL (including prefix) in `api_filters`. The plugin automatically strips the prefix when matching request paths against spec endpoints:

```yaml
specs:
  - name: symboldb
    swagger_url: https://shared-domain.com/symboldb/swagger.json
    api_filters:
      - https://shared-domain.com/symboldb
    # /symboldb is auto-stripped from request paths before spec matching

  - name: symboldb-editor
    swagger_url: https://shared-domain.com/symboldb-editor/swagger.json
    api_filters:
      - https://shared-domain.com/symboldb-editor
    # /symboldb-editor is auto-stripped automatically
```

A request to `https://shared-domain.com/symboldb/users` is matched against `GET /users` in the `symboldb` spec.

## Plugin Activation

The plugin only activates when at least one of the following is provided:

- `--coverage-spec` flag
- `--coverage-config` flag (with path to the config file)

If neither is present, the plugin silently disables itself and does not affect the test run. **Note:** The plugin does not auto-discover config files — you must pass `--coverage-config=path/to/config.yaml` explicitly.

## See Also

- [Usage Guide](usage.md) — CLI options and basic examples
- [Troubleshooting](troubleshooting.md) — common issues and spec-name errors

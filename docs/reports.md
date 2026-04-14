# Coverage Reports

The plugin generates reports after each test session. Reports are written to the configured output directory (default: `api-coverage-report/`). HTML, JSON, and CSV formats are available; HTML is the default.

## Report Formats

### HTML Report

Visual report rendered as a self-contained HTML file. Contains:

- Coverage percentage bar (red below 50%, yellow/orange 50–79%, green 80%+)
- Summary statistics cards: coverage %, endpoints covered, total requests
- Color-coded endpoint table with method-level detail
- Response code breakdown per method (color-coded by HTTP status class)
- Sortable columns: Path, Hit Count, Status

The table groups endpoints by path. Each row within a path group represents one HTTP method. Rows are sorted by total hit count descending so the most-exercised endpoints appear first.

In multi-spec mode, the filename is `{spec_name}-coverage.html` instead of `coverage.html`.

### JSON Report

Machine-readable format with full endpoint detail. Written atomically to avoid partial reads in CI.

```json
{
  "format_version": "1.0",
  "generated_at": "2025-01-15T10:30:00+00:00",
  "swagger_source": "api/swagger.yaml",
  "split_by_origin": false,
  "summary": {
    "total_endpoints": 20,
    "covered_endpoints": 15,
    "coverage_percentage": 75.0,
    "total_requests": 150,
    "unmatched_requests": 3
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

**Field reference:**

| Field | Description |
|---|---|
| `format_version` | Schema version for programmatic consumers. Currently `"1.0"`. Incremented when the structure changes in a breaking way. Check this field before parsing if your tooling depends on the exact shape. |
| `generated_at` | ISO 8601 UTC timestamp of when the report was written |
| `swagger_source` | Path or URL of the OpenAPI spec used |
| `split_by_origin` | `false` for standard reports; `true` when `--coverage-split-by-origin` was used (different structure, see below) |
| `summary.total_endpoints` | Total number of `(method, path)` pairs defined in the spec |
| `summary.covered_endpoints` | Number of those pairs hit at least once |
| `summary.coverage_percentage` | `covered_endpoints / total_endpoints * 100` |
| `summary.total_requests` | Total matched HTTP requests recorded during the session |
| `summary.unmatched_requests` | Requests that were recorded but matched no spec endpoint |
| `endpoints[].hit_count` | Total hits across all methods for this path |
| `endpoints[].is_covered` | `true` if any method was hit at least once |
| `endpoints[].all_methods_covered` | `true` if every method in the spec for this path was hit |
| `methods[].hit_count` | Number of times this specific method was called |
| `methods[].response_codes` | Map of HTTP status code (string) to hit count |
| `methods[].test_names` | Sorted list of test function names that triggered this method |

**Split-by-origin structure:** When `--coverage-split-by-origin` is used, the top-level `endpoints` and `summary` keys are replaced by `origins` (a dict keyed by origin URL, each containing its own `summary` and `endpoints`) and `combined_summary` (aggregate across all origins including `origins_count`).

### CSV Report

Spreadsheet-friendly format. One row per method per path, with the path and total hit count appearing only in the first method row for a given path. Suitable for import into Excel, Google Sheets, or further processing with command-line tools.

**Columns:** `Path`, `Hit Count`, `Method`, `Method Count`, `Response Codes`, `Covered`

Example rows:

| Path | Hit Count | Method | Method Count | Response Codes | Covered |
|------|-----------|--------|--------------|----------------|---------|
| SWAGGER | api/swagger.yaml | | | | |
| /users/{id} | 8 | GET | 5 | 200(4), 404(1) | Yes |
| | | DELETE | 3 | 204(3) | Yes |
| /users | 10 | GET | 7 | 200(7) | Yes |
| | | POST | 3 | 201(3) | Yes |
| TOTAL | 150 | | 15/20 endpoints | | 75.0% |

The first data row (`SWAGGER`) records the spec source path for traceability. The final row (`TOTAL`) is a summary with aggregate request count, endpoint ratio, and overall coverage percentage.

When `--coverage-split-by-origin` is used, an `Origin` column is prepended, each origin gets a `SUBTOTAL` row, and the final row uses `ALL` / `TOTAL`.

### Terminal Summary

After test execution, a summary line is printed to the pytest terminal output:

```
========================= API Coverage Summary =========================
swagger   15/20 endpoints   75.0%   150 req   api-coverage-report/coverage.html
```

If any recorded requests did not match a spec endpoint:

```
[api-coverage] 3 request(s) did not match any endpoint in the spec
```

In multi-spec mode, one row is printed per spec plus a `TOTAL` row:

```
=================== API Coverage Summary (2 specs) ====================
users-api      12/15 endpoints   80.0%   90 req    users-api-coverage.html
payments-api    3/5 endpoints    60.0%   60 req    payments-api-coverage.html
TOTAL          15/20 endpoints   75.0%   150 req   0 unmatched
```

## Interpreting Results

### Coverage Percentage

Coverage percentage is calculated as:

```
coverage % = covered_endpoints / total_endpoints * 100
```

where `total_endpoints` is the count of distinct `(method, path)` pairs defined in the OpenAPI spec, and `covered_endpoints` is the count of those pairs that received at least one matching HTTP request during the test session.

An endpoint is "covered" when the plugin recorded at least one request where the HTTP method matched and the request path matched the spec path pattern (including path parameters such as `{id}`).

Hitting an endpoint once counts the same as hitting it many times for the coverage percentage. The `hit_count` and `methods[].hit_count` fields let you distinguish single-hit coverage from repeated exercise.

### Unmatched Requests

The terminal line `N request(s) did not match any endpoint in the spec` (and `summary.unmatched_requests` in the JSON report) counts HTTP requests that were successfully recorded by the plugin but did not correspond to any endpoint defined in the spec.

Common causes:

- **URL prefix mismatch.** Your API serves paths like `/v1/users` but the spec defines `/users`. Fix with `--coverage-strip-prefix=/v1`.
- **Path parameters not recognized.** The spec defines `/users/{id}` but requests hit `/users/profile/settings` — a deeper path structure the pattern does not match. Verify the spec reflects your actual routes.
- **Endpoint not in spec.** Your tests exercise an endpoint that exists in the API but is missing from the OpenAPI spec. Update the spec to include it.
- **Filter mismatch.** When using `--coverage-url-filter` or a multi-spec config, requests not matching any `api_filters` substring are excluded before matching. Confirm the configured filters match the actual base URLs your tests call (the filter is a case-insensitive substring of the full request URL).

Unmatched requests are not failures on their own, but a non-zero count usually signals a configuration issue worth resolving before trusting the coverage percentage.

### Acting on Low Coverage

Start by checking unmatched requests first. A large unmatched count means the coverage percentage is deflated by misconfiguration, not by genuinely untested endpoints. Fix the configuration (prefix stripping, origin filtering, spec completeness) before interpreting the percentage.

Once unmatched requests are near zero:

- Use the JSON report for automated threshold checks in CI pipelines. The `summary.coverage_percentage` field is straightforward to parse with `jq`.
- Prioritize covering POST, PUT, PATCH, and DELETE endpoints over GET — write operations carry higher risk and tend to have more complex state-dependent behaviour.
- Use `test_names` in the JSON report to identify which tests cover which endpoints. Endpoints with no `test_names` have zero hits.
- Filter the HTML report by the "Not Covered" status to get a focused list of gaps.

### HTML Report Color Coding

Each path row in the HTML endpoint table is color-coded by coverage state:

| Row color | Status | Meaning |
|---|---|---|
| Green background | **Covered** | All HTTP methods for this path are covered (each method hit at least once) |
| Yellow/Amber background | **Partial** | Some methods for this path are covered, but not all |
| Red background | **Not Covered** | No methods for this path have been hit |

The table also displays per-method badges:

| Badge | Meaning |
|---|---|
| Green **Covered** | Method hit more than once (`hit_count > 1`) |
| Yellow/Amber **Once** | Method hit exactly once (`hit_count == 1`) |
| Red **Not Covered** | Method never hit (`hit_count == 0`) |

The per-method "Once" badge highlights methods with only a single test path through them. A single hit means there is no redundancy and likely no negative-path testing for that method.

The coverage progress bar at the top of the report also changes color: red below 50%, amber/yellow from 50% to 79%, and green at 80% or above.

Response codes are color-coded inline:

| Badge color | Range |
|---|---|
| Green | 2xx Success |
| Yellow | 3xx Redirect |
| Red (light) | 4xx Client Error |
| Red (dark) | 5xx Server Error |

## Output File Naming

File names are determined by whether a spec name prefix is present. The prefix comes from `--coverage-spec-name` (single-spec CLI usage) or the `name` field in a multi-spec config file.

| Mode | HTML filename | JSON filename | CSV filename |
|---|---|---|---|
| Single spec (no name) | `coverage.html` | `coverage.json` | `coverage.csv` |
| Single spec with `--coverage-spec-name=myapi` | `myapi-coverage.html` | `myapi-coverage.json` | `myapi-coverage.csv` |
| Multi-spec config | `{name}-coverage.html` per spec | `{name}-coverage.json` per spec | `{name}-coverage.csv` per spec |

All files are written to the output directory configured by `--coverage-output` (default: `api-coverage-report/`). The directory is created automatically if it does not exist. Writes are atomic: each file is written to a temporary path first, then renamed into place, so a partial write never leaves a corrupt report file.

## See Also

- [Usage Guide](usage.md) — `--coverage-format` and `--coverage-output` options

# Troubleshooting

## 0 HTTP requests captured

**Symptom:** Report shows 0% coverage and "0 HTTP requests captured".

**Cause 1: Mocking libraries intercept at the socket level**

The following libraries are incompatible with pytest-api-coverage:
- `responses` — intercepts at the urllib3 level
- `respx` — intercepts the httpx transport
- `vcrpy` / `pytest-recording` — intercept at the urllib3 level
- `pytest-httpserver` — fully replaces the network stack

**Solution:** pytest-api-coverage patches `requests.Session.request` and `httpx.Client.request`.
If tests use mocking at a lower level, requests will not be captured.
Use a real server (test environment) or ensure requests go through the `requests`/`httpx` API.

**Cause 2: Tests do not make HTTP requests**

The plugin is active but tests do not call `requests` or `httpx`. Make sure your tests
make real HTTP requests and are not using mocks for all calls.

## No HTTP adapter available

If you installed `pytest-api-coverage` without extras, neither `requests` nor `httpx` adapters will be active. No HTTP calls will be intercepted and coverage will always show 0%.

Install with extras:

```bash
pip install pytest-api-coverage[requests]
pip install pytest-api-coverage[httpx]
pip install pytest-api-coverage[all]
```

## Spec not found

**Symptom:** `Swagger file not found: /absolute/path/to/spec.yaml`

Make sure the path is relative to the directory where pytest is run (usually the project root).

## Auto-discovery not working

**Symptom:** Plugin does not activate even though `coverage-config.yaml` exists.

Supported file names: `coverage-config.yaml`, `coverage-config.yml`, `coverage-config.json`.
The file must be in the project root (the directory where pytest is run).

## N requests did not match any endpoints

**Symptom:** Report or terminal shows "N request(s) did not match any endpoint".

Possible causes:
- URL contains a base path (e.g. `/api/v1/users`) but the spec defines the path as `/users`. Use `--coverage-strip-prefix=/api/v1`.
- The request URL points to a different origin — use `--coverage-spec-api-url` to filter.

## Conflict with pytest-httpx or responses

pytest-api-coverage patches `httpx.Client.request` at the method level.
`pytest-httpx` uses httpx's transport mechanism — no conflict, but requests will be recorded as mocked.
This is the correct behaviour when testing API contracts.

## xdist: coverage lower than expected

If workers terminated with an error, their data is lost.
Check for warnings like `"Worker gw0 finished without coverage_data"` in the pytest output.

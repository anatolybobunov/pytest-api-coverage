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

`requests` and `httpx` are optional extras for pytest-api-coverage (`pip install pytest-api-coverage[requests]`, `pip install pytest-api-coverage[httpx]`, or `pip install pytest-api-coverage[all]`). An adapter skip does not indicate a broken install — it means one of the optional libraries is not installed or failed to import at runtime (e.g., a heavily constrained virtualenv).

If you see a warning about an adapter being skipped, verify that both libraries are importable in your test environment:

```bash
python -c "import requests, httpx; print('OK')"
```

If the command fails, reinstall the affected library or inspect your virtualenv for conflicts.

## Spec not found

**Symptom:** `Swagger file not found: /absolute/path/to/spec.yaml`

Make sure the path is relative to the directory where pytest is run (usually the project root).

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

### `--coverage-spec-api-url` has no effect

**Symptom:** You passed `--coverage-spec-api-url` but requests are not matched against that URL prefix.

**Cause:** `--coverage-spec-api-url` is ignored unless used together with `--coverage-spec` (and optionally `--coverage-spec-name`). In multi-spec config file mode, define `api_urls` per spec in the config file instead.

**Fix:** Always combine with `--coverage-spec`:

```bash
pytest --coverage-spec=openapi.yaml --coverage-spec-api-url=https://api.example.com
```

### HTTP requests not captured, no error shown

**Symptom:** Coverage shows 0 requests captured but you expect HTTP calls to be intercepted.

**Cause:** In rare constrained environments, if `requests` or `httpx` fails to import, the adapter is silently skipped with no warning.

**Fix:** Verify both libraries are importable in your test environment:

```bash
python -c "import requests, httpx; print('OK')"
```

Also ensure your tests are not using mocking libraries that intercept at the socket level (e.g., `responses`, `pytest-httpx`) — see the note in [Usage Guide](usage.md).

## See Also

- [Installation Guide](installation.md) — dependency requirements
- [Configuration Reference](configuration.md) — multi-spec setup
- [Usage Guide](usage.md) — CLI options and examples

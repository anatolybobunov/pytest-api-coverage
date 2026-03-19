# Troubleshooting

## 0 HTTP requests captured

**Symptom:** Report shows 0% coverage and "0 HTTP requests captured".

**Cause 1: Mocking libraries intercept below the patched layer**

**Fully incompatible** — these libraries replace the network stack entirely; no real requests are made, so nothing can be captured:

- `pytest-httpserver` — binds a real local server but replaces the HTTP response stack

**Compatible with caveats** — these libraries work alongside pytest-api-coverage, but the recorded interactions reflect the mocked responses, not a real server. Coverage numbers will be based on the mock data:

- `responses` — intercepts at the urllib3 level; requests still pass through `requests.Session.request`, so the plugin captures the call (with the mocked response)
- `respx` — intercepts the httpx transport; calls still pass through `httpx.Client.request`
- `vcrpy` / `pytest-recording` — replays cassettes through the urllib3 layer; calls are still intercepted by the plugin at the `requests`/`httpx` level

**Solution:** Use a real test server when you need accurate API coverage data. With mock libraries (except `pytest-httpserver`), you will see coverage numbers, but they reflect your mock definitions rather than a live service.

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
- The request URL does not match any configured filter — use `--coverage-url-filter` to specify a substring to match against request URLs.

## Conflict with pytest-httpx or responses

pytest-api-coverage patches `httpx.Client.request` at the method level.
`pytest-httpx` uses httpx's transport mechanism — no conflict, but requests will be recorded as mocked.
This is the correct behaviour when testing API contracts.

## xdist: coverage lower than expected

If workers terminated with an error, their data is lost.
Check for warnings like `"Worker gw0 finished without coverage_data"` in the pytest output.

### `--coverage-url-filter` has no effect

**Symptom:** You passed `--coverage-url-filter` but requests are not matched against that filter.

**Cause:** `--coverage-url-filter` is ignored unless used together with `--coverage-spec` (and optionally `--coverage-spec-name`). In multi-spec config file mode, define `api_filters` per spec in the config file instead.

**Fix:** Always combine with `--coverage-spec`. The filter value is a substring matched against the full request URL (case-insensitive):

```bash
# Match by full origin (http or https)
pytest --coverage-spec=openapi.yaml --coverage-url-filter=api.example.com

# Match by partial hostname (matches both http and https)
pytest --coverage-spec=openapi.yaml --coverage-url-filter=api.example.com
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

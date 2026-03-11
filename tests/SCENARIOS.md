# Test Scenarios

## User Stories

### Story 1: Multi-threaded coverage collection
Run API coverage for 1 Swagger spec + multiple test suites in parallel mode (pytest-xdist).
**Expected:** Single HTML report with all matched endpoints.

### Story 2: Single-threaded HTML report
Run API coverage for 1 Swagger spec + 1 test file, single-threaded, report-type=html.
**Expected:** HTML report with all matched endpoints.

### Story 3: JSON report format
Run API coverage for 1 Swagger spec + 1 test file, single-threaded, report-type=json.
**Expected:** JSON report with all matched endpoints.

### Story 4: CSV report format
Run API coverage for 1 Swagger spec + 1 test file, single-threaded, report-type=csv.
**Expected:** CSV report with all matched endpoints.

### Story 5: Requests library support
Run API coverage using `requests` library for HTTP calls.
**Expected:** All requests are intercepted and matched against Swagger spec.

### Story 6: HTTPX library support
Run API coverage using `httpx` library for HTTP calls.
**Expected:** All requests are intercepted and matched against Swagger spec.

---

## New Scenario Ideas

Coverage for multiple Swagger specs simultaneously — aggregate results into a single report.

OpenAPI 3.0/3.1 support in addition to Swagger 2.0.

Filtering endpoints by tags or paths (e.g., only `/api/v1/*` endpoints).

Threshold validation — fail tests if coverage drops below a specified percentage.

Diff report — compare coverage between two test runs and highlight changes.

Exclude specific endpoints from coverage calculation via config.

Integration with CI/CD — output coverage as GitHub Actions annotation or GitLab badge.

Support for async httpx client (`httpx.AsyncClient`).

Coverage by response status codes — track which status codes were tested per endpoint.

Markdown report format for easy embedding in PR descriptions.

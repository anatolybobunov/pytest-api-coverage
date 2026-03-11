---
phase: 01-config-and-activation
plan: "04"
subsystem: config
tags: [pytest, pytester, config-discovery, multi-spec, integration-testing, yaml, json]

requires:
  - phase: 01-02
    provides: load_multi_spec_config and _discover_config_file functions in multi_spec.py
  - phase: 01-03
    provides: CoverageSettings with specs field and CLI flags wired in from_pytest_config()
provides:
  - from_pytest_config() fully wired to _discover_config_file() and load_multi_spec_config()
  - Explicit --coverage-config path support with pytest.exit() on missing file
  - Auto-discovery of coverage-config.yaml and coverage-config.json from pytest rootdir
  - Spec path existence validation after loading; abort with clear message if missing
  - 6 integration tests via pytester covering all config discovery scenarios
affects: [02-collection, 03-reporting]

tech-stack:
  added: [pytester (pytest built-in, enabled via pyproject.toml addopts)]
  patterns:
    - Local imports inside from_pytest_config() for multi_spec functions to avoid circular imports
    - pytester fixture for black-box integration tests of pytest plugins

key-files:
  created:
    - tests/integration/__init__.py
    - tests/integration/test_config_discovery.py
  modified:
    - src/pytest_api_coverage/config/settings.py
    - tests/unit/test_settings.py
    - tests/test_settings.py
    - pyproject.toml

key-decisions:
  - "Local imports in from_pytest_config() for _discover_config_file and load_multi_spec_config to avoid circular import (multi_spec.py imports SpecConfig from settings.py)"
  - "pytest.exit() message goes to stderr (not stdout) — integration test uses result.stderr.fnmatch_lines"
  - "pytester enabled globally via pyproject.toml addopts = -p pytester rather than per-test conftest"
  - "swagger is None guard ensures config file loading only happens when swagger mode is inactive"

patterns-established:
  - "Integration tests use pytester.makefile() to create temp project files and runpytest() for in-process execution"
  - "Spec path validation after loading config file catches missing spec files before collection starts"

requirements-completed: [CFG-02, CFG-03]

duration: 8min
completed: 2026-03-11
---

# Phase 1 Plan 4: Config File Activation Wiring Summary

**Full config activation path wired: coverage-config.yaml/json auto-discovered from rootdir, explicit --coverage-config respected, missing files abort with clear pytest.exit() messages, validated by 6 pytester integration tests**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-11T12:31:12Z
- **Completed:** 2026-03-11T12:39:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- `from_pytest_config()` in `settings.py` now wires `_discover_config_file()` and `load_multi_spec_config()` into the activation path
- Explicit `--coverage-config=path` loads specs from the given file; missing path triggers `pytest.exit()` with "[api-coverage] Config file not found: ..."
- Auto-discovery probes pytest `rootpath` for `coverage-config.yaml` then `coverage-config.json`; YAML wins if both present
- Spec path existence validated after loading — any missing spec file triggers `pytest.exit()` with "[api-coverage] Spec file not found: ..."
- 6 pytester-based integration tests cover all activation scenarios end-to-end
- Silent fall-through when no config and no CLI spec flags (`is_enabled()` returns False)

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire loader into from_pytest_config()** - `6197b4c` (feat)
2. **Task 2: Integration tests for auto-discovery and explicit config path** - `3b1170c` (test)

**Plan metadata:** _(to be committed with docs)_

## Files Created/Modified
- `src/pytest_api_coverage/config/settings.py` - Replaced TODO comment with actual wiring; local imports for multi_spec functions; swagger-is-None guard; spec path validation
- `tests/integration/__init__.py` - Empty package init (makes tests/integration a Python package)
- `tests/integration/test_config_discovery.py` - 6 pytester integration tests for all config discovery scenarios
- `pyproject.toml` - Added `[tool.pytest.ini_options]` with `addopts = "-p pytester"` to enable pytester fixture
- `tests/unit/test_settings.py` - Added `mock_config.rootpath = Path("/tmp")` to mock helper
- `tests/test_settings.py` - Fixed `test_from_pytest_config_defaults` to include new CLI options in mock and set rootpath

## Decisions Made
- **Local imports for circular import avoidance:** `multi_spec.py` imports `SpecConfig` from `settings.py`, so a top-level import of `multi_spec` in `settings.py` would cause a circular import. Used local imports inside `from_pytest_config()` instead.
- **pytest.exit() outputs to stderr:** Discovered during integration tests that `pytest.exit()` writes its message to stderr (as `"Exit: <message>"`), not stdout. Integration test uses `result.stderr.fnmatch_lines()`.
- **Global pytester enablement via pyproject.toml:** Added `addopts = "-p pytester"` so the fixture is available project-wide without per-test conftest setup.
- **swagger is None guard:** Changed the final `else` branch to `elif swagger is None` so swagger-only runs (no spec flags) don't incorrectly enter the config file loading path.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Mock configs missing rootpath attribute**
- **Found during:** Task 1 (unit tests after wiring)
- **Issue:** `_discover_config_file(config.rootpath)` called `rootpath / "coverage-config.yaml"` but `rootpath` was a Mock object (not a Path), causing `TypeError: unsupported operand type(s) for /: 'Mock' and 'str'`
- **Fix:** Added `mock_config.rootpath = Path("/tmp")` to mock helpers in `tests/unit/test_settings.py` and `tests/test_settings.py`; also added missing new CLI option keys to the defaults dict
- **Files modified:** `tests/unit/test_settings.py`, `tests/test_settings.py`
- **Verification:** All 33 unit tests pass after fix
- **Committed in:** `6197b4c` (Task 1 commit) and `3b1170c` (Task 2 commit)

**2. [Rule 1 - Bug] pytest.exit() message in stderr not stdout**
- **Found during:** Task 2 (integration test run)
- **Issue:** `test_explicit_coverage_config_missing_file` checked `result.stdout.fnmatch_lines(["*Config file not found*"])` but the message appears in stderr
- **Fix:** Changed assertion to `result.stderr.fnmatch_lines(["*Config file not found*"])`
- **Files modified:** `tests/integration/test_config_discovery.py`
- **Verification:** All 6 integration tests pass after fix
- **Committed in:** `3b1170c` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 × Rule 1 - Bug)
**Impact on plan:** Both fixes necessary for correctness. No scope creep. Test mock infrastructure now accurately reflects the runtime contract.

## Issues Encountered
- `pytester` fixture not available by default — required enabling via `addopts = "-p pytester"` in `pyproject.toml`. This is standard pytest behavior for built-in but opt-in fixtures.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 1 complete: all four plans (01-01 through 01-04) delivered
- Full activation path works: config file found → parsed → specs in CoverageSettings → `is_enabled()` returns True
- Phase 2 (collection) can rely on `CoverageSettings.specs` being populated for multi-spec routing
- No blockers

---
*Phase: 01-config-and-activation*
*Completed: 2026-03-11*

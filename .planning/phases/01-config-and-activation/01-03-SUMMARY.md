---
phase: 01-config-and-activation
plan: 03
subsystem: testing
tags: [pytest, dataclass, config, cli, xdist, openapi]

# Dependency graph
requires:
  - phase: 01-01
    provides: "SpecConfig dataclass with from_dict/to_dict and __post_init__ validation in settings.py"
provides:
  - "5 new CLI flags in pytest_addoption(): --coverage-config, --coverage-spec-name, --coverage-spec-path, --coverage-spec-url, --coverage-spec-base-url"
  - "CoverageSettings.specs field (list[SpecConfig], default empty)"
  - "CoverageSettings.is_enabled() returns True when specs is non-empty"
  - "CoverageSettings.to_dict() / from_dict() xdist-safe round-trip for specs"
  - "Single-spec CLI path assembles SpecConfig from CLI flags in from_pytest_config()"
  - "Swagger + multi-spec conflict guard with printed warning"
affects:
  - "01-04 (config file loader wiring builds on these CLI flags and specs field)"
  - "Phase 2+ (MultiSpecOrchestrator reads settings.specs)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "action=append with default=None for repeatable CLI flags (avoids argparse list mutation bug)"
    - "SpecConfig defined before CoverageSettings to resolve forward reference in specs field annotation"
    - "TODO comment pattern for deferred wiring: # TODO(Plan 04): add config file auto-discovery here"

key-files:
  created:
    - "tests/unit/test_settings.py"
  modified:
    - "src/pytest_api_coverage/config/settings.py"
    - "src/pytest_api_coverage/plugin.py"

key-decisions:
  - "SpecConfig moved before CoverageSettings in settings.py to avoid forward reference issues with the specs field annotation"
  - "--coverage-spec-base-url uses action=append, default=None (not default=[]) to prevent argparse list mutation across test invocations"
  - "Swagger + spec-flags conflict: swagger wins, specs is [], warning printed; this keeps the existing single-spec path simple"
  - "No base_urls case: skip SpecConfig assembly and print warning rather than raise (graceful degradation at CLI layer)"
  - "Config file auto-discovery intentionally deferred to Plan 04 via TODO comment; Plan 03 only handles CLI flags"
  - "Path('./auth.yaml') normalises to Path('auth.yaml') in Python — test assertions updated to match actual Path normalisation behaviour"

patterns-established:
  - "CLI spec flags pattern: name + (path | url) + base_url(s) assembles a single SpecConfig"
  - "Conflict guard pattern: if swagger AND any spec flag -> print warning, swagger wins, specs empty"

requirements-completed: [CFG-04, CFG-05, SET-01]

# Metrics
duration: 3min
completed: 2026-03-11
---

# Phase 1 Plan 03: CoverageSettings Extension + CLI Flags Summary

**5 new CLI flags registered in plugin.py and CoverageSettings extended with specs field, is_enabled()/to_dict()/from_dict()/from_pytest_config() updated for single-spec CLI path and swagger conflict guard**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-11T12:05:55Z
- **Completed:** 2026-03-11T12:08:33Z
- **Tasks:** 1 (TDD)
- **Files modified:** 3

## Accomplishments

- Registered 5 new CLI flags in `pytest_addoption()` for multi-spec configuration (`--coverage-config`, `--coverage-spec-name`, `--coverage-spec-path`, `--coverage-spec-url`, `--coverage-spec-base-url`)
- Extended `CoverageSettings` with `specs: list[SpecConfig]` field and updated all four methods
- 11 unit tests covering all scenarios; no regressions in 29 existing tests

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — Failing tests** - `0afc243` (test)
2. **Task 1: GREEN — Implementation** - `7e72422` (feat)

_Note: TDD tasks have multiple commits (test -> feat)_

## Files Created/Modified

- `tests/unit/test_settings.py` - 11 unit tests for CoverageSettings extension (specs field, is_enabled, to_dict, from_dict, from_pytest_config)
- `src/pytest_api_coverage/config/settings.py` - SpecConfig moved before CoverageSettings; specs field added; is_enabled, to_dict, from_dict, from_pytest_config updated
- `src/pytest_api_coverage/plugin.py` - 5 new addoptions added after --coverage-split-by-origin

## Decisions Made

- **SpecConfig order change:** Moved `SpecConfig` before `CoverageSettings` in `settings.py` so the `specs: list[SpecConfig]` annotation resolves without forward reference issues. This is a non-breaking structural change — public API unchanged.
- **`default=None` for `--coverage-spec-base-url`:** The `action="append"` argparse flag must use `default=None` not `default=[]` to prevent list mutation across test runs.
- **Swagger conflict guard:** When both `--swagger` and any spec flag are present, swagger wins and a warning is printed. This matches the plan spec exactly.
- **Path normalisation:** `Path("./auth.yaml")` normalises to `Path("auth.yaml")` in Python's pathlib. Test assertions corrected to expect `"auth.yaml"` not `"./auth.yaml"`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Path normalisation in test assertions**
- **Found during:** Task 1 GREEN phase (running tests)
- **Issue:** Test asserted `spec_dict["path"] == "./auth.yaml"` but `Path("./auth.yaml")` normalises to `Path("auth.yaml")` in pathlib, so `to_dict()` returns `"auth.yaml"`. Same issue in `test_from_pytest_config_cli_spec_path`.
- **Fix:** Updated two test assertions to expect `"auth.yaml"` and `Path("auth.yaml")` respectively
- **Files modified:** `tests/unit/test_settings.py`
- **Verification:** All 11 tests pass after fix
- **Committed in:** `7e72422` (feat commit, updated test file included)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug: incorrect test assertion for Path normalisation)
**Impact on plan:** Assertion corrected to match actual Python pathlib behaviour. No functional impact.

## Issues Encountered

- Pre-existing test failure in `tests/test_split_by_origin.py::test_combined_summary_aggregates` (assert 4 == 3). Not caused by this plan's changes. Logged to `deferred-items.md`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `CoverageSettings.specs` field is stable; Plan 04 can now add config file auto-discovery in `from_pytest_config()`
- All 5 CLI flags registered; Plan 04 can read `coverage_config` to locate config file
- `specs` field is xdist-safe (to_dict/from_dict round-trip verified)
- 177 tests passing (1 pre-existing failure in split_by_origin unrelated to this plan)

---
*Phase: 01-config-and-activation*
*Completed: 2026-03-11*

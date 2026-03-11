---
phase: 01-config-and-activation
plan: 02
subsystem: config
tags: [yaml, json, config-loader, tdd, file-io]

# Dependency graph
requires:
  - "SpecConfig dataclass from 01-01 (settings.py)"
provides:
  - "load_multi_spec_config() — parses YAML/JSON config file into list[SpecConfig] + top-level settings dict"
  - "_discover_config_file() — auto-discovers coverage-config.yaml or .json in a rootpath"
  - "tests/unit/test_multi_spec_loader.py — 12 unit tests for the loader module"
affects:
  - "01-03 (CoverageSettings.from_pytest_config will call _discover_config_file and load_multi_spec_config)"
  - "01-04 (multi-spec activation uses loaded specs)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure function module pattern: no pytest config, no CLI, no side effects beyond print() warnings"
    - "Warn-and-skip pattern: invalid config entries produce warnings but never raise; callers always get a valid (possibly empty) list"
    - "Real temp files in tests (tmp_path fixture) rather than mocked file I/O"

key-files:
  created:
    - "src/pytest_api_coverage/config/multi_spec.py"
    - "tests/unit/test_multi_spec_loader.py"
  modified: []

key-decisions:
  - "Use print() for warnings (not warnings.warn) to match project convention established in loader spec"
  - "top_level dict excludes 'specs' key so callers get only settings (output_dir, formats, etc.)"
  - "Return ([], {}) on any parse failure — never raise — so pytest_configure can handle absence gracefully"
  - "Real temp files in tests via tmp_path — no mocking, cleaner and more reliable for pure file I/O"

requirements-completed: [CFG-02, CFG-03]

# Metrics
duration: 2min
completed: 2026-03-11
---

# Phase 1 Plan 02: Multi-Spec Loader Summary

**YAML/JSON config loader with warn-and-skip validation and auto-discovery, fully tested with 12 unit tests using real temp files**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-11T12:05:51Z
- **Completed:** 2026-03-11T12:07:11Z
- **Tasks:** 1 (TDD = 2 commits)
- **Files modified:** 2

## Accomplishments

- Created `src/pytest_api_coverage/config/multi_spec.py` as a pure function module with no pytest/CLI dependencies
- `load_multi_spec_config()` handles YAML and JSON, warns and skips invalid entries (missing name, empty urls, both path+url set), returns `([], {})` on file read/parse failure
- `_discover_config_file()` probes for `coverage-config.yaml` then `coverage-config.json`, warns when both exist
- 12 unit tests using real temp files (tmp_path fixture) — no mocking of file I/O

## Task Commits

Each TDD phase committed atomically:

1. **RED: Failing tests** - `738b7ad` (test)
2. **GREEN: Implementation** - `64502aa` (feat)

## Files Created/Modified

- `src/pytest_api_coverage/config/multi_spec.py` — loader module with `load_multi_spec_config`, `_parse_spec_entry`, `_discover_config_file`
- `tests/unit/test_multi_spec_loader.py` — 12 unit tests covering all spec behaviors and discovery logic

## Decisions Made

- `print()` used for warnings (not `warnings.warn`) — consistent with the project spec and avoids pytest warning capture complexity.
- `top_level` dict is built by excluding the `specs` key, so callers receive only the top-level settings they care about (e.g., `output_dir`, `formats`).
- Parse failures return `([], {})` and never raise — `pytest_configure` can decide how to handle a missing/corrupt config file.
- Tests use `tmp_path` with real YAML/JSON files — simpler and more reliable than mocking for a pure file I/O module.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing test failures noted (not caused by this plan):
- `tests/unit/test_settings.py` — 6 failures are the RED phase tests from Plan 01-03 (CoverageSettings extension), intentionally failing pending that plan's implementation.
- `tests/test_split_by_origin.py::test_combined_summary_aggregates` — pre-existing failure unrelated to config loading.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `load_multi_spec_config` and `_discover_config_file` are ready for Plan 01-03 to wire into `CoverageSettings.from_pytest_config`
- All 12 new loader tests pass; no regressions to previously-passing tests

---
*Phase: 01-config-and-activation*
*Completed: 2026-03-11*

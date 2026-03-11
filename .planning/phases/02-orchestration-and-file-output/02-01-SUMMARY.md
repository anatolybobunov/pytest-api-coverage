---
phase: 02-orchestration-and-file-output
plan: "02-01"
subsystem: writers, config/settings
tags: [tdd, prefix, serialisation, xdist, SpecConfig, write_reports]
dependency_graph:
  requires: []
  provides: [write_reports-prefix-param, SpecConfig-round-trip-verified]
  affects: [02-02-multi-spec-orchestrator, 02-03-xdist-serialisation]
tech_stack:
  added: []
  patterns: [optional-trailing-param, f-string-stem, to_dict/from_dict]
key_files:
  created: []
  modified:
    - src/pytest_api_coverage/writers/__init__.py
    - tests/test_writers.py
    - tests/test_settings.py
decisions:
  - "prefix param added as fourth positional/keyword arg with default None — existing 3-arg call sites unchanged"
  - "stem computed once as f'{prefix}-coverage' if prefix else 'coverage' — all three formats share the same stem expression"
  - "SpecConfig round-trip tests confirm Phase 1 implementation is xdist-safe — no code changes needed"
metrics:
  duration: "2 min"
  completed: "2026-03-11T13:38:28Z"
  tasks_completed: 2
  files_modified: 3
---

# Phase 2 Plan 01: write_reports() prefix param + SpecConfig round-trip tests Summary

**One-liner:** Optional `prefix` param added to `write_reports()` producing `{prefix}-coverage.{ext}` filenames; SpecConfig xdist JSON serialisation verified green with 4 round-trip tests.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Add prefix param to write_reports() — RED then GREEN | 6ac0852 (RED), 279890c (GREEN) | tests/test_writers.py, src/pytest_api_coverage/writers/__init__.py |
| 2 | SpecConfig round-trip test — RED then GREEN | 05182e2 | tests/test_settings.py |

## What Was Built

### write_reports() prefix parameter (SET-02)

Added `prefix: str | None = None` as the fourth parameter to `write_reports()`. The implementation computes a single `stem` variable: `f"{prefix}-coverage" if prefix else "coverage"`, which is reused across all three format writers. This ensures:

- `write_reports(data, dir, formats)` — produces `coverage.json/csv/html` (unchanged)
- `write_reports(data, dir, formats, prefix=None)` — same as above
- `write_reports(data, dir, formats, prefix="auth")` — produces `auth-coverage.json/csv/html`

### SpecConfig round-trip verification (COMPAT-03)

Added `TestSpecConfigRoundTrip` to `tests/test_settings.py` with four tests verifying that `SpecConfig` serialises safely for xdist inter-process communication:

- `test_round_trip_with_path` — Path field converts to `str` in `to_dict()`, restores to `Path` after `from_dict()`
- `test_round_trip_with_url` — url field round-trips correctly; path is None
- `test_round_trip_multi_url` — multiple URLs preserved
- `test_path_none_round_trips` — None path serialises as None (not omitted)

All four passed immediately confirming the Phase 1 implementation was correct.

## Verification

```
uv run pytest tests/test_writers.py tests/test_settings.py -q
49 passed in 0.06s
```

## Deviations from Plan

None — plan executed exactly as written. The SpecConfig tests passed on first run as the plan predicted.

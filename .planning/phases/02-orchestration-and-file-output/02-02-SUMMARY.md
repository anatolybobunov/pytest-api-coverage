---
phase: 02-orchestration-and-file-output
plan: "02-02"
subsystem: api
tags: [orchestrator, routing, multi-spec, coverage, openapi]

# Dependency graph
requires:
  - phase: 02-01
    provides: write_reports() with prefix param; SpecConfig serialisation
  - phase: 01-config-and-activation
    provides: CoverageSettings, SpecConfig dataclasses
provides:
  - MultiSpecOrchestrator class (src/pytest_api_coverage/orchestrator.py)
  - Per-spec CoverageReporter creation at init
  - route_interaction() with origin + path-prefix matching, first-match-wins
  - process_interactions() routing with unmatched_count tracking
  - generate_all_reports() with prefixed filenames via write_reports()
affects:
  - 02-03-plugin-wiring (depends on MultiSpecOrchestrator.generate_all_reports())

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Try/except per spec load with warn-and-skip (never raise from _load_all_specs)
    - First-match-wins routing via ordered _specs list
    - Trailing-slash guard for path-prefix: startswith(spec_path + "/") prevents /auth matching /authentic

key-files:
  created:
    - src/pytest_api_coverage/orchestrator.py
    - tests/unit/test_orchestrator.py
  modified: []

key-decisions:
  - "MultiSpecOrchestrator._matches_spec uses origin check first, then path-prefix with trailing-slash guard"
  - "All spec load failures produce warn+skip; if ALL fail _specs is empty and orchestrator is silent no-op"
  - "Overlapping URL warning at load time uses exact string comparison across spec.urls lists"

patterns-established:
  - "Pattern 1: _load_all_specs() wraps each spec in try/except — consistent with existing _load_swagger() convention"
  - "Pattern 2: process_interactions() wraps single interaction in list when delegating to CoverageReporter"

requirements-completed: [ORC-01, ORC-02]

# Metrics
duration: 4min
completed: 2026-03-11
---

# Phase 2 Plan 02: MultiSpecOrchestrator Summary

**MultiSpecOrchestrator class with origin + path-prefix routing (first-match-wins), per-spec CoverageReporter creation, and prefixed report generation via write_reports()**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-11T13:41:10Z
- **Completed:** 2026-03-11T13:45:00Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments

- `MultiSpecOrchestrator` class created with full routing and reporting lifecycle
- 9 unit tests covering all specified behaviors — all green
- Trailing-slash path-prefix guard ensures `/auth` matches `/auth/users` but not `/authentic`
- `unmatched_count` increments for interactions matching no registered spec URL

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing orchestrator tests (RED)** - `3892a29` (test)
2. **Task 2: Implement MultiSpecOrchestrator (GREEN)** - `64844c5` (feat)

_Note: TDD plan — test commit then implementation commit._

## Files Created/Modified

- `src/pytest_api_coverage/orchestrator.py` - MultiSpecOrchestrator class; routing, loading, reporting
- `tests/unit/test_orchestrator.py` - 9 unit tests covering init, routing, path-prefix, unmatched count, process_interactions

## Decisions Made

- `_matches_spec` checks origin equality first, then path-prefix with `startswith(normalized_spec + "/")` guard to prevent partial-segment matches
- Overlapping URL detection uses exact URL string comparison (not normalized origin) — matches the spec.urls values as provided by the user
- `process_interactions()` wraps each single interaction in a list `[interaction]` when calling reporter, consistent with `CoverageReporter.process_interactions(interactions: list[dict])` signature

## Deviations from Plan

None - plan executed exactly as written. The provided implementation sketch in Task 2 was used directly with no modifications needed.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `MultiSpecOrchestrator` is ready for plugin wiring in Plan 02-03
- `generate_all_reports()` is the single call point the plugin needs at session end
- `process_interactions()` ready to receive routed interactions from plugin layer
- Full unit test coverage — no known edge cases outstanding

---
*Phase: 02-orchestration-and-file-output*
*Completed: 2026-03-11*

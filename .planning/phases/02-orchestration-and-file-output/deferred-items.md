# Deferred Items — Phase 02

## Pre-existing Test Failures (Out of Scope)

### test_split_by_origin.py::TestSplitByOriginCoverage::test_combined_summary_aggregates

- **Found during:** Plan 02-03, Task 2 full suite run
- **Status:** Pre-existing failure (confirmed by stash test: fails on commit 8ba77cc before any plugin wiring changes)
- **Error:** `AssertionError: assert 4 == 3` — `combined["covered_endpoints"]` returns 4 instead of expected 3
- **Location:** `tests/test_split_by_origin.py:157`
- **Cause:** Test asserts `covered_endpoints` is the max across origins (3), but implementation appears to count unique covered endpoints across all origins (4)
- **Impact:** Does not affect multi-spec output functionality; test is for split_by_origin mode (legacy feature)
- **Recommendation:** Fix test expectation or fix `combined_summary` aggregation logic in a dedicated plan

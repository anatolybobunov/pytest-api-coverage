# Deferred Items

Items discovered during plan execution that are out of scope for the current plan.

## Pre-existing Test Failure

**Discovered during:** 01-03 execution
**File:** `tests/test_split_by_origin.py::TestSplitByOriginCoverage::test_combined_summary_aggregates`
**Status:** Pre-existing failure, not caused by Plan 03 changes
**Issue:** `assert 4 == 3` — combined summary `covered_endpoints` assertion mismatch
**Action needed:** Investigate in a future plan or as a separate fix; the reporter logic
for `covered_endpoints` aggregation across origins appears off-by-one.

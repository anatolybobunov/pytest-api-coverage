# Roadmap: pytest-api-coverage Multi-Spec

## Overview

The plugin currently supports one specification per run. This work adds multi-spec support: users define multiple OpenAPI specs mapped to service URLs, run one `pytest`, and get separate coverage reports per spec. Three phases deliver this incrementally — config parsing first, then orchestration and file output, then terminal summary and compatibility hardening.

## Phases

- [x] **Phase 1: Config and Activation** - Parse multi-spec configuration from all sources and activate the plugin correctly (completed 2026-03-11)
- [ ] **Phase 2: Orchestration and File Output** - Route requests to per-spec reporters and write prefixed report files
- [ ] **Phase 3: Terminal Summary and Compatibility** - Display per-spec summary, validate backward compatibility, confirm xdist works

## Phase Details

### Phase 1: Config and Activation
**Goal**: Users can configure multi-spec coverage through any of three sources — config file, CLI flags, or auto-discovery — and the plugin activates correctly for each
**Depends on**: Nothing (first phase)
**Requirements**: CFG-01, CFG-02, CFG-03, CFG-04, CFG-05, SET-01
**Success Criteria** (what must be TRUE):
  1. User can run `pytest --coverage-config=coverage-config.yaml` and the plugin reads all specs from the file
  2. User can place `coverage-config.yaml` in project root and the plugin discovers it automatically without any flags
  3. User can run `pytest --coverage-spec-name=auth --coverage-spec-path=./auth.yaml --coverage-spec-url=https://auth.example.com` for a single spec via CLI
  4. Running `pytest --swagger=spec.yaml --coverage-spec-path=./auth.yaml` produces a clear error explaining the flags cannot be combined
  5. `is_enabled()` returns `True` when any of `--swagger`, `--coverage-spec-path`, or a discovered config file is present
**Plans**: 4 plans

Plans:
- [ ] 01-01-PLAN.md — SpecConfig dataclass + tests/unit/ scaffold (CFG-01, TDD)
- [ ] 01-02-PLAN.md — multi_spec.py config loader + _discover_config_file() (CFG-01, CFG-02, CFG-03, TDD)
- [ ] 01-03-PLAN.md — CLI flags in plugin.py + CoverageSettings.specs extension (CFG-04, CFG-05, SET-01, TDD)
- [ ] 01-04-PLAN.md — Wire loader into from_pytest_config() + integration tests (CFG-02, CFG-03)

### Phase 2: Orchestration and File Output
**Goal**: HTTP requests are routed to the correct per-spec reporter and each spec produces its own set of output files with the spec name as prefix
**Depends on**: Phase 1
**Requirements**: ORC-01, ORC-02, ORC-03, OUT-01, SET-02, COMPAT-03
**Success Criteria** (what must be TRUE):
  1. After a test run with two specs configured, two separate sets of report files exist: `auth-coverage.html` and `orders-coverage.html`
  2. An HTTP request to `https://orders.example.com/items` is counted in the orders spec report and not in the auth spec report
  3. An HTTP request to an unregistered URL causes no error and does not appear in any spec report
  4. `write_reports()` called with `prefix=None` produces `coverage.json/html/csv` — identical to current behavior
  5. `SpecConfig` round-trips correctly through `to_dict()` / `from_dict()` without data loss
**Plans**: TBD

### Phase 3: Terminal Summary and Compatibility
**Goal**: Users see a readable per-spec summary in the terminal, the legacy `--swagger` flag works without any changes, and multi-spec mode survives pytest-xdist parallel runs
**Depends on**: Phase 2
**Requirements**: OUT-02, OUT-03, COMPAT-01, COMPAT-02
**Success Criteria** (what must be TRUE):
  1. Terminal output after a multi-spec run shows one line per spec with coverage percentage, request count, and output file name
  2. Terminal output includes a totals row showing aggregate coverage and a count of requests that matched no spec
  3. Running `pytest --swagger=spec.yaml` produces `coverage.json`, `coverage.html`, `coverage.csv` with no behavioral change from before this work
  4. Running tests with `pytest-xdist` (`-n auto`) in multi-spec mode produces the same report files as a non-parallel run
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Config and Activation | 4/4 | Complete   | 2026-03-11 |
| 2. Orchestration and File Output | 0/? | Not started | - |
| 3. Terminal Summary and Compatibility | 0/? | Not started | - |

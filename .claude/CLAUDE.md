# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

pytest-api-coverage is a pytest plugin for API test coverage analysis. It intercepts HTTP requests during test execution (from `requests` and `httpx` libraries), compares them against Swagger/OpenAPI specifications, and generates coverage reports in JSON, CSV, and HTML formats.

## Build & Development Commands

```bash
# Install with dev dependencies (uses uv)
uv sync --dev

# Run single test file with coverage
uv run pytest tests/test_collector.py --swagger=PATH_or_URL

# Run multiple test files with coverage
uv run pytest tests/ --swagger=PATH_or_URL

# Run multiple test files with coverage and pytest-xdist (parallel)
uv run pytest tests/ -n=4 --swagger=PATH_or_URL

# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type checking
uv run mypy src/
```
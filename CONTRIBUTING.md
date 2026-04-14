# Contributing to pytest-api-coverage

Thank you for your interest in contributing to pytest-api-coverage!

## Development Setup

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/anatolybobunov/pytest-api-coverage.git
cd pytest-api-coverage

# Install dependencies
uv sync --group dev
```

## Development Workflow

### Running Tests

```bash
uv run pytest tests/ -v
```

### Code Quality

Before submitting a PR, ensure your code passes all checks:

```bash
# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/

# Type checking
uv run ty check src/
```

## Pre-commit hooks

Install and run pre-commit hooks:

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

### Code Style

This project uses:
- [Ruff](https://github.com/astral-sh/ruff) for linting and formatting
- [ty](https://docs.astral.sh/ty/) for static type checking
- Line length: 120 characters
- Target Python version: 3.11+

## Submitting Changes

### Git Workflow

This project follows a `feature → dev → main` branching model:

- **`main`** — stable release branch. Do not open PRs directly to `main` unless explicitly asked by maintainers.
- **`dev`** — integration branch for all new work. Open your PRs here.
- **`feature/*`** — your feature branches, created from `dev`.

### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b {feat/fix/docs/refactor/test}/{branch name} dev`)
3. Make your changes
4. Run tests and linting
5. Commit your changes with a descriptive message
6. Push to your fork
7. Open a Pull Request **targeting the `dev` branch**

### Commit Messages and PR Titles

Use clear, descriptive commit messages:

- `feat: add new feature`
- `fix: resolve bug in X`
- `docs: update documentation`
- `refactor: improve code structure`
- `test: add tests for X`

**PR titles must also follow this format** — CI validates them automatically on every PR.

Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

Use `!` to indicate a breaking change: `feat!: redesign config format`

### Versioning

Version bumping is fully automated. When changes are merged into `main`, CI automatically determines the version bump type from the commit history:

- `fix:`, `docs:`, `refactor:`, etc. → **minor** version bump                                                                                                                                       
- `feat:` → **patch** version bump                                                                                                                                                                  
- `feat!:` or `BREAKING CHANGE` → **major** version bump 

**Do not manually change version numbers** in `pyproject.toml` or any other files.

## Project Structure

```
pytest-api-coverage/
├── src/pytest_api_coverage/
│   ├── adapters/           # HTTP interception (requests, httpx)
│   ├── config/             # Configuration settings
│   ├── schemas/            # Swagger/OpenAPI parsing
│   ├── writers/            # Report writers (JSON, CSV, HTML)
│   ├── collector.py        # Request collection
│   ├── reporter.py         # Coverage reporting
│   ├── plugin.py           # Pytest plugin entry point
│   └── models.py           # Data models
├── tests/                  # Test suite
├── docs/                   # Documentation
└── example_swagger_links.yml  # Example swagger link config
```

## Reporting Issues

When reporting issues, please include:

- Python version
- pytest version
- pytest-api-coverage version
- Minimal reproducible example
- Expected vs actual behavior

## Questions?

Feel free to open an issue for any questions about contributing.
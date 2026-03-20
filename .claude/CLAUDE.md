# CLAUDE.md

## Documentation

Use these guides based on task context:

| When you need to...                          | Read                                                  |
|----------------------------------------------|-------------------------------------------------------|
| Understand internal architecture / design    | [docs/architecture.md](docs/architecture.md)          |
| Write or modify plugin code / public API     | [docs/api-reference.md](docs/api-reference.md)        |
| Work with CLI options or pytest integration  | [docs/usage.md](docs/usage.md)                        |
| Change config handling or multi-spec support | [docs/configuration.md](docs/configuration.md)        |
| Modify report generation (HTML/JSON/CSV)     | [docs/reports.md](docs/reports.md)                    |
| Debug issues or understand edge cases        | [docs/troubleshooting.md](docs/troubleshooting.md)    |
| Set up dev environment or contribute         | [CONTRIBUTING.md](CONTRIBUTING.md)                    |
| Check install requirements or dependencies   | [docs/installation.md](docs/installation.md)          |
| Review release history                       | [CHANGELOG.md](CHANGELOG.md)                          |


## Planning Rules

Always structure plans as **Stages → Tasks → Parallelization**.

### Stages
- 2–7 high-level stages (milestones).

### Tasks
- Each stage → atomic, independent tasks.
- One task = one clear outcome.

### Parallelization
- Design tasks for parallel execution by agents.
- Minimize dependencies; if any — state explicitly.

### Agents
- Assign each task to an agent type (code, docs, research, review).

### Constraints
- Prefer parallel over sequential.

**MANDATORY: use this structure for all plans.**

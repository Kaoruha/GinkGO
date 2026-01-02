# Repository Guidelines

## Project Structure & Module Organization
- Source: `src/ginkgo/` (core packages: `core/`, `libs/`, `trading/`, `data/`, `features/`, `notifier/`, `quant_ml/`).
- CLI/API entry points: `main.py`, `api/main.py`.
- Tests: `test/` (unit tests under `test/unit/...`, utilities under `test/utils/...`, templates in `test/templates/`).
- Docs & assets: `docs/` (notebooks, guides); configs and tooling in `.conf/`, `feast_repo/`.

## Build, Test, and Development Commands
- Install (editable + dev tools): `pip install -e .[dev]` or `python ./install.py`.
- Lint/format: `ruff check .`, `black .` (line length 120).
- Type check: `mypy src` (strict mode; add types for new code).
- Run tests: `pytest -m "unit and not slow"` (fast unit set) or `pytest --cov=src/ginkgo --cov-report=term-missing`.
- CLI quick check: `ginkgo version`, `ginkgo dev server` (after install, CLI is globally available).

## Coding Style & Naming Conventions
- Python 3.8+; use 4‑space indents and type hints everywhere.
- Format with Black (120 cols). Keep imports clean; fix with Ruff.
- Naming: `snake_case` for functions/vars, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants, module names lowercase.
- Keep functions small, side‑effect free where possible; log via `ginkgo.libs.core.logger`.

## Testing Guidelines
- Framework: Pytest. File patterns: `test_*.py`, `*_test.py`; classes `Test*`, funcs `test_*`.
- Markers: `unit`, `integration`, `slow`, `performance`, `database`, `network`. Example: `pytest -m "unit and not slow"`.
- Coverage: maintain or improve; check `htmlcov/`. Place tests near domain (e.g., `test/unit/core/…`). See `test/templates/unit_test_template.py` for structure.

## Commit & Pull Request Guidelines
- Use Conventional Commits: `feat: …`, `fix: …`, `docs: …`, `refactor: …`, `test: …`, `chore: …`. Example: `feat(core): add DI container health checks`.
- PRs must include: clear description, rationale, test coverage, updated docs/CHANGELOG for user‑visible changes, and steps to validate.
- Before opening PR: run `ruff`, `black`, `mypy`, and `pytest` locally; no new warnings or type errors.

## Security & Configuration Tips
- Never commit secrets. Configure via `~/.ginkgo/config.yaml` and `~/.ginkgo/secure.yml` (use base64‑encoded credentials as in README).
- For tests that touch external systems, scope with `database`/`network` markers and provide opt‑in flags.


## Active Technologies
- Python 3.12.8 + ClickHouse, MySQL, MongoDB, Redis, Kafka, Typer, Rich, Pydantic (006-notification-system)
- ClickHouse (时序数据), MySQL (关系数据), MongoDB (文档数据), Redis (缓存) (006-notification-system)

## Recent Changes
- 006-notification-system: Added Python 3.12.8 + ClickHouse, MySQL, MongoDB, Redis, Kafka, Typer, Rich, Pydantic

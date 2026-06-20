---
name: python-testing
description: >
  Generate tests for Llamitai backend (FastAPI + async SQLAlchemy) following project conventions.
  Use when the user asks to "write tests", "add tests", "test this", "make test", "create test for",
  "increase coverage", or references a source file that needs testing. Handles all 4 architectural
  layers: domain (pure unit tests), application/use cases (mocked repos), infrastructure/repositories
  (async DB integration tests), and presentation/API (E2E HTTP integration tests).
  Always uses expects library, standalone functions, AAA pattern, and pytest fixtures.
---

# Python Testing — Llamitai Backend

Generate tests for Llamitai backend source files following project conventions.

## Workflow

1. Read the source file to test
2. Determine the **architectural layer** (domain, application, infrastructure, presentation)
3. Read existing fixtures in `tests/conftest.py` and relevant module `conftest.py` files
4. Read the **layer-specific patterns** from [references/patterns.md](references/patterns.md)
5. Generate the test file at the correct path
6. Run `cd backend && uv run pytest <test_file_path> -v` to verify
7. Run `cd backend && uv run ruff format <test_file_path>` to auto-format

## Path Convention

Source: `backend/src/<module>/<layer>/<feature>/<file>.py`
Test: `backend/tests/<module>/<layer>/<feature>/test_<file>.py`

Ensure `__init__.py` exists in every directory of the test path.

## Core Rules

- **`expects`** for all assertions — never bare `assert`
- **Standalone functions** — never classes with `@staticmethod`
- **AAA pattern** — blank line before Assert block
- **async by default** — use `async def test_...` for any test involving async code. `asyncio_mode = "auto"` is configured, so no `@pytest.mark.asyncio` decorator needed
- **No `scope='function'`** on fixtures — it's the default
- Test naming: `test_<action>__<scenario>` (double underscore separates action from scenario)

## Design Principles

- **One behavior per test** — each test verifies exactly one thing. Easier to diagnose failures.
- **Always test error paths** — don't just test happy paths. Test exceptions, not-found, invalid input.
- **Use parametrize for variants** — when testing the same logic with different inputs, use `@pytest.mark.parametrize`.
- **Test isolation** — no shared state between tests. Each test is independent.

## Available Fixtures

### Global (`tests/conftest.py`)
- `tenant_id`: random UUID
- `tenant`: `Tenant` domain entity (ACTIVE status)
- `setup_database` (session-scoped, autouse): creates all tables via async SQLAlchemy, disposes on teardown
- `async_session`: function-scoped `AsyncSession` for DB operations

### E2E API (`tests/api/conftest.py`)
- `api_key_header`: admin API key header dict
- `new_registered_user`: registers test user via HTTP
- `new_registered_tenant`: registers test tenant via HTTP
- `login_user`: `LoginTestContext` with `access_token`, `refresh_token`, `tenant_slug`, `tenant_id`

### Module-level (in `tests/<module>/conftest.py`)
Place mocked repositories here with `create_autospec(spec=Repository, spec_set=True, instance=True)`.

### Inline (in test file)
Use for fixtures specific to that test file only (e.g., `use_case`, `orm_instance`).

## Test Markers

```python
@pytest.mark.single       # Run with pytest -m single — for debugging one test
@pytest.mark.api           # Mark as API/E2E test
@pytest.mark.webhook       # Mark as webhook test
@pytest.mark.skip(reason="...")  # Skip with reason
```

Note: `asyncio_mode = "auto"` is set in `pyproject.toml`, so `@pytest.mark.asyncio` is NOT needed.

## Quick Reference by Layer

| Layer          | DB?  | Async? | Mocks?      | Fixture source                     |
|----------------|------|--------|-------------|-------------------------------------|
| Domain         | No   | No     | No          | inline or `conftest.py`             |
| Application    | No   | Yes    | Yes (repos) | `conftest.py` + module conftest     |
| Infrastructure | Yes  | Yes    | No          | `async_session` + factories         |
| Presentation   | Yes  | No*    | No          | `login_user` + `requests` (E2E)    |

*Presentation tests use `requests` (sync HTTP client) against a running server, not async.

For detailed patterns and examples per layer, see [references/patterns.md](references/patterns.md).

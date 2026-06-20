# Testing

Maps the three test kinds onto the 4 layers, and folds the essential patterns inline so this file
stands alone. Examples use the `projects` feature / `Project` entity.

## Test kind → layer

| Kind | Layer | DB? | Mocks? |
|---|---|---|---|
| Unit (pure) | `domain/` | no | no |
| Unit (mocked) | `application/` use cases | no | `AsyncMock(spec=…)` repos/buses/services |
| Integration | `infrastructure/repositories/` | real async DB + ORM factories | no |
| Functional / API | `presentation/` (HTTP) | running server | no (sync `requests`) |

Test path mirrors source: `src/[bounded_context]/[layer]/[file].py` → `tests/[bounded_context]/[layer]/test_[file].py`.
Every dir needs `__init__.py`.

## Non-negotiables

- **`expects`, never `assert`**: `expect(x).to(equal(y))`, `expect(r).to(be_a(Cls))`, `expect(x).to(be_none)`.
- **Standalone async functions**, never test classes. AAA layout with a blank line (often `# Arrange`/`# Act`/`# Assert` comments) before the assert block.
- **`asyncio_mode = "auto"`** (`pyproject.toml`) — async tests run without any decorator; do not add `@pytest.mark.asyncio`. API tests are sync and marked `@pytest.mark.api`.
- **Markers** (`pyproject.toml`): `single`, `api`, `webhook`. The default test target runs `-m 'not api'`; an `apis` target boots infra + waits before running `-m api`; a `single` target runs `-m single`.

## Application: mock at the boundary (conftest builder pattern)

Inject mocked repos/buses/services into the use case via fixtures. Stub async returns directly; use
`side_effect=lambda x: x` for a pass-through `persist`. Mock every collaborator named in the use case's
`__init__`. Error paths use `pytest.raises(<DomainError subclass>)`.

```python
@pytest.fixture
def mock_project_repository() -> AsyncMock:
    repository = AsyncMock(spec=ProjectRepository)
    repository.persist = AsyncMock(side_effect=lambda x: x)
    return repository

@pytest.fixture
def mock_notification_service() -> AsyncMock:
    return AsyncMock(spec=NotificationService)

async def test_project_creator_persists_project(mock_project_repository: AsyncMock) -> None:
    # Arrange
    creator = ProjectCreator(repository=mock_project_repository)

    # Act
    project = await creator.execute(name="Apollo", tenant_id=tenant_id)

    # Assert
    expect(project).to(be_a(Project))
    mock_project_repository.persist.assert_awaited_once()

async def test_project_getter_raises_when_missing(mock_project_repository: AsyncMock) -> None:
    mock_project_repository.find_by_id = AsyncMock(return_value=None)
    getter = ProjectGetter(repository=mock_project_repository)

    with pytest.raises(ProjectNotFoundError):
        await getter.execute(project_id=missing_id, tenant_id=tenant_id)
```

## Infrastructure: real DB + async factories

Session-scoped `setup_database` creates/disposes tables; function-scoped `async_session` yields a session
(in `tests/conftest.py`). The repo fixture takes that session; factories seed rows and must be torn down.

```python
@pytest.fixture
def project_repository(async_session) -> ProjectRepository:
    return SQLProjectRepository(session=async_session)

@pytest.fixture(scope="function")
async def tenant_orm() -> TenantORM:
    tenant_orm = await TenantORMFactory()
    yield tenant_orm
    await TenantORMFactory.clean_up()
```

Factories live in `src/common/database/factories/` (e.g. `TenantORMFactory`, `ProjectORMFactory`). They
extend `AsyncSQLAlchemyTestFactory`, bind `sqlalchemy_session = get_scoped_session()`, track created rows
by `uuid`, and **must** be torn down with `await <Factory>.clean_up()`. Create rows with kwargs:
`await ProjectORMFactory(tenant_id=tenant_orm.uuid, name="Apollo")`.

Always include a **wrong-tenant isolation test** — query a row under a different `tenant_id` and assert
`be_none`:

```python
async def test_find_by_id_isolates_by_tenant(
    project_repository: ProjectRepository, tenant_orm: TenantORM
) -> None:
    project = await ProjectORMFactory(tenant_id=tenant_orm.uuid, name="Apollo")

    found = await project_repository.find_by_id(
        project_id=project.uuid, tenant_id=other_tenant_id
    )

    expect(found).to(be_none)
    await ProjectORMFactory.clean_up()
```

## API: HTTP against the running server

Sync `requests` to `BASE_URL` (e.g. `os.environ["E2E_BASE_URL"]`). Session fixtures in
`tests/api/conftest.py` register/login and return a small login-context dataclass; protected routes send
the JWT, admin routes use an `x-api-key` header. Mark with `@pytest.mark.api` so the default target skips
them.

```python
@pytest.mark.api
def test_create_project(login_user) -> None:
    response = requests.post(
        f"{BASE_URL}/v1/projects",
        json={"name": "Apollo"},
        headers={"Authorization": f"Bearer {login_user.access_token}"},
    )

    expect(response.status_code).to(equal(201))
    expect(response.json()["data"]["name"]).to(equal("Apollo"))
```

## See also

- Pair with a dedicated testing skill if your project has one for deeper matcher/parametrize reference.
- [layers.md](layers.md) — the 4 layers these tests mirror.
- [repositories.md](repositories.md) · [use-cases.md](use-cases.md) · [cqrs-buses.md](cqrs-buses.md) — units under test.

# Test Patterns by Architectural Layer

## 1. Domain Layer — Pure Unit Tests

No DB, no mocks. Test Pydantic models, value objects, enums, domain logic.

```python
from uuid import uuid4

from expects import be_true, equal, expect

from src.common.domain.entities.tenants.tenant_user import TenantUser
from src.common.domain.enums.users import TenantUserStatus


def test_is_active__when_active_status():
    tenant_user = TenantUser(
        uuid=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        is_owner=False,
        status=TenantUserStatus.ACTIVE,
    )

    expect(tenant_user.is_active).to(be_true)


def test_check_permission__returns_true_for_owner():
    tenant_user = TenantUser(
        uuid=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        is_owner=True,
        status=TenantUserStatus.ACTIVE,
    )

    result = tenant_user.check_permission("any.permission")

    expect(result).to(be_true)
```

### When to use `freeze_time`
For domain logic that depends on current time:
```python
from freezegun import freeze_time

@freeze_time("2026-01-15")
def test_something__when_past_date():
    # ...
    expect(result.is_expired).to(be_true)
```

---

## 2. Application Layer — Use Cases with Mocked Repos

Mock repositories via `create_autospec`. Test orchestration logic. Use cases are **async** (dataclasses with `execute()` method).

### conftest.py for the module
```python
# tests/<module>/application/conftest.py
from unittest.mock import create_autospec

import pytest

from src.<module>.domain.repositories.<repo> import SomeRepository


@pytest.fixture
def some_repository():
    return create_autospec(spec=SomeRepository, spec_set=True, instance=True)
```

### Test file
```python
from uuid import uuid4

import pytest
from expects import be_a, be_true, equal, expect, raise_error

from src.users.application.use_cases.tenant_user.getter import TenantUserGetter


@pytest.fixture
def use_case(query_bus_mock, tenant):
    return TenantUserGetter(
        tenant_id=tenant.uuid,
        tenant_user_id=uuid4(),
        query_bus=query_bus_mock,
    )


async def test_execute__returns_user(use_case, tenant_user):
    # Arrange — configure mock returns on the query_bus_mock
    use_case.query_bus.ask.return_value = tenant_user

    result = await use_case.execute()

    expect(result).to(be_a(TenantUser))
    expect(result.uuid).to(equal(tenant_user.uuid))


async def test_execute__not_found_raises(use_case):
    use_case.query_bus.ask.return_value = None

    expect(calling(use_case.execute)).to(raise_error(EntityNotFound))
```

### Testing CommandBus dispatch
```python
from unittest.mock import call


async def test_execute__dispatches_command(use_case, command_bus_mock):
    await use_case.execute()

    expect(command_bus_mock.dispatch.call_args).to(
        equal(call(command=SomeCommand(tenant_id=use_case.tenant_id)))
    )
```

### Testing side effects with multiple calls
```python
async def test_execute__retries_on_transient_error(use_case, some_repository):
    some_repository.persist.side_effect = [
        ConnectionError("timeout"),
        tenant_user,  # succeeds on 2nd call
    ]

    result = await use_case.execute()

    expect(result).to(be_a(TenantUser))
    expect(some_repository.persist.call_count).to(equal(2))
```

---

## 3. Infrastructure Layer — Repository Integration Tests

Real DB via `async_session`. Use async factory-boy factories or direct model creation.

### conftest.py for repositories
```python
# tests/<module>/infrastructure/repositories/conftest.py
import pytest

from src.<module>.infrastructure.repositories.sql_<entity> import SQL<Entity>Repository


@pytest.fixture
def repository(async_session):
    return SQL<Entity>Repository(session=async_session)
```

### Test file
```python
from uuid import uuid4

import pytest
from expects import be_a, be_none, equal, expect

from src.common.domain.entities.tenants.tenant_user import TenantUser


async def test_find__returns_entity(repository, async_session):
    # Create test data directly via session
    # ...

    result = await repository.find(entity_id=some_id)

    expect(result).to(be_a(TenantUser))
    expect(result.uuid).to(equal(some_id))


async def test_find__not_found(repository):
    result = await repository.find(entity_id=uuid4())

    expect(result).to(be_none)


async def test_find__wrong_tenant_returns_none(repository, async_session):
    # Create test data for one tenant, query with another
    result = await repository.find(
        entity_id=some_id,
        tenant_id=uuid4(),
    )

    expect(result).to(be_none)
```

### Testing persist (create + update)
```python
async def test_persist__creates_new(repository, tenant):
    entity = TenantUser(
        uuid=uuid4(),
        tenant_id=tenant.uuid,
        user_id=uuid4(),
        is_owner=False,
        status=TenantUserStatus.ACTIVE,
    )

    result = await repository.persist(instance=entity)

    expect(result).to(be_a(TenantUser))
    expect(result.uuid).to(equal(entity.uuid))
```

---

## 4. Presentation Layer — E2E API Integration Tests

Full HTTP cycle with `requests` against a running server. These tests require the backend to be running (typically via Docker).

### conftest.py
```python
# tests/api/conftest.py — already provides:
# - api_key_header: admin API key
# - login_user: LoginTestContext with tokens
# - new_registered_user / new_registered_tenant: setup fixtures
```

### Test file
```python
import pytest
import requests
from expects import equal, expect

from src.common.domain.constants.status import HTTP_200_OK, HTTP_401_UNAUTHORIZED

BASE_URL = "http://api:8200"

pytestmark = [pytest.mark.api]


def test_get_tenant_users__authenticated(login_user):
    response = requests.get(
        url=f"{BASE_URL}/v1/tenants/users",
        headers={"Authorization": f"Bearer {login_user.access_token}"},
        timeout=30,
    )

    expect(response.status_code).to(equal(HTTP_200_OK))


def test_get_tenant_users__unauthenticated():
    response = requests.get(
        url=f"{BASE_URL}/v1/tenants/users",
        timeout=30,
    )

    expect(response.status_code).to(equal(HTTP_401_UNAUTHORIZED))


def test_create_tenant_user__returns_created(login_user):
    response = requests.post(
        url=f"{BASE_URL}/v1/tenants/users",
        json={
            "email": "newuser@example.com",
            "password": "SecureP@ss123",
            "firstName": "New",
            "lastName": "User",
        },
        headers={"Authorization": f"Bearer {login_user.access_token}"},
        timeout=30,
    )

    expect(response.status_code).to(equal(201))
    data = response.json()["data"]
    expect(data["firstName"]).to(equal("New"))
```

---

## Parametrized Tests

Use `@pytest.mark.parametrize` when testing the same logic with different inputs.

### Enums and choices
```python
import pytest
from expects import equal, expect

from src.common.domain.enums.users import TenantUserStatus


@pytest.mark.parametrize("value,expected", [
    ("ACTIVE", TenantUserStatus.ACTIVE),
    ("PENDING", TenantUserStatus.PENDING),
    ("INACTIVE", TenantUserStatus.INACTIVE),
])
def test_from_value__valid(value, expected):
    result = TenantUserStatus.from_value(value)

    expect(result).to(equal(expected))


@pytest.mark.parametrize("invalid_value", ["INVALID", "", None])
def test_from_value__invalid_returns_none(invalid_value):
    result = TenantUserStatus.from_value(invalid_value)

    expect(result).to(be_none)
```

### Use `pytest.param` for custom IDs
```python
@pytest.mark.parametrize("status,is_active", [
    pytest.param(TenantUserStatus.ACTIVE, True, id="active-user"),
    pytest.param(TenantUserStatus.PENDING, False, id="pending-user"),
    pytest.param(TenantUserStatus.INACTIVE, False, id="inactive-user"),
])
def test_is_active__by_status(status, is_active):
    tenant_user = TenantUser(
        uuid=uuid4(), tenant_id=uuid4(), user_id=uuid4(),
        is_owner=False, status=status,
    )

    expect(tenant_user.is_active).to(equal(is_active))
```

---

## One Behavior Per Test

Each test verifies exactly one thing. Makes failures easy to diagnose.

```python
# BAD — testing multiple behaviors
async def test_user_service(use_case, repository):
    user = await use_case.create(data)
    expect(user.uuid).not_to(be_none)
    expect(user.email).to(equal(data["email"]))
    updated = await use_case.update(user.uuid, {"first_name": "New"})
    expect(updated.first_name).to(equal("New"))

# GOOD — focused tests
async def test_create__assigns_uuid(use_case, repository):
    user = await use_case.create(data)

    expect(user.uuid).not_to(be_none)


async def test_create__stores_email(use_case, repository):
    user = await use_case.create(data)

    expect(user.email).to(equal(data["email"]))


async def test_update__changes_first_name(use_case, repository):
    updated = await use_case.update(user_id, {"first_name": "New"})

    expect(updated.first_name).to(equal("New"))
```

---

## Always Test Error Paths

Don't just test happy paths. Every public method should have tests for:
- Not found / empty results
- Invalid input / validation errors
- Domain exceptions (`DomainError` subclasses with code, message, status_code)
- Unauthorized / forbidden access (API layer)

```python
async def test_execute__not_found_raises(use_case, repository):
    repository.find.return_value = None

    expect(calling(use_case.execute, user_id=uuid4())).to(
        raise_error(EntityNotFound)
    )


def test_check_permission__returns_false_for_inactive_user():
    inactive_user = TenantUser(
        uuid=uuid4(), tenant_id=uuid4(), user_id=uuid4(),
        is_owner=False, status=TenantUserStatus.INACTIVE,
    )

    result = inactive_user.check_permission("users.read")

    expect(result).to(be_false)
```

---

## Multi-tenant Testing

Always verify tenant isolation:
```python
async def test_find__wrong_tenant_returns_none(repository):
    result = await repository.find(
        entity_id=some_id,
        tenant_id=uuid4(),  # Random tenant
    )

    expect(result).to(be_none)
```

---

## Expects Matchers Reference

```python
from expects import (
    be_a,           # expect(x).to(be_a(SomeClass))
    be_empty,       # expect(list).to(be_empty)
    be_false,       # expect(x).to(be_false)
    be_none,        # expect(x).to(be_none)
    be_true,        # expect(x).to(be_true)
    contain,        # expect(list).to(contain(item))
    equal,          # expect(x).to(equal(y))
    have_key,       # expect(dict).to(have_key('key'))
    have_length,    # expect(list).to(have_length(3))
    raise_error,    # expect(callable).to(raise_error(SomeError))
)

# Negation
expect(x).not_to(be_none)
expect(x).not_to(equal(y))
```

---

## What NOT to Test

- `config/` — app configuration and startup
- `src/common/database/versions/` — Alembic migrations
- `src/*/presentation/router.py` — route registration (just wiring)
- `scripts/` — seed and CLI scripts with heavy I/O
- `__init__.py` files
- Temporal workflow definitions (`src/workflows/`) — test the activities, not the workflow orchestration

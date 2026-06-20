---
title: Add a Use Case
description: The most common backend contribution — implement a new use case end-to-end.
difficulty: beginner
estimatedTime: 15 min
prerequisites:
  - Read the architecture overview
  - Have a backend dev environment running
sidebar:
  order: 1
---

This guide walks you through adding a new backend use case — the most common contribution flow. We'll add a `SendInvite` use case to the `auth` module.

## The use case

```python
@dataclass
class SendInvite(UseCase[SendInviteCommand, None]):
    users: UserRepository
    mailer: Mailer
    clock: Clock

    async def execute(self, command: SendInviteCommand) -> None:
        user = await self.users.get_by_email(command.email)
        if user is None:
            return  # silent — never reveal whether an email exists
        token = self.clock.now().timestamp().__str__()
        await self.mailer.send_invite(user.email, token)
```

## Steps

### 1. Define the command

```python
# src/auth/application/commands/send_invite.py
from dataclasses import dataclass

@dataclass(frozen=True)
class SendInviteCommand:
    email: str
```

### 2. Implement the use case

```python
# src/auth/application/use_cases/send_invite.py
from typing import Protocol
from common.application.use_case import UseCase
from .commands.send_invite import SendInviteCommand

class UserRepository(Protocol):
    async def get_by_email(self, email: str) -> User | None: ...

class Mailer(Protocol):
    async def send_invite(self, email: str, token: str) -> None: ...

class Clock(Protocol):
    def now(self) -> datetime: ...

@dataclass
class SendInvite(UseCase[SendInviteCommand, None]):
    users: UserRepository
    mailer: Mailer
    clock: Clock

    async def execute(self, command: SendInviteCommand) -> None:
        user = await self.users.get_by_email(command.email)
        if user is None:
            return
        token = self.clock.now().isoformat()
        await self.mailer.send_invite(user.email, token)
```

### 3. Wire the route

```python
# src/auth/presentation/router.py
from ..application.use_cases.send_invite import SendInvite, SendInviteCommand

@router.post("/invites")
async def send_invite(
    body: SendInviteRequest,
    use_case: FromDishka[SendInvite],
):
    await use_case.execute(SendInviteCommand(email=body.email))
    return {"ok": True}
```

### 4. Register in the composition root

```python
# src/auth/composition.py
def build_send_invite(container: Container) -> SendInvite:
    return SendInvite(
        users=container.get(UserRepository),
        mailer=container.get(Mailer),
        clock=container.get(Clock),
    )
```

### 5. Add tests

```python
async def test_send_invite_sends_mail_when_user_exists():
    # Arrange
    users = Mock(UserRepository)
    users.get_by_email.return_value = User(email="a@b.c")
    mailer = Mock(Mailer)
    clock = Mock(Clock)
    use_case = SendInvite(users=users, mailer=mailer, clock=clock)

    # Act
    await use_case.execute(SendInviteCommand(email="a@b.c"))

    # Assert
    mailer.send_invite.assert_called_once()
```

## Checklist

- [ ] Command dataclass in `application/commands/`
- [ ] Use case in `application/use_cases/`
- [ ] Router in `presentation/router.py`
- [ ] Composition registration in `composition.py`
- [ ] Unit test in `tests/application/use_cases/`
- [ ] Integration test in `tests/presentation/`

## Common pitfalls

- **Don't** import SQLAlchemy models inside the use case. Depend on the repository interface.
- **Don't** call `httpx`, `requests`, or any HTTP client directly. Use a protocol-typed adapter.
- **Do** keep `execute()` side-effect ordered: validate → load → mutate → save → emit.

## Where to go next

- [Add an SSE Endpoint](/guides/add-an-sse-endpoint)
- [Add a BFF Route](/guides/add-a-bff-route)

---
title: Architecture
description: Doxiq follows Clean Architecture with DDD, separated by module.
sidebar:
  label: Architecture
  order: 3
---

Doxiq backend follows **Clean Architecture + DDD**. Every module is laid out as `domain → application → infrastructure → presentation`.

## Module layout

Each backend module has the same shape:

```
backend/src/<module>/
  domain/         # Pure business logic: entities, value objects, repository interfaces
  application/    # Use cases (commands + queries), DTOs
  infrastructure/ # SQL repositories, external adapters
  presentation/   # FastAPI routers, presenters
```

## Bounded contexts

```mermaid
flowchart TB
  subgraph Core
    Auth[auth]
    Users[users]
    Tenants[tenants]
    Profile[profile]
  end

  subgraph Workflow
    Industries[industries]
    Workflows[workflows]
    Extraction[extraction]
  end

  subgraph Knowledge
    KB[knowledge_base]
    Integrations[integrations]
    FS[file_storage]
  end

  subgraph Platform
    Common[common]
    Messaging[messaging]
  end

  Auth --> Users
  Users --> Tenants
  Workflows --> Industries
  Extraction --> Workflows
  Extraction --> KB
  Workflows --> Messaging
  Extraction --> FS
```

## Request lifecycle

```mermaid
sequenceDiagram
  participant Client
  participant BFF as Next.js BFF
  participant API as FastAPI
  participant UC as Use Case
  participant Repo as Repository
  participant DB as PostgreSQL
  participant Worker as Temporal

  Client->>BFF: POST /api/documents/upload
  BFF->>API: POST /api/v1/documents (with X-Api-Key)
  API->>UC: UploadDocument.execute()
  UC->>Repo: documents.create()
  Repo->>DB: INSERT
  UC->>Worker: workflow.start(extract)
  UC-->>API: Document (queued)
  API-->>BFF: 202 Accepted
  BFF-->>Client: 202 Accepted (stream URL)

  Worker->>DB: update status (running)
  Worker->>Worker: OCR + LLM + rules
  Worker->>DB: update status (completed)
  Worker-->>Client: SSE event
```

## Key patterns

### Use cases

A use case is a dataclass that implements a `UseCase` protocol and exposes `execute()`. It depends on **repository interfaces** declared in `domain/`, never on SQLAlchemy or HTTP clients.

```python
@dataclass
class UploadDocument(UseCase[UploadDocumentCommand, Document]):
    documents: DocumentRepository
    workflows: WorkflowRunner

    async def execute(self, command: UploadDocumentCommand) -> Document:
        doc = await self.documents.create(command.tenant_id, command.file)
        await self.workflows.start("extract", doc.id)
        return doc
```

### Repositories

Domain declares an abstract `Repository`; infrastructure provides the SQLAlchemy implementation. The use case receives the concrete instance through DI in `composition.py`.

### Presenters

Routers never return ORM models. They call a presenter that converts the domain entity into a camelCase response dict.

### Multi-tenant

Every query is scoped by `tenant_id` extracted from the JWT. The `tenant` module owns the JWT-issuing route; every other module reads `current_tenant` from a FastAPI dependency.

## Where to go next

- [Backend modules](/docs/backend/modules)
- [Add a Use Case](/guides/add-a-use-case)
- [Temporal Workflows](/guides/temporal-workflow)

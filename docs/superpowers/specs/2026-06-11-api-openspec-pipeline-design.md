# API OpenSpec Pipeline — Design

**Date:** 2026-06-11
**Status:** Draft (pending review)

## Problem

Doxiq has a FastAPI backend with many modules (auth, users, tenants, workflows,
extraction, knowledge_base, integrations, file_storage, industries, profile,
common, messaging). Every module exposes its own router, has its own use cases,
and ships its own Pydantic DTOs.

The docs site today has hand-written `.md` files under
`docs/src/content/api/` that try to document the same surface. They drift:

- The first session of this branch (fixing `RenderUndefinedEntryError`) showed
  the docs were already out of sync with the code (links in the sidebar to
  endpoints that never existed).
- Hand-typed OpenAPI examples go stale on every backend change.
- The "API" section in the docs is not navigable: there is no index, no
  "try-it" panel, and no machine-readable contract for SDK generators or
  Postman import.

We need **one source of truth** for the API surface, generated from the
backend code, that the docs site can render. The source must be easy to
refresh and easy to audit for quality.

## Goals

1. A single `openapi.json` (OpenAPI 3.1) that fully describes every HTTP
   endpoint exposed by the backend, including request/response schemas,
   status codes, tags, and security requirements.
2. A repeatable pipeline that re-generates the spec from source, with no
   hand edits to the JSON.
3. An LLM-driven audit pass that flags quality issues (missing summaries,
   missing field descriptions, untagged endpoints, etc.) without silently
   mutating the spec.
4. A docs page that renders the spec interactively.
5. The whole thing is a single `just spec` invocation, wired into CI.

## Non-Goals

- Documenting internal Temporal workflows or non-HTTP RPC patterns.
- Generating client SDKs (the OpenAPI spec enables it later; not in scope now).
- Replacing the hand-written `docs` (architecture, guides) content. Only the
  API reference surface is in scope.
- Making the LLM auto-edit the spec. The LLM is a **reporter**, not a writer.

## Architecture

```
backend/                              # source of truth (existing)
└── src/<module>/
    ├── presentation/routers/         # FastAPI routes
    ├── application/use_cases/        # UseCase[TCommand, TEntity] dataclasses
    └── application/dtos/             # Pydantic BaseModel DTOs
        │
        │  AST parse (no code execution)
        ▼
scripts/spec/
├── extractor.py            # AST walks → AST-graph JSON
├── emitter.py              # AST-graph → OpenAPI 3.1 JSON
├── llm_auditor.py          # OpenAPI + AST-graph → audit report (LLM)
├── llm_auditor_prompt.txt  # versioned prompt for the LLM auditor
├── models.py               # internal dataclasses (RouteNode, UseCaseNode, DTONode, ...)
├── openapi_types.py        # OpenAPI 3.1 dataclasses (paths, components, ...)
├── cli.py                  # argparse entry point
├── __main__.py             # `python -m spec`
├── pyproject.toml          # own deps (openapi-spec-validator, pytest, ...)
├── _build/                 # gitignored, generated artifacts
│   ├── ast-graph.json
│   └── audit-report.md
└── tests/
    ├── fixtures/
    ├── test_extractor.py
    ├── test_emitter.py
    ├── test_audit_heuristic.py
    └── test_e2e.py
        │
        │  emit
        ▼
docs/src/content/api/_generated/openapi.json   # generated, gitignored
        │
        │  consumed at build / SSR
        ▼
docs/src/pages/api-docs.astro                  # Stoplight Elements web component
```

Three independent stages, each idempotent. Every stage writes to
`scripts/spec/_build/` for caching and debugging.

## Components

### 1. `scripts/spec/extractor.py` — AST extraction

Reads `backend/src/**` with the stdlib `ast` module. **Does not import or
execute the backend.** For each module:

- **Routers**: detect calls to `add_api_route(path=..., methods=[...],
  ...)`, decorators `@router.get/post/put/patch/delete`, and
  `APIRouter({...})` prefixes. For each captured route, record:
  - `path`, `methods`, `endpoint_name`
  - `summary` / `description` from the docstring
  - `tags` from the prefix
  - `response_model`, `status_code` from the decorator or `add_api_route`
  - `dependencies` (auth, current_tenant, …) — captured by name, mapped to
    security schemes later
  - Pydantic types in the signature: `payload: CreateUserCommand`, `query:
    PageQuery`, path params from the URL pattern
- **Use cases**: dataclasses whose first base is `UseCase[...]` (or whose
  class name matches the project convention `*UseCase`). For each:
  - `name`, `module`
  - `command` type (first generic argument)
  - `return` type (second generic argument)
  - `dependencies`: the dataclass field types that are `Repository` or other
    port interfaces (used later to draw a dependency graph, optional v1.5)
- **DTOs**: any class that inherits from `pydantic.BaseModel` (also
  `BaseModel` from `pydantic.v1` if present). For each:
  - `name`, `module`, `qualname`
  - `fields`: name, python type, pydantic `Field(...)` metadata
    (description, default, examples, alias, …)

Output: `scripts/spec/_build/ast-graph.json` (one big JSON, schema defined
in `models.py` and versioned).

**Edge cases the extractor must handle:**

- Path parameters in FastAPI: `/items/{item_id}` → `parameters[].name =
  "item_id", in=path, required=true`.
- Multiple `@router.get(...)` decorators stacked: keep the first non-empty
  one.
- `add_api_route` invoked inside a function (sometimes used to register
  dynamic routes). We capture the literal arguments only.
- Re-exports (`from .dto import CreateUserCommand`) — we follow the import
  and capture the original definition site so `components.schemas` is
  deduplicated.
- Generic DTOs like `Page[T]`: emit `PageCreateUser` (specialize once per
  found instantiation) — keep simple: only specialize on classes that
  inherit from `Generic[T]` and have a concrete instantiation in the
  codebase. If no instantiation is found, emit a `Page` schema with
  `description: "uninstantiated generic Page[T] — auditor will flag"` and
  add a `x-unresolved-generics` entry to the OpenAPI root. This is a
  known limitation revisited in v1.5 (see Out of Scope).
- Re-export dedup: the dedup key is the fully-qualified class name
  (`module.qualname`). If a name is re-exported from multiple paths, the
  extractor keeps the first definition found in a deterministic
  alphabetical walk of `backend/src/**`. If two definitions with the
  same FQCN differ, the emitter exits non-zero with a "schema collision"
  error pointing to both files.

### 2. `scripts/spec/emitter.py` — AST → OpenAPI 3.1

Reads the AST-graph and emits a single `openapi.json` matching
OpenAPI 3.1.0. The structure:

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "Doxiq API",
    "version": "<from backend pyproject>",
    "description": "<from backend pyproject or a constant>"
  },
  "servers": [{ "url": "/api/v1" }],
  "tags": [
    { "name": "auth", "description": "..." },
    { "name": "users", "description": "..." }
  ],
  "paths": {
    "/auth/login": {
      "post": {
        "tags": ["auth"],
        "summary": "...",
        "description": "...",
        "security": [{ "ApiKeyAuth": [] }],
        "requestBody": { "$ref": "#/components/schemas/LoginCommand" },
        "responses": {
          "200": { "description": "OK", "content": { "application/json": { "schema": { "$ref": "#/components/schemas/TokenPair" } } } },
          "401": { "description": "Invalid credentials" }
        }
      }
    }
  },
  "components": {
    "securitySchemes": {
      "ApiKeyAuth": { "type": "apiKey", "in": "header", "name": "X-Api-Key" }
    },
    "schemas": {
      "LoginCommand": { "type": "object", "properties": { ... }, "required": [...] },
      "TokenPair":   { "type": "object", "properties": { ... }, "required": [...] }
    }
  }
}
```

Mapping rules:

- Python `str` → OpenAPI `{ "type": "string" }`
- `int` → `{ "type": "integer" }`
- `float` → `{ "type": "number", "format": "double" }`
- `bool` → `{ "type": "boolean" }`
- `datetime` → `{ "type": "string", "format": "date-time" }`
- `date` → `{ "type": "string", "format": "date" }`
- `UUID` → `{ "type": "string", "format": "uuid" }`
- `list[T]` → `{ "type": "array", "items": { "$ref": "...T..." } }`
- `dict[str, T]` → `{ "type": "object", "additionalProperties": { "$ref": "..." } }`
- `Optional[T]` / `T | None` → `{ "anyOf": [{ "$ref": "T" }, { "type": "null" }] }`
- `Literal["a", "b"]` → `{ "enum": ["a", "b"] }`
- `Enum` subclass → `{ "enum": [...member values...] }`
- Unresolved / `Any` → `{ "description": "unresolved type — auditor will flag", "nullable": true }` and the emitter records the path in `x-unresolved-types` at the OpenAPI root. The emitter exits non-zero if any unresolved types are present, unless the flag `--allow-unresolved` is passed (default: off). The `--fail-under` audit check also fails on unresolved types regardless of score.

`required` is built from Pydantic field metadata (anything without a
default and not marked `Optional`).

`security` is added globally (`security: [{ ApiKeyAuth: [] }]`) and
overridden per-route when the route uses a different dependency (e.g.
`OAuth2PasswordBearer` for `/auth/login`).

### 3. `scripts/spec/llm_auditor.py` — quality auditor

Reads both the AST-graph and the generated `openapi.json`. Calls an LLM
(model: configurable via env `SPEC_AUDITOR_MODEL`, default
`claude-sonnet-4-5`) with a fixed prompt stored in
`scripts/spec/llm_auditor_prompt.txt` (versioned alongside the code;
breaking prompt changes bump the `prompt_version` field in the report
metadata). The LLM returns a structured report:

```json
{
  "coverage_score": 0..100,
  "endpoints": [
    {
      "path": "/auth/login",
      "method": "post",
      "issues": [
        { "kind": "missing_summary", "severity": "high", "suggestion": "..." },
        { "kind": "missing_field_description", "field": "password", "severity": "medium", "suggestion": "..." }
      ]
    }
  ],
  "global_issues": [
    { "kind": "tagless_endpoints", "count": 3, "examples": ["/x", "/y"] },
    { "kind": "unresolved_types", "count": 7 }
  ]
}
```

The auditor **never writes to the spec**. It only emits
`scripts/spec/_build/audit-report.md` and prints a summary to stdout.

If `SPEC_AUDITOR_MODEL` is unset or `--no-llm` is passed, the auditor
falls back to a deterministic checker that catches the same issue kinds
with simpler heuristics (regex / JSON inspection) and marks them
`source: heuristic` in the report.

**Coverage score formula (deterministic, identical for LLM and
heuristic paths):**

```
score = 100
score -= 5 * count(missing_summary)
score -= 3 * count(missing_field_description)
score -= 2 * count(tagless_endpoint)
score -= 1 * count(missing_response_description)
score -= 10 * count(unresolved_type)
score -= 10 * count(schema_collision)
score = max(0, score)
```

The score is computed in Python from the issue list; the LLM may only
*add* issues, never override the score. CI uses the heuristic score by
default.

### 4. CLI

`scripts/spec/__main__.py` exposes a `spec` command group:

```bash
python -m spec extract    # AST → ast-graph.json
python -m spec emit       # ast-graph.json → openapi.json
python -m spec audit      # openapi.json + ast-graph.json → audit-report.md
python -m spec all        # extract && emit && audit
python -m spec diff       # show diff between working-tree openapi.json and the version last committed (git show HEAD:<path>)
```

Flags:
- `--backend-root PATH` (default: `backend`)
- `--out PATH` for `emit` (default: `docs/src/content/api/_generated/openapi.json`)
- `--no-llm` for `audit`
- `--model NAME` for `audit`
- `--fail-under N` for `audit` (exit non-zero if coverage score < N)
- `--allow-unresolved` for `emit` (allow unresolved types without
  exiting non-zero; default off)

### 5. Docs rendering: `docs/src/pages/api-docs.astro`

New page in the docs site. Loads the `openapi.json` (imported as a JSON
asset so SSR works) and mounts the **Stoplight Elements** web component:

```astro
---
import openapi from '@/content/api/_generated/openapi.json';
const specString = JSON.stringify(openapi);
---
<Layout title="API Reference">
  <elements-api
    apiDescriptionDocument={specString}
    router="hash"
    layout="sidebar"
    tryItCredentialsPolicy="include"
  />
  <script type="module" src="https://unpkg.com/@stoplight/elements/web-components.min.js"></script>
</Layout>
```

The page is reachable from the top nav (`/api-docs`) and from a "View
interactive API" button in the existing `/api/[...slug]` page (which
serves as the per-endpoint human-written narrative; the OpenAPI page is
the interactive mirror).

We do **not** delete `/api/[...slug].astro` — it now also links to
`/api-docs#<operationId>` for each endpoint it documents.

**Stoplight loading strategy (decided):** the web component is installed
as an npm dependency (`@stoplight/elements`) and bundled by Astro at
build time, **not** loaded from a CDN. This avoids the `unpkg.com`
outage risk and CSP friction. The `<script>` tag imports the local
package; no external network calls at runtime. License: BSD-3-Clause.

## Data Flow

1. Dev edits a router / DTO / use case in `backend/src/`.
2. `just spec` runs `python -m spec all` (or CI does).
3. `extractor` walks the AST, writes `ast-graph.json`.
4. `emitter` reads `ast-graph.json`, writes `openapi.json`.
5. `auditor` reads both, calls LLM (or heuristics), writes
   `audit-report.md`, prints summary.
6. Dev reads the report, fixes the source (e.g. adds a docstring), re-runs.
7. `docs` site is regenerated. `/api-docs` page picks up the new spec.

## Error Handling

- **Extractor fails on a file** (syntax error, unsupported pattern): log
  the file + reason to stderr, skip it, continue. The emitter reports
  which files were skipped so the user can fix them.
- **Emitter finds an unresolved type** (e.g. `Any`, a class defined in
  generated code): emit a placeholder schema, list it under
  `x-unresolved-types` in the OpenAPI root. The auditor will flag every
  entry.
- **Auditor API call fails** (rate limit, network): fall back to the
  heuristic auditor and mark the report `source: heuristic-fallback`.
- **OpenAPI spec is invalid** (fails JSON Schema validation against
  OpenAPI 3.1 metaschema): emitter exits non-zero. CI fails.

## Testing

- `scripts/spec/tests/test_extractor.py` — unit tests for AST walker
  using small fixture files in `scripts/spec/tests/fixtures/`. Fixtures
  are intentionally minimal: they are *not* a copy of the real backend,
  so they don't drift. They cover: bare `@router.get`, `add_api_route`
  with kwargs, stacked decorators, re-exported DTOs, generic DTO
  instantiations, Pydantic v1 and v2 base classes, `Enum` and `Literal`
  types.
- `scripts/spec/tests/test_emitter.py` — unit tests for type mapping
  (Python type → OpenAPI schema) and the route-to-path translation.
  Asserts: path parameters extracted, `required` array correct,
  `Optional[T]` rendered as `anyOf`, `Page[T]` specialization creates
  a new schema name, unresolved types produce `x-unresolved-types` and
  cause non-zero exit without `--allow-unresolved`.
- `scripts/spec/tests/test_audit_heuristic.py` — covers the no-LLM path
  with golden-output assertions for the coverage score formula.
- `scripts/spec/tests/test_e2e.py` — runs the full pipeline against a
  small synthetic backend fixture and asserts the output is valid
  OpenAPI 3.1 (validated with `openapi-spec-validator` pinned to
  `^0.7` in `scripts/spec/pyproject.toml`).
- `docs/src/pages/api-docs.astro` — Playwright smoke test in
  `docs/tests/api-docs.spec.ts`: load `/api-docs`, wait for the
  `elements-api` custom element to be defined, assert at least one
  operation is visible. This test runs in `just test-frontend` (it is
  *new*, not pre-existing).
- Coverage target for `scripts/spec/`: ≥ 90% line coverage. Enforced by
  `pytest --cov` in the pipeline test step.

## CI / Wiring

- `justfile` adds:
  - `spec` — runs `python -m spec all` (no LLM by default in CI for
    speed; pass `SPEC_LLM=1` to opt in).
  - `spec-audit` — runs `python -m spec audit --fail-under 80`.
  - `spec-diff` — runs `python -m spec diff` and fails if there's an
    uncommitted change to the generated `openapi.json`. The diff is
    against `HEAD` of the working tree (i.e. "what would be committed
    right now"). For long-lived branches, CI also runs a nightly
    `spec-diff-vs-main` job that diffs against `origin/main` and
    opens an issue if there's drift.
- `docs/src/content/api/_generated/openapi.json` is **gitignored**
  (path: `docs/src/content/api/_generated/`). It is regenerated on
  every docs build via a prebuild step in `package.json`. The first
  rollout commit includes a checked-in `openapi.json` for one cycle,
  so reviewers can see the initial output; that file is deleted in
  the rollout step 4.

## Risks & Open Questions

**Decided:**

- **Pydantic v1 vs v2 detection:** the extractor scans every import
  statement in `backend/src/**`. If `pydantic` resolves to a v2 install
  (default in new codebases), the v2 path is used (`BaseModel` from
  `pydantic`, `Field` from `pydantic`, `ConfigDict` allowed). If v1 is
  imported (`from pydantic import BaseModel` *and* the resolved module
  is `pydantic.v1`, or the file is pinned in `pydantic.v1` namespace),
  the v1 path is used. If both are present in the same file, the
  extractor emits a `pydantic-mixed-version` warning and falls back to
  v2 semantics. If neither is present, the file is skipped with a
  warning (no BaseModel = nothing to extract). Detection is logged in
  the AST-graph under `meta.pydantic_version`.
- **Stoplight Elements distribution:** bundled via npm
  (`@stoplight/elements`), not CDN. License BSD-3-Clause is compatible.
- **LLM cost:** CI uses the heuristic auditor (no LLM calls). LLM
  audits are local dev only, gated by `SPEC_LLM=1`. A typical audit
  is ~3-5K input + ~1-2K output tokens.

**Deferred to v1.5:**

- Robust generic DTO specialization (`Page[T]`, `Result[T]`). v1 emits
  what it can and flags the rest.

## Rollout

1. Land the extractor + emitter + heuristic auditor + CLI behind a
   `just spec` recipe. Land `api-docs.astro` reading a checked-in
   initial spec for verification.
2. Add the `just spec-audit` CI check.
3. Add the "View interactive API" link from existing `/api/[...slug]`
   pages.
4. Once stable, mark the checked-in initial spec as generated and
   gitignore it.

## Out of Scope (v1.5+)

- Generating Python / TypeScript SDKs from the spec.
- Documenting Temporal workflows separately.
- Auto-fixing the spec with the LLM (always human-in-the-loop).
- Runtime extraction (importing the FastAPI app to introspect live
  routes) as an alternative to AST parsing.

---

## Implementation Plan

The plan is split into **6 phases**. Each phase ends with a working,
verifiable artefact and a checkpoint. We commit at the end of every
phase.

### Reality check (from codebase exploration)

Before writing the plan we inspected the actual backend. Findings that
shape the implementation:

- The backend has **15 modules** with routers: `admin, auth, common,
  connections, dashboard, evals, industries, knowledge_base, profile,
  staff, storage, tenants, usage, users, workflows`.
- The full HTTP surface is composed in **`backend/config/router.py`**,
  which calls `api_router.include_router(<sub>, prefix="/v1", tags=[…])`.
  Parsing this file is the **most reliable way** to recover the final
  path prefix and tag for every route.
- Each module's `presentation/router.py` then either uses
  `add_api_route(...)` (most common) or `@router.get/post/...`
  decorators.
- DTOs live in mixed places: some modules have `presentation/requests/`
  and `presentation/responses/`, others have `presentation/schemas/`,
  and the request model is sometimes defined **inline** in the endpoint
  file (e.g. `LoginRequest` in `auth/presentation/endpoints/login.py`).
  The extractor must scan **all** of `presentation/**` and pick up
  inline classes too.
- Use cases are `dataclass` classes that inherit from
  `common.domain.interfaces.use_case.UseCase` (transitively, often
  through a mixin). Detection: `is_dataclass(cls)` AND
  `issubclass(cls, UseCase)`. Generic parameters are **not used** in
  this codebase; the spec is updated accordingly.
- Pydantic is **v2 only** (v2.11+). `CamelCaseRequest` uses
  `ConfigDict`, `model_validator`, `alias_generator=to_snake`. The
  detector should default to v2, log it once, and never fall back.

### Phase 1 — Scaffolding (≈30 min)

**Goal:** an importable `scripts/spec` package with CLI dispatch and
gitignored build dir.

Files:

```
backend/scripts/spec/
├── __init__.py
├── __main__.py             # `python -m spec` entry point
├── cli.py                  # argparse sub-commands: extract / emit / audit / all / diff
├── _build/.gitignore       # `*`
└── pyproject.toml          # local deps: openapi-spec-validator, pytest
```

`scripts/spec/pyproject.toml` is a **standalone** project (its own
deps), not part of the backend's `pyproject.toml`. Install with
`pip install -e scripts/spec` (called from a new `just install-spec`).

`cli.py` defines the sub-commands and flags as documented in the
component spec, but each command is a **stub** that prints
`TODO: not implemented yet` and exits 0. The `all` command runs them
in order. This lets us wire the recipe into `justfile` immediately
and validate the wiring before the real logic lands.

**Acceptance:** `python -m spec --help` and `python -m spec all` work.
`just spec` runs the all command.

### Phase 2 — Extractor (≈3 h)

**Goal:** `python -m spec extract` writes a complete
`scripts/spec/_build/ast-graph.json` from the real backend.

Implementation order:

1. `models.py` — dataclasses:
   - `RouteNode(path, method, endpoint_name, file, line, tags, request_dto, response_dto, dependencies, summary, description)`
   - `UseCaseNode(name, qualname, file, line, module, command_fields, return_type_hint)`
   - `DTONode(name, qualname, file, line, fields, base, is_request, is_response)`
   - `ASTGraph(schema_version=1, generated_at, meta, routes, use_cases, dtos, unresolved)`

2. `extractor.py` — two passes:
   - **Pass A: router composition.** Read `backend/config/router.py`
     with `ast.parse`. Walk top-level statements; for every
     `api_router.include_router(<name>, prefix=..., tags=...)` call,
     record `sub_router_name -> (prefix, tags)`. Resolve the import
     to find the `APIRouter(...)` instance in the imported file, then
     walk that file too. Combine prefixes.
   - **Pass B: per-router extraction.** For each sub-router file
     found in Pass A, walk:
     - `add_api_route(path=..., methods=[...], endpoint=...)` calls
       (combine with prefix from Pass A).
     - `@router.get/post/put/patch/delete("/path")` decorators
       (combine with prefix).
     - For each captured route, look up the endpoint function by
       name (via the import map) and read its signature to find
       Pydantic-typed parameters and the return annotation.

3. DTO scanning: walk every `*.py` under
   `backend/src/**/presentation/**`. For every class that inherits
   from `pydantic.BaseModel`, record it as a `DTONode`. Track the
   file path so we can mark `is_request=True` if the file is named
   `*request*` or `is_response=True` if `*response*`; everything
   else is `is_request=False, is_response=False` (the emitter will
   keep it as a schema and routes can reference it explicitly).

4. Use case scanning: walk every `*.py` under
   `backend/src/**/application/use_cases/**`. For every
   `is_dataclass(cls) and issubclass(cls, UseCase)`, record a
   `UseCaseNode`.

5. Edge cases to handle explicitly (write a test for each):
   - Inline request class (`class LoginRequest(CamelCaseRequest): …`
     inside an endpoint file).
   - Multiple `add_api_route` calls per router.
   - Re-exported endpoint function (`from .login import login`).
   - A router mounted with no prefix (use `""`).
   - Pydantic v2 `Field(description="...")` annotations on DTOs.

6. Failure modes:
   - File with `SyntaxError`: log, skip, continue. The emitter
     reports which files were skipped.
   - Unresolved import: log warning, skip the route / DTO, but
     record it under `unresolved.imports` so the auditor flags it.

**Acceptance:** `python -m spec extract` against the real backend
produces an AST-graph with all 15 routers' routes, ~30+ DTOs, and
~80+ use cases. The number is asserted in the e2e test
(`len(routes) >= 50`).

### Phase 3 — Emitter (≈3 h)

**Goal:** `python -m spec emit` produces a valid OpenAPI 3.1 JSON.

Implementation order:

1. `openapi_types.py` — `@dataclass` tree mirroring OpenAPI 3.1:
   `OpenAPI`, `Info`, `Server`, `Tag`, `PathItem`, `Operation`,
   `Parameter`, `RequestBody`, `Response`, `MediaType`, `Schema`,
   `Components`, `SecurityScheme`, `Reference`. All fields are
   `field(default_factory=...)` to play well with Pydantic-style
   mutation. A single `to_dict()` method on each class produces the
   JSON-friendly dict (drops `None` fields, snake_case → camelCase
   keys, schemas as dicts).

2. `emitter.py`:
   - `Info` from `pyproject.toml` (`name`, `version`, `description`).
   - `Servers`: one entry with `url: "/api/v1"` (the global prefix
     the docs site proxies through, matches the
     `src/proxy.ts` rewrite).
   - `Tags`: union of all `tags` strings found in the routes,
     alphabetically sorted, with a default description
     `"<tag> endpoints"`.
   - `Paths`: built by joining the router prefix + route path. Path
     parameters (`{item_id}`) translated to `parameters[].name =
     "item_id", in=path, required=true, schema={type: string}`.
   - `Operation`:
     - `summary` from the endpoint function's first docstring line.
     - `description` from the rest of the docstring.
     - `tags` from the router mount.
     - `security` defaulting to `[{ApiKeyAuth: []}]`; routes that
       don't use `get_app_context` get `[]`.
     - `requestBody`: built from the endpoint's first Pydantic
       parameter (skip `Depends(...)` and primitive types).
     - `responses`: 200 from the return annotation if it's a
       Pydantic class; 422 default; 401 if security is required.
   - `components.schemas`: every `DTONode` emitted as a JSON Schema
     object. Field types translated per the mapping table in the
     component spec. `Field(description=...)` becomes
     `property.description`. `Field(alias=...)` becomes
     `property.x-snake-name` (we keep the alias too).
   - `securitySchemes`: hard-coded `ApiKeyAuth` (matches
     `src/proxy.ts: X-Api-Key`).

3. Validators:
   - `json.dump` to a temp file, then `openapi-spec-validator`
     validates against the OpenAPI 3.1 metaschema. If invalid,
     the emitter exits non-zero with the validator's error.
   - If `x-unresolved-types` is non-empty and `--allow-unresolved`
     is not set, exit non-zero **after** writing the file (so the
     user can inspect the partial output).

4. Deduplication: schemas are keyed by FQCN. Re-exports of the same
   FQCN produce one schema. Conflicts (two different classes with
   the same FQCN) exit non-zero with a `schema_collision` error
   pointing to both files.

**Acceptance:** `python -m spec extract && python -m spec emit`
produces a `docs/src/content/api/_generated/openapi.json` that
passes `openapi-spec-validator` and contains every route in the
backend's `config/router.py`.

### Phase 4 — Auditor (≈2 h)

**Goal:** `python -m spec audit` produces an audit report and a
deterministic coverage score.

Two sub-components, both in `llm_auditor.py` (heuristic) and a small
`heuristic_auditor.py` (no-LLM path).

1. **Heuristic auditor** (always works, no network):
   - Walk every `Operation` and every `Schema` in the spec.
   - Emit issues with `source: "heuristic"` and the kinds listed in
     the spec (missing_summary, missing_field_description, etc.).
   - Compute the coverage score with the formula in the spec.

2. **LLM auditor** (`llm_auditor.py`):
   - Reads the same issues computed by the heuristic auditor.
   - Calls the LLM with the prompt from
     `scripts/spec/llm_auditor_prompt.txt`.
   - LLM response is **merged** into the issue list: it may add
     new issues, but cannot remove or downgrade. The score stays
     from the heuristic computation.
   - `prompt_version` field in the report = the SHA-256 of
     `llm_auditor_prompt.txt`. If the prompt file changes, the
     version bumps; the report is still deterministic in score.
   - If `SPEC_AUDITOR_MODEL` is unset or `--no-llm` is passed,
     skip the LLM call entirely. If the call fails (rate limit,
     network), fall back and mark the report
     `source: "heuristic-fallback"`.

3. Report format: Markdown table with columns `Endpoint | Issues |
   Severity`. Top of file: `coverage_score: 87/100` (big) and
   `prompt_version: <sha>` (small, when LLM was used). End of file:
   a `## Unresolved` section listing every unresolved type / import
   from the AST-graph.

4. `--fail-under N`: after computing the score, if `score < N`,
   exit non-zero.

**Acceptance:** `python -m spec audit --fail-under 80` exits 0
against a clean backend; the report has a deterministic score
(run twice → same number).

### Phase 5 — Docs page (≈1.5 h)

**Goal:** `/api-docs` renders the generated spec with Stoplight
Elements.

Files:

```
docs/src/pages/api-docs.astro       # new
docs/tests/api-docs.spec.ts         # new (Playwright smoke)
```

Implementation:

1. `docs/package.json`: add `@stoplight/elements` (BSD-3-Clause) as
   a dep. `pnpm install` once.

2. `api-docs.astro`:
   - `import openapi from '@/content/api/_generated/openapi.json'`
     (Astro inlines the JSON at build time; works in dev too).
   - Wrap in `DocsLayout` (matches the existing nav).
   - Mount `<elements-api apiDescriptionDocument={JSON.stringify(openapi)} router="hash" layout="sidebar" tryItCredentialsPolicy="include" />`.
   - Import the component client-side:
     `<script>import '@stoplight/elements/web-components.min.js';</script>`
     (Astro bundles this; no CDN).

3. Add a "View interactive API" link to the existing
   `docs/src/pages/api/[...slug].astro` (in the per-endpoint
   human-written narrative) that points to `/api-docs`. The link
   uses the endpoint's path to anchor to
   `/api-docs#operation/<operationId>`.

4. Playwright test in `docs/tests/api-docs.spec.ts` (new file):
   - `await page.goto('/api-docs')`.
   - `await page.waitForFunction(() => customElements.get('elements-api'))`.
   - Assert at least one `text=/login/i` is visible (one of the
     endpoints must be on the page).

**Acceptance:** dev server renders `/api-docs` with at least the
auth endpoints visible. Playwright test passes.

### Phase 6 — CI + justfile (≈45 min)

**Goal:** the pipeline is one `just spec` away and CI enforces quality.

1. `justfile` additions:
   ```
   spec:           install-spec && (cd scripts/spec && python -m spec all)
   install-spec:   pip install -e scripts/spec
   spec-audit:     (cd scripts/spec && python -m spec audit --fail-under 80)
   spec-diff:      (cd scripts/spec && python -m spec diff)
   ```

2. `.gitignore` in `docs/src/content/api/_generated/`:
   ```
   *
   !.gitkeep
   ```

3. Prebuild hook: `docs/package.json`:
   ```
   "prebuild": "python -m spec emit",
   "predev":   "python -m spec emit"
   ```
   (Uses `python3`; if not in PATH, the prebuild is a no-op and the
   user runs `just spec` manually. We document this in the spec
   rollout.)

4. CI hook: the `just spec-audit` recipe is the gate. Add a single
   line to whatever CI config the repo uses (a comment in
   `justfile` pointing at the right file).

5. E2E test for the pipeline: `scripts/spec/tests/test_e2e.py`
   uses a small synthetic backend fixture and asserts the output
   passes `openapi-spec-validator`. Fixture is hand-written
   (3 routes, 2 DTOs, 1 use case) and lives in
   `scripts/spec/tests/fixtures/synthetic_backend/`.

**Acceptance:** `just spec` runs the full pipeline; `just
spec-audit --fail-under 80` exits 0 on the current backend;
`just spec-diff` shows zero diff if nothing changed.

### Phase ordering & dependencies

```
Phase 1 (scaffold)
   │
   ▼
Phase 2 (extractor) ─────► Phase 3 (emitter) ─────► Phase 4 (auditor)
                                                         │
                                                         ▼
                                                   Phase 5 (docs page)
                                                         │
                                                         ▼
                                                   Phase 6 (CI)
```

Phases 2-3 must land together (emitter is useless without extractor).
Phase 4 can land after 3. Phase 5 can start in parallel with 4 (mock
spec works). Phase 6 last.

### Estimated effort

| Phase | Estimate | Hardest part |
|-------|----------|--------------|
| 1     | 30 min   | argparse sub-commands |
| 2     | 3 h      | parsing `include_router` + decorator walks |
| 3     | 3 h      | Python type → JSON Schema mapping + dedup |
| 4     | 2 h      | prompt version + deterministic score |
| 5     | 1.5 h    | Stoplight bundle import + Playwright wiring |
| 6     | 45 min   | `prebuild` hook + `just` recipes |
| **Total** | **~11 h** | |

### Checkpoint at the end of each phase

After each phase, run the relevant command and capture the output in
the phase's commit message. A phase is **done** only when its
acceptance criterion is met.


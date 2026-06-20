---
feature: data-model
type: spec
status: obsolete
coverage: 10
audited: 2026-06-16
superseded_by: backend DDD re-arch (ver docs/backend/)
---

# Workspace ERD - Modelos relacionados a WorkspaceORM

```mermaid
erDiagram
    TenantORM {
        uuid uuid PK
        datetime created_at
        datetime updated_at
        string name
        string slug UK
        bool view_workspace
        arrayfield processing_case_types
    }

    CustomUser {
        id id PK
        string email
        string password
    }

    TenantUserORM {
        uuid uuid PK
        datetime created_at
        datetime updated_at
        uuid tenant FK
        uuid user FK
        uuid role FK "TenantRoleORM, nullable"
        bool is_owner
        string status "PENDING | ACTIVE | INACTIVE"
        bool is_admin
    }

    DocumentTypeORM {
        uuid uuid PK
        datetime created_at
        datetime updated_at
        uuid tenant FK
        string name
        bool is_shareable
        string processing_document_type "nullable"
        text description "nullable"
        json metadata
    }

    WorkspaceORM {
        uuid uuid PK
        datetime created_at
        datetime updated_at
        uuid tenant FK
        uuid created_by FK "CustomUser, nullable"
        string name
        json metadata
        bool is_archived
        bool is_main
    }

    WorkspaceDocumentTypeORM {
        uuid uuid PK
        datetime created_at
        datetime updated_at
        uuid tenant FK
        uuid workspace FK
        uuid document_type FK
        json metadata
    }

    WorkspaceDocumentORM {
        uuid uuid PK
        datetime created_at
        datetime updated_at
        uuid tenant FK
        uuid workspace FK
        uuid document_type FK "nullable"
        uuid created_by FK "TenantUserORM, nullable"
        string name
        string digest "SHA-256, nullable"
        string status "PENDING | PROCESSING | COMPLETED | FAILED"
        string source "nullable"
        file document "nullable, S3"
        datetime uploaded_at "nullable"
        datetime started_at "nullable"
        datetime failed_at "nullable"
        datetime completed_at "nullable"
        decimal processing_time "nullable"
        json extraction
        json metadata
    }

    WorkspaceDocumentPageORM {
        uuid uuid PK
        datetime created_at
        datetime updated_at
        uuid tenant FK
        uuid workspace FK
        uuid workspace_document FK
        int page_number "1-indexed"
        file page_file "nullable, S3"
        file cleaned_page_file "nullable, S3"
        datetime synced_at "nullable"
    }

    TenantORM ||--o{ WorkspaceORM : "has many"
    TenantORM ||--o{ TenantUserORM : "has many"
    TenantORM ||--o{ DocumentTypeORM : "has many"
    TenantORM ||--o{ WorkspaceDocumentORM : "has many"
    TenantORM ||--o{ WorkspaceDocumentPageORM : "has many"
    TenantORM ||--o{ WorkspaceDocumentTypeORM : "has many"

    CustomUser ||--o{ WorkspaceORM : "created_by"
    CustomUser ||--o| TenantUserORM : "user (unique)"

    WorkspaceORM ||--o{ WorkspaceDocumentORM : "documents"
    WorkspaceORM ||--o{ WorkspaceDocumentPageORM : "document_pages"
    WorkspaceORM ||--o{ WorkspaceDocumentTypeORM : "workspace_document_types"

    WorkspaceDocumentORM ||--o{ WorkspaceDocumentPageORM : "pages"
    WorkspaceDocumentORM }o--o| DocumentTypeORM : "document_type"

    DocumentTypeORM ||--o{ WorkspaceDocumentTypeORM : "workspace_associations"

    TenantUserORM ||--o{ WorkspaceDocumentORM : "created_by"
```

## Resumen de relaciones

| Tabla origen | Tabla destino | Tipo | Campo FK | on_delete |
|---|---|---|---|---|
| `WorkspaceORM` | `TenantORM` | Many-to-One | `tenant` | CASCADE |
| `WorkspaceORM` | `CustomUser` | Many-to-One | `created_by` | SET_NULL |
| `WorkspaceDocumentORM` | `WorkspaceORM` | Many-to-One | `workspace` | CASCADE |
| `WorkspaceDocumentORM` | `DocumentTypeORM` | Many-to-One | `document_type` | SET_NULL |
| `WorkspaceDocumentORM` | `TenantUserORM` | Many-to-One | `created_by` | SET_NULL |
| `WorkspaceDocumentORM` | `TenantORM` | Many-to-One | `tenant` | CASCADE |
| `WorkspaceDocumentPageORM` | `WorkspaceORM` | Many-to-One | `workspace` | CASCADE |
| `WorkspaceDocumentPageORM` | `WorkspaceDocumentORM` | Many-to-One | `workspace_document` | CASCADE |
| `WorkspaceDocumentPageORM` | `TenantORM` | Many-to-One | `tenant` | CASCADE |
| `WorkspaceDocumentTypeORM` | `WorkspaceORM` | Many-to-One | `workspace` | CASCADE |
| `WorkspaceDocumentTypeORM` | `DocumentTypeORM` | Many-to-One | `document_type` | CASCADE |
| `WorkspaceDocumentTypeORM` | `TenantORM` | Many-to-One | `tenant` | CASCADE |

## Tablas de DB

| Modelo | `db_table` |
|---|---|
| `TenantORM` | `tenants` |
| `TenantUserORM` | `tenant_users` |
| `DocumentTypeORM` | `document_types` |
| `WorkspaceORM` | `workspaces` |
| `WorkspaceDocumentORM` | `workspace_documents` |
| `WorkspaceDocumentPageORM` | `workspace_document_pages` |
| `WorkspaceDocumentTypeORM` | `workspaces_document_types` |

## Constraints e Indexes

- **`WorkspaceDocumentPageORM`**: `UNIQUE(workspace_document, page_number)`
- **`TenantUserORM`**: `UNIQUE(user)`, `UNIQUE(user, tenant)`
- **`WorkspaceORM`**: Index en `(tenant, is_archived, -created_at)`
- **`WorkspaceDocumentORM`**: Index en `(workspace, status, -uploaded_at)` y `(tenant, workspace, -uploaded_at)`
- **`WorkspaceDocumentORM`**: ordering por `-uploaded_at`
- **`WorkspaceDocumentPageORM`**: ordering por `(workspace_document, page_number)`

## Notas para migrar

- Todos los modelos usan **UUID como PK** (no auto-increment)
- Todos tienen `created_at` (auto_now_add) y `updated_at` (auto_now)
- Todos los modelos del workspace tienen FK redundante a `tenant` (desnormalizado para queries directas)
- Archivos (`document`, `page_file`, `cleaned_page_file`) se almacenan en **S3** con paths como: `workspaces/ws_{uuid}/documents/...`
- `WorkspaceDocumentTypeORM` actua como tabla intermedia (M2M manual) entre Workspace y DocumentType
- `digest` en WorkspaceDocumentORM es SHA-256 para deduplicacion de archivos
- `extraction` es un JSONField que guarda datos estructurados del procesamiento
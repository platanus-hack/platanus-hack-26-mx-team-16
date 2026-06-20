# Diagrama Entidad-Relación — Llamitai

> Todos los modelos con `UUIDTenantTimestampMixin` heredan: `uuid (PK)`, `tenant_id (FK→tenants)`, `created_at`, `updated_at`.
> Los modelos con `UUIDTimestampMixin` heredan: `uuid (PK)`, `created_at`, `updated_at` (sin tenant).

```mermaid
erDiagram

    %% ═══════════════════════════════════════
    %% CORE: AUTH & USERS
    %% ═══════════════════════════════════════

    email_addresses {
        uuid uuid PK
        string email UK
        bool is_verified
        timestamp created_at
        timestamp updated_at
    }

    phone_numbers {
        uuid uuid PK
        string iso_code
        int dial_code
        string phone_number
        string prefix
        bool is_verified
        timestamp created_at
        timestamp updated_at
    }

    users {
        uuid uuid PK
        string username UK
        string password
        string first_name
        string last_name
        uuid email_address_id FK
        uuid phone_number_id FK
        uuid current_tenant_id FK
        bool is_active
        bool is_staff
        bool is_superuser
        timestamp last_login
        timestamp created_at
        timestamp updated_at
    }

    %% ═══════════════════════════════════════
    %% TENANTS & ROLES
    %% ═══════════════════════════════════════

    tenants {
        uuid uuid PK
        string name
        string slug UK
        string status
        string time_zone
        string country_code
        string currency_code
        string logo_url
        uuid owner_id FK
        timestamp created_at
        timestamp updated_at
    }

    tenant_roles {
        uuid uuid PK
        uuid tenant_id FK
        string name
        string slug
        string status
        string icon_url
        json permissions
        timestamp created_at
        timestamp updated_at
    }

    tenant_users {
        uuid uuid PK
        uuid tenant_id FK
        uuid user_id FK
        uuid tenant_role_id FK
        string first_name
        string last_name
        string photo
        bool is_owner
        bool is_support
        string status
        json permissions
        timestamp created_at
        timestamp updated_at
    }

    %% ═══════════════════════════════════════
    %% WORKSPACES
    %% ═══════════════════════════════════════

    workspaces {
        uuid uuid PK
        uuid tenant_id FK
        string name
        text description
        bool is_archived
        timestamp created_at
        timestamp updated_at
    }

    %% ═══════════════════════════════════════
    %% INDUSTRIES & PROCESSES
    %% ═══════════════════════════════════════

    industries {
        uuid uuid PK
        uuid tenant_id FK
        string slug
        string name
        string icon
        text description
        timestamp created_at
        timestamp updated_at
    }

    processes {
        uuid uuid PK
        uuid tenant_id FK
        uuid industry_id FK
        string slug
        string name
        string icon
        text description
        string workflow_type
        text generic_prompt
        text extraction_prompt
        jsonb prompt_overrides
        string builder_subtitle
        string default_workflow_name
        jsonb doc_type_catalog
        jsonb default_selected_keys
        jsonb default_schemas
        timestamp created_at
        timestamp updated_at
    }

    %% ═══════════════════════════════════════
    %% EXTRACTION PIPELINE
    %% ═══════════════════════════════════════

    extraction_workflows {
        uuid uuid PK
        uuid tenant_id FK
        uuid process_id FK
        string name
        jsonb selected_doc_types
        jsonb per_doc_schema
        jsonb kb_document_ids
        jsonb per_doc_kb_ids
        string structuring_model
        string llm_model
        timestamp created_at
        timestamp updated_at
    }

    extraction_cases {
        uuid uuid PK
        uuid tenant_id FK
        uuid workflow_id FK
        uuid created_by FK
        string name
        string status
        string last_ocr_provider
        timestamp created_at
        timestamp updated_at
    }

    extraction_jobs {
        uuid uuid PK
        uuid tenant_id FK
        uuid case_id FK
        string status
        jsonb results
        text error
        bool is_cancelled
        string temporal_workflow_id
        timestamp created_at
        timestamp updated_at
    }

    case_documents {
        uuid uuid PK
        uuid tenant_id FK
        uuid case_id FK
        uuid file_id FK
        string doc_type_key
        string file_name
        string status
        jsonb extracted_fields
        text extracted_text
        string ocr_provider_used
        numeric confidence
        bool include_in_extraction
        jsonb kb_context_used
        timestamp created_at
        timestamp updated_at
    }

    %% ═══════════════════════════════════════
    %% BUSINESS RULES & EVALUATION
    %% ═══════════════════════════════════════

    business_rules {
        uuid uuid PK
        uuid tenant_id FK
        uuid workflow_id FK
        string name
        text text
        bool is_active
        jsonb kb_ids
        timestamp created_at
        timestamp updated_at
    }

    rule_evaluation_results {
        uuid uuid PK
        uuid tenant_id FK
        uuid case_id FK
        uuid rule_id FK
        bool is_passed
        text reasoning
        jsonb structured_data
        text error
        timestamp created_at
        timestamp updated_at
    }

    %% ═══════════════════════════════════════
    %% FILE STORAGE
    %% ═══════════════════════════════════════

    file_uploads {
        uuid uuid PK
        uuid tenant_id FK
        string file_name
        string mime
        int size
        string s3_key
        timestamp created_at
        timestamp updated_at
    }

    %% ═══════════════════════════════════════
    %% KNOWLEDGE BASE
    %% ═══════════════════════════════════════

    kb_documents {
        uuid uuid PK
        uuid tenant_id FK
        string file_name
        string mime
        uuid file_id FK
        text extracted_text
        timestamp created_at
        timestamp updated_at
    }

    kb_embeddings {
        uuid uuid PK
        uuid tenant_id FK
        uuid kb_document_id FK
        int chunk_index
        text chunk_text
        vector embedding
        timestamp created_at
        timestamp updated_at
    }

    %% ═══════════════════════════════════════
    %% RELACIONES
    %% ═══════════════════════════════════════

    %% Auth & Users
    users ||--o| email_addresses : "email_address_id"
    users ||--o| phone_numbers : "phone_number_id"
    users }o--o| tenants : "current_tenant_id"

    %% Tenants
    tenants }o--o| users : "owner_id"
    tenant_roles }o--|| tenants : "tenant_id"
    tenant_users }o--|| tenants : "tenant_id"
    tenant_users }o--|| users : "user_id"
    tenant_users }o--o| tenant_roles : "tenant_role_id"

    %% Workspaces
    workspaces }o--|| tenants : "tenant_id"

    %% Industries & Processes
    industries }o--|| tenants : "tenant_id"
    processes }o--|| tenants : "tenant_id"
    processes }o--|| industries : "industry_id"

    %% Extraction Pipeline
    extraction_workflows }o--|| tenants : "tenant_id"
    extraction_workflows }o--|| processes : "process_id"
    extraction_cases }o--|| tenants : "tenant_id"
    extraction_cases }o--|| extraction_workflows : "workflow_id"
    extraction_cases }o--o| users : "created_by"
    extraction_jobs }o--|| tenants : "tenant_id"
    extraction_jobs }o--|| extraction_cases : "case_id"
    case_documents }o--|| tenants : "tenant_id"
    case_documents }o--|| extraction_cases : "case_id"
    case_documents }o--o| file_uploads : "file_id"

    %% Business Rules
    business_rules }o--|| tenants : "tenant_id"
    business_rules }o--|| extraction_workflows : "workflow_id"
    rule_evaluation_results }o--|| tenants : "tenant_id"
    rule_evaluation_results }o--|| extraction_cases : "case_id"
    rule_evaluation_results }o--|| business_rules : "rule_id"

    %% File Storage
    file_uploads }o--|| tenants : "tenant_id"

    %% Knowledge Base
    kb_documents }o--|| tenants : "tenant_id"
    kb_documents }o--o| file_uploads : "file_id"
    kb_embeddings }o--|| tenants : "tenant_id"
    kb_embeddings }o--|| kb_documents : "kb_document_id"
```

---

## Uso de cada modelo

### Auth & Users

| Modelo | Tabla | Uso |
|--------|-------|-----|
| **EmailAddressORM** | `email_addresses` | Almacena emails únicos verificables. Referenciado por `users` para login/contacto. |
| **PhoneNumberORM** | `phone_numbers` | Almacena teléfonos con código de país. Referenciado por `users` para contacto/verificación. |
| **UserORM** | `users` | Usuario del sistema. Tiene credenciales (username/password), flags de permisos (staff/superuser), y referencia al tenant activo. Base para autenticación JWT. |

### Tenants & Roles

| Modelo | Tabla | Uso |
|--------|-------|-----|
| **TenantORM** | `tenants` | Organización/empresa. Aísla todos los datos por tenant (multi-tenancy). Configura localización (timezone, país, moneda). |
| **TenantRoleORM** | `tenant_roles` | Roles dentro de un tenant (ej: Admin, Viewer). Contiene array JSON de permisos granulares. |
| **TenantUserORM** | `tenant_users` | Membresía usuario↔tenant. Asigna rol, permisos específicos, perfil (nombre/foto) dentro del tenant. Un usuario puede pertenecer a múltiples tenants. |

### Workspaces

| Modelo | Tabla | Uso |
|--------|-------|-----|
| **WorkspaceORM** | `workspaces` | Espacios de trabajo dentro de un tenant para organizar recursos. Puede archivarse. Actualmente no tiene FK hacia otros modelos de extracción. |

### Industries & Processes

| Modelo | Tabla | Uso |
|--------|-------|-----|
| **IndustryORM** | `industries` | Catálogo de industrias por tenant (ej: Inmobiliaria, Salud, Financiera). Agrupa procesos relacionados. |
| **ProcessORM** | `processes` | Template de proceso de extracción. Define el catálogo de tipos de documento (`doc_type_catalog`), schemas por defecto, prompts de extracción, y configuración del builder UI. Un process = un tipo de workflow (ej: "Análisis de crédito hipotecario"). Unique por `(tenant_id, workflow_type)`. |

### Extraction Pipeline

| Modelo | Tabla | Uso |
|--------|-------|-----|
| **ExtractionWorkflowORM** | `extraction_workflows` | Instancia configurada de un Process. El usuario selecciona doc types, personaliza schemas, asigna KBs, y elige modelos LLM. Es el "template activo" sobre el que se crean casos. |
| **ExtractionCaseORM** | `extraction_cases` | Un caso de análisis (ej: un expediente de crédito). Contiene documentos subidos, pasa por estados (DRAFT → PROCESSING → DONE). Vinculado al workflow y al usuario que lo creó. |
| **ExtractionJobORM** | `extraction_jobs` | Job de extracción OCR+LLM para un caso. Trackea status (PENDING/RUNNING/DONE/FAILED), resultados JSON, errores, y el workflow_id de Temporal. Permite cancelación. |
| **CaseDocumentORM** | `case_documents` | Documento individual dentro de un caso. Almacena el archivo subido, tipo de documento, campos extraídos (`extracted_fields` JSONB), texto OCR, confianza, y contexto KB usado. Unique por `(case_id, doc_type_key)`. |

### Business Rules & Evaluation

| Modelo | Tabla | Uso |
|--------|-------|-----|
| **BusinessRuleORM** | `business_rules` | Regla de negocio vinculada a un workflow. Contiene la lógica en texto natural (ej: "Verificar que @receta.medicamentos incluya..."). Puede referenciar KBs para contexto adicional. Toggle `is_active` para incluir/excluir del análisis. |
| **RuleEvaluationResultORM** | `rule_evaluation_results` | Resultado de evaluar una regla contra un caso. Almacena pass/fail, razonamiento del LLM, datos estructurados opcionales, y errores. Vincula `case_id` ↔ `rule_id`. |

### File Storage

| Modelo | Tabla | Uso |
|--------|-------|-----|
| **FileUploadORM** | `file_uploads` | Registro de archivo subido a S3. Metadata (nombre, MIME, tamaño) + `s3_key` para descarga. Referenciado por `case_documents` y `kb_documents`. |

### Knowledge Base

| Modelo | Tabla | Uso |
|--------|-------|-----|
| **KBDocumentORM** | `kb_documents` | Documento de knowledge base. Almacena el archivo fuente y su texto extraído. Se usa como contexto de referencia para extracción y evaluación de reglas. |
| **KBEmbeddingORM** | `kb_embeddings` | Chunk vectorizado de un KB document. Usa pgvector (768 dims) para búsqueda semántica. Unique por `(kb_document_id, chunk_index)`. Permite RAG sobre la base de conocimiento. |

---

## Flujo principal de datos

```
Industry → Process → ExtractionWorkflow → ExtractionCase → CaseDocument
                          ↓                      ↓
                    BusinessRule          RuleEvaluationResult
                          ↓                      ↑
                      (evalúa)  ─────────────────┘

FileUpload ← CaseDocument (archivo del caso)
FileUpload ← KBDocument → KBEmbedding (knowledge base para RAG)
```

## Referencias lógicas (no FK, via JSONB)

| Campo | En tabla | Referencia lógica |
|-------|----------|-------------------|
| `kb_document_ids` | `extraction_workflows` | → `kb_documents.uuid[]` |
| `per_doc_kb_ids` | `extraction_workflows` | → `kb_documents.uuid[]` por doc_type |
| `kb_ids` | `business_rules` | → `kb_documents.uuid[]` |
| `kb_context_used` | `case_documents` | → chunks de KB usados en extracción |
| `doc_type_catalog` | `processes` | Catálogo de tipos de documento (JSON) |
| `default_schemas` | `processes` | Schemas de extracción por defecto (JSON) |
| `selected_doc_types` | `extraction_workflows` | Doc types seleccionados del catálogo |
| `per_doc_schema` | `extraction_workflows` | Schemas personalizados por doc type |
| `extracted_fields` | `case_documents` | Campos extraídos del documento (JSON) |

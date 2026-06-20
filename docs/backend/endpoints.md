# Backend API Endpoints

## Common (2 endpoints)

| Method | Path | Function | Description |
|--------|------|----------|-------------|
| GET | `/` | `home` | Health check / status |
| GET | `/sentry-debug` | `sentry_debug` | Test Sentry integration (dev only) |

## Auth (6 endpoints)

Prefix: `/auth`

| Method | Path | Function | Description |
|--------|------|----------|-------------|
| POST | `/auth/login` | `login` | Login |
| POST | `/auth/google-login` | `google_login` | Google OAuth login |
| POST | `/auth/reset-password` | `reset_password` | Reset password |
| POST | `/auth/refresh` | `refresh` | Refresh token |
| POST | `/auth/logout` | `logout` | Logout |
| GET | `/auth/session` | `session` | Get current session |

## Users (1 endpoint)

Prefix: `/users`

| Method | Path | Function | Description |
|--------|------|----------|-------------|
| POST | `/users` | `register_user` | Register a new user |

## Profile / Me (5 endpoints)

Prefix: `/me`

| Method | Path | Function | Description |
|--------|------|----------|-------------|
| GET | `/me/profile` | `get_profile` | Get current user profile |
| PUT | `/me/profile` | `update_profile` | Update current user profile |
| PUT | `/me/password` | `update_password` | Update current user password |
| GET | `/me/tenants` | `get_user_tenants` | Get tenants where user is member |
| PUT | `/me/tenants/{tenant_id}` | `update_me_tenant` | Update current tenant |

## Tenants (14 endpoints)

Prefix: `/tenants`

| Method | Path | Function | Description |
|--------|------|----------|-------------|
| POST | `/tenants` | `register_tenant` | Register a new tenant |
| PUT | `/tenants/{tenant_id}` | `update_tenant` | Update tenant |
| POST | `/tenants/permissions/missing` | `get_missing_permissions` | Get missing permissions |
| **Users** | | | |
| GET | `/tenants/users/stats` | `get_tenant_user_stats` | Get tenant user stats |
| GET | `/tenants/users` | `get_tenant_users` | List tenant users |
| POST | `/tenants/users` | `create_tenant_user` | Create tenant user |
| GET | `/tenants/users/{tenant_user_id}` | `get_tenant_user` | Get tenant user detail |
| PUT | `/tenants/users/{tenant_user_id}` | `update_tenant_user` | Update tenant user |
| DELETE | `/tenants/users/{tenant_user_id}` | `delete_tenant_user` | Remove tenant user |
| **Roles** | | | |
| GET | `/tenants/roles` | `get_tenant_roles` | List tenant roles |
| POST | `/tenants/roles` | `create_tenant_role` | Create tenant role |
| POST | `/tenants/roles/bootstrap` | `bootstrap_tenant_roles` | Bootstrap default roles |
| GET | `/tenants/roles/{role_id}` | `get_tenant_role` | Get role detail |
| PUT | `/tenants/roles/{role_id}` | `update_tenant_role` | Update role |
| DELETE | `/tenants/roles/{role_id}` | `delete_tenant_role` | Delete role |

## Workspaces (5 endpoints)

Prefix: `/workspaces`

| Method | Path | Function | Description |
|--------|------|----------|-------------|
| GET | `/workspaces/` | `list_workspaces` | List workspaces (paginated) |
| POST | `/workspaces/` | `create_workspace` | Create workspace |
| GET | `/workspaces/{workspace_id}` | `get_workspace` | Get workspace by ID |
| PATCH/PUT | `/workspaces/{workspace_id}` | `update_workspace` | Update workspace |
| DELETE | `/workspaces/{workspace_id}` | `delete_workspace` | Delete workspace |

## File Storage (3 endpoints)

Prefix: `/files`

| Method | Path | Function | Description |
|--------|------|----------|-------------|
| POST | `/files/upload` | `upload_file` | Upload file to S3 |
| GET | `/files/{file_id}` | `get_file` | Get file metadata + presigned URL |
| DELETE | `/files/{file_id}` | `delete_file` | Delete file from S3 |

## Industries (5 endpoints)

Prefix: `/industries`

| Method | Path | Function | Description |
|--------|------|----------|-------------|
| GET | `/industries` | `list_industries` | List industries for tenant |
| POST | `/industries` | `create_industry` | Create industry |
| PUT | `/industries/{slug}` | `update_industry` | Update industry |
| DELETE | `/industries/{slug}` | `delete_industry` | Delete industry (cascade) |
| GET | `/industries/{industry_slug}/processes` | `list_processes` | List processes for industry |

## Processes (4 endpoints)

Prefix: `/processes`

| Method | Path | Function | Description |
|--------|------|----------|-------------|
| GET | `/processes/{industry_slug}/{process_slug}` | `get_process_config` | Get process config |
| POST | `/processes` | `create_process` | Create process |
| PUT | `/processes/{industry_slug}/{process_slug}` | `update_process` | Update process |
| DELETE | `/processes/{industry_slug}/{process_slug}` | `delete_process` | Delete process |

## Extraction (19 endpoints)

Prefix: `/extraction`

### Workflows

| Method | Path | Function | Description |
|--------|------|----------|-------------|
| GET | `/extraction/workflows` | `list_workflows` | List workflows by process ID |
| POST | `/extraction/workflows` | `create_workflow` | Create workflow |
| GET | `/extraction/workflows/{workflow_id}` | `get_workflow` | Get workflow |
| PUT | `/extraction/workflows/{workflow_id}` | `update_workflow` | Update workflow |
| DELETE | `/extraction/workflows/{workflow_id}` | `delete_workflow` | Delete workflow (cascade) |

### Cases

| Method | Path | Function | Description |
|--------|------|----------|-------------|
| GET | `/extraction/workflows/{workflow_id}/cases` | `list_cases` | List cases for workflow |
| POST | `/extraction/workflows/{workflow_id}/cases` | `create_case` | Create case |
| GET | `/extraction/cases/{case_id}` | `get_case` | Get case with documents |
| PUT | `/extraction/cases/{case_id}` | `update_case` | Update case |
| DELETE | `/extraction/cases/{case_id}` | `delete_case` | Delete case (cascade) |

### Documents

| Method | Path | Function | Description |
|--------|------|----------|-------------|
| POST | `/extraction/documents/{doc_id}/upload` | `upload_document` | Upload file to document |
| PUT | `/extraction/documents/{document_id}` | `update_document` | Update document fields |

### Business Rules

| Method | Path | Function | Description |
|--------|------|----------|-------------|
| GET | `/extraction/workflows/{workflow_id}/rules` | `list_rules` | List rules for workflow |
| POST | `/extraction/workflows/{workflow_id}/rules` | `create_rule` | Create rule |
| PUT | `/extraction/rules/{rule_id}` | `update_rule` | Update rule |
| DELETE | `/extraction/rules/{rule_id}` | `delete_rule` | Delete rule |

### Jobs & Analysis

| Method | Path | Function | Description |
|--------|------|----------|-------------|
| POST | `/extraction/cases/{case_id}/extract` | `start_extraction_job` | Start extraction job |
| GET | `/extraction/jobs/{job_id}/status` | `get_job_status` | Poll job status |
| POST | `/extraction/jobs/{job_id}/cancel` | `cancel_extraction_job` | Cancel a PENDING/RUNNING job |
| POST | `/extraction/cases/{caseId}/analyze-stream` | `analyze_stream` | Run analysis (SSE stream) |
| GET | `/extraction/cases/{caseId}/analysis-results` | `get_analysis_results` | Get saved analysis results |

## Knowledge Base (5 endpoints)

Prefix: `/knowledge-base`

| Method | Path | Function | Description |
|--------|------|----------|-------------|
| POST | `/knowledge-base/documents` | `upload_document` | Upload, extract, chunk & embed document |
| GET | `/knowledge-base/documents` | `list_documents` | List KB documents for tenant |
| DELETE | `/knowledge-base/documents/{document_id}` | `delete_document` | Delete KB document + embeddings |
| POST | `/knowledge-base/search` | `search_chunks` | Search similar chunks (pgvector) |
| POST | `/knowledge-base/suggest-rules` | `suggest_rules` | Generate rule suggestions from KB |

## Integrations (1 endpoint)

| Method | Path | Function | Description |
|--------|------|----------|-------------|
| POST | `/admin/users/set-password` | `set_user_password` | Set user password (admin) |

---

**Total: 70 endpoints**

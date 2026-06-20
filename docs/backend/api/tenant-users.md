# Tenant Users API

Base URL: `/api/v1/tenants`

All endpoints require authentication and an active tenant user session. The `tenant_id` is inferred from the authenticated user's current tenant context.

All requests and responses use **camelCase** keys.

---

## List Tenant Users

```
GET /api/v1/tenants/users
```

Returns a paginated list of tenant users (excludes the current user).

**Permissions:** `tenant_user.view`

### Query Parameters

| Parameter  | Type     | Required | Description                                              |
|------------|----------|----------|----------------------------------------------------------|
| cursor     | string   | No       | Pagination cursor for the next page                      |
| limit      | integer  | No       | Number of items per page (default: server config)        |
| search     | string   | No       | Search by name or email                                  |
| statuses   | string   | No       | Comma-separated statuses: `ACTIVE`, `PENDING`, `INACTIVE`|

### Response `200 OK`

```json
{
  "data": [
    {
      "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "firstName": "John",
      "lastName": "Doe",
      "phoneNumber": {
        "uuid": "f1e2d3c4-b5a6-7890-abcd-ef1234567890",
        "dialCode": 1,
        "phoneNumber": "5551234567",
        "isVerified": true
      },
      "emailAddress": {
        "uuid": "b1c2d3e4-f5a6-7890-abcd-ef1234567890",
        "email": "john@example.com",
        "isVerified": true
      },
      "isOwner": false,
      "status": "ACTIVE",
      "tenantRole": {
        "uuid": "c1d2e3f4-a5b6-7890-abcd-ef1234567890",
        "name": "Admin",
        "status": "ACTIVE"
      },
      "createdAt": "2026-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "nextCursor": "eyJpZCI6IDEwfQ==",
    "hasMore": true
  },
  "timestamp": "2026-04-04T12:00:00Z"
}
```

---

## Create Tenant User

```
POST /api/v1/tenants/users
```

Creates a new user and associates them with the current tenant. If `reuse=true`, attempts to re-associate an existing user before creating a new one.

**Permissions:** `tenant_user.create`

### Query Parameters

| Parameter | Type    | Required | Description                                      |
|-----------|---------|----------|--------------------------------------------------|
| reuse     | boolean | No       | If `true`, reuse an existing user (default: false)|

### Request Body

```json
{
  "email": "jane@example.com",
  "password": "SecureP@ss123",
  "firstName": "Jane",
  "lastName": "Smith",
  "status": "ACTIVE",
  "tenantRoleId": "c1d2e3f4-a5b6-7890-abcd-ef1234567890",
  "phoneNumber": {
    "dialCode": 1,
    "phoneNumber": "5559876543",
    "isoCode": "US",
    "prefix": null
  }
}
```

| Field        | Type   | Required | Description                                           |
|--------------|--------|----------|-------------------------------------------------------|
| email        | string | Yes      | Valid email address                                   |
| password     | string | Yes      | User password                                         |
| firstName    | string | No       | First name (max 150 chars)                            |
| lastName     | string | No       | Last name (max 150 chars)                             |
| status       | string | No       | `ACTIVE` (default), `PENDING`, or `INACTIVE`          |
| tenantRoleId | string | No       | UUID of the tenant role to assign                     |
| phoneNumber  | object | No       | Phone number object (see below)                       |

**phoneNumber object:**

| Field       | Type    | Required | Description                         |
|-------------|---------|----------|-------------------------------------|
| dialCode    | integer | Yes      | Country dial code (e.g. `1`)        |
| phoneNumber | string  | Yes      | Phone number without dial code      |
| isoCode     | string  | Yes      | Country ISO code (e.g. `US`, `MX`)  |
| prefix      | string  | No       | Optional prefix                     |

### Response `201 Created`

```json
{
  "data": {
    "uuid": "d1e2f3a4-b5c6-7890-abcd-ef1234567890",
    "firstName": "Jane",
    "lastName": "Smith",
    "phoneNumber": {
      "uuid": "e1f2a3b4-c5d6-7890-abcd-ef1234567890",
      "dialCode": 1,
      "phoneNumber": "5559876543",
      "isVerified": false
    },
    "emailAddress": {
      "uuid": "f1a2b3c4-d5e6-7890-abcd-ef1234567890",
      "email": "jane@example.com",
      "isVerified": false
    },
    "isOwner": false,
    "status": "ACTIVE",
    "tenantRole": {
      "uuid": "c1d2e3f4-a5b6-7890-abcd-ef1234567890",
      "name": "Admin",
      "status": "ACTIVE"
    },
    "createdAt": "2026-04-04T12:00:00Z"
  },
  "timestamp": "2026-04-04T12:00:00Z"
}
```

---

## Get Tenant User

```
GET /api/v1/tenants/users/{tenantUserId}
```

Returns the details of a specific tenant user.

**Permissions:** `tenant_user.view`

### Path Parameters

| Parameter    | Type | Required | Description            |
|--------------|------|----------|------------------------|
| tenantUserId | UUID | Yes      | The tenant user's UUID |

### Response `200 OK`

```json
{
  "data": {
    "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "firstName": "John",
    "lastName": "Doe",
    "phoneNumber": {
      "uuid": "f1e2d3c4-b5a6-7890-abcd-ef1234567890",
      "dialCode": 1,
      "phoneNumber": "5551234567",
      "isVerified": true
    },
    "emailAddress": {
      "uuid": "b1c2d3e4-f5a6-7890-abcd-ef1234567890",
      "email": "john@example.com",
      "isVerified": true
    },
    "isOwner": false,
    "status": "ACTIVE",
    "tenantRole": {
      "uuid": "c1d2e3f4-a5b6-7890-abcd-ef1234567890",
      "name": "Admin",
      "status": "ACTIVE"
    },
    "createdAt": "2026-01-15T10:30:00Z"
  },
  "timestamp": "2026-04-04T12:00:00Z"
}
```

---

## Update Tenant User

```
PUT /api/v1/tenants/users/{tenantUserId}
```

Updates the specified tenant user. Only provided fields are updated (partial update via `exclude_none`).

**Permissions:** `tenant_user.update`

### Path Parameters

| Parameter    | Type | Required | Description            |
|--------------|------|----------|------------------------|
| tenantUserId | UUID | Yes      | The tenant user's UUID |

### Request Body

```json
{
  "firstName": "Jonathan",
  "lastName": "Doe",
  "status": "INACTIVE",
  "tenantRoleId": "c1d2e3f4-a5b6-7890-abcd-ef1234567890",
  "isOwner": false,
  "email": "jonathan@example.com",
  "phoneNumber": {
    "dialCode": 1,
    "phoneNumber": "5551112222",
    "isoCode": "US"
  }
}
```

| Field        | Type    | Required | Description                                  |
|--------------|---------|----------|----------------------------------------------|
| firstName    | string  | No       | First name (max 150 chars)                   |
| lastName     | string  | No       | Last name (max 150 chars)                    |
| status       | string  | No       | `ACTIVE`, `PENDING`, or `INACTIVE`           |
| tenantRoleId | string  | No       | UUID of the tenant role to assign            |
| isOwner      | boolean | No       | Whether the user is a tenant owner           |
| email        | string  | No       | New email address                            |
| phoneNumber  | object  | No       | Phone number object (same schema as create)  |

### Response `200 OK`

Same structure as [Get Tenant User](#get-tenant-user) response.

---

## Delete Tenant User

```
DELETE /api/v1/tenants/users/{tenantUserId}
```

Removes a user from the tenant.

**Permissions:** `tenant_user.delete`

### Path Parameters

| Parameter    | Type | Required | Description            |
|--------------|------|----------|------------------------|
| tenantUserId | UUID | Yes      | The tenant user's UUID |

### Response `200 OK`

```json
{
  "data": {
    "status": "SUCCESS"
  },
  "timestamp": "2026-04-04T12:00:00Z"
}
```

---

## Get Tenant User Stats

```
GET /api/v1/tenants/users/stats
```

Returns aggregated counts of tenant users by status (excludes the current user).

**Permissions:** `tenant_user.view`

### Response `200 OK`

```json
{
  "data": {
    "total": 25,
    "active": 20,
    "pending": 3,
    "inactive": 2
  },
  "timestamp": "2026-04-04T12:00:00Z"
}
```

---

## Enums

### TenantUserStatus

| Value      | Description                  |
|------------|------------------------------|
| `ACTIVE`   | User is active in the tenant |
| `PENDING`  | User is pending activation   |
| `INACTIVE` | User has been deactivated    |

---

## Notes

- **Request format:** All request bodies accept camelCase keys. The server converts them to snake_case internally via `CamelCaseRequest`.
- **Response format:** All response keys are serialized as camelCase via `CamelCaseJSONResponse`.
- **Pagination:** List endpoints use cursor-based pagination. Use the `nextCursor` value from the response to fetch the next page.
- **Phone/email as null:** If a user has no phone number or email, those fields return `null`.
- **Tenant role as null:** If no role is assigned, `tenantRole` returns `null`.
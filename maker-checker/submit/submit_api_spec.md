# Submit API Spec

## 1. API Purpose

This API is used by the dataset / attribute page `Submit` button.

It stages user changes into:

- `approval_request`
- `table_entity_pending`
- `attribute_entity_pending`

It does not publish directly to current tables.

## 2. OAuth2 and Token Validation

### Expected flow

Your current understanding is broadly correct.

The recommended flow is:

1. The frontend redirects the user to the auth server login page.
2. The auth server completes login and returns an authorization code.
3. The frontend exchanges the code for an access token.
4. The frontend calls the submit API with:

   `Authorization: Bearer <access_token>`

5. The submit API validates the token and extracts:
   - user identity
   - display name
   - tenant AD group / role information
6. The submit API compares the user groups from token claims with the target tenant requester group in `tenant_role_mapping`.

### Role of this service

This service should act as a resource server for write APIs.

It should not receive the authorization code directly.

It should only receive the access token.

### Practical integration options

There are two common ways to validate the access token:

1. **Local JWT validation**
   - If the auth server issues JWT access tokens, this service can validate the token locally using issuer and JWKS.
   - This is the preferred option for your setup because the access token already contains the required claims, including the custom tenant AD groups claim.

2. **UserInfo / Introspection**
   - This service calls the auth server using the bearer token.
   - The auth server returns the authenticated principal and claims.
   - This is an acceptable fallback when JWT validation cannot be configured yet.

### Current implementation choice

The current preferred implementation is local JWT validation:

- `AUTH_JWKS_URL`
- optionally `AUTH_ISSUER`
- optionally `AUTH_AUDIENCE`
- optionally `AUTH_JWT_ALGORITHMS`

If JWKS is not configured, the implementation can fall back to:

- `AUTH_USERINFO_URL`
- or `AUTH_INTROSPECTION_URL`

## 3. Authentication Decision

### Decision

The submit API must validate that the user is authenticated from the bearer access token.

### Reason

- The frontend login check is only a UX guard.
- The backend must still enforce authentication for all write actions.
- Otherwise, anonymous callers could bypass the UI and submit directly.

## 4. Tenant Requester Validation

The API validates that:

1. the bearer token is valid
2. the token contains user identity
3. the token contains group or role claims
4. the authenticated user belongs to the requester AD group for the target tenant
5. the tenant in the request matches the tenant of the operated dataset / attribute data

The common validation method is extracted into:

- `services/maker_checker_access_control.py`

This method can be reused by other protected APIs later.

## 5. Conflict Handling Decision

### Decision

Submit uses atomic conflict handling.

If any item in the request already has a pending request conflict, the entire submit fails with `409`.

### Reason

- one submit action should create one coherent `request_id`
- partial success would make request tracking and UI feedback much more complex
- atomic failure is easier to reason about and easier to review

### Conflict response

The API returns:

- `409 Conflict`
- error code `PENDING_CONFLICT`
- a list of conflicting items

## 6. Endpoint

`POST /api/v1/submit`

## 7. Request Headers

| Header | Required | Description |
| --- | --- | --- |
| `Authorization` | Yes | OAuth2 bearer access token |

## 8. Auth Server Configuration

The current implementation expects JWT validation configuration first:

| Setting | Required | Purpose |
| --- | --- | --- |
| `AUTH_JWKS_URL` | preferred | JWKS endpoint used to verify JWT access token signature |
| `AUTH_ISSUER` | optional | expected JWT issuer |
| `AUTH_AUDIENCE` | optional | expected JWT audience |
| `AUTH_JWT_ALGORITHMS` | optional | accepted JWT algorithms, default `RS256` |
| `AUTH_USERINFO_URL` | optional | user info endpoint used to resolve claims from token |
| `AUTH_INTROSPECTION_URL` | optional | introspection endpoint used to resolve token activity and claims |
| `AUTH_CLIENT_ID` | optional | client id for introspection endpoint |
| `AUTH_CLIENT_SECRET` | optional | client secret for introspection endpoint |
| `AUTH_GROUPS_CLAIM` | optional | token claim name holding group names, default `groups` |
| `AUTH_USER_ID_CLAIM` | optional | token claim name for user id, default `sub` |
| `AUTH_USER_NAME_CLAIM` | optional | token claim name for user display name, default `preferred_username` |

Recommended:

- `AUTH_JWKS_URL`

Fallback:

- `AUTH_USERINFO_URL`
- `AUTH_INTROSPECTION_URL`

At least one validation path must be configured.

## 9. Request Body

```json
{
  "sourceType": "UI",
  "domainId": "domain-001",
  "tenantUniqueId": "tenant-001",
  "makerComment": "submit from dataset page",
  "dataset": {
    "action": "U",
    "entityId": "dataset-123",
    "currentVersionSeq": 1,
    "tableMetadata": {
      "id": "dataset-123",
      "tableName": "customer_positions",
      "domainId": "domain-001",
      "tenantUniqueId": "tenant-001",
      "tableDescription": "Updated description"
    }
  },
  "attributes": [
    {
      "action": "U",
      "entityId": "attr-001",
      "currentVersionSeq": 1,
      "metadata": {
        "id": "attr-001",
        "tableId": "dataset-123",
        "Field Name": "position_id",
        "domainId": "domain-001",
        "tenantUniqueId": "tenant-001",
        "Field Description": "Updated field description"
      }
    },
    {
      "action": "A",
      "metadata": {
        "tableId": "dataset-123",
        "Field Name": "portfolio_id",
        "domainId": "domain-001",
        "tenantUniqueId": "tenant-001",
        "Field Description": "New field"
      }
    }
  ]
}
```

## 10. Request Rules

### Dataset rules

- `dataset.entityId` is required for `U` and `D`
- `dataset.tableMetadata` is required
- for `A`, a new dataset id is generated by backend

### Attribute rules

- `attribute.entityId` is required for `U` and `D`
- `attribute.metadata` is required
- for `A`, a new attribute id is generated by backend
- if a dataset add is included in the same request, the backend injects the generated dataset id into new attribute payloads when needed

### Scope validation

- request-level `domainId` and `tenantUniqueId` define the submit scope
- if item payload already contains those fields and they mismatch, the API returns `400`

## 11. Delete Dataset Rule

If the dataset action is `D`:

- the submit API only stages the dataset delete request
- it does **not** generate separate attribute delete pending rows

The related attributes are soft deleted later during approve publish logic.

This keeps the request lightweight even when one dataset has many attributes.

## 12. Success Response

`200 OK`

```json
{
  "requestId": "req-uuid",
  "requestStatus": "PENDING",
  "totalItems": 3,
  "datasetItems": 1,
  "attributeItems": 2,
  "message": "Submit accepted and staged in pending tables."
}
```

## 13. Error Responses

### `401 Unauthorized`

- missing bearer token
- invalid or expired token
- token does not contain user identity

### `403 Forbidden`

- user does not belong to requester AD group for the target tenant
- item tenant does not match request tenant

### `404 Not Found`

- target dataset or attribute does not exist for update / delete

### `409 Conflict`

- at least one item already has a pending request

Example:

```json
{
  "detail": {
    "code": "PENDING_CONFLICT",
    "message": "Submit failed because at least one item already has a pending request.",
    "conflicts": [
      {
        "entityType": "DATASET",
        "action": "U",
        "entityId": "dataset-123",
        "businessKey": "dataset:dataset-123",
        "existingRequestId": "req-001",
        "message": "A pending dataset request already exists for this dataset."
      }
    ]
  }
}
```

## 14. Database Behavior

On successful submit:

1. validate bearer token
2. resolve user claims from JWT access token, or from auth server fallback endpoint
3. validate requester role against `tenant_role_mapping`
4. validate tenant scope
5. check pending conflicts
6. create `approval_request`
7. create `table_entity_pending` if dataset change exists
8. create `attribute_entity_pending` rows

On submit conflict:

- no request row is created
- no pending row is created
- the entire submit fails atomically

## 15. Recommendation for Spring Boot OAuth2 Server

For your Spring Boot auth server, the cleanest target is:

1. use Authorization Code flow on the frontend
2. issue access token to the frontend
3. include user identity and AD group information in the access token claims
4. let this service behave as a resource server for write APIs

For the token payload, the most useful claims for this service are:

- user id
- display name
- groups or roles

For example:

- `sub`
- `preferred_username`
- `groups`

The frontend should send the access token, not the ID token.

If tenant requester / approver AD groups are already available in the access token claims, this service can map them directly against `tenant_role_mapping` without calling userinfo for every request.

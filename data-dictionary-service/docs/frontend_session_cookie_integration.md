# Frontend Session Cookie Integration Guide

## 1. Overview

Data Dictionary Service now uses a server-side session model for authenticated actions.

The frontend does not need to store access tokens. Instead, it calls the backend login API with username and password. If login succeeds, the backend creates a session in the database and returns an HttpOnly cookie named `dds_session`.

After login, the browser automatically sends this cookie to the backend for authenticated APIs such as submit, approve, reject, and `/auth/me`.

## 2. Key Rules

1. The frontend must call APIs with `credentials: "include"`.
2. The frontend cannot read or write the `dds_session` cookie because it is HttpOnly.
3. The backend owns session creation, validation, expiry, and logout.
4. The frontend should use `/api/v1/auth/me` to determine whether the user is currently logged in.
5. If a protected business API returns `401`, the frontend should treat the user as logged out or session expired.

## 3. Local Development

Backend local example:

```text
http://localhost:8080
```

Frontend local example:

```text
http://localhost:3000
http://localhost:5173
```

Backend local config should include:

```powershell
$env:ENV = "local"
$env:AUTH_ENABLE_MOCK_LOGIN = "true"
$env:AUTH_MOCK_USERS_FILE = "dev/auth/mock_users.json"
$env:SESSION_COOKIE_NAME = "dds_session"
$env:SESSION_COOKIE_SECURE = "false"
$env:SESSION_COOKIE_SAMESITE = "lax"
$env:SESSION_TTL_SECONDS = "28800"
$env:CORS_ALLOW_ORIGINS = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
```

For local testing, `SESSION_COOKIE_SECURE=false` is required because local HTTP cannot use Secure cookies.

## 4. Cloud Run Deployment

Frontend and backend are deployed as different Cloud Run services. Example:

```text
Frontend: https://data-dictionary-ui-xxxxx.a.run.app
Backend:  https://data-dictionary-api-xxxxx.a.run.app
```

Backend Cloud Run config should include:

```text
AUTH_LOGIN_URL=https://your-auth-server/login
CORS_ALLOW_ORIGINS=https://data-dictionary-ui-xxxxx.a.run.app
SESSION_COOKIE_NAME=dds_session
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=none
SESSION_TTL_SECONDS=28800
```

For cross-service Cloud Run calls, `SESSION_COOKIE_SAMESITE=none` and `SESSION_COOKIE_SECURE=true` are required so the browser can send the cookie cross-site over HTTPS.

Do not use `CORS_ALLOW_ORIGINS=*` when cookies are required. The backend must use explicit frontend origins.

## 5. Login Flow

Frontend calls:

```http
POST /api/v1/auth/login
```

Example:

```ts
const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
  method: "POST",
  credentials: "include",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    username,
    password,
  }),
});

if (!response.ok) {
  throw new Error("Login failed");
}

const user = await response.json();
```

On success, the backend returns `Set-Cookie: dds_session=...`. The browser stores it automatically.

The frontend should not manually store the session id in localStorage, sessionStorage, or JavaScript state.

## 6. Check Current User

Frontend calls:

```http
GET /api/v1/auth/me
```

Example:

```ts
const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
  method: "GET",
  credentials: "include",
});

const me = await response.json();

if (!me.authenticated) {
  // User is anonymous or session has expired.
}
```

Anonymous response:

```json
{
  "authenticated": false,
  "userId": null,
  "userName": null,
  "displayName": null,
  "email": null,
  "groups": [],
  "roles": []
}
```

Authenticated response:

```json
{
  "authenticated": true,
  "userId": "requester_user",
  "userName": "requester_user",
  "displayName": "Local Requester User",
  "email": "requester_user@example.com",
  "groups": ["Custody_Unity_REQUESTER"],
  "roles": [
    {
      "domainId": "...",
      "tenantUniqueId": "...",
      "roleType": "REQUESTER",
      "adGroupName": "Custody_Unity_REQUESTER"
    }
  ]
}
```

Recommended frontend usage:

1. Call `/auth/me` when the app starts.
2. Store the returned user profile and roles in frontend state.
3. Use `authenticated` to decide whether to show login state.
4. Use `roles` only for UI hints. Backend still performs final authorization.

## 7. Business API Calls

All authenticated business API calls must include credentials.

Example submit:

```ts
const response = await fetch(`${API_BASE_URL}/api/v1/submit`, {
  method: "POST",
  credentials: "include",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify(payload),
});

if (response.status === 401) {
  // Session is missing or expired. Redirect to login or show login modal.
}

if (response.status === 403) {
  // User is logged in but does not have the required tenant role.
}
```

Example approve:

```ts
const response = await fetch(`${API_BASE_URL}/api/v1/review/approve`, {
  method: "POST",
  credentials: "include",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify(payload),
});
```

Example reject:

```ts
const response = await fetch(`${API_BASE_URL}/api/v1/review/reject`, {
  method: "POST",
  credentials: "include",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify(payload),
});
```

## 8. Logout Flow

Frontend calls:

```http
POST /api/v1/auth/logout
```

Example:

```ts
await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
  method: "POST",
  credentials: "include",
});

// Clear frontend user state after logout succeeds.
```

The backend revokes the session and clears the cookie.

## 9. Session Expiry Handling

The frontend cannot inspect the HttpOnly cookie expiry directly. It should rely on backend responses.

Recommended handling:

1. On app startup, call `/auth/me`.
2. Before showing protected maker/checker actions, call `/auth/me` or rely on current frontend auth state.
3. For every protected business API, if response status is `401`, treat the session as expired.
4. Clear frontend user state and show login modal or redirect to login.
5. If response status is `403`, keep the user logged in but show an authorization error.

Status handling:

```text
200: API succeeded.
401: Not logged in, session missing, revoked, or expired.
403: Logged in but does not have required role for the tenant/request.
422: Request payload validation failed.
500/502: Backend or auth server error.
```

## 10. Cookie Maintenance

The browser maintains the cookie automatically. Frontend responsibilities are:

1. Always use `credentials: "include"` for backend calls.
2. Do not store the session id manually.
3. Do not attempt to read `dds_session`.
4. Clear frontend user state after logout or `401`.

Backend responsibilities are:

1. Set cookie on login.
2. Validate session on protected APIs.
3. Refresh `last_seen_at` when the session is used.
4. Reject expired or revoked sessions.
5. Clear cookie on logout.

## 11. Local Mock Accounts

For local testing before auth server integration, use:

```text
requester_user / requester123
Role: Custody_Unity_REQUESTER

approver_user / approver123
Role: Custody_Unity_APPROVER

maker_checker_user / makerchecker123
Role: Custody_Unity_REQUESTER + Custody_Unity_APPROVER
```

These accounts only work when:

```text
AUTH_ENABLE_MOCK_LOGIN=true
```

The authority names must exist in `tenant_role_mapping.ad_group_name`, otherwise login succeeds but `roles` will be empty.

## 12. Frontend API Client Example

```ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export async function apiFetch(path: string, options: RequestInit = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (response.status === 401) {
    // Clear frontend auth state and show login.
  }

  return response;
}
```

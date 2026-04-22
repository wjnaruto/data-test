# Local JWT Test Assets

These files are for local frontend/backend integration testing only.

## Files

- `private_key.pem`: local test signing key
- `public_key.pem`: matching public key
- `jwks.json`: JWKS document for backend validation
- `tokens.json`: pre-generated bearer tokens for common test scenarios

## Recommended local config

Set the service environment like this:

```powershell
$env:AUTH_JWKS_URL="http://127.0.0.1:9100/jwks.json"
$env:AUTH_ISSUER="http://local-test-auth"
$env:AUTH_AUDIENCE="data-dictionary-service"
$env:AUTH_GROUPS_CLAIM="groups"
$env:AUTH_USER_ID_CLAIM="sub"
$env:AUTH_USER_NAME_CLAIM="preferred_username"
```

## Serve JWKS locally

```powershell
cd D:\work\projects\data-dictonary-service\dev\auth
py -m http.server 9100
```

## Token scenarios

- `custody_unity_requester`
- `custody_unity_approver`
- `geneva_requester`
- `geneva_approver`

All tokens are RS256 JWT access tokens and include the `groups` claim.

from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "dev" / "auth"
PRIVATE_KEY_PATH = OUTPUT_DIR / "private_key.pem"
PUBLIC_KEY_PATH = OUTPUT_DIR / "public_key.pem"
JWKS_PATH = OUTPUT_DIR / "jwks.json"
TOKENS_PATH = OUTPUT_DIR / "tokens.json"
README_PATH = OUTPUT_DIR / "README.md"

ISSUER = "http://local-test-auth"
AUDIENCE = "data-dictionary-service"
GROUPS_CLAIM = "groups"
KID = "local-dev-rs256-1"
TOKEN_TTL_HOURS = 72


def b64url_uint(value: int) -> str:
    byte_length = (value.bit_length() + 7) // 8
    raw = value.to_bytes(byte_length, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_keys() -> tuple[bytes, bytes, dict]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    public_numbers = public_key.public_numbers()
    jwk = {
        "kty": "RSA",
        "use": "sig",
        "kid": KID,
        "alg": "RS256",
        "n": b64url_uint(public_numbers.n),
        "e": b64url_uint(public_numbers.e),
    }
    return private_pem, public_pem, jwk


def build_token(private_pem: bytes, *, sub: str, preferred_username: str, name: str, groups: list[str]) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": sub,
        "preferred_username": preferred_username,
        "name": name,
        GROUPS_CLAIM: groups,
        "scope": "openid profile email api.read api.write",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=TOKEN_TTL_HOURS)).timestamp()),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, private_pem, algorithm="RS256", headers={"kid": KID})


def write_readme() -> None:
    content = f"""# Local JWT Test Assets

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
$env:AUTH_ISSUER="{ISSUER}"
$env:AUTH_AUDIENCE="{AUDIENCE}"
$env:AUTH_GROUPS_CLAIM="{GROUPS_CLAIM}"
$env:AUTH_USER_ID_CLAIM="sub"
$env:AUTH_USER_NAME_CLAIM="preferred_username"
```

## Serve JWKS locally

```powershell
cd {OUTPUT_DIR}
py -m http.server 9100
```

## Token scenarios

- `custody_unity_requester`
- `custody_unity_approver`
- `geneva_requester`
- `geneva_approver`

All tokens are RS256 JWT access tokens and include the `{GROUPS_CLAIM}` claim.
"""
    README_PATH.write_text(content, encoding="utf-8")


def main() -> None:
    ensure_output_dir()
    private_pem, public_pem, jwk = generate_keys()

    PRIVATE_KEY_PATH.write_bytes(private_pem)
    PUBLIC_KEY_PATH.write_bytes(public_pem)
    JWKS_PATH.write_text(json.dumps({"keys": [jwk]}, indent=2), encoding="utf-8")

    scenarios = {
        "custody_unity_requester": {
            "sub": "u10001",
            "preferred_username": "custody.unity.requester",
            "name": "Custody Unity Requester",
            "groups": ["Custody_Unity_REQUESTER"],
        },
        "custody_unity_approver": {
            "sub": "u10002",
            "preferred_username": "custody.unity.approver",
            "name": "Custody Unity Approver",
            "groups": ["Custody_Unity_APPROVER"],
        },
        "geneva_requester": {
            "sub": "u10003",
            "preferred_username": "geneva.requester",
            "name": "GENEVA Requester",
            "groups": ["GENEVA_REQUESTER"],
        },
        "geneva_approver": {
            "sub": "u10004",
            "preferred_username": "geneva.approver",
            "name": "GENEVA Approver",
            "groups": ["GENEVA_APPROVER"],
        },
    }

    tokens = {
        name: {
            "description": config["name"] if "name" in config else name,
            "sub": config["sub"],
            "preferred_username": config["preferred_username"],
            "groups": config["groups"],
            "token": build_token(
                private_pem,
                sub=config["sub"],
                preferred_username=config["preferred_username"],
                name=config["name"],
                groups=config["groups"],
            ),
        }
        for name, config in scenarios.items()
    }

    TOKENS_PATH.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
    write_readme()

    print(f"Generated JWKS at: {JWKS_PATH}")
    print(f"Generated tokens at: {TOKENS_PATH}")


if __name__ == "__main__":
    main()

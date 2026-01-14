from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from typing import Any, Dict, List

app = FastAPI()

_EVENTS: List[dict] = []
_MODE = {"ok": True, "message": ""}


@app.get("/__events")
def events():
    return {"events": _EVENTS}


@app.post("/__reset")
def reset():
    _EVENTS.clear()
    _MODE["ok"] = True
    _MODE["message"] = ""
    return {"status": "ok"}


@app.post("/__mode")
def mode(payload_mode: dict):
    _MODE["ok"] = payload_mode.get("ok", True)
    _MODE["message"] = payload_mode.get("message", "")
    return {"status": "ok"}


def _missing_headers(headers: Dict[str, str]) -> List[str]:
    missing = []
    # ITMClient sets these explicitly
    if not headers.get("authorization"):
        missing.append("Authorization")
    if not headers.get("consumer-type"):
        missing.append("Consumer-Type")
    if not headers.get("source-system"):
        missing.append("source-system")
    ct = headers.get("content-type", "")
    if "application/json" not in ct.lower():
        missing.append("Content-Type=application/json")
    return missing


def _validate_payload(body: Any) -> str | None:
    if not isinstance(body, dict):
        return "body must be a JSON object"
    inst = body.get("instructions")
    if not isinstance(inst, list) or not inst:
        return "missing or invalid 'instructions'"
    i0 = inst[0]
    if not isinstance(i0, dict):
        return "instructions[0] must be an object"
    for k in ("sourceUniqueRef", "clientAccountRegion", "messageCategory", "productIdentifier", "payload"):
        if k not in i0:
            return f"missing field in instructions[0]: {k}"
    return None


@app.post("/{path:path}")
async def catch_all_post(path: str, req: Request):
    headers = {k.lower(): v for k, v in req.headers.items()}
    try:
        body = await req.json()
    except Exception:
        body = None

    _EVENTS.append(
        {
            "path": f"/{path}",
            "headers": dict(req.headers),
            "body": body,
        }
    )

    missing = _missing_headers(headers)
    if missing:
        return JSONResponse(
            status_code=400,
            content={
                "status": "failed",
                "message": f"missing headers: {', '.join(missing)}",
                "instructionsCount": 0,
            },
        )

    err = _validate_payload(body)
    if err:
        return JSONResponse(
            status_code=400,
            content={"status": "failed", "message": err, "instructionsCount": 0},
        )

    if not _MODE["ok"]:
        return JSONResponse(
            status_code=200,
            content={
                "status": "failed",
                "message": _MODE["message"] or "forced failure",
                "instructionsCount": len(body.get("instructions", [])) if isinstance(body, dict) else 0,
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": "ok",
            "instructionsCount": len(body.get("instructions", [])),
        },
    )
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from typing import Any, List

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
def mode(payload: dict):
    _MODE["ok"] = payload.get("ok", True)
    _MODE["message"] = payload.get("message", "")
    return {"status": "ok"}

def _validate_payload(body: Any) -> str | None:
    if not isinstance(body, dict):
        return "body must be a JSON object"
    if "file_path" not in body:
        return "missing 'file_path' field"
    if "reason" not in body:
        return "missing 'reason' field"
    return None

@app.post("/{path:path}")
async def catch_all_post(path: str, req: Request):
    try:
        body = await req.json()
        print(f"Fake Iqube: {path} - {body}")
    except Exception:
        body = None
    
    _EVENTS.append({"path": f"/{path}", "headers": dict(req.headers), "body": body})
    
    err = _validate_payload(body)
    if err:
        return JSONResponse(status_code=400, content={"status": "failed", "message": err})
    
    if not _MODE["ok"]:
        return JSONResponse(status_code=200, content={"status": "failed", "message": _MODE["message"]})
    
    return JSONResponse(status_code=200, content={"status": "ok", "message": "notified"})
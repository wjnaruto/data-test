from fastapi import FastAPI, UploadFile, File, Form, Body
from fastapi.responses import JSONResponse
from typing import Any, Dict, List, Optional

app = FastAPI()

_EVENTS: List[dict] = []

# Mode:
# - ok=True: return {"result":[...], "failed":[]}
# - ok=False: return {"failed":[{"status":"failed", ...}], "result":[]}
_MODE: Dict[str, Any] = {
    "ok": True,
    "response_type": "ok",  # ok | failed | non_dict | missing_result | empty_result | http_400 | http_422
    "failure_reason": "data format error",
    "detailed_failure_reason": "forced failure",
}


@app.get("/__events")
def events():
    return {"events": _EVENTS}


@app.post("/__reset")
def reset():
    _EVENTS.clear()
    _MODE["ok"] = True
    _MODE["response_type"] = "ok"
    _MODE["failure_reason"] = "data format error"
    _MODE["detailed_failure_reason"] = "forced failure"
    return {"status": "ok"}


@app.post("/__mode")
def mode(payload: dict = Body(default_factory=dict)):
    if "ok" in payload:
        _MODE["ok"] = bool(payload["ok"])
    if "response_type" in payload:
        _MODE["response_type"] = str(payload["response_type"] or "")
    if "failure_reason" in payload:
        _MODE["failure_reason"] = str(payload["failure_reason"] or "")
    if "detailed_failure_reason" in payload:
        _MODE["detailed_failure_reason"] = str(payload["detailed_failure_reason"] or "")
    return {"status": "ok", "mode": dict(_MODE)}


def _success_payload(filename: str, remitter: str) -> Dict[str, Any]:
    row = {"filename": filename, "remitter": remitter, "extracted": True}
    return {"result": [row], "failed": []}


def _failed_payload(filename: str) -> Dict[str, Any]:
    return {
        "failed": [
            {
                "status": "failed",
                "failure_reason": _MODE.get("failure_reason", "unknown"),
                "detailed_failure_reason": _MODE.get("detailed_failure_reason", ""),
                "file_name": filename,
            }
        ],
        "result": [],
    }


def _apply_mode(filename: str, remitter: str):
    rt = str(_MODE.get("response_type", "ok")).lower()
    if rt == "http_400":
        return JSONResponse(status_code=400, content={"detail": "forced http 400"})
    if rt == "http_422":
        return JSONResponse(status_code=422, content={"detail": "forced http 422"})
    if rt == "non_dict":
        return JSONResponse(status_code=200, content=["not-a-dict"])
    if rt == "missing_result":
        return JSONResponse(status_code=200, content={"failed": []})
    if rt == "empty_result":
        return JSONResponse(status_code=200, content={"failed": [], "result": []})

    if (not _MODE.get("ok", True)) or rt == "failed":
        return JSONResponse(status_code=200, content=_failed_payload(filename or ""))

    return JSONResponse(status_code=200, content=_success_payload(filename or "", remitter))


@app.post("/extract/{remitter}")
async def extract_legacy(
    remitter: str,
    file: UploadFile = File(...),
    temp_pwd: Optional[str] = Form(default=None),
    replace_pwd: Optional[bool] = Form(default=False),
):
    _EVENTS.append(
        {
            "path": f"/extract/{remitter}",
            "filename": file.filename,
            "content_type": file.content_type,
            "temp_pwd": temp_pwd,
            "replace_pwd": replace_pwd,
        }
    )

    return _apply_mode(file.filename or "", remitter)


@app.post("/extract/{remitter}/extraction")
async def extract_upload(
    remitter: str,
    file: UploadFile = File(...),
    temp_pwd: Optional[str] = Form(default=None),
    replace_pwd: Optional[bool] = Form(default=False),
):
    _EVENTS.append(
        {
            "path": f"/extract/{remitter}/extraction",
            "filename": file.filename,
            "content_type": file.content_type,
            "temp_pwd": temp_pwd,
            "replace_pwd": replace_pwd,
        }
    )
    return _apply_mode(file.filename or "", remitter)


@app.post("/extract/{remitter}/filename_extraction")
async def extract_by_filename(
    remitter: str,
    file_name: str = Form(...),
    temp_pwd: Optional[str] = Form(default=None),
    replace_pwd: Optional[bool] = Form(default=False),
):
    _EVENTS.append(
        {
            "path": f"/extract/{remitter}/filename_extraction",
            "filename": file_name,
            "content_type": None,
            "temp_pwd": temp_pwd,
            "replace_pwd": replace_pwd,
        }
    )
    return _apply_mode(file_name or "", remitter)

import json
import uuid
from typing import Tuple, List, Any
import httpx
from misc.config import settings
from misc.constants import Events
from logs.logging_utils import log_event
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from managers.itm_oauth_token_manager import ITMOAuthTokenManager


class ITMClient:
    def __init__(self):
        self.settings = settings
        self.base_url = self.settings.ITM_API_URL
        timeout = httpx.Timeout(
            connect=self.settings.ITM_CONNECT_TIMEOUT,
            read=self.settings.ITM_READ_TIMEOUT,
            write=self.settings.ITM_WRITE_TIMEOUT,
            pool=self.settings.ITM_POOL_TIMEOUT,
        )
        self._client = httpx.AsyncClient(
            timeout=timeout,
            verify=(self.settings.ITM_CA_BUNDLE or self.settings.ITM_VERIFY_TLS),
            trust_env=False
        )
        self._auth_mgr = ITMOAuthTokenManager()

    async def aclose(self):
        await self._auth_mgr.aclose()
        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(settings.MAX_RETRY_COUNT),
        wait=wait_exponential(multiplier=settings.RETRY_BASE_SECONDS, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    async def _post(self, url: str, json: dict, headers: dict) -> httpx.Response:
        return await self._client.post(url, json=json, headers=headers)

    async def submit(self, foI_data: dict, remitter: str, path) -> Tuple[bool, str, bool]:
        try:
            token = await self._auth_mgr.get_token()
        except Exception as e:
            log_event(event="ITM_TOKEN_FAILED", level="error", message=f"exception:{e}")
            return False, f"failed to get oauth token: {e}", False

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Consumer-Type": settings.ENV,
            "source-system": "DET"
        }

        payload = await self._build_itm_payload(foI_data, remitter)

        try:
            resp = await self._post(self.base_url, json=payload, headers=headers)
        except Exception as e:
            log_event(event="ITM_FAILED", level="error", message=f"exception:{e}")
            return False, str(e), True

        if resp.status_code in (401, 403):
            new_token = await self._auth_mgr.refresh_after_failure()
            headers["Authorization"] = f"Bearer {new_token}"
            resp = await self._post(self.base_url, json=payload, headers=headers)

        status_code = resp.status_code
        text = resp.text or ""
        ok_http = httpx.codes.is_success(status_code)  # 200 <= status_code < 300
        retryable_internal = 500 <= status_code < 600

        try:
            j = resp.json()
            status_val = j.get("status", "").lower()
            msg = j.get("message", text)
            cnt = j.get("instructionsCount", -1)
            ok = ok_http and (status_val == "success")
        except Exception:
            msg = text
            cnt = -1
            ok = ok_http

        if ok:
            log_event(event=Events.ITM_SUCCEEDED, message=f"code={status_code}", extra={"instructionCount": cnt})
        else:
            log_event(event=Events.ITM_FAILED, level="error", message=f"code={status_code}, resp={text[:200]}",
                        extra={"instructionCount": cnt})

        return ok, msg, (not ok and retryable_internal)

    async def _build_itm_payload(self, foi_data: dict, remitter: str):
        return {
            "instructions": [
                {
                    "sourceUniqueRef": str(uuid.uuid4()),
                    "clientIdentifier": remitter,
                    "clientAccountRegion": settings.ITM_CLIENT_ACCOUNT_REGION,
                    "messageCategory": settings.ITM_MESSAGE_CATEGORY,
                    "productIdentifier": settings.ITM_PRODUCT_IDENTIFIER,
                    "payload": json.dumps(foi_data)
                }
            ]
        }

    async def close(self):
        await self._client.aclose()

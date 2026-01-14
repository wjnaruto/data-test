import httpx
from .it_config import ITConfig

class CoordinatorClient:
    def __init__(self, cfg: ITConfig):
        self.cfg = cfg
        self._client = httpx.Client(timeout=10.0, trust_env=False)

    def close(self) -> None:
        self._client.close()

    def run_ok(self):
        url = f"{self.cfg.coordinator_base_url}{self.cfg.run_path}"
        print (f"[IT] Triggering coordinator run at {url}")

        r = self._client.post(url)
        print(f"[IT] Coordinator run response: {r.status_code} {r.text}")

        if r.status_code not in (200, 202):
            raise AssertionError(f"Coordinator run failed: {r.status_code} {r.text}")
        
        ct = r.headers.get("Content-Type", "")
        return r.json() if ct.startswith("application/json") else r.text

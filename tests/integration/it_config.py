from dataclasses import dataclass
import os

@dataclass(frozen=True)
class ITConfig:
    coordinator_base_url: str
    run_path: str
    db_url: str

    @staticmethod
    def load() -> "ITConfig":
        def req(k: str) -> str:
            v = os.getenv(k)
            if not v:
                raise RuntimeError(f"Missing required env var for ITConfig: {k}")
            return v

        return ITConfig(
            coordinator_base_url=req("IT_COORDINATOR_BASE_URL").rstrip("/"),
            run_path=os.getenv("IT_COORD_RUN_PATH", "/api/v1/coordinator/runs"),
            db_url=req("DATABASE_URL"),
        )
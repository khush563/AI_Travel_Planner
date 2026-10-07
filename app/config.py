from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    demo_mode: str = "auto"
    llm_provider: str = "openai"
    llm_model: str = "gpt-4.1-mini"
    openai_api_key: str = ""
    llm_base_url: str | None = None
    llm_timeout_seconds: float = 180.0
    serper_api_key: str = ""
    database_dir: Path = Path(".data")
    log_level: str = "INFO"

    @property
    def mode(self) -> str:
        value = self.demo_mode.strip().lower()
        if value in {"true", "1", "yes"}:
            return "demo"
        if value in {"false", "0", "no"}:
            return "live"
        if value == "auto":
            return "live" if self.openai_api_key and self.serper_api_key else "demo"
        raise ValueError("DEMO_MODE must be auto, true, or false")

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(PROJECT_ROOT / ".env")
        return cls(
            demo_mode=os.getenv("DEMO_MODE", "auto"),
            llm_provider=os.getenv("LLM_PROVIDER", "openai"),
            llm_model=os.getenv("LLM_MODEL", "gpt-4.1-mini"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            llm_base_url=os.getenv("LLM_BASE_URL") or None,
            llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "180")),
            serper_api_key=os.getenv("SERPER_API_KEY", ""),
            database_dir=Path(os.getenv("DATABASE_DIR", ".data")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

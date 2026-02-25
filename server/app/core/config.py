from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Growora"
    app_version: str = "0.2.0"
    db_path: str = "server/data/growora.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    growora_llm_provider: str = "none"
    growora_ollama_url: str = "http://localhost:11434"
    growora_ollama_model: str = "llama3.1"
    growora_network_mode: str = "offline"
    growora_allowed_hosts: str = "localhost,127.0.0.1"
    growora_log_prompts: bool = False

    coevo_url: str | None = None
    coevo_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def sqlite_url(self) -> str:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        Path("server/data/uploads").mkdir(parents=True, exist_ok=True)
        Path("server/data/extracted").mkdir(parents=True, exist_ok=True)
        Path("server/data/exports").mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{self.db_path}"

    @property
    def allowed_hosts(self) -> set[str]:
        return {h.strip() for h in self.growora_allowed_hosts.split(",") if h.strip()}


settings = Settings()

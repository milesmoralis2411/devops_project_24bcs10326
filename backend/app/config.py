from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (or a local .env file)."""

    app_name: str = "StockPilot API"
    app_version: str = "1.0.0"
    environment: str = "local"
    # Commit SHA baked into the image by CI; lets the UI show exactly which build is live.
    git_sha: str = "dev"
    database_url: str = "postgresql+psycopg://stockpilot:stockpilot@localhost:5432/stockpilot"
    # Comma separated list of allowed browser origins (only needed when the UI is served
    # from a different origin than the API, e.g. the Vite dev server).
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    seed_demo_data: bool = False
    # How long the container waits for PostgreSQL on start-up before giving up.
    db_wait_timeout_seconds: int = 90
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()

from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "CHIRAAG Routing Engine"
    API_V1_STR: str = "/api/v1"

    # PostgreSQL / PostGIS Connection Settings
    POSTGRES_USER: str = "chiraag"
    POSTGRES_PASSWORD: str = "chiraag"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5434"
    POSTGRES_DB: str = "chiraag"

    # Managed providers require TLS. "prefer" negotiates it when offered and
    # falls back for the local container, which has no certificate.
    POSTGRES_SSLMODE: str = "prefer"

    # Set this to a full connection string to bypass the parts above. Handy
    # when a host hands you one DSN rather than five separate values.
    DATABASE_URL_OVERRIDE: str = ""

    # Comma-separated origins allowed to call the API. Set to the deployed
    # frontend URL in production.
    ALLOWED_ORIGINS_RAW: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def DATABASE_URL(self) -> str:
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE

        # Managed database passwords routinely contain characters that are
        # reserved in a URL (@ : / ? #). Without quoting, the DSN silently
        # parses into the wrong host or user.
        user = quote_plus(self.POSTGRES_USER)
        password = quote_plus(self.POSTGRES_PASSWORD)

        return (
            f"postgresql://{user}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            f"?sslmode={self.POSTGRES_SSLMODE}"
        )

    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS_RAW.split(",")
            if origin.strip()
        ]


settings = Settings()
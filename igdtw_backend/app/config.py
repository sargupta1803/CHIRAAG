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
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
settings = Settings()
from typing import List, Union, Optional
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for FasalFlow backend."""

    PROJECT_NAME: str = "FasalFlow API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+psycopg://fasalflow:fasalflow_dev@localhost:5432/fasalflow"
    TEST_DATABASE_URL: Optional[str] = None

    # Security & JWT
    JWT_SECRET: str = "fasalflow_dev_jwt_secret_key_2026_hsc27_min32"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60 * 24 * 7  # 7 days
    INTERNAL_API_KEY: str = "fasalflow_internal_secret_key_change_in_production"

    # CORS
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    from pydantic import model_validator

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        insecure_defaults = [
            "fasalflow_super_secret_jwt_key_for_dev_change_in_production",
            "fasalflow_dev_jwt_secret_key_2026_hsc27_min32",
            "secret",
            "changeme",
            "default",
        ]
        if self.ENVIRONMENT.lower() == "production":
            if not self.JWT_SECRET or self.JWT_SECRET.strip() in insecure_defaults or len(self.JWT_SECRET) < 32:
                raise ValueError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: A strong, non-default JWT_SECRET "
                    "(at least 32 characters) must be configured in production."
                )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

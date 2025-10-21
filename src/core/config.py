from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = Field("LogCenter API", env="APP_NAME")
    ENV: str = Field("dev", env="ENV")
    HOST: str = Field("0.0.0.0", env="HOST")
    PORT: int = Field(8000, env="PORT")

    # Mongo (Atlas ou self-hosted)
    MONGO_URI: str = Field(..., env="MONGO_URI")
    MONGO_DB: str = Field("logcenter", env="MONGO_DB")
    MONGO_DEBUG: bool = Field(False, env="MONGO_DEBUG")

    # Auth
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    REQUIRE_API_KEY: bool = Field(False, env="REQUIRE_API_KEY")

    # Observabilidade
    SENTRY_DSN: Optional[str] = Field(None, env="SENTRY_DSN")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CargoFlow AI API"
    app_env: str = "development"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./cargoflow.db"
    database_echo: bool = False
    auto_create_tables: bool = False
    jwt_secret_key: str = "change-me-for-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_minutes: int = 60 * 24 * 7

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()

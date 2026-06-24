from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "sqlite:///./app.db"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    GROQ_API_KEY: str = ""
    SERPER_API_KEY: str = ""
    WP_URL: str = ""
    WP_USERNAME: str = ""
    WP_APP_PASSWORD: str = ""
    DEFAULT_LLM_MODEL: str = "llama-3.3-70b-versatile"


settings = Settings()

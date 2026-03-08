from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Trash WebApp API"
    ENV: str = "dev"

    DATABASE_URL: str

    JWT_SECRET: str
    JWT_EXPIRES_MINUTES: int = 60 * 24 * 30

    BOT_TOKEN: str = ""
    TELEGRAM_AUTH_DEV_BYPASS: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
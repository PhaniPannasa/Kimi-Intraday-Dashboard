from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://engine:engine@timescaledb:5432/intraday"
    redis_url: str = "redis://redis:6379/0"
    upstox_analytics_token: str = ""
    upstox_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    session_start: str = "09:15"
    session_end: str = "15:30"
    force_expire: str = "15:15"
    nightly_rebuild: str = "23:00"
    nifty_universe_count: int = 100
    top_n: int = 25

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

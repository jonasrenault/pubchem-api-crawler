from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    rate_limit_calls: int = 5
    rate_limit_period: int = 3


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    zenoti_api_key: str = ""
    zenoti_client_id: str = ""
    zenoti_client_secret: str = ""
    zenoti_base_url: str = "https://api.zenoti.com/v1"
    database_url: str = "sqlite+aiosqlite:///./zenoti_warehouse.db"
    sync_page_size: int = 100

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()

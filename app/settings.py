from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    db_host: str
    db_port: str
    postgres_user: str
    postgres_password: str
    postgres_db: str
    
    port: int
    secret_key: str
    database_url: str
    redis_url: str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
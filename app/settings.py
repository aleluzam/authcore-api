from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ConfigDict

class Settings(BaseSettings):
    postgres_host: str
    postgres_port: str
    postgres_user: str
    postgres_password: str
    postgres_name: str
    postgres_url: str
    
    secret_key: str
    
    redis_url: str    
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
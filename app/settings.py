from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    base_url: str
    
    db_host: str
    db_port: str
    postgres_user: str
    postgres_password: str
    postgres_db: str
    
    port: int
    
    secret_key: str
    algorithm: str
    
    database_url: str
    async_database_url: str
    redis_url: str
    
    resend_api_key: str
    admin_mail: str
    

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
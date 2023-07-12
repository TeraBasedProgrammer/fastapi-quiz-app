from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str 
    port: int 
    database_url: str

    class Config:
        env_file = ".env"

settings = Settings()
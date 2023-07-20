from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str 
    port: int 
    database_url: str
    redis_url: str
    test_database_url: str
    jwt_secret: str
    auth0_domain: str 
    auth0_api_audience: str 
    auth0_algorithms: str 
    auth0_issuer: str 

    class Config:
        env_file = ".env"

settings = Settings()
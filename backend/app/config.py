import json
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    supabase_service_role_key: str = ""
    cors_origins: str = '["http://localhost:3000"]'
    environment: str = "development"

    @property
    def cors_origins_list(self) -> list[str]:
        return json.loads(self.cors_origins)

    class Config:
        env_file = ".env"


settings = Settings()

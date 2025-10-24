"""Configuration management for Pharma Intelligence scrapers."""

import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase Configuration
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_KEY")
    supabase_service_role_key: Optional[str] = Field(None, env="SUPABASE_SERVICE_ROLE_KEY")

    # Scraper Configuration
    max_requests_per_crawl: int = Field(default=100000, env="MAX_REQUESTS_PER_CRAWL")
    request_delay_ms: int = Field(default=500, env="REQUEST_DELAY_MS")
    max_concurrency: int = Field(default=5, env="MAX_CONCURRENCY")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Proxy Configuration
    proxy_urls: Optional[str] = Field(None, env="PROXY_URLS")

    # Optional: BigQuery Configuration (for sync)
    google_application_credentials: Optional[str] = Field(
        None, env="GOOGLE_APPLICATION_CREDENTIALS"
    )
    gcp_project_id: Optional[str] = Field(None, env="GCP_PROJECT_ID")
    bq_dataset_id: Optional[str] = Field(None, env="BQ_DATASET_ID")

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = False


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings (singleton pattern)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Pharmacy target URLs
PHARMACY_URLS = {
    "farma_oliva": {
        "base_url": "https://www.farmaoliva.com.py",
        "categories": {
            "medicamentos": "/catalogo/medicamentos-c3",
            "suplementos": "/catalogo/suplementos-nutricionales-c5",
        },
    },
    "punto_farma": {
        "base_url": "https://www.puntofarma.com.py",
        "categories": {},  # TODO: Map categories
    },
    "farma_center": {
        "base_url": "https://www.farmacenter.com.py",
        "categories": {
            "medicamentos": "/medicamentos",
        },
    },
    "farmacia_catedral": {
        "base_url": "https://www.farmaciacatedral.com.py",
        "categories": {
            "medicamentos": "/categoria/1/medicamentos?marcas=&categorias=&categorias_top=",
            "suplementos": "/categoria/35/suplemento-vitaminico-y-mineral?marcas=&categorias=&categorias_top=",
        },
    },
}

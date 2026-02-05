from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    GROQ_API_KEY: str  # Will be loaded from .env file
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        env_file_encoding = 'utf-8'


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance - cached to avoid re-reading .env on every request"""
    return Settings()


# Singleton instance for convenience
settings = get_settings()

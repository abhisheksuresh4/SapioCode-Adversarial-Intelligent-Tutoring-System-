from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # ── AI Inference ──────────────────────────
    GROQ_API_KEY: str  # Will be loaded from .env file
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # ── Role 1: Execution Backend ─────────────
    EXECUTION_BACKEND_URL: str = "http://localhost:8000"

    # ── Role 3: BKT / Cognitive Engine ────────
    BKT_BACKEND_URL: str = "http://localhost:8001"

    # ── Role 3: Neo4j (for direct queries) ────
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "sapiocode_dev"

    # ── This service (Role 2) ─────────────────
    AI_ENGINE_PORT: int = 8002

    # ── Database ──────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./sapiocode.db"
    REDIS_URL: str = ""

    # ── JWT Auth ──────────────────────────────
    JWT_SECRET_KEY: str = "dev-secret-change-in-production"
    JWT_EXPIRE_MINUTES: int = 60

    # ── BKT Default Parameters ────────────────
    BKT_DEFAULT_P_L: float = 0.3    # Prior mastery
    BKT_DEFAULT_P_T: float = 0.1    # Learn probability
    BKT_DEFAULT_P_S: float = 0.1    # Slip probability
    BKT_DEFAULT_P_G: float = 0.2    # Guess probability

    # ── Tutoring Thresholds ───────────────────
    FRUSTRATION_HIGH: float = 0.7
    FRUSTRATION_MED: float = 0.4
    MASTERY_THRESHOLD: float = 0.8   # Concept considered "mastered"

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

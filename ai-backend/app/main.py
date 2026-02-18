import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ai_routes
from app.api import viva_routes
from app.api import peer_routes
from app.api import integration_routes
from app.api import teacher_routes
from app.auth.auth_routes import router as auth_router

logger = logging.getLogger("sapiocode")


# ── Lifespan ──────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle for the AI engine."""
    logger.info("SapioCode AI Engine starting up …")

    # ── Database (PostgreSQL) ──
    try:
        from app.db.postgres import init_db
        await init_db()
        logger.info("✓ PostgreSQL tables initialised")
    except Exception as e:
        logger.warning(f"PostgreSQL unavailable – running in-memory ({e})")

    # ── Cache (Redis) ──
    try:
        from app.db.redis_cache import get_redis_cache
        redis = get_redis_cache()
        await redis.connect()
        logger.info("✓ Redis connected")
    except Exception as e:
        logger.warning(f"Redis unavailable – caching disabled ({e})")

    # ── Knowledge graph (Neo4j) ──
    try:
        from app.db.neo4j_graph import get_curriculum_graph, seed_curriculum
        graph = get_curriculum_graph()
        await graph.connect()
        await graph.setup_schema()
        await seed_curriculum(graph)
        logger.info("✓ Neo4j graph ready & seeded")
    except Exception as e:
        logger.warning(f"Neo4j unavailable – using fallback curriculum ({e})")

    yield  # ← Application serves requests here

    # ── Shutdown ──
    logger.info("SapioCode AI Engine shutting down …")
    try:
        from app.services.groq_service import get_groq_service
        groq = get_groq_service()
        await groq.close()
    except Exception:
        pass
    try:
        from app.db.redis_cache import get_redis_cache
        redis = get_redis_cache()
        await redis.disconnect()
    except Exception:
        pass
    try:
        graph = get_curriculum_graph()
        graph.close()
    except Exception:
        pass
    logger.info("Shutdown complete.")


# ── App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="SapioCode AI Engine",
    description="The Brain – AI tutoring and verification system for SapioCode",
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS – allow local dev frontends; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://localhost:8001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(ai_routes.router, prefix="/api/ai", tags=["AI"])
app.include_router(viva_routes.router, prefix="/api", tags=["Viva Voce"])
app.include_router(peer_routes.router, prefix="/api", tags=["Peer Learning"])
app.include_router(integration_routes.router, prefix="/api/integration", tags=["Integration"])
app.include_router(teacher_routes.router, prefix="/api/teacher", tags=["Teacher Dashboard"])


@app.get("/")
async def root():
    """Root endpoint – welcome message"""
    return {
        "message": "SapioCode AI Engine",
        "status": "operational",
        "role": "The Brain 🧠",
        "version": "4.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    checks = {"service": "ai-engine", "role": "AI Engineer (The Brain)"}
    # Optional: probe backing services
    try:
        from app.db.redis_cache import get_redis_cache
        r = get_redis_cache()
        checks["redis"] = "connected" if r._connected else "unavailable"
    except Exception:
        checks["redis"] = "unavailable"
    checks["status"] = "healthy"
    return checks

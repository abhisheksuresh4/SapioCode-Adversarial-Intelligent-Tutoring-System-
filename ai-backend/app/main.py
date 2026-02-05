from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import ai_routes
from app.api import viva_routes
from app.api import peer_routes


app = FastAPI(
    title="SapioCode AI Engine",
    description="The Brain - AI tutoring and verification system for SapioCode",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(ai_routes.router, prefix="/api/ai", tags=["AI"])
app.include_router(viva_routes.router, prefix="/api", tags=["Viva Voce"])
app.include_router(peer_routes.router, prefix="/api", tags=["Peer Learning"])


@app.get("/")
async def root():
    """Root endpoint - Welcome message"""
    return {
        "message": "SapioCode AI Engine",
        "status": "operational",
        "role": "The Brain 🧠",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "ai-engine",
        "role": "AI Engineer (The Brain)"
    }


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    from app.services.groq_service import get_groq_service
    try:
        groq = get_groq_service()
        await groq.close()
    except:
        pass

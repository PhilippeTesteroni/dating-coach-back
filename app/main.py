import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, user, purchase, characters, modes, conversations, app_settings, subscription
from app.schemas import HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info(f"🚀 Starting Dating Coach API on port {settings.port}")
    logger.info(f"📱 App ID: {settings.app_id}")
    logger.info(f"🌍 Environment: {settings.environment}")
    yield
    logger.info("👋 Shutting down Dating Coach API")


app = FastAPI(
    title="Dating Coach API",
    description="Backend API for Dating Coach mobile app",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(user.router, prefix="/api")
app.include_router(purchase.router)
app.include_router(characters.router, prefix="/api")
app.include_router(modes.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(app_settings.router, prefix="/api")
app.include_router(subscription.router, prefix="/api")


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Health check endpoint"""
    return HealthResponse()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
    )

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from app.core.config import settings
from app.core.database import engine, Base
# Ensure all routers are imported correctly
from app.api import auth, users, agents, telemetry, admin, ai, student, academic
# Import models to ensure SQLModel sees them for table creation
from app.models.academic import Student, AcademicRecord 
from app.middleware.audit import AuditLoggingMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup logging
    logger = logging.getLogger("uvicorn.error")
    
    if settings.secret_key == "change-me-in-production":
        logger.warning("SECRET_KEY is default; set a secure value in production")
    
    # DATABASE INITIALIZATION (SQLite)
    try:
        async with engine.begin() as conn:
            # Create tables for both SQLAlchemy Base and SQLModel
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    yield
    # Clean up
    await engine.dispose()

# --- APP INITIALIZATION ---
app = FastAPI(
    title=settings.app_name,
    description="Control Plane for the Atlas AI Command Center.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- MIDDLEWARE ---
# Audit Logging first
app.add_middleware(AuditLoggingMiddleware)

# CORS - Specifically configured for your Frontend on 3001
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3000", # Keeping 3000 as a backup
    ],
    allow_credentials=True,  # Set to True to allow session headers/cookies
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# --- ROUTERS ---
# The prefix "/api" is critical. Your frontend must call /api/academic/...
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(agents.router, prefix="/api", tags=["agents"])
app.include_router(telemetry.router, prefix="/api", tags=["telemetry"])
app.include_router(admin.router, prefix="/api", tags=["admin"])
app.include_router(ai.router, prefix="/api", tags=["ai"])

# Feature specific routers
try:
    app.include_router(student.router, prefix="/api", tags=["student"])
except Exception:
    pass

app.include_router(academic.router, prefix="/api", tags=["academic"])

@app.get("/health")
async def health():
    return {"status": "ok", "port": 5000}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
    )
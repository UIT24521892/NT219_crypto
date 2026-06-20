"""
Citizen Services Portal — FastAPI backend entry point.
NT219 Cryptography — Topic 11.
"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.verify import router as verify_router
from app.api.audit import router as audit_router
from app.api.public_keys import router as public_keys_router
from app.api.agencies import router as agencies_router
from app.config import settings
from app.database import Base, engine, get_session


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Create tables for a fresh demo DB. Existing schemas still need migrations."""

    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET environment variable must be set and non-empty")

    from app import models  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="Citizen Services Portal",
    description="Public administrative services with ML-DSA-44 post-quantum signatures",
    version="0.1.0",
    lifespan=lifespan,
)

# Trust X-Forwarded-For from nginx so audit logs capture real client IPs.
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="127.0.0.1")

# CORS — frontend dev server + deployed EC2 origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://54.169.147.134.nip.io",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(verify_router)
app.include_router(audit_router)
app.include_router(public_keys_router)
app.include_router(agencies_router)


@app.get("/ping", tags=["health"])
async def ping():
    """Liveness check — returns 200 OK if the service is up."""
    return {"status": "ok", "service": "citizen-portal", "version": "0.1.0"}


@app.get("/ping/db", tags=["health"])
async def ping_db(session: AsyncSession = Depends(get_session)):
    """Readiness check — confirms DB is reachable and queryable."""
    try:
        result = await session.execute(
            text("SELECT current_database(), current_user, now()")
        )
        row = result.first()
        return {
            "status": "ok",
            "database": row[0],
            "user": row[1],
            "server_time": row[2].isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"DB unreachable: {type(e).__name__}: {e}",
        )

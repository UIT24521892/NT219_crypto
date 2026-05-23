"""
Citizen Services Portal — FastAPI backend entry point.
NT219 Cryptography — Topic 11.
"""
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.verify import router as verify_router
from app.api.audit import router as audit_router
from app.database import get_session

app = FastAPI(
    title="Citizen Services Portal",
    description="Public administrative services with FALCON-512 post-quantum signatures",
    version="0.1.0",
)

# CORS — cho phép frontend (Vite dev server) gọi API.
# Thêm origin LAN/EC2 vào danh sách khi deploy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(verify_router)
app.include_router(audit_router)


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

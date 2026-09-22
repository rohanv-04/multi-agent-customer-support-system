import os
import time
import uuid
import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import text
from .core.logging import logger, request_id_ctx, org_id_ctx
from .database.database import SessionLocal, init_db, get_db
from .rag.vector_store import policy_store

# API Routers
from .api.chat import router as chat_router
from .api.tasks import router as tasks_router
from .api.agents import router as agents_router
from .api.tools import router as tools_router
from .api.memory import router as memory_router
from .api.knowledge import router as knowledge_router
from .api.escalations import router as escalations_router
from .api.analytics import router as analytics_router
from .api.customers import router as customers_router
from .api.cases import router as cases_router
from .api.omnichannel import router as omnichannel_router
from .api.proactive import router as proactive_router
from .api.sla import router as sla_router
from .api.observability import router as observability_router
from .api.evaluations import router as evaluations_router
from .api.audit import router as audit_router
from .api.auth import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database & seed demo data
    logger.info("[Startup] Initializing NovaCart SQLite database...")
    init_db()
    # Index knowledge base documents
    logger.info("[Startup] Indexing NovaCart corporate policies in vector store...")
    policy_store.index_documents()
    logger.info(f"[Startup] Ready! {len(policy_store.chunks)} policy chunks indexed.")
    yield
    logger.info("[Shutdown] Cleaning up application resources...")

app = FastAPI(
    title="SupportOS AI - Autonomous Customer Support Operations Platform",
    description="Autonomous Multi-Agent Customer Support System with SupportCase Engine, LangGraph, RAG, and Real Database Tools",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000")
if allowed_origins_env.strip() == "*":
    allow_origins = ["*"]
else:
    allow_origins = [orig.strip() for orig in allowed_origins_env.split(",") if orig.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID & Distributed Tracing Middleware
@app.middleware("http")
async def request_tracing_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:12]}"
    token = request_id_ctx.set(req_id)
    
    start_time = time.perf_counter()
    try:
        response: Response = await call_next(request)
        process_time = (time.perf_counter() - start_time) * 1000
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Response-Time-Ms"] = f"{process_time:.2f}"
        
        # Log HTTP access only for non-health endpoints to avoid log flooding
        if not request.url.path.startswith("/health") and not request.url.path.startswith("/api/health"):
            logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({process_time:.2f}ms)")
        return response
    except Exception as exc:
        process_time = (time.perf_counter() - start_time) * 1000
        logger.error(f"Unhandled exception during {request.method} {request.url.path}: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected server error occurred. Please contact support.",
                    "request_id": req_id,
                    "timestamp": datetime.datetime.now(datetime.UTC).isoformat()
                }
            },
            headers={"X-Request-ID": req_id}
        )
    finally:
        request_id_ctx.reset(token)

# Global Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    req_id = request_id_ctx.get()
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error": {
                "code": exc.status_code,
                "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
                "request_id": req_id,
                "timestamp": datetime.datetime.now(datetime.UTC).isoformat()
            }
        },
        headers={"X-Request-ID": req_id}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = request_id_ctx.get()
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters or payload format",
                "details": exc.errors(),
                "request_id": req_id,
                "timestamp": datetime.datetime.now(datetime.UTC).isoformat()
            }
        },
        headers={"X-Request-ID": req_id}
    )

# Include API routers
app.include_router(cases_router)
app.include_router(chat_router)
app.include_router(tasks_router)
app.include_router(agents_router)
app.include_router(tools_router)
app.include_router(memory_router)
app.include_router(knowledge_router)
app.include_router(escalations_router)
app.include_router(analytics_router)
app.include_router(customers_router)
app.include_router(omnichannel_router)
app.include_router(proactive_router)
app.include_router(sla_router)
app.include_router(observability_router)
app.include_router(evaluations_router)
app.include_router(audit_router)
app.include_router(auth_router)

# Health & Readiness Endpoints
@app.get("/health", tags=["System Health"])
@app.get("/api/health", tags=["System Health"])
def health_check():
    """Liveness probe: verifies the service is alive."""
    return {
        "status": "healthy",
        "system": "SupportOS AI",
        "version": "1.0.0",
        "request_id": request_id_ctx.get(),
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat()
    }

@app.get("/health/ready", tags=["System Health"])
@app.get("/api/health/ready", tags=["System Health"])
def readiness_check():
    """Readiness probe: validates SQLite connectivity and vector store indexing status."""
    db_ok = False
    try:
        db = SessionLocal()
        try:
            res = db.execute(text("SELECT 1")).scalar()
            db_ok = (res == 1)
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Readiness check failed on database: {e}")
        db_ok = False

    vector_ok = len(policy_store.chunks) > 0
    
    if db_ok and vector_ok:
        return {
            "status": "ready",
            "database": "connected",
            "knowledge_chunks": len(policy_store.chunks),
            "agents_active": 9,
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat()
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "database": "connected" if db_ok else "failed",
                "knowledge_base": "indexed" if vector_ok else "empty"
            }
        )

@app.get("/health/live", tags=["System Health"])
@app.get("/api/health/live", tags=["System Health"])
def liveness_check():
    """Kubernetes / container liveness probe."""
    return {"status": "live", "timestamp": datetime.datetime.now(datetime.UTC).isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)

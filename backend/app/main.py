import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from .database.database import init_db
from .rag.vector_store import policy_store
from .api.chat import router as chat_router
from .api.tasks import router as tasks_router
from .api.agents import router as agents_router
from .api.tools import router as tools_router
from .api.memory import router as memory_router
from .api.knowledge import router as knowledge_router
from .api.escalations import router as escalations_router
from .api.analytics import router as analytics_router
from .api.customers import router as customers_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database & seed demo data
    print("[Startup] Initializing NovaCart SQLite database...")
    init_db()
    # Index knowledge base documents
    print("[Startup] Indexing NovaCart corporate policies in vector store...")
    policy_store.index_documents()
    print(f"[Startup] Ready! {len(policy_store.chunks)} policy chunks indexed.")
    yield
    print("[Shutdown] Cleaning up...")

app = FastAPI(
    title="AgentSupport AI - Backend Engine",
    description="Autonomous Multi-Agent Customer Support System with LangGraph, RAG, and Real Database Tools",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(chat_router)
app.include_router(tasks_router)
app.include_router(agents_router)
app.include_router(tools_router)
app.include_router(memory_router)
app.include_router(knowledge_router)
app.include_router(escalations_router)
app.include_router(analytics_router)
app.include_router(customers_router)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "system": "AgentSupport AI",
        "agents_active": 7,
        "policy_chunks": len(policy_store.chunks),
        "database": "SQLite (novacart.db)"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)

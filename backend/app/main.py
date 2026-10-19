from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import get_settings
from app.routers import disputes, health, merchants, risk, transactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.connect()
    await db.ensure_indexes()
    yield
    db.close()


app = FastAPI(
    title="DhanRakshak API",
    description="Agentic fraud detection + smart dispute assistant on PayPal sandbox",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(transactions.router)
app.include_router(risk.router)
app.include_router(disputes.router)
app.include_router(merchants.router)


@app.get("/")
async def root():
    return {"name": "DhanRakshak", "docs": "/docs", "health": "/api/health"}
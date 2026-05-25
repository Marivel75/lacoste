"""Application FastAPI — Veille Rénovation Énergétique.

Point d'entrée de l'API REST. Initialise la base de données au démarrage (lifespan),
configure le CORS pour le frontend Streamlit (port 8501) et enregistre les routers.
Démarrage : uvicorn api.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import articles, newsletter, pipeline, weeks
from src.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Veille Rénovation Énergétique",
    description="API de veille hebdomadaire — OPTIMMO Énergies",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(articles.router)
app.include_router(weeks.router)
app.include_router(pipeline.router)
app.include_router(newsletter.router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "version": "0.1.0"}

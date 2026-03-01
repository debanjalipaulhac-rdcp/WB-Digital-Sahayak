"""
WB Digital Sahayak — FastAPI Entry Point
=========================================
Root entry point for local dev and AWS Lambda (via Mangum adapter).

Run locally:
    uvicorn main:app --reload --port 8000

Deploy to Lambda:
    Mangum wraps the FastAPI app as a Lambda handler.
    Lambda handler in infra/template.yaml points to: main.handler
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from src.config.settings import settings
from src.channels.api import router as api_router

settings.validate() 

# ── App init ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="WB Digital Sahayak",
    description="Voice-First Welfare Eligibility Engine for West Bengal",
    version="1.0.0",
    docs_url="/docs",       # Swagger UI  → http://localhost:8000/docs
    redoc_url="/redoc",     # ReDoc UI    → http://localhost:8000/redoc
    
)

# ── CORS (allow React frontend + WhatsApp webhook) ───────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount routers ────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1", tags=["Core API"])
# app.include_router(whatsapp_router, prefix="/webhook", tags=["WhatsApp"])  # Level 4

# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {
        "service": "WB Digital Sahayak",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
    }

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}

# ── AWS Lambda handler (Mangum) ──────────────────────────────────────────────
# This is what Lambda calls. Do NOT rename 'handler'.
handler = Mangum(app, lifespan="off")
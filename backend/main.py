"""
main.py
=======
FastAPI application entry point + AWS Lambda handler (via Mangum).

Registers all routers. Configures logging.
Single file — Lambda needs one handler reference.

Usage:
  Local dev:  uvicorn main:app --reload --port 8000
  Lambda:     handler = main.handler  (set in Lambda config)
"""

import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from src.channels.whatsapp import router as whatsapp_router
from src.channels.auth_controller    import router as auth_router
from src.channels.schemes_controller import router as schemes_router
from src.channels.profile_controller import router as profile_router


# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────
app = FastAPI(
    title="WB Digital Sahayak",
    description="Voice-first West Bengal government scheme eligibility engine",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],

)

# ─────────────────────────────────────────────
# ROUTERS
# ─────────────────────────────────────────────
app.include_router(whatsapp_router, tags=["WhatsApp"])
# app.include_router(api_router,      tags=["API"], prefix="/api/v1")
app.include_router(auth_router,    prefix="/api/v1")
app.include_router(schemes_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "ok", "service": "WB Digital Sahayak"}


# ─────────────────────────────────────────────
# LAMBDA HANDLER
# ─────────────────────────────────────────────
handler = Mangum(app, lifespan="off")
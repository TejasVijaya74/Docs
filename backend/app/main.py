import logging
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes.analyze import router as analyze_router
from app.services.summarizer import SummarizerService
from app.services.ner import NERService
from app.services.sentiment import SentimentService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

API_KEY = os.getenv("X_API_KEY", "hackathon-key-2024")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Warming up AI models...")
    SummarizerService.get_instance()
    NERService.get_instance()
    SentimentService.get_instance()
    logger.info("All models loaded and ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Document Analysis API",
    description="Extract structured insights from PDF, DOCX, and image documents.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
        return await call_next(request)
    key = request.headers.get("x-api-key")
    if not key or key != API_KEY:
        return JSONResponse(status_code=401, content={"detail": "Invalid or missing x-api-key"})
    return await call_next(request)


app.include_router(analyze_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
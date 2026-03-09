import logging
from fastapi import FastAPI
from api.session import router as session_router
from api.generate import router as generate_router
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)

app = FastAPI(
    title="RAG Content Generator",
    version="1.0.0",
    description="NCERT/CBSE content generation API for teachers — powered by RAG + Gemini",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


@app.get("/")
def read_root():
    return {
        "app": "RAG Content Generator",
        "description": "Generate question papers, notes, summaries, mindmaps, and more from NCERT chapters.",
        "endpoints": ["/session/start", "/generate/{type}", "/docs"],
    }


@app.get("/api/status")
def status():
    return {"status": "ok"}


app.include_router(session_router, prefix="/session")
app.include_router(generate_router, prefix="/generate")
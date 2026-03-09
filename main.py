import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from api.session import router as session_router
from api.generate import router as generate_router
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from utils.errors import APIError
from services.reranker import preload_reranker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG Content Generator",
    version="1.0.0",
    description="NCERT/CBSE content generation API for teachers — powered by RAG + Gemini",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

@app.on_event("startup")
def startup_event():
    logger.info("Initializing models on startup...")
    preload_reranker()
    logger.info("Initialization complete.")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------------------------

@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """Handle structured API errors — return consistent JSON format."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """
    Handle FastAPI validation errors (missing params, wrong types, etc.).
    Returns a structured response instead of the default 422 format.
    """
    errors = exc.errors()
    # Build a human-readable summary of what's wrong
    missing = []
    invalid = []
    for err in errors:
        field = " → ".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "")
        if err.get("type") == "missing":
            missing.append(field)
        else:
            invalid.append(f"{field}: {msg}")

    parts = []
    if missing:
        parts.append(f"Missing required fields: {', '.join(missing)}")
    if invalid:
        parts.append(f"Invalid fields: {'; '.join(invalid)}")

    message = ". ".join(parts) if parts else "Invalid request parameters."

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "INVALID_PARAM",
                "status": 422,
                "message": message,
                "retry": False,
                "details": errors,
            }
        },
    )


@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    """
    Catch-all for any unhandled server errors.
    Logs the full traceback and returns a safe message to the frontend.
    """
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    logger.error(traceback.format_exc())

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "status": 500,
                "message": "An unexpected server error occurred. Please try again or contact support.",
                "retry": True,
            }
        },
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

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
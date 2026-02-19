from fastapi import FastAPI
from api.session import router as session_router
from api.generate import router as generate_router
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

app = FastAPI(title="Paper Generator", version="1.0.0", description="NCERT Paper Generator", docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)

@app.get("/")
def read_root():
    return {
        "AI": "This API fetches jobs from multiple job boards using JobSpy.",
        "endpoints": ["/api/jobs", "/status"],
    }

@app.get("/api/status")
def status():
    return {"status": "ok", "cached_records": 0}


app.include_router(session_router, prefix="/session")
app.include_router(generate_router, prefix="/generate")
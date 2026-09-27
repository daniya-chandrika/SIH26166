"""
FastAPI Server Application for SIH26166 Lunar Image Registration Platform.
Run with: py -3.11 -m uvicorn api.server:app --port 8080 --host 0.0.0.0
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from api.routes import router as api_v1_router

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = WORKSPACE_ROOT / "frontend"

app = FastAPI(
    title="SIH26166 Scientific Lunar Image Registration API",
    description="Multi-Sensor Lunar Image Alignment & Scientific Validation API for Chandrayaan-2 (OHRC, TMC-2, IIRS) and LROC NAC.",
    version="2.0.0"
)

# Enable CORS for scientific web clients & dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_v1_router)

# Mount frontend static files if available
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def root():
    return {
        "title": "SIH26166 Scientific Lunar Image Registration Platform",
        "api_docs": "/docs",
        "health_check": "/api/v1/health",
        "version": "2.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.server:app", host="0.0.0.0", port=8080, reload=False)

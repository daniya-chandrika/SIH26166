"""
FastAPI Server Application for SIH26166 Lunar Image Registration Platform.
Provides full web UI dashboard serving, static assets, and unified REST API endpoints.
Run locally with: py -3.11 -m uvicorn api.server:app --port 8080 --host 0.0.0.0
"""
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from api.routes import router as api_router

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = WORKSPACE_ROOT / "frontend"

app = FastAPI(
    title="SIH26166 Scientific Lunar Image Registration API",
    description="Multi-Sensor Lunar Image Alignment & Scientific Validation API for Chandrayaan-2 (OHRC, TMC-2, IIRS) and LROC NAC.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Enable CORS for all scientific clients and browser dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router at both /api and /api/v1 prefixes for universal client compatibility
app.include_router(api_router, prefix="/api")
app.include_router(api_router, prefix="/api/v1")


# Serve Frontend Web Dashboard & Assets
@app.get("/", include_in_schema=False)
async def serve_index(request: Request):
    index_file = FRONTEND_DIR / "index.html"
    accept = request.headers.get("accept", "")
    # If standard browser navigation (Accept: text/html), serve the HTML dashboard
    if "text/html" in accept and index_file.exists():
        return FileResponse(index_file, media_type="text/html")
    # For API test clients, CLI curl, or JSON callers, return API metadata
    return JSONResponse({
        "title": "SIH26166 Scientific Lunar Image Registration Platform",
        "api_docs": "/docs",
        "health_check": "/api/v1/health",
        "version": "2.0.0"
    })


@app.get("/index.html", include_in_schema=False)
async def serve_index_html():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file, media_type="text/html")
    raise HTTPException(status_code=404, detail="index.html not found")


@app.get("/style.css", include_in_schema=False)
async def serve_style_css():
    css_file = FRONTEND_DIR / "style.css"
    if css_file.exists():
        return FileResponse(css_file, media_type="text/css")
    raise HTTPException(status_code=404, detail="style.css not found")


@app.get("/app.js", include_in_schema=False)
async def serve_app_js():
    js_file = FRONTEND_DIR / "app.js"
    if js_file.exists():
        return FileResponse(js_file, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="app.js not found")


@app.get("/favicon.ico", include_in_schema=False)
async def serve_favicon():
    return JSONResponse({}, status_code=204)


# Mount static directory for any additional assets
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.server:app", host="0.0.0.0", port=8080, reload=False)

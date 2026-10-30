from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path
from contextlib import asynccontextmanager

from app.database import init_db
from app.config import BASE_DIR, SNAPSHOTS_DIR
from app.routers import exam, proctor, admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database tables and seed questions
    init_db()
    yield
    # Shutdown logic if any

app = FastAPI(
    title="AI Online Exam Proctoring System",
    description="Automated AI proctoring with multi-factor anomaly detection and live proctor dashboard.",
    version="1.0.0",
    lifespan=lifespan
)

# Static and Snapshots Mounts
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
app.mount("/snapshots", StaticFiles(directory=str(SNAPSHOTS_DIR)), name="snapshots")

# Templates
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

# Include API Routers
app.include_router(exam.router)
app.include_router(proctor.router)
app.include_router(admin.router)

# Frontend Page Routes
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/system-check", response_class=HTMLResponse)
async def system_check_page(request: Request):
    return templates.TemplateResponse(request=request, name="system_check.html")

@app.get("/exam/{session_id}", response_class=HTMLResponse)
async def exam_room(request: Request, session_id: str):
    return templates.TemplateResponse(request=request, name="exam.html", context={"session_id": session_id})

@app.get("/result/{session_id}", response_class=HTMLResponse)
async def result_page(request: Request, session_id: str):
    return templates.TemplateResponse(request=request, name="result.html", context={"session_id": session_id})

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html")

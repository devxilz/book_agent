from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from pathlib import Path
from backend.routers import upload, login, singin, query_api, library
from . import models
from .database import engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Book Teacher")


# API routers that contain your backend features.
app.include_router(upload.router)
app.include_router(login.router)
app.include_router(singin.router)
app.include_router(query_api.router)
app.include_router(library.router)

# The frontend is served by FastAPI so cookies stay same-origin and httpOnly.
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"


def frontend_page(filename: str):
    return FileResponse(frontend_dir / filename)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add browser security headers for every frontend/API response."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()"
    )
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )
    if request.url.scheme == "https":
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains"
        )
    return response


@app.get("/", include_in_schema=False)
def entry_page():
    return frontend_page("index.html")


@app.get("/login", include_in_schema=False)
def login_page():
    return frontend_page("login.html")


@app.get("/signup", include_in_schema=False)
def signup_page():
    return frontend_page("signup.html")


@app.get("/upload", include_in_schema=False)
def upload_page():
    return frontend_page("upload.html")


@app.get("/reader", include_in_schema=False)
def reader_page():
    return frontend_page("reader.html")


@app.get("/style.css", include_in_schema=False)
def stylesheet():
    return FileResponse(frontend_dir / "style.css", media_type="text/css")


@app.get("/app.js", include_in_schema=False)
def javascript():
    return FileResponse(frontend_dir / "app.js", media_type="text/javascript")


@app.get("/{legacy_page}.html", include_in_schema=False)
def redirect_legacy_html_routes(legacy_page: str):
    """Keep old .html URLs from exposing files directly; use clean routes."""
    allowed_pages = {
        "index": "/",
        "login": "/login",
        "signup": "/signup",
        "upload": "/upload",
        "reader": "/reader",
    }
    destination = allowed_pages.get(legacy_page)
    if destination:
        return RedirectResponse(destination, status_code=308)
    return RedirectResponse("/", status_code=308)

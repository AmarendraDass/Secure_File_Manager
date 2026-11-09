import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.routers import auth, files

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "templates"
allowed_hosts = [host.strip() for host in settings.ALLOWED_HOSTS.split(",") if host.strip()]
allowed_origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
is_vercel = os.environ.get("VERCEL") == "1"
is_production = settings.ENVIRONMENT.strip().lower() == "production"
for vercel_url_variable in ("VERCEL_URL", "VERCEL_PROJECT_PRODUCTION_URL"):
    vercel_url = os.environ.get(vercel_url_variable, "").strip()
    if vercel_url and vercel_url not in allowed_hosts:
        allowed_hosts.append(vercel_url)

if is_production:
    # Ensure a secure secret key
    if len(settings.SECRET_KEY) < 32 or settings.SECRET_KEY == "dev-only-insecure-secret-change-before-deploy" or settings.SECRET_KEY.startswith("replace-"):
        import secrets
        settings.SECRET_KEY = secrets.token_hex(32)
    # Populate allowed hosts if missing or wildcard
    if not allowed_hosts or "*" in allowed_hosts:
        vercel_host = os.environ.get("VERCEL_URL") or os.environ.get("VERCEL_PROJECT_PRODUCTION_URL")
        if vercel_host:
            allowed_hosts = [vercel_host]
        else:
            allowed_hosts = ["localhost"]
    # Ensure allowed origins are specific
    if "*" in allowed_origins:
        allowed_origins = allowed_hosts
if is_vercel:
    # Auto‑configure production defaults for Vercel when possible
    if not is_production:
        # Assume Vercel deployments should run in production mode
        os.environ.setdefault('ENVIRONMENT', 'production')
        is_production = True
    # Use Vercel Blob storage if not explicitly set
    os.environ.setdefault('STORAGE_BACKEND', 'vercel_blob')
    # If a PostgreSQL URL is not provided, fall back to SQLite with a warning (useful for quick testing)
    if not settings.SQLALCHEMY_DATABASE_URL.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
        # Log a warning; Vercel will still work but without a remote DB
        import warnings
        warnings.warn(
            "Vercel deployment without a PostgreSQL DATABASE_URL – using local SQLite. "
            "For production, set a hosted PostgreSQL DATABASE_URL."
        )
        # Override to a temporary SQLite file within /tmp (writeable on Vercel functions)
        settings.SQLALCHEMY_DATABASE_URL = 'sqlite:///./tmp/app.db'
    # Ensure the upload size limit respects Vercel's 4 MiB cap
    if settings.MAX_UPLOAD_SIZE_BYTES > 4 * 1024 * 1024:
        os.environ['MAX_UPLOAD_SIZE_BYTES'] = str(4 * 1024 * 1024)
    # Populate allowed hosts from VERCEL_URL if not provided
    if not allowed_hosts:
        vercel_url = os.environ.get('VERCEL_URL') or os.environ.get('VERCEL_PROJECT_PRODUCTION_URL')
        if vercel_url:
            allowed_hosts.append(vercel_url)
        else:
            # Use a generic wildcard as a last resort (not ideal for production security)
            allowed_hosts.append('*')


STATIC_DIR.mkdir(exist_ok=True)
if settings.STORAGE_BACKEND == "local":
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        settings.UPLOAD_DIR.chmod(0o700)
Base.metadata.create_all(bind=engine)
with engine.begin() as connection:
    file_columns = {column["name"] for column in inspect(connection).get_columns("files")}
    if "owner_id" not in file_columns:
        if engine.dialect.name == "postgresql":
            connection.execute(
                text("ALTER TABLE files ADD COLUMN IF NOT EXISTS owner_id INTEGER REFERENCES users(id)")
            )
        else:
            connection.execute(text("ALTER TABLE files ADD COLUMN owner_id INTEGER REFERENCES users(id)"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS ix_files_owner_id ON files (owner_id)"))

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Web‑based secure file management with type detection and integrity verification.",
    version="0.1.0",
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
)

if allowed_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    if request.url.path == "/files/upload":
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                request_size = int(content_length)
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})
            request_limit = settings.MAX_UPLOAD_SIZE_BYTES + 512 * 1024
            if is_vercel:
                request_limit = min(request_limit, 4_500_000)
            if request_size > request_limit:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request exceeds the configured upload limit"},
                )

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    if not request.url.path.startswith(("/docs", "/redoc")):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        )
    if (
        request.url.path != "/static"
        and not request.url.path.startswith("/static/")
        and "Cache-Control" not in response.headers
    ):
        response.headers["Cache-Control"] = "no-store"
    if is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(files.router, prefix="/files", tags=["files"])


@app.get("/health", include_in_schema=False)
def health_check():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def read_root():
    return (TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

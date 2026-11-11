import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse

from .config import settings
from .database import Base, SessionLocal, engine
from .errors import install_error_handlers
from .routers import ai, auth, catalogue, desk, orders, salesman

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    if settings.seed_demo_data:
        from .seed import seed
        with SessionLocal() as db:
            seed(db)
    yield


app = FastAPI(title="Retailer Ordering API", version="1.0.0", lifespan=lifespan,
              docs_url="/api/docs" if settings.env != "production" else None, redoc_url=None,
              openapi_url="/api/openapi.json" if settings.env != "production" else None)
install_error_handlers(app)
app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
                   allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    if request.url.path.startswith("/api"):
        resp.headers.setdefault("Cache-Control", "no-store")
    elif request.url.path.startswith("/assets/"):          # content-hashed filenames: safe to cache for a year
        resp.headers.setdefault("Cache-Control", "public, max-age=31536000, immutable")
    return resp


for r in (auth.router, catalogue.router, orders.router, ai.router, desk.router, salesman.router):
    app.include_router(r, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Optionally serve the built frontend from the same origin (single-service deployment).
# Pre-compressed Brotli files (written by `npm run build`) are served when the browser accepts them: smaller on slow networks.
import mimetypes  # noqa: E402

_dist = Path(os.getenv("FRONTEND_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist"))


def _file(request: Request, target: Path, headers: dict | None = None) -> FileResponse:
    headers = dict(headers or {})
    media = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    br = target.with_name(target.name + ".br")
    if "br" in request.headers.get("accept-encoding", "") and br.is_file():
        headers.update({"Content-Encoding": "br", "Vary": "Accept-Encoding"})
        return FileResponse(br, media_type=media, headers=headers)
    return FileResponse(target, media_type=media, headers=headers)


if _dist.is_dir():
    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str, request: Request):
        if path.startswith("api/"):
            from .errors import ApiError
            raise ApiError(404, "NOT_FOUND", "Not found.")
        target = (_dist / path).resolve()
        if path and target.is_file() and _dist.resolve() in target.parents:
            return _file(request, target, {"Cache-Control": "no-cache"} if path in {"sw.js", "index.html", "manifest.webmanifest"} else None)
        return _file(request, _dist / "index.html", {"Cache-Control": "no-cache"})

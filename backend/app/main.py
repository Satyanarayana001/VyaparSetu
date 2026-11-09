import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
_dist = Path(os.getenv("FRONTEND_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist"))
if _dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            from .errors import ApiError
            raise ApiError(404, "NOT_FOUND", "Not found.")
        target = (_dist / path).resolve()
        if path and target.is_file() and _dist.resolve() in target.parents:
            headers = {"Cache-Control": "no-cache"} if path in {"sw.js", "index.html"} else {}
            return FileResponse(target, headers=headers)
        return FileResponse(_dist / "index.html", headers={"Cache-Control": "no-cache"})

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .config import settings
from .db import init_db
from .routers import statements, transactions, analytics, rules, admin, settings as settings_router


def create_app() -> FastAPI:
    app = FastAPI(title="SaveIt", version="0.2.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"], allow_headers=["*"], allow_credentials=True,
    )
    init_db()

    # API routers — all mounted under /api so the SPA can own everything else.
    api_routers = [statements.router, transactions.router, analytics.router,
                   rules.router, admin.router, settings_router.router]
    for r in api_routers:
        app.include_router(r, prefix="/api")

    @app.get("/api/health")
    @app.get("/health")
    def health():
        return {"ok": True, "env": settings.env}

    # Serve the built React app in prod. In dev, Vite serves it on :5173 and
    # proxies /api → :8000, so we leave this off to avoid masking 404s.
    if settings.serve_frontend:
        dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
        if dist.is_dir():
            app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

            @app.get("/{full_path:path}", include_in_schema=False)
            def spa_fallback(full_path: str):
                # Static files first
                candidate = dist / full_path
                if full_path and candidate.is_file():
                    return FileResponse(candidate)
                return FileResponse(dist / "index.html")

    return app


app = create_app()

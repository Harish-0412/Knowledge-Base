from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.assistant_guarded import router as assistant_guarded_router
from app.api.chunks import router as chunks_router
from app.api.debug import router as debug_router
from app.api.documents import router as documents_router
from app.api.export import router as export_router
from app.api.frontend_compat import router as frontend_compat_router
from app.api.health import router as health_router
from app.api.rule_candidates import router as rule_candidates_router
from app.api.rulebook_ask import router as rulebook_ask_router
from app.api.security_intelligence import router as security_intelligence_router
from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database tables exist on every startup."""
    try:
        from app.db.session import engine
        from app.db.models import Base
        if engine is not None:
            Base.metadata.create_all(bind=engine)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("DB table init failed: %s", exc)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.app_debug)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.app_debug,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "Health", "description": "Service, database, and LLM health checks."},
            {"name": "Documents", "description": "Upload, profile, extract, and run document intelligence."},
            {"name": "Chunks", "description": "Read extracted document chunks."},
            {"name": "Rule Candidates", "description": "Read, normalize, and export rule candidates."},
            {"name": "Security Intelligence", "description": "External CVE risk enrichment from trusted APIs."},
            {"name": "Debug", "description": "Demo and diagnostics endpoints."},
            {"name": "Export", "description": "Integration export endpoints for teammate services."},
            {"name": "Assistant", "description": "Guarded assistant pipeline with scope, intent, evidence, and output validation."},
            {"name": "Rulebook", "description": "Compatibility rulebook AI ask endpoint."},
        ],
    )

    # CORS must be added BEFORE the catch-all handler so it fires first on the response
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Catch-all for unhandled exceptions: return JSON so CORS middleware can
    # inject the Access-Control-Allow-Origin header on error responses.
    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        import logging
        logging.getLogger(__name__).error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred.", "type": type(exc).__name__},
        )

    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(health_router, prefix="/api")
    app.include_router(documents_router, prefix="/api")
    app.include_router(chunks_router, prefix="/api")
    app.include_router(debug_router, prefix="/api")
    app.include_router(export_router, prefix="/api")
    app.include_router(rule_candidates_router, prefix="/api")
    app.include_router(security_intelligence_router, prefix="/api")
    app.include_router(frontend_compat_router, prefix="/api")
    app.include_router(assistant_guarded_router, prefix="/api")
    app.include_router(rulebook_ask_router, prefix="/api")

    return app


app = create_app()

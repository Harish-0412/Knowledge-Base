from fastapi import APIRouter

from app.core.config import get_settings
from app.core.database import check_database_connection
from app.db.session import SessionLocal
from app.services.llm_service import LLMServiceFactory

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def health_check() -> dict:
    return {
        "status": "ok",
        "service": get_settings().app_name,
        "version": "0.1.0",
    }


@router.get("/db")
def database_health_check() -> dict:
    return check_database_connection(SessionLocal)


@router.get("/llm")
def llm_health_check(deep: bool = False) -> dict:
    settings = get_settings()
    response = {
        "provider": settings.llm_provider,
        "use_mock_llm": settings.use_mock_llm,
        "allow_mock_llm_rule_extraction": settings.allow_mock_llm_rule_extraction,
        "model": settings.ollama_model,
        "api_key_present": bool(settings.ollama_api_key),
        "status": "ok" if settings.use_mock_llm else "configured",
    }
    if not settings.use_mock_llm:
        response["base_url_configured"] = bool(settings.ollama_base_url)
        response["generate_path"] = settings.ollama_generate_path

    if deep:
        service = LLMServiceFactory.create(settings)
        service.generate_json("Return JSON: {\"ok\": true}")
        response["status"] = "ok"

    return response

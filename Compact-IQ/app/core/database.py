from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker


def check_database_connection(session_factory: sessionmaker | None) -> dict:
    if session_factory is None:
        return {
            "status": "unconfigured",
            "database_url_configured": False,
        }

    try:
        with session_factory() as session:
            session.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database_url_configured": True,
        }
    except SQLAlchemyError as exc:
        return {
            "status": "failed",
            "database_url_configured": True,
            "error": exc.__class__.__name__,
        }

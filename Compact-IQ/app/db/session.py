from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.errors import AppError


class Base(DeclarativeBase):
    pass


def build_engine():
    settings = get_settings()
    if not settings.database_url:
        return None

    connect_args = {}
    engine_kwargs = {"pool_pre_ping": True}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if settings.database_url in {"sqlite://", "sqlite:///:memory:"}:
            engine_kwargs["poolclass"] = StaticPool

    return create_engine(
        settings.database_url,
        connect_args=connect_args,
        **engine_kwargs,
    )


engine = build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise AppError(
            code="database_not_configured",
            message="DATABASE_URL is not configured.",
            status_code=503,
        )

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

import os
import shutil
from pathlib import Path

import pytest


os.environ["DATABASE_URL"] = "sqlite://"
os.environ["UPLOAD_DIR"] = ".pytest_uploads"
os.environ["EXPORT_DIR"] = ".pytest_exports"
os.environ["MAX_UPLOAD_MB"] = "25"
os.environ["USE_MOCK_LLM"] = "true"
os.environ["ALLOW_MOCK_LLM_RULE_EXTRACTION"] = "true"
os.environ["OLLAMA_API_KEY"] = ""


@pytest.fixture(autouse=True)
def reset_test_database_and_uploads():
    from app.core.config import get_settings
    from app.db import models  # noqa: F401
    from app.db.session import Base, engine

    get_settings.cache_clear()
    assert engine is not None
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    upload_dir = Path(os.environ["UPLOAD_DIR"])
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    export_dir = Path(os.environ["EXPORT_DIR"])
    if export_dir.exists():
        shutil.rmtree(export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)

    yield

    Base.metadata.drop_all(bind=engine)
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
    if export_dir.exists():
        shutil.rmtree(export_dir)
    get_settings.cache_clear()

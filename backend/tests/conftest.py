
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base, get_db
from app.main import app
from app.models import sensor  # noqa: F401


GOOD = {
    "temperature": 29.4,
    "humidity": 66,
    "soil": 37,
    "rain": 0,
    "water": 1700,
    "light": 450,
}


@pytest.fixture()
def client():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    test_client = TestClient(app)
    test_client.test_session_factory = Session

    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()
        test_client.close()
        eng.dispose()


@pytest.fixture(autouse=True)
def _tmp_upload_dir(tmp_path, monkeypatch):
    """Uploaded test images never touch the real data/raw folder."""
    from app import config

    monkeypatch.setattr(config, "VISION_UPLOAD_DIR", tmp_path / "uploads")

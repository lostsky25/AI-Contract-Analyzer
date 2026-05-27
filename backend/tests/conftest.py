from collections.abc import Generator
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings
from app.database import get_db
from app.main import app


class DummyDBSession:
    def add(self, _obj: object) -> None:
        return None

    def commit(self) -> None:
        return None

    def refresh(self, _obj: object) -> None:
        return None

    def rollback(self) -> None:
        return None


@pytest.fixture(scope="session", autouse=True)
def disable_startup_events() -> None:
    app.router.on_startup.clear()


@pytest.fixture(autouse=True)
def configure_test_upload_dir(tmp_path: Path) -> Generator[None, None, None]:
    original_upload_dir = settings.upload_dir
    settings.upload_dir = str(tmp_path / "uploads")
    yield
    settings.upload_dir = original_upload_dir


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[DummyDBSession, None, None]:
        yield DummyDBSession()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

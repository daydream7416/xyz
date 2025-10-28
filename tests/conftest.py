# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def test_client() -> Generator[TestClient, None, None]:
    """
    Provides a FastAPI TestClient backed by an isolated SQLite database.
    The fixture reconfigures DATABASE_URL before importing backend modules,
    so tests do not touch local Postgres or production data.
    """
    repo_root = Path(__file__).resolve().parents[1]
    backend_dir = repo_root / "backend"
    sys.path.insert(0, str(backend_dir))

    tmp_db_path = backend_dir / "tmp_test_api.db"
    if tmp_db_path.exists():
        tmp_db_path.unlink()

    os.environ.pop("USE_SQLITE", None)
    os.environ["DATABASE_URL"] = "sqlite:///" + tmp_db_path.as_posix()

    if "database" in sys.modules:
        importlib.reload(sys.modules["database"])
    database = importlib.import_module("database")
    database.Base.metadata.drop_all(bind=database.engine)
    database.Base.metadata.create_all(bind=database.engine)

    # Ensure models/main pick up the refreshed metadata
    if "models" in sys.modules:
        importlib.reload(sys.modules["models"])
    importlib.import_module("models")

    if "main" in sys.modules:
        importlib.reload(sys.modules["main"])
    main = importlib.import_module("main")

    client = TestClient(main.app)
    try:
        yield client
    finally:
        client.close()
        database.engine.dispose()
        if tmp_db_path.exists():
            try:
                tmp_db_path.unlink()
            except OSError:
                pass

    # Remove backend path if it was injected by the fixture
    if str(backend_dir) in sys.path:
        sys.path.remove(str(backend_dir))

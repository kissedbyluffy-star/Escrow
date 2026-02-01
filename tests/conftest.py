import os
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from escrow_bot.services.db import init_db
from escrow_bot.services.settings import seed_defaults


@pytest.fixture(autouse=True)
def _test_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "escrow.db"
    monkeypatch.setenv("ESCROW_DB_PATH", str(db_path))
    init_db()
    seed_defaults()
    yield
    if db_path.exists():
        os.remove(db_path)

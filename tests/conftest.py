import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core import config, database


def _clear_function_caches() -> None:
    for func in (config.get_settings, database.get_engine, database.get_session_factory):
        cache_clear = getattr(func, "cache_clear", None)
        if cache_clear is not None:
            cache_clear()


@pytest.fixture(autouse=True)
def clear_function_caches() -> None:
    _clear_function_caches()
    yield
    _clear_function_caches()

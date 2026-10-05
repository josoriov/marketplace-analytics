import pytest

from app.core import config, database


@pytest.fixture(autouse=True)
def clear_function_caches():
    config.get_settings.cache_clear()
    database.get_engine.cache_clear()
    yield
    config.get_settings.cache_clear()
    database.get_engine.cache_clear()

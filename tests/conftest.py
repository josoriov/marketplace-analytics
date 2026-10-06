import json
import socket
from http.client import HTTPConnection
from threading import Thread

import pytest
import uvicorn

from app.core import config, database
from app.main import app


@pytest.fixture(autouse=True)
def clear_function_caches():
    config.get_settings.cache_clear()
    database.get_engine.cache_clear()
    yield
    config.get_settings.cache_clear()
    database.get_engine.cache_clear()


@pytest.fixture
def http_get():
    """Exercise real HTTP with the installed server and standard-library client."""
    with socket.create_server(("127.0.0.1", 0)) as sock:
        server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
        thread = Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()

        def get(path):
            connection = HTTPConnection(*sock.getsockname(), timeout=10)
            try:
                connection.request("GET", path)
                response = connection.getresponse()
                return response.status, json.loads(response.read())
            finally:
                connection.close()

        try:
            yield get
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            assert not thread.is_alive(), "HTTP server did not stop"

"""全局 fixture：本地演示服务、API 客户端、登录态."""

import socket
import threading
import time
from pathlib import Path
from sys import path as _sys_path

import pytest
import requests

_sys_path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.http_client import ApiClient  # noqa: E402


@pytest.fixture(scope="session")
def base_url():
    """进程内启动演示 API（uvicorn 子线程），返回 base_url."""
    import uvicorn
    from demo_app.app import app

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1",
                                           port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            requests.get(url + "/docs", timeout=1)
            break
        except requests.ConnectionError:
            time.sleep(0.1)
    else:
        pytest.fail("演示服务启动失败")
    yield url
    server.should_exit = True


@pytest.fixture(autouse=True)
def reset_state(base_url):
    """每个用例前重置演示服务状态，保证用例顺序无关."""
    import requests
    requests.post(base_url + "/__test__/reset", timeout=5)
    yield


@pytest.fixture()
def api(base_url) -> ApiClient:
    """未登录客户端（函数级隔离，避免登录态串扰）."""
    return ApiClient(base_url)


@pytest.fixture()
def alice(base_url) -> ApiClient:
    """已登录的富余额账户（alice, 30 元）."""
    c = ApiClient(base_url)
    c.login("alice", "alice123")
    return c


@pytest.fixture()
def bob(base_url) -> ApiClient:
    """已登录的零余额账户（bob, 0 元）."""
    c = ApiClient(base_url)
    c.login("bob", "bob123")
    return c

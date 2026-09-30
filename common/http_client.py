"""统一 HTTP 客户端：会话管理、登录态注入、请求日志、重试."""

import logging
from typing import Optional

import requests

log = logging.getLogger("api")


class ApiClient:
    """每个测试会话一个实例；登录态通过 set_token 注入请求头."""

    def __init__(self, base_url: str, timeout: float = 10.0,
                 max_retries: int = 2):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = requests.Session()
        # 屏蔽系统/环境代理：测试客户端应直连目标服务，避免本机代理
        # 对 keep-alive 连接复用的干扰（曾导致复用连接上的第 2 个请求
        # 被代理错路由返回 404）。内网/本地测试就该直连。
        self._session.trust_env = False
        self._token: Optional[str] = None

    # -- 登录态 --------------------------------------------------------
    def set_token(self, token: Optional[str]) -> None:
        self._token = token

    def clear_token(self) -> None:
        self.set_token(None)

    @property
    def token(self) -> Optional[str]:
        return self._token

    # -- 请求 ----------------------------------------------------------
    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = self.base_url + path
        headers = kwargs.pop("headers", {}) or {}
        if self._token and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {self._token}"
        kwargs.setdefault("timeout", self.timeout)
        kwargs["headers"] = headers

        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self._session.request(method, url, **kwargs)
                log.info("%s %s -> %s (%.0fms)", method, url,
                         resp.status_code, resp.elapsed.total_seconds() * 1000)
                return resp
            except (requests.ConnectionError, requests.Timeout) as e:
                last_exc = e
                log.warning("请求失败(第%d次): %s %s: %s",
                            attempt, method, url, e)
        raise last_exc

    def get(self, path: str, **kw) -> requests.Response:
        return self.request("GET", path, **kw)

    def post(self, path: str, **kw) -> requests.Response:
        return self.request("POST", path, **kw)

    def delete(self, path: str, **kw) -> requests.Response:
        return self.request("DELETE", path, **kw)

    # -- 业务便捷方法 ---------------------------------------------------
    def login(self, username: str, password: str) -> str:
        """登录并把 token 注入当前客户端."""
        resp = self.post("/auth/login", json={"username": username,
                                              "password": password})
        assert resp.status_code == 200, f"登录失败: {resp.status_code}"
        token = resp.json()["token"]
        self.set_token(token)
        return token

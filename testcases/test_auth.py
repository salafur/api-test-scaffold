"""认证接口测试."""

import pytest
from allure import feature, story

from common.assertions import assert_field, assert_json, assert_status

TOKEN_SCHEMA = {
    "type": "object",
    "required": ["token", "token_type"],
    "properties": {
        "token": {"type": "string", "minLength": 16},
        "token_type": {"const": "bearer"},
    },
}


@feature("认证模块")
class TestLogin:
    @story("正确凭据登录成功")
    def test_login_ok(self, api):
        resp = api.post("/auth/login", json={"username": "alice",
                                             "password": "alice123"})
        assert_status(resp, 200)
        body = assert_json(resp)
        assert_field(body, "token_type", "bearer")
        from common.assertions import assert_schema
        assert_schema(resp, TOKEN_SCHEMA)

    @pytest.mark.parametrize("username,password", [
        ("alice", "wrong"),       # 密码错误
        ("ghost", "alice123"),    # 用户不存在
        ("", ""),                 # 空凭据
    ], ids=["错误密码", "用户不存在", "空凭据"])
    @story("错误凭据登录被拒")
    def test_login_rejected(self, api, username, password):
        resp = api.post("/auth/login", json={"username": username,
                                             "password": password})
        assert_status(resp, 401)

    @story("每次登录签发独立 token")
    def test_tokens_differ(self, api):
        t1 = api.login("alice", "alice123")
        t2 = api.login("alice", "alice123")
        assert t1 != t2


@feature("认证模块")
class TestAuthEnforcement:
    @story("无 token 访问受保护接口")
    def test_me_without_token(self, api):
        resp = api.get("/users/me")
        assert_status(resp, 401)

    @story("伪造 token 被拒")
    def test_me_with_fake_token(self, api):
        resp = api.get("/users/me", headers={"Authorization": "Bearer " + "x" * 32})
        assert_status(resp, 401)

    @story("token 下发后可访问 /users/me")
    def test_me_with_token(self, alice):
        resp = alice.get("/users/me")
        assert_status(resp, 200)
        body = assert_json(resp)
        assert_field(body, "username", "alice")

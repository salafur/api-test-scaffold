"""用户接口测试."""

from allure import feature, story

from common.assertions import assert_field, assert_json, assert_schema

ME_SCHEMA = {
    "type": "object",
    "required": ["username", "balance"],
    "properties": {
        "username": {"type": "string"},
        "balance": {"type": "number"},
    },
}


@feature("用户模块")
class TestMe:
    @story("返回当前用户信息")
    def test_me_schema(self, alice):
        assert_schema(alice.get("/users/me"), ME_SCHEMA)

    @story("余额为账户初始值")
    def test_alice_balance(self, alice):
        body = assert_json(alice.get("/users/me"))
        assert_field(body, "balance", 30.0)

    @story("不同账户数据隔离")
    def test_accounts_isolated(self, alice, bob):
        assert_field(assert_json(alice.get("/users/me")), "username", "alice")
        assert_field(assert_json(bob.get("/users/me")), "username", "bob")
        assert_field(assert_json(bob.get("/users/me")), "balance", 0.0)

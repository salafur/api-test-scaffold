"""订单接口测试：数据驱动 + 业务规则 + 资源归属 + 删除退款."""

import pytest
from allure import feature, story

from common.assertions import (assert_field, assert_json, assert_schema,
                               assert_status)
from common.dataloader import load_cases

ORDER_SCHEMA = {
    "type": "object",
    "required": ["id", "owner", "item", "qty", "unit_price", "total", "status"],
    "properties": {
        "id": {"type": "integer"},
        "owner": {"type": "string"},
        "item": {"type": "string"},
        "qty": {"type": "integer", "minimum": 1},
        "total": {"type": "number"},
        "status": {"enum": ["paid", "cancelled"]},
    },
}


@feature("订单模块")
class TestCreateOrder:
    @story("正常下单（数据驱动）")
    @pytest.mark.parametrize("case", load_cases("orders.yaml", "create_cases"),
                             ids=lambda c: c["name"])
    def test_create_ok(self, alice, case):
        resp = alice.post("/orders", json={"item": case["item"],
                                           "qty": case["qty"],
                                           "unit_price": case["unit_price"]})
        assert_status(resp, 201)
        body = assert_json(resp)
        assert_schema(resp, ORDER_SCHEMA)
        assert_field(body, "total", case["expect_total"])
        assert_field(body, "owner", "alice")

    @story("异常参数（数据驱动）")
    @pytest.mark.parametrize("case", load_cases("orders.yaml", "invalid_cases"),
                             ids=lambda c: c["name"])
    def test_create_invalid(self, alice, case):
        resp = alice.post("/orders", json={"item": case["item"],
                                           "qty": case["qty"],
                                           "unit_price": case["unit_price"]})
        assert_status(resp, case["expect_status"])

    @story("余额不足返回 409 且余额不变")
    @pytest.mark.parametrize("case", load_cases("orders.yaml", "insufficient_cases"),
                             ids=lambda c: c["name"])
    def test_insufficient_balance(self, alice, case):
        before = assert_json(alice.get("/users/me"))["balance"]
        resp = alice.post("/orders", json={"item": case["item"],
                                           "qty": case["qty"],
                                           "unit_price": case["unit_price"]})
        assert_status(resp, 409)
        after = assert_json(alice.get("/users/me"))["balance"]
        assert before == after, "余额不足时余额不应变化"


@feature("订单模块")
class TestOrderAccess:
    @story("查询自己的订单")
    def test_get_own_order(self, alice):
        order = assert_json(alice.post("/orders", json={
            "item": "desk", "qty": 1, "unit_price": 5.0}))
        resp = alice.get(f"/orders/{order['id']}")
        assert_status(resp, 200)
        assert_field(resp.json(), "owner", "alice")

    @story("无权访问他人订单 -> 403")
    def test_get_others_order_forbidden(self, alice, bob):
        order = assert_json(alice.post("/orders", json={
            "item": "desk", "qty": 1, "unit_price": 5.0}))
        assert_status(bob.get(f"/orders/{order['id']}"), 403)
        assert_status(bob.delete(f"/orders/{order['id']}"), 403)

    @story("不存在的订单 -> 404")
    def test_order_not_found(self, alice):
        assert_status(alice.get("/orders/999999"), 404)


@feature("订单模块")
class TestCancelOrder:
    @story("取消订单退款并更新余额")
    def test_cancel_refunds(self, alice):
        before = assert_json(alice.get("/users/me"))["balance"]
        order = assert_json(alice.post("/orders", json={
            "item": "lamp", "qty": 1, "unit_price": 7.5}))
        during = assert_json(alice.get("/users/me"))["balance"]
        assert during == round(before - 7.5, 2), "下单后余额应扣减"

        resp = alice.delete(f"/orders/{order['id']}")
        assert_status(resp, 200)
        assert_field(resp.json(), "refunded", 7.5)
        after = assert_json(alice.get("/users/me"))["balance"]
        assert after == before, "取消后余额应恢复"

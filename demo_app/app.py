"""演示电商 API：脚手架的被测对象，自带内存数据库.

故意暴露典型接口测试考点：登录态、权限、参数校验、业务规则
（余额不足）、资源归属（403）与幂等的删除退款。
"""

import secrets
from typing import Dict, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Demo Shop API", version="1.0.0")

USERS: Dict[str, str] = {"admin": "admin123", "alice": "alice123", "bob": "bob123"}
BALANCES: Dict[str, float] = {"admin": 1000.0, "alice": 30.0, "bob": 0.0}
TOKENS: Dict[str, str] = {}          # token -> username
ORDERS: Dict[int, dict] = {}         # order_id -> order
_next_order_id = 1


def _auth(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "缺少或格式错误的 Authorization 头")
    token = authorization[len("Bearer "):]
    user = TOKENS.get(token)
    if user is None:
        raise HTTPException(401, "无效或过期的 token")
    return user


class LoginBody(BaseModel):
    username: str
    password: str


@app.post("/auth/login")
def login(body: LoginBody):
    if USERS.get(body.username) != body.password:
        raise HTTPException(401, "用户名或密码错误")
    token = secrets.token_hex(16)
    TOKENS[token] = body.username
    return {"token": token, "token_type": "bearer"}


@app.get("/users/me")
def me(authorization: Optional[str] = Header(None)):
    user = _auth(authorization)
    return {"username": user, "balance": BALANCES[user]}


class OrderBody(BaseModel):
    item: str
    qty: int
    unit_price: float


@app.post("/orders", status_code=201)
def create_order(body: OrderBody, authorization: Optional[str] = Header(None)):
    user = _auth(authorization)
    if body.qty <= 0:
        raise HTTPException(400, "qty 必须为正整数")
    if not body.item.strip():
        raise HTTPException(400, "item 不能为空")
    total = round(body.qty * body.unit_price, 2)
    if BALANCES[user] < total:
        raise HTTPException(409, f"余额不足: 需要 {total}, 现有 {BALANCES[user]}")
    global _next_order_id
    oid = _next_order_id
    _next_order_id += 1
    BALANCES[user] = round(BALANCES[user] - total, 2)
    ORDERS[oid] = {"id": oid, "owner": user, "item": body.item,
                   "qty": body.qty, "unit_price": body.unit_price,
                   "total": total, "status": "paid"}
    return ORDERS[oid]


@app.get("/orders")
def list_orders(authorization: Optional[str] = Header(None)):
    user = _auth(authorization)
    return [o for o in ORDERS.values() if o["owner"] == user]


@app.get("/orders/{order_id}")
def get_order(order_id: int, authorization: Optional[str] = Header(None)):
    user = _auth(authorization)
    order = ORDERS.get(order_id)
    if order is None:
        raise HTTPException(404, "订单不存在")
    if order["owner"] != user:
        raise HTTPException(403, "无权访问他人订单")
    return order


@app.delete("/orders/{order_id}")
def cancel_order(order_id: int, authorization: Optional[str] = Header(None)):
    user = _auth(authorization)
    order = ORDERS.get(order_id)
    if order is None:
        raise HTTPException(404, "订单不存在")
    if order["owner"] != user:
        raise HTTPException(403, "无权操作他人订单")
    BALANCES[user] = round(BALANCES[user] + order["total"], 2)
    order["status"] = "cancelled"
    return {"id": order_id, "status": "cancelled",
            "refunded": order["total"], "balance": BALANCES[user]}


# ---- 可测试性设计：测试钩子（生产实现中常见做法，隔离测试数据） ----
_INITIAL_BALANCES = {"admin": 1000.0, "alice": 30.0, "bob": 0.0}


@app.post("/__test__/reset", include_in_schema=False)
def test_reset():
    """恢复初始数据。仅演示用途；真实项目用测试库/容器隔离替代."""
    TOKENS.clear()
    ORDERS.clear()
    BALANCES.clear()
    BALANCES.update(_INITIAL_BALANCES)
    global _next_order_id
    _next_order_id = 1
    return {"reset": True}

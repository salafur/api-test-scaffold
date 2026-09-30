"""断言库：状态码 / JSON 字段 / JSON Schema，全部带友好失败信息."""

from typing import Any

from jsonschema import validate
from requests import Response


def assert_status(resp: Response, expected: int) -> None:
    assert resp.status_code == expected, (
        f"期望 {expected}，实际 {resp.status_code}: {resp.text[:200]}")


def assert_json(resp: Response) -> Any:
    assert resp.headers.get("content-type", "").startswith("application/json"), \
        f"响应不是 JSON: {resp.headers.get('content-type')}"
    return resp.json()


def assert_field(obj: Any, path: str, expected: Any) -> None:
    """点路径取值断言: assert_field(order, "owner.username", "alice")."""
    cur = obj
    for key in path.split("."):
        assert isinstance(cur, dict) and key in cur, \
            f"路径 {path!r} 不存在，实际对象: {str(cur)[:200]}"
        cur = cur[key]
    assert cur == expected, f"{path} 期望 {expected!r}, 实际 {cur!r}"


def assert_schema(resp: Response, schema: dict) -> None:
    """校验响应体结构（不校验具体业务值）."""
    body = assert_json(resp)
    try:
        validate(instance=body, schema=schema)
    except Exception as e:  # ValidationError
        raise AssertionError(f"Schema 校验失败: {e}\n响应: {str(body)[:300]}")

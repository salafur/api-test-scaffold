"""测试数据加载：YAML 数据驱动用例."""

from pathlib import Path
from typing import Any, List

import yaml

DATA_DIR = Path(__file__).resolve().parent.parent / "testdata"


def load_cases(filename: str, key: str) -> List[dict]:
    """从 testdata/<filename> 读取用例列表，附上用例名作为 pytest id."""
    with open(DATA_DIR / filename, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    cases = doc[key]
    assert isinstance(cases, list) and cases, f"{filename}[{key}] 为空"
    return cases

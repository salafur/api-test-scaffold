"""配置加载：按 API_ENV 环境变量切换环境."""

import os
from pathlib import Path
from typing import Any, Dict

import yaml

_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def load_config(env: str = None) -> Dict[str, Any]:
    env = env or os.getenv("API_ENV", "local")
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if env not in doc:
        raise KeyError(f"未知环境 {env!r}，可选: {list(k for k in doc if k != 'accounts')}")
    cfg = dict(doc[env])
    cfg["accounts"] = doc.get("accounts", {})
    return cfg

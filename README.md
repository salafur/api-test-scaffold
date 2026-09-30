# api-test-scaffold · pytest 接口自动化测试脚手架

生产级规范的 API 自动化测试工程模板：分层封装、数据驱动、Schema 校验、
Allure 报告、CI 集成，自带一个可离线运行的演示 API——clone 下来即可跑通，
替换 `config/config.yaml` 与用例层即可接入真实项目。

## 工程结构

```
├── demo_app/          # 被测演示 API（FastAPI，内存数据，离线可跑）
├── common/
│   ├── http_client.py # ApiClient：会话/登录态注入/日志/自动重试
│   ├── assertions.py  # assert_status / assert_field / assert_schema
│   └── dataloader.py  # YAML 数据驱动用例加载
├── config/            # 多环境配置（API_ENV 切换）+ 账户管理
├── testcases/         # 用例层：只写业务断言，不碰实现细节
├── testdata/          # 数据驱动 YAML
└── pytest.ini
```

## 分层原则

| 层 | 职责 | 禁止 |
|---|---|---|
| `testcases/` | 业务语义断言（"下单后余额扣减"） | 拼 URL、解析 token |
| `common/` | HTTP 机制、重试、通用断言 | 出现任何业务字段名 |
| `config/` | 环境与账户 | 硬编码进用例 |

接口测试最容易烂掉的方式就是"一个用例一份 requests 代码"——
本脚手架强制分层：换环境改配置，换被测接口改客户端，用例只描述业务。

## 快速开始

```bash
pip install -r requirements.txt
pytest testcases/ -v
```

23 个用例全绿（自带演示服务，无需任何外部依赖；每用例自动重置状态，顺序无关）。

## 特性

- **数据驱动**：`testdata/orders.yaml` + `pytest.mark.parametrize`，用例名即报告名
- **Schema 校验**：jsonschema 校验响应结构，与业务值断言分离（接口契约变了先红结构）
- **认证态管理**：`ApiClient.login()` 一行注入 token，fixture 按角色出客户端
- **异常场景全覆盖**：401/403/404/400/409，含"余额不足时余额不变"这类状态断言
- **Allure**：`@feature/@story` 标注，`pytest --alluredir=allure-results` 生成报告
- **多环境**：`API_ENV=staging pytest ...` 一键切换，账户集中管理

## CI

GitHub Actions：push 自动跑全部用例并上传 Allure 结果工件
（`.github/workflows/tests.yml`）。

## License

MIT

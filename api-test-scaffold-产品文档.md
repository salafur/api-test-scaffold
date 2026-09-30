# api-test-scaffold · 产品文档说明报告

> 项目名称：api-test-scaffold — pytest 接口自动化测试脚手架
> 文档版本：v1.0（基于 2026-09-29 源码逐行梳理）
> 项目路径：`C:\Users\Administrator\WorkBuddy\2026-09-29-19-58-12\api-test-scaffold`
> 许可证：MIT

---

## 1. 项目定位：一句话说清它是干嘛的

**一个生产级规范的 pytest 接口自动化测试工程模板：分层封装、数据驱动、Schema 校验、Allure 报告、CI 集成，自带一个可离线运行的演示 API——clone 下来即可跑通，替换配置与用例层即可接入真实项目。**

它与你在公司用 Postman/Bruno 手工测接口的关系：**把手工接口测试升级为代码化、可回归、可入 CI 的自动化工程**。这正是你简历"系统补充接口测试与自动化测试原理"目标对应的成品样板。

## 2. 它解决什么问题

接口测试最容易烂掉的三种方式：

1. **一个用例一份 requests 代码**——复制粘贴 50 份后，接口改一个参数要改 50 处
2. **环境硬编码**——URL、账号写死在用例里，换环境没法跑
3. **断言无章法**——只验状态码，响应体结构变了根本不知道

本脚手架用**强制分层**解决前两个，用 **Schema 校验**解决第三个。

## 3. 分层架构（工程的骨架）

```
testcases/      用例层：只写业务断言（"下单后余额扣减"）
    │ 依赖
    ▼
common/         机制层：HTTP 客户端 / 断言库 / 数据加载
    │ 依赖
    ▼
config/         配置层：多环境 URL + 账户管理
    │
demo_app/       被测对象：FastAPI 演示服务（内存数据，离线可跑）
testdata/       YAML 数据驱动文件
```

### 分层规则（README 原话整理）

| 层 | 职责 | 禁止 |
|---|---|---|
| `testcases/` | 业务语义断言 | 拼 URL、解析 token |
| `common/` | HTTP 机制、重试、通用断言 | 出现任何业务字段名 |
| `config/` | 环境与账户 | 硬编码进用例 |

**核心原则：换环境改配置，换被测接口改客户端，用例只描述业务。**

## 4. 模块拆解（逐文件）

### 4.1 `common/http_client.py` — 统一 HTTP 客户端

`ApiClient`，每个测试会话一个实例：

- **会话管理**：内部持 `requests.Session()`，连接复用
- **登录态注入**：`set_token()` 后每个请求自动带 `Authorization: Bearer <token>`——用例层永远不用手动拼请求头
- **自动重试**：连接错误/超时重试 `max_retries` 次后抛出
- **请求日志**：每次请求记录 method、URL、状态码、耗时毫秒
- **`trust_env = False`**：屏蔽系统代理——注释里记着一个真实踩坑："曾导致复用连接上的第 2 个请求被代理错路由返回 404"
- **`login()` 便捷方法**：POST `/auth/login` 拿 token 并注入，一行完成

### 4.2 `common/assertions.py` — 断言库

四个通用断言，全部带友好失败信息（失败时打印实际响应前 200 字符）：

| 函数 | 干什么 | 示例 |
|------|--------|------|
| `assert_status(resp, 201)` | 状态码 | 全部用例 |
| `assert_json(resp)` | 验 content-type 是 JSON 并解析 | 取响应体 |
| `assert_field(obj, "owner.username", "alice")` | **点路径**取嵌套字段断言 | 验业务值 |
| `assert_schema(resp, schema)` | **jsonschema 校验响应结构** | 契约测试 |

**关键思想：结构校验与业务值断言分离**。接口契约变了（字段改名/缺失）先红 Schema；值不对红业务断言——两类问题一眼分清。

### 4.3 `common/dataloader.py` — 数据驱动加载

`load_cases(filename, key)`：从 `testdata/` 读 YAML 返回用例列表，配合 `pytest.mark.parametrize` 实现"用例数据与用例代码分离"。

### 4.4 `config/` — 多环境配置

`config.yaml` 定义 `local` / `staging` 两套 `base_url` + 三个账户（admin/rich/poor）。`settings.py` 按 `API_ENV` 环境变量切换：

```bash
API_ENV=staging pytest testcases/ -v    # 一键切环境，用例零改动
```

### 4.5 `testcases/conftest.py` — fixture 体系（脚手架的精华之一）

- **`base_url`（session 级）**：在进程内用 uvicorn 子线程**自动拉起演示 API**——随机空闲端口启动，就绪探测循环等待，测试结束自动关停。**这就是"clone 下来即可跑通"的秘密**
- **`reset_state`（autouse）**：每个用例前 POST `/__test__/reset` 重置数据——**保证用例顺序无关**，这是自动化工程的硬指标
- **`api` / `alice` / `bob`（函数级）**：三种身份的客户端 fixture——未登录 / 已登录有余额（30 元）/ 已登录零余额。用例签名要什么身份就注入什么，**不用在用例里写登录代码**

### 4.6 `demo_app/app.py` — 被测演示 API

FastAPI 写的迷你电商服务（约 120 行），故意暴露**典型接口测试考点**：

| 接口 | 考点 |
|------|------|
| `POST /auth/login` | token 签发、401 错误凭据 |
| `GET /users/me` | 认证态校验（无 token/伪造 token → 401） |
| `POST /orders` | 参数校验（qty≤0/item 空 → 400）、业务规则（余额不足 → 409）、201 创建 |
| `GET /orders/{id}` | 资源归属：他人的订单 → 403；不存在 → 404 |
| `DELETE /orders/{id}` | 取消退款、余额恢复（业务闭环） |
| `POST /__test__/reset` | **可测试性设计**：测试钩子，仅演示用，真实项目用测试库/容器隔离替代 |

### 4.7 `testcases/` — 用例层

三个文件 23 个用例，风格样板：

```python
@feature("订单模块")
class TestCreateOrder:
    @story("余额不足返回 409 且余额不变")
    def test_insufficient_balance(self, alice, case):
        before = assert_json(alice.get("/users/me"))["balance"]
        resp = alice.post("/orders", json={...})
        assert_status(resp, 409)
        after = assert_json(alice.get("/users/me"))["balance"]
        assert before == after, "余额不足时余额不应变化"
```

注意这个用例的**双断言**思想：不只验"返回 409"，还验"余额没被错误扣减"——**副作用断言**。这是你接口测试补课最该学的用例设计思路。

`testcases/test_auth.py` 里的 `test_tokens_differ`（每次登录签发独立 token）也是经典考点：验 token 不重复。

### 4.8 `testdata/orders.yaml` — 数据驱动数据

三组用例集：`create_cases`（正常）、`invalid_cases`（400 边界）、`insufficient_cases`（409）。`ids=lambda c: c["name"]` 让 YAML 里的中文用例名直接成为 pytest 报告里的用例名。

## 5. 特性清单

- ✅ **数据驱动**：YAML + parametrize，加用例改 YAML 不动代码
- ✅ **Schema 校验**：jsonschema，契约变化先红结构
- ✅ **认证态管理**：fixture 按角色出客户端，用例不碰 token
- ✅ **异常场景全覆盖**：401/403/404/400/409，含"余额不足时余额不变"这类状态断言
- ✅ **Allure 报告**：`@feature/@story` 标注，`pytest --alluredir=allure-results`
- ✅ **多环境**：`API_ENV` 一键切换
- ✅ **用例顺序无关**：每用例自动 reset
- ✅ **CI**：GitHub Actions 自动跑并上传 Allure 结果工件

## 6. 依赖与环境

```
pytest>=8.0  requests>=2.31  pyyaml>=6.0  jsonschema>=4.20
allure-pytest>=2.13  fastapi>=0.110  uvicorn>=0.29
```

fastapi/uvicorn 只服务于演示服务；接入真实项目时可以把 demo_app 删掉，改 `config.yaml` 指向真实环境即可。

## 7. 如何接入真实项目（三步）

1. 改 `config/config.yaml`：填真实环境 base_url 和账户
2. 按 `testcases/` 的样板写业务用例（只写业务断言）
3. 需要新接口封装时在 `common/` 或 `ApiClient` 加方法

## 8. 关键设计决策（面试可讲）

1. **为什么分层而不是平铺？** 复制粘贴型用例的维护成本随用例数线性爆炸；分层后"接口变了一处改客户端"
2. **为什么 Schema 和业务值分开验？** 两类错误的归因速度不同——结构红=契约变，值红=逻辑错
3. **为什么每用例 reset？** 顺序无关的用例才能随意并行、随意重跑单个
4. **为什么 trust_env=False？** 本机代理会干扰 keep-alive 连接复用（真实踩坑记录）
5. **为什么演示服务进程内启动？** 零外部依赖，clone 即跑，CI 无需准备环境

## 9. 局限与扩展

- 演示服务是内存存储：真实项目接测试库（MySQL/容器化）
- 无并发压测能力：可叠加 locust/pytest-xdist
- 无数据造数工厂：可加 faker 生成动态测试数据
- Allure 需要本地装 allure 命令行才能 `allure serve`

## 10. 与你的求职目标的对应关系

- 银行 UAT/SIT 岗位（HSBC 方向）面试高频问题：**"接口自动化框架怎么设计的"**——本脚手架的分层表就是标准答案模板
- **"用例怎么保证独立性"**——reset fixture + 函数级客户端隔离
- **"数据驱动怎么做"**——YAML + parametrize + ids
- 建议面试前动手把 demo_app 换成你熟悉的业务（比如拉霸下注接口），讲自己改造的经历比讲模板更有说服力

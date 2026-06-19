# ADR-009: 全局服务容器 service_hub

**Status:** Accepted
**Date:** 2026-06-13

## Context

全局单例若用模块级裸变量散落各处，会导致依赖关系不可见、初始化顺序脆弱、测试难以替换为 mock。

## Decision

通过**依赖注入容器** `service_hub` 统一管理全局服务，并以 `from ginkgo import services` 作为公共访问入口：

- `service_hub` 按域分层暴露服务工厂：`service_hub.data.services.*`、`service_hub.core.services.*`、`service_hub.trading.services.*`。
- `services`（`src/ginkgo/__init__.py`）聚合常用服务：`bar_service`、`config_service`、`logger_service`、`thread_service` 等。
- 习惯称呼 **GLOG**（日志）/ **GCONF**（配置）/ **GTM**（线程管理）对应 `logger_service` / `config_service` / `thread_service`。

## Rationale

- **依赖可见**：服务获取经过容器，调用图可静态分析，而非隐式模块副作用。
- **可测试**：测试时可替换容器内的服务工厂为 mock，无需 monkey-patch 全局变量。
- **初始化集中**：服务创建顺序由容器管理，消除"导入即副作用"的脆弱性。

## Consequences

- 获取全局服务统一走 `services` 或 `service_hub`，不直接 `import` 服务实现类的模块级实例。
- 新增全局服务时，注册到对应域的 `service_hub` 分层下，并在 `services` 公共接口按需导出。
- 重构时禁止擅自修改 Base 类（BaseCRUD / BaseService），在具体实现层处理。

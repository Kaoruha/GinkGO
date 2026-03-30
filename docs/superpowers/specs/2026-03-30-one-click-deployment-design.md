# 一键部署设计文档

**日期**: 2026-03-30
**分支**: 017-one-click-deployment
**目标**: 从回测结果一键部署到纸上交易/实盘(OKX)

## 1. 概述

实现回测 → 纸上交易/实盘的一键部署功能。用户通过 Web UI 按钮或 CLI 命令，将已完成回测的策略（含所有组件）深拷贝并部署到纸上交易或 OKX 实盘环境。

### 部署目标

| 模式 | Broker | 需要 MLiveAccount | 说明 |
|------|--------|-------------------|------|
| Paper | SimBroker | 否 | 纸上交易，复用回测引擎 |
| Live (OKX) | OKXBroker | 是 | OKX 实盘交易 |

## 2. 架构

### 2.1 部署数据流

```
用户触发 (Web UI / CLI)
       ↓
DeploymentService.deploy(backtest_task_id, mode, account_id?)
  ├── 1. 校验: 回测完成、账号有效(live模式)
  ├── 2. 收集: 读取原 Portfolio + Mapping + Param + MFile + Graph
  ├── 3. 深拷贝: MFile(clone) + Mapping(新建) + Param(复制) + Graph(复制)
  ├── 4. 创建: 新 Portfolio(mode=PAPER/LIVE)
  ├── 5. 绑定: Paper → PaperTradingController / Live → MBrokerInstance
  ├── 6. 记录: 创建 MDeployment 追踪记录
  └── 7. 返回: 新 portfolio_id + deployment_id
```

### 2.2 深拷贝策略

部署时对以下数据进行完全独立的深拷贝，确保部署后两侧互不影响：

```
回测 Portfolio (id=A)
├── MFile: file_1 (strategy code)
│   └── version, parent_uuid=null
├── MPortfolioFileMapping: A↔file_1 (mapping_id=m1)
│   └── MParam: m1 → {index:0, value:"5"}, {index:1, value:"20"}
└── MongoDB Graph (完整图结构)

         ↓ 部署（全部深拷贝）

新 Portfolio (id=B, mode=PAPER/LIVE)
├── MFile: file_1_copy (clone, parent_uuid=file_1)  ← 独立副本
│   └── version, parent_uuid=file_1
├── MPortfolioFileMapping: B↔file_1_copy (mapping_id=m2)
│   └── MParam: m2 → {index:0, value:"5"}, {index:1, value:"20"}
└── MongoDB Graph: 独立副本
```

**血统追溯**: MFile.parent_uuid + MDeployment.source_portfolio_id + MDeployment.source_task_id

## 3. 新增组件

### 3.1 DeploymentService

**文件**: `src/ginkgo/trading/services/deployment_service.py`

核心方法：

```python
class DeploymentService:
    def deploy(
        self,
        backtest_task_id: str,
        mode: EXECUTION_MODE,       # PAPER or LIVE
        account_id: str = None,     # MLiveAccount.uuid (live模式必填)
        name: str = None,           # 新Portfolio名称
    ) -> ServiceResult:
        """
        一键部署

        Steps:
        1. 验证回测任务状态(completed)
        2. 验证实盘账号(live模式, 账号enabled即可，不强制可用)
        3. 读取原 Portfolio 配置
        4. 深拷贝 MFile (file_service.clone)
        5. 新建 MPortfolioFileMapping
        6. 复制 MParam
        7. 复制 MongoDB Graph
        8. 创建新 Portfolio (mode=PAPER/LIVE)
        9. Paper: 注册 PaperTradingController
           Live: 创建 MBrokerInstance + 启动 BrokerManager
        10. 创建 MDeployment 记录
        11. 返回 portfolio_id
        """

    def get_deployment_info(self, portfolio_id: str) -> ServiceResult:
        """获取部署信息：回测摘要 + 当前状态 + 纸上交易历史"""

    def list_deployments(self, source_task_id: str = None) -> ServiceResult:
        """列出部署记录"""
```

### 3.2 MDeployment 数据模型

**文件**: `src/ginkgo/data/models/model_deployment.py`

```python
class MDeployment(MMysqlBase):
    __tablename__ = "deployment"

    source_task_id: str        # 回测任务ID (BacktestTask.run_id)
    target_portfolio_id: str   # 部署后的Portfolio ID
    source_portfolio_id: str   # 原始回测Portfolio ID
    mode: int                  # EXECUTION_MODE.PAPER / LIVE
    account_id: str            # MLiveAccount.uuid (live模式必填, paper为null)
    status: int                # PENDING / DEPLOYED / FAILED / STOPPED
```

### 3.3 API 端点

**文件**: `api/routers/deployment.py`

```
POST /api/v1/deploy
Body: {
  "backtest_task_id": "xxx",
  "mode": "paper" | "live",
  "account_id": "xxx" | null,
  "name": "xxx" | null
}
Response: {
  "deployment_id": "xxx",
  "portfolio_id": "xxx",
  "status": "deployed",
  "source_backtest_task_id": "xxx"
}

GET /api/v1/deploy/{portfolio_id}
Response: {
  "deployment": {...},
  "source_backtest_task": {...},
  "paper_history": [...]
}

GET /api/v1/deploy?task_id=xxx
Response: {
  "deployments": [...]
}
```

### 3.4 CLI 命令

**文件**: `src/ginkgo/client/deploy_cli.py`

```bash
# 部署到纸上交易
ginkgo deploy {backtest_task_id} --mode paper

# 部署到实盘
ginkgo deploy {backtest_task_id} --mode live --account {account_id}

# 查看部署详情
ginkgo deploy info {portfolio_id}

# 列出部署记录
ginkgo deploy list [--task {task_id}]
```

## 4. 复用现有组件

| 组件 | 用途 |
|------|------|
| `FileService.clone()` | MFile 深拷贝 |
| `PortfolioMappingService` | Mapping + Param 管理 |
| `PortfolioService` | Portfolio CRUD |
| `BacktestTaskService` | 回测任务查询 |
| `LiveAccountService` | 实盘账号验证 |
| `BrokerInstanceCRUD` | Broker 实例管理 |
| `BrokerManager` | Broker 生命周期 |
| `GinkgoMongo` | Graph 图结构存储 |
| `ServiceResult` | 统一返回格式 |

## 5. 前置校验

| 校验项 | Paper | Live |
|--------|-------|------|
| 回测任务状态 = completed | 必须 | 必须 |
| 实盘账号 enabled | 不需要 | 必须 |
| 展示回测摘要 | 是 | 是 |
| 展示纸上交易历史 | 是 | 是 |

**注意**: 实盘账号仅需 enabled 状态。如果账号不可用（如API失效），用户可以选择通过邮件通知手动交易。

## 6. 血统追溯

部署记录支持完整追溯链路：

```
MDeployment.source_task_id → BacktestTask (回测结果)
MDeployment.source_portfolio_id → 原始 Portfolio
MDeployment.target_portfolio_id → 部署后 Portfolio
MFile.parent_uuid → 代码血统
```

支持查询：回测 → 纸上交易 → 实盘 的完整部署链。

## 7. 错误处理

- 回测任务未完成 → 返回错误，提示等待回测完成
- 实盘账号 disabled → 返回错误，提示启用账号
- MFile clone 失败 → 回滚已创建的资源，返回错误
- Portfolio 创建失败 → 回滚，返回错误
- 使用 ServiceResult 统一错误格式

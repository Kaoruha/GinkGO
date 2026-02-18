# Backtest Task Model Refactoring

**Date**: 2026-02-17
**Feature**: 011-quant-research-modules
**Status**: Design

## 背景

当前回测列表 API `/api/v1/backtest` 返回的是 `MEngine` 实体，但从业务语义来看：

- 用户期望看到的是"一次回测执行的结果"
- 回测列表应展示收益率、最大回撤等**执行结果指标**
- `MEngine` 更像是"引擎配置模板"，可以重复使用执行多次回测

## 设计决策

将 **BacktestTask** 对应到 **`MRunRecord`**（重命名为 `MBacktestTask`），而不是 `MEngine`。

## 实体重命名

| 原名称 | 新名称 | 说明 |
|--------|--------|------|
| `MRunRecord` | `MBacktestTask` | 回测任务（一次执行） |
| `MEngine` | 保持不变 | 引擎配置模板 |

## 实体关系

```
┌─────────────────────────────────────────────────────────────┐
│                      MEngine (引擎配置)                      │
│                     可复用的回测配置模板                       │
├─────────────────────────────────────────────────────────────┤
│ uuid                │ 引擎唯一标识                           │
│ name                │ 引擎名称                               │
│ config_hash         │ 配置哈希（检测配置变化）                 │
│ config_snapshot     │ 配置快照JSON                           │
│ backtest_start_date │ 回测开始时间                           │
│ backtest_end_date   │ 回测结束时间                           │
│ is_live             │ 是否实盘                               │
│ status              │ 引擎状态 (IDLE/RUNNING/STOPPED)        │
│ run_count           │ 累计执行次数                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ 1:N
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              MBacktestTask (回测任务/执行记录)                │
│                       一次回测执行                            │
├─────────────────────────────────────────────────────────────┤
│ uuid                │ 任务唯一标识                           │
│ task_id             │ 任务会话ID（唯一）                      │
│ engine_id           │ 所属引擎ID → MEngine.uuid              │
│ portfolio_id        │ 关联的投资组合ID                        │
│                                                             │
│ # 执行信息                                                   │
│ start_time          │ 开始时间                               │
│ end_time            │ 结束时间                               │
│ duration_seconds    │ 运行时长                               │
│ status              │ 状态: running/completed/failed/stopped │
│ error_message       │ 错误信息                               │
│                                                             │
│ # 业务统计                                                   │
│ total_orders        │ 订单总数                               │
│ total_signals       │ 信号总数                               │
│ total_positions     │ 持仓记录数                             │
│ total_events        │ 事件总数                               │
│                                                             │
│ # 性能指标                                                   │
│ final_portfolio_value│ 最终组合价值                          │
│ total_pnl           │ 总盈亏                                 │
│ max_drawdown        │ 最大回撤                               │
│ avg_event_processing_ms│ 平均事件处理时间                    │
│                                                             │
│ # 配置快照                                                   │
│ config_snapshot     │ 执行时的配置快照JSON                    │
│ environment_info    │ 环境信息JSON                           │
└─────────────────────────────────────────────────────────────┘
```

## API 调整

### 回测任务 API（基于 MBacktestTask）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/backtest` | GET | 获取回测任务列表 |
| `/api/v1/backtest` | POST | 创建并执行回测任务 |
| `/api/v1/backtest/{task_id}` | GET | 获取回测任务详情 |
| `/api/v1/backtest/{task_id}` | DELETE | 删除回测任务 |
| `/api/v1/backtest/{task_id}/stop` | POST | 停止运行中的任务 |
| `/api/v1/backtest/{task_id}/netvalue` | GET | 获取净值曲线数据 |
| `/api/v1/backtest/{task_id}/orders` | GET | 获取订单记录 |
| `/api/v1/backtest/{task_id}/positions` | GET | 获取持仓记录 |
| `/api/v1/backtest/compare` | POST | 对比多个回测任务 |

### 引擎配置 API（基于 MEngine）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/engine` | GET | 获取引擎配置列表 |
| `/api/v1/engine` | POST | 创建引擎配置 |
| `/api/v1/engine/{engine_id}` | GET | 获取引擎配置详情 |
| `/api/v1/engine/{engine_id}` | PUT | 更新引擎配置 |
| `/api/v1/engine/{engine_id}` | DELETE | 删除引擎配置 |
| `/api/v1/engine/{engine_id}/tasks` | GET | 获取该引擎的所有回测任务 |

## 数据库变更

### 表重命名

```sql
-- 重命名表
RENAME TABLE run_record TO backtest_task;

-- 更新字段名（如果需要）
ALTER TABLE backtest_task
  CHANGE COLUMN run_id task_id VARCHAR(128),
  CHANGE COLUMN parent_engine_id engine_id VARCHAR(64);
```

### 新增字段

```sql
-- 添加 portfolio_id 关联
ALTER TABLE backtest_task
  ADD COLUMN portfolio_id VARCHAR(32) COMMENT '关联的投资组合ID' AFTER engine_id;

-- 添加索引
ALTER TABLE backtest_task
  ADD INDEX idx_portfolio_id (portfolio_id),
  ADD INDEX idx_engine_id (engine_id),
  ADD INDEX idx_status (status),
  ADD INDEX idx_start_time (start_time);
```

## 代码变更

### 1. 模型重命名

```python
# src/ginkgo/data/models/model_backtest_task.py

class MBacktestTask(MMysqlBase, MBacktestRecordBase):
    """
    回测任务模型：记录每次回测执行的完整信息
    """
    __tablename__ = "backtest_task"

    # 标识
    task_id: Mapped[str] = mapped_column(String(128), unique=True, comment="任务会话ID")
    engine_id: Mapped[str] = mapped_column(String(64), comment="所属引擎ID")
    portfolio_id: Mapped[str] = mapped_column(String(32), comment="关联投资组合ID")

    # ... 其他字段保持不变
```

### 2. CRUD 重命名

```python
# src/ginkgo/data/crud/backtest_task_crud.py

class BacktestTaskCRUD(BaseCRUD):
    """回测任务 CRUD"""

    def get_tasks_by_engine(self, engine_id: str) -> List[MBacktestTask]:
        """获取引擎的所有任务"""
        ...

    def get_tasks_by_portfolio(self, portfolio_id: str) -> List[MBacktestTask]:
        """获取投资组合的所有任务"""
        ...
```

### 3. 服务层调整

```python
# src/ginkgo/data/services/backtest_task_service.py

class BacktestTaskService(BaseService):
    """回测任务服务"""

    def create_task(self, engine_id: str, portfolio_id: str, config: dict) -> MBacktestTask:
        """创建回测任务"""
        ...

    def run_task(self, task_id: str) -> ServiceResult:
        """执行回测任务"""
        ...

    def get_task_results(self, task_id: str) -> dict:
        """获取任务结果"""
        ...
```

## 前端调整

### 回测列表页面

- 展示每次执行的**结果**（收益率、最大回撤、夏普比率等）
- 支持按引擎、按投资组合筛选
- 支持对比多个回测任务

### 引擎配置页面（新增）

- 管理可复用的引擎配置模板
- 查看该引擎下的所有执行历史

## 迁移计划

1. **Phase 1**: 创建 `MBacktestTask` 模型和 CRUD（兼容现有 `MRunRecord`）
2. **Phase 2**: 更新 API 端点，返回 `MBacktestTask` 数据
3. **Phase 3**: 前端调整，适配新的数据结构
4. **Phase 4**: 数据迁移，将 `run_record` 表数据迁移到 `backtest_task`
5. **Phase 5**: 移除旧的 `MRunRecord` 代码

## 向后兼容

- 保留 `MRunRecord` 作为别名，指向 `MBacktestTask`
- API 保持 `/api/v1/backtest` 路径不变
- 返回数据格式兼容旧版本

```python
# 向后兼容别名
MRunRecord = MBacktestTask
```

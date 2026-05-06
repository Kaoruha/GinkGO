# 分析器聚合类型声明 设计

## 概述

为 `BaseAnalyzer` 添加 `aggregation_type` 类属性，让分析器声明自己的数据聚合方式（均值 vs 增量）。分段稳定性验证根据此属性选择正确的聚合算法。

## 背景

分段稳定性验证从 `analyzer_record` 读取时序数据并按时间段聚合。当前所有分析器统一用段内均值，但 `signal_count` 和 `order_count` 是累计计数器，均值无意义 — 应该用段内增量（段末值 - 段首值）。

系统允许自定义分析器，硬编码分类列表无法扩展。

## 变更范围

| 文件 | 变更 |
|------|------|
| `src/ginkgo/trading/analysis/analyzers/base_analyzer.py` | 添加 `aggregation_type = "mean"` 类属性 |
| `src/ginkgo/trading/analysis/analyzers/signal_count.py` | 添加 `aggregation_type = "delta"` |
| `src/ginkgo/trading/analysis/analyzers/order_count.py` | 添加 `aggregation_type = "delta"` |
| `src/ginkgo/data/services/validation_service.py` | `get_available_metrics()` 从注册表读取 aggregation_type；`segment_stability()` 按类型分支聚合逻辑 |
| `web-ui/src/api/modules/validation.ts` | `AvailableMetric` 接口加 `aggregation_type` 字段 |

## aggregation_type 值定义

| 值 | 含义 | 分段聚合方式 |
|---|---|---|
| `"mean"` | 运行指标（默认） | 段内所有记录的均值 |
| `"delta"` | 累计计数器 | 段内最后一条记录值 - 段内第一条记录值 |

## 后端实现

### BaseAnalyzer

在类级别属性区域（第 31 行附近）添加：

```python
class BaseAnalyzer(TimeMixin, ContextMixin, NamedMixin, Base):
    aggregation_type = "mean"  # 子类可覆盖为 "delta"
```

### SignalCount / OrderCount

在类定义内、`__abstract__ = False` 下方各加一行：

```python
aggregation_type = "delta"
```

### ValidationService.get_available_metrics()

通过 `AnalyzerRegistry.get(name)` 查找分析器类，读取 `aggregation_type`：

```python
def get_available_metrics(self, task_id: str, portfolio_id: str) -> ServiceResult:
    from ginkgo.trading.analysis.analyzers.registry import AnalyzerRegistry
    registry = AnalyzerRegistry()
    registry.scan_builtin()

    records = self._analyzer_crud.get_by_task_id(task_id=task_id, portfolio_id=portfolio_id, page_size=10000)
    names = sorted(set(r.name for r in records))
    metrics = []
    for n in names:
        cls = registry.get(n)
        agg_type = getattr(cls, 'aggregation_type', 'mean') if cls else 'mean'
        metrics.append({"name": n, "label": ANALYZER_LABELS.get(n, n), "aggregation_type": agg_type})
    return ServiceResult.success(data={"metrics": metrics})
```

### ValidationService.segment_stability()

在第 206 行聚合逻辑处，按 aggregation_type 分支：

```python
# 查询 analyzer 类的聚合类型
cls = registry.get(metric_name)
agg_type = getattr(cls, 'aggregation_type', 'mean') if cls else 'mean'

if agg_type == "delta" and len(seg_values) >= 2:
    # 累计计数器：取段内增量
    seg_dict[metric_name] = round(seg_values[-1] - seg_values[0], 6)
else:
    # 运行指标：取段内均值
    seg_dict[metric_name] = round(float(np.mean(seg_values)), 6) if seg_values else 0.0
```

注意：records 按时间升序排列时，seg_values 列表中最后一个是段末值，第一个是段首值。但当前 `get_by_task_id` 返回的是降序，需要在按段分组时先排序。实际上在 `segment_stability` 中 records 已经在内存中，需要确保按 timestamp 升序后再分段。

## 前端变更

`validation.ts` 的 `AvailableMetric` 接口添加：

```typescript
export interface AvailableMetric {
  name: string
  label: string
  aggregation_type: 'mean' | 'delta'  // 新增
}
```

前端不使用此字段做逻辑判断（聚合在后端完成），仅供展示参考。

## 不做的事

- 不修改其他 19 个内置分析器（继承默认 `"mean"` 即可）
- 不修改 `AnalyzerRegistry` 的注册逻辑（仅使用已有的 `get()` 方法）
- 不在 UI 上暴露聚合方式切换（后端自动处理）
- 不修改 `_do_record` 等分析器写入逻辑

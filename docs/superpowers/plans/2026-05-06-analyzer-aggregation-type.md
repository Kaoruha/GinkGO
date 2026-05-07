# 分析器聚合类型声明 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 BaseAnalyzer 添加 aggregation_type 类属性，让分段稳定性验证根据类型选择均值或增量聚合。

**Architecture:** BaseAnalyzer 默认 `aggregation_type = "mean"`，SignalCount/OrderCount 覆盖为 `"delta"`。ValidationService 通过 AnalyzerRegistry 查找分析器类读取属性，在聚合时分支处理。

**Tech Stack:** Python 3.12 + numpy

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/ginkgo/trading/analysis/analyzers/base_analyzer.py` | Modify | 添加 aggregation_type 类属性 |
| `src/ginkgo/trading/analysis/analyzers/signal_count.py` | Modify | 覆盖为 "delta" |
| `src/ginkgo/trading/analysis/analyzers/order_count.py` | Modify | 覆盖为 "delta" |
| `src/ginkgo/data/services/validation_service.py` | Modify | get_available_metrics 读取 aggregation_type；segment_stability 按类型分支聚合 |
| `web-ui/src/api/modules/validation.ts` | Modify | AvailableMetric 接口加 aggregation_type 字段 |

---

### Task 1: BaseAnalyzer 添加 aggregation_type 类属性

**Files:**
- Modify: `src/ginkgo/trading/analysis/analyzers/base_analyzer.py`

- [ ] **Step 1: 在 BaseAnalyzer 类定义中添加 aggregation_type 属性**

在 `base_analyzer.py` 中，找到类级别属性区域（`_execution_stats` 和 `_performance_log` 附近），在其后添加：

```python
    aggregation_type = "mean"  # 子类可覆盖为 "delta"
```

- [ ] **Step 2: Commit**

```bash
git add src/ginkgo/trading/analysis/analyzers/base_analyzer.py && git commit -m "feat: add aggregation_type class attribute to BaseAnalyzer"
```

---

### Task 2: SignalCount 和 OrderCount 覆盖为 "delta"

**Files:**
- Modify: `src/ginkgo/trading/analysis/analyzers/signal_count.py`
- Modify: `src/ginkgo/trading/analysis/analyzers/order_count.py`

- [ ] **Step 1: 在 SignalCount 类中添加 aggregation_type**

在 `signal_count.py` 中，`__abstract__ = False` 行下方添加：

```python
    aggregation_type = "delta"
```

- [ ] **Step 2: 在 OrderCount 类中添加 aggregation_type**

在 `order_count.py` 中，`__abstract__ = False` 行下方添加：

```python
    aggregation_type = "delta"
```

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/trading/analysis/analyzers/signal_count.py src/ginkgo/trading/analysis/analyzers/order_count.py && git commit -m "feat: set aggregation_type=delta for SignalCount and OrderCount"
```

---

### Task 3: ValidationService 读取并使用 aggregation_type

**Files:**
- Modify: `src/ginkgo/data/services/validation_service.py`

- [ ] **Step 1: 修改 get_available_metrics 从注册表读取 aggregation_type**

将现有的 `get_available_metrics` 方法替换为：

```python
    def get_available_metrics(self, task_id: str, portfolio_id: str) -> ServiceResult:
        """查询 analyzer_record 表中该任务实际存在的分析器名称及中文标签"""
        try:
            from ginkgo.trading.analysis.analyzers.registry import AnalyzerRegistry
            registry = AnalyzerRegistry()
            registry.scan_builtin()

            records = self._analyzer_crud.get_by_task_id(
                task_id=task_id,
                portfolio_id=portfolio_id,
                page_size=10000,
            )
            names = sorted(set(r.name for r in records))
            metrics = []
            for n in names:
                cls = registry.get(n)
                agg_type = getattr(cls, 'aggregation_type', 'mean') if cls else 'mean'
                metrics.append({"name": n, "label": ANALYZER_LABELS.get(n, n), "aggregation_type": agg_type})
            return ServiceResult.success(data={"metrics": metrics})
        except Exception as e:
            GLOG.ERROR(f"获取可用指标失败: {e}")
            return ServiceResult.error(f"获取可用指标失败: {e}")
```

- [ ] **Step 2: 修改 segment_stability 的聚合逻辑**

在 `segment_stability` 方法中，找到计算 `seg_dict[metric_name]` 的位置，将：

```python
                    seg_dict[metric_name] = round(float(np.mean(seg_values)), 6) if seg_values else 0.0
```

替换为（确保 `seg_values` 中的记录按时间排序，最后一个是段末值，第一个是段首值）：

```python
                    cls = registry.get(metric_name)
                    agg_type = getattr(cls, 'aggregation_type', 'mean') if cls else 'mean'
                    if agg_type == "delta" and len(seg_values) >= 2:
                        seg_dict[metric_name] = round(seg_values[-1] - seg_values[0], 6)
                    else:
                        seg_dict[metric_name] = round(float(np.mean(seg_values)), 6) if seg_values else 0.0
```

注意：需要在 `segment_stability` 方法开头（try 块内）初始化 registry：

```python
            from ginkgo.trading.analysis.analyzers.registry import AnalyzerRegistry
            registry = AnalyzerRegistry()
            registry.scan_builtin()
```

同时需要确保 `seg_values` 中的记录是按时间排序的。当前 `by_name` dict 中的记录来自 `get_by_task_id`（降序），需要在按段分组前对每个分析器的记录按 `business_timestamp` 或 `timestamp` 升序排列。找到 `by_name` 构建位置，将记录排序：

```python
            by_name = {}
            for r in all_records:
                by_name.setdefault(r.name, []).append(r)
            # 确保每个分析器的记录按时间升序（delta 聚合需要首尾值）
            for name in by_name:
                by_name[name].sort(key=lambda r: r.business_timestamp or r.timestamp)
```

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/data/services/validation_service.py && git commit -m "feat: use analyzer aggregation_type for segment stability aggregation"
```

---

### Task 4: 前端类型更新

**Files:**
- Modify: `web-ui/src/api/modules/validation.ts`

- [ ] **Step 1: AvailableMetric 接口加 aggregation_type 字段**

将 `AvailableMetric` 接口改为：

```typescript
export interface AvailableMetric {
  name: string
  label: string
  aggregation_type: 'mean' | 'delta'
}
```

- [ ] **Step 2: Commit**

```bash
git add web-ui/src/api/modules/validation.ts && git commit -m "feat: add aggregation_type to AvailableMetric interface"
```

---

### Task 5: 浏览器验证

- [ ] **Step 1: 用 Playwright 验证**

1. 选择回测任务 → 确认 `signal_count` 和 `order_count` 指标的 `aggregation_type` 为 `"delta"`
2. 运行分析 → 确认 signal_count 不再递增，而是显示每段增量
3. 确认其他指标（sharpe_ratio 等）仍显示段内均值

- [ ] **Step 2: Push**

```bash
git push -u github 026-feat/analyzer-aggregation-type
```

# 动态指标选择器 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 分段稳定性验证页面支持动态指标选择 — 用户从回测已有的分析器中选择指标进行分段对比。

**Architecture:** 后端新增 `available-metrics` API 查询 `analyzer_record` 表中实际存在的分析器；修改 `segment_stability` 接受 `metrics` 参数按段聚合取均值。前端新增指标 tag 多选器，图表根据选中指标动态渲染折线。

**Tech Stack:** Python 3.12 + FastAPI + numpy / Vue 3 + ECharts 5

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/ginkgo/data/services/validation_service.py` | Modify | 新增 ANALYZER_LABELS 映射、`get_available_metrics()`、重写 `segment_stability()` |
| `api/api/validation.py` | Modify | 新增 `/available-metrics` 端点，修改 `SegmentStabilityRequest` |
| `web-ui/src/api/modules/validation.ts` | Modify | 新增 `availableMetrics()` 接口，更新类型定义 |
| `web-ui/src/views/portfolio/validation/SegmentStability.vue` | Modify | 新增指标选择器，动态渲染概览图和详情图 |

---

### Task 1: 后端 — 新增 ANALYZER_LABELS 映射和 get_available_metrics()

**Files:**
- Modify: `src/ginkgo/data/services/validation_service.py`

- [ ] **Step 1: 在 ValidationService 类上方添加 ANALYZER_LABELS 字典**

在 `validation_service.py` 文件中，`class ValidationService` 之前（约第 11 行后），添加：

```python
ANALYZER_LABELS = {
    "net_value": "净值",
    "ProfitAna": "每日盈亏",
    "annualized_return": "年化收益",
    "sharpe_ratio": "夏普比率",
    "max_drawdown": "最大回撤",
    "win_rate": "胜率",
    "hold_pct": "仓位占比",
    "order_count": "订单数",
    "signal_count": "信号数",
    "sortino_ratio": "Sortino 比率",
    "calmar_ratio": "Calmar 比率",
    "volatility": "波动率",
    "underwater_time": "水下时间",
    "var_cvar": "VaR",
    "skew_kurtosis": "偏度/峰度",
    "consecutive_pnl": "连续盈亏",
    "trade_win_rate": "交易胜率",
    "avg_win_loss_ratio": "盈亏比",
    "profit_factor": "利润因子",
    "avg_holding_period": "平均持仓天数",
    "max_consecutive_losses": "最大连续亏损",
}
```

- [ ] **Step 2: 在 ValidationService 中添加 get_available_metrics 方法**

在 `__init__` 方法之后添加：

```python
def get_available_metrics(self, task_id: str, portfolio_id: str) -> ServiceResult:
    """查询 analyzer_record 表中该任务实际存在的分析器名称及中文标签"""
    try:
        records = self._analyzer_crud.get_by_task_id(
            task_id=task_id,
            portfolio_id=portfolio_id,
            page_size=10000,
        )
        names = sorted(set(r.name for r in records))
        metrics = [{"name": n, "label": ANALYZER_LABELS.get(n, n)} for n in names]
        return ServiceResult.success(data={"metrics": metrics})
    except Exception as e:
        GLOG.ERROR(f"获取可用指标失败: {e}")
        return ServiceResult.error(f"获取可用指标失败: {e}")
```

- [ ] **Step 3: Commit**

```bash
cd /home/kaoru/Ginkgo && git add src/ginkgo/data/services/validation_service.py && git commit -m "feat: add ANALYZER_LABELS and get_available_metrics to ValidationService"
```

---

### Task 2: 后端 — 重写 segment_stability() 支持动态指标

**Files:**
- Modify: `src/ginkgo/data/services/validation_service.py`

将 `segment_stability()` 方法从基于 net_value 重新计算改为直接从 `analyzer_record` 读取各分析器数据按段聚合。

- [ ] **Step 1: 添加 _get_time_range 辅助方法**

在 `get_available_metrics` 之后添加：

```python
def _get_time_range(self, records) -> tuple:
    """从 net_value 记录获取起止时间"""
    if not records:
        return None, None
    timestamps = [r.business_timestamp or r.timestamp for r in records if (r.business_timestamp or r.timestamp)]
    if not timestamps:
        return None, None
    return min(timestamps), max(timestamps)
```

- [ ] **Step 2: 添加 _aggregate_by_segments 辅助方法**

```python
def _aggregate_by_segments(self, records, boundaries, metric_name: str) -> list:
    """按时间段边界聚合分析器记录，返回每段均值"""
    values = []
    for i in range(len(boundaries) - 1):
        start, end = boundaries[i], boundaries[i + 1]
        seg_values = [
            float(r.value) for r in records
            if start <= (r.business_timestamp or r.timestamp) < end
        ]
        values.append(round(float(np.mean(seg_values)), 6) if seg_values else 0.0)
    return values
```

- [ ] **Step 3: 重写 segment_stability 方法**

替换现有的 `segment_stability` 方法（第 115-166 行）为：

```python
DEFAULT_METRICS = ["annualized_return", "sharpe_ratio", "max_drawdown", "win_rate"]

def segment_stability(
    self,
    task_id: str,
    portfolio_id: str,
    n_segments_list: Optional[List[int]] = None,
    metrics: Optional[List[str]] = None,
) -> ServiceResult:
    """分段稳定性验证 — 按指定分析器分段聚合取均值"""
    if n_segments_list is None:
        n_segments_list = [2, 4, 8]
    if metrics is None:
        metrics = self.DEFAULT_METRICS

    try:
        # 获取时间范围
        nv_records = self._get_net_value_records(task_id, portfolio_id)
        if len(nv_records) < 10:
            return ServiceResult.error("数据不足：net_value 记录少于 10 条")

        time_start, time_end = self._get_time_range(nv_records)
        if not time_start or not time_end:
            return ServiceResult.error("无法确定回测时间范围")

        # 计算稳定性评分（基于 net_value 的收益率分段）
        returns = self._records_to_returns(nv_records)

        windows = []
        for n in n_segments_list:
            if n > len(returns):
                continue

            # 时间段边界
            total_seconds = (time_end - time_start).total_seconds()
            seg_duration = total_seconds / n
            boundaries = [time_start + __import__('datetime').timedelta(seconds=seg_duration * i) for i in range(n + 1)]

            # 按段聚合每个指标
            segments_data = []
            for seg_idx in range(n):
                seg_dict = {}
                for metric_name in metrics:
                    metric_records = self._analyzer_crud.get_by_task_id(
                        task_id=task_id,
                        portfolio_id=portfolio_id,
                        analyzer_name=metric_name,
                        page_size=10000,
                    )
                    # 筛选本段的记录
                    seg_values = [
                        float(r.value) for r in metric_records
                        if boundaries[seg_idx] <= (r.business_timestamp or r.timestamp) < boundaries[seg_idx + 1]
                    ]
                    seg_dict[metric_name] = round(float(np.mean(seg_values)), 6) if seg_values else 0.0
                segments_data.append(seg_dict)

            # 稳定性评分（基于 annualized_return 的分段收益标准差）
            seg_returns_for_score = [s.get("annualized_return", 0) for s in segments_data]
            if returns is not None and len(returns) >= n:
                seg_returns_arr = self._split_returns(returns, n)
                seg_returns_for_score = [float(np.sum(s)) for s in seg_returns_arr]
            stability_score = self._calc_stability_score(seg_returns_for_score)

            windows.append({
                "n_segments": n,
                "segments": segments_data,
                "stability_score": stability_score,
                "available_metrics": metrics,
            })

        if not windows:
            return ServiceResult.error("分段数均大于数据长度，无法计算")

        return ServiceResult.success(data={"windows": windows})

    except Exception as e:
        GLOG.ERROR(f"分段稳定性计算失败: {e}")
        return ServiceResult.error(f"计算失败: {e}")
```

注意：上述方法中每次循环内查询所有 metric_records 效率较低，但数据量通常在几千条以内可以接受。如果性能不足后续可优化为一次性查询所有分析器记录后在内存中分组。

- [ ] **Step 4: Commit**

```bash
cd /home/kaoru/Ginkgo && git add src/ginkgo/data/services/validation_service.py && git commit -m "feat: rewrite segment_stability to aggregate by selected metrics"
```

---

### Task 3: 后端 — API 层新增 available-metrics 端点

**Files:**
- Modify: `api/api/validation.py`

- [ ] **Step 1: 在 SegmentStabilityRequest 中添加 metrics 字段**

将 `SegmentStabilityRequest` 修改为：

```python
class SegmentStabilityRequest(BaseModel):
    task_id: str = Field(..., description="回测任务 UUID")
    portfolio_id: str = Field(..., description="组合 UUID")
    n_segments: Optional[List[int]] = Field(default=[2, 4, 8], description="分段数列表")
    metrics: Optional[List[str]] = Field(default=None, description="分析器名称列表")
```

- [ ] **Step 2: 新增 AvailableMetricsRequest 和 available_metrics 端点**

在 `MonteCarloRequest` 之前添加：

```python
class AvailableMetricsRequest(BaseModel):
    task_id: str = Field(..., description="回测任务 UUID")
    portfolio_id: str = Field(..., description="组合 UUID")


@router.post("/available-metrics")
async def available_metrics(req: AvailableMetricsRequest):
    """查询指定回测任务可用的分析器指标"""
    try:
        svc = get_validation_service()
        result = svc.get_available_metrics(
            task_id=req.task_id,
            portfolio_id=req.portfolio_id,
        )
        if not result.is_success():
            raise BusinessError(result.error)
        return ok(data=result.data)
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"获取可用指标异常: {e}")
        raise BusinessError(f"获取可用指标失败: {e}")
```

- [ ] **Step 3: 修改 segment_stability 端点传递 metrics 参数**

将 `segment_stability` 端点的 `svc.segment_stability(...)` 调用改为：

```python
result = svc.segment_stability(
    task_id=req.task_id,
    portfolio_id=req.portfolio_id,
    n_segments_list=req.n_segments,
    metrics=req.metrics,
)
```

- [ ] **Step 4: Commit**

```bash
cd /home/kaoru/Ginkgo && git add api/api/validation.py && git commit -m "feat: add available-metrics endpoint and metrics param to segment-stability"
```

---

### Task 4: 前端 — 更新 TypeScript 接口和 API 方法

**Files:**
- Modify: `web-ui/src/api/modules/validation.ts`

- [ ] **Step 1: 更新 SegmentStabilityConfig 添加 metrics 字段**

将 `SegmentStabilityConfig`（第 80-84 行）改为：

```typescript
export interface SegmentStabilityConfig {
  task_id: string
  portfolio_id: string
  n_segments?: number[]
  metrics?: string[]
}
```

- [ ] **Step 2: 更新 SegmentStabilityResult 支持动态指标**

将 `SegmentStabilityResult`（第 86-97 行）改为：

```typescript
export interface SegmentStabilityResult {
  windows: {
    n_segments: number
    segments: Record<string, number>[]
    stability_score: number
    available_metrics: string[]
  }[]
}
```

- [ ] **Step 3: 新增 AvailableMetric 类型和 availableMetrics 方法**

在 `SegmentStabilityResult` 之后添加：

```typescript
export interface AvailableMetric {
  name: string
  label: string
}
```

在 `validationApi` 对象中，`segmentStability` 方法之前添加：

```typescript
/**
 * 查询可用分析器指标
 */
availableMetrics(params: { task_id: string; portfolio_id: string }): Promise<{ data: { metrics: AvailableMetric[] } }> {
  return request.post('/api/v1/validation/available-metrics', params)
},
```

- [ ] **Step 4: 修改 segmentStability 方法传递 metrics**

将 `segmentStability` 方法改为：

```typescript
segmentStability(config: SegmentStabilityConfig): Promise<SegmentStabilityResult> {
  return request.post('/api/v1/validation/segment-stability', {
    task_id: config.task_id,
    portfolio_id: config.portfolio_id,
    n_segments: config.n_segments || [2, 4, 8],
    metrics: config.metrics,
  })
},
```

- [ ] **Step 5: Commit**

```bash
cd /home/kaoru/Ginkgo && git add web-ui/src/api/modules/validation.ts && git commit -m "feat: add availableMetrics API and update types for dynamic metrics"
```

---

### Task 5: 前端 — SegmentStability.vue 添加指标选择器和动态图表

**Files:**
- Modify: `web-ui/src/views/portfolio/validation/SegmentStability.vue`

- [ ] **Step 1: 添加指标相关状态变量**

在 `const config = reactive(...)` 之后添加：

```typescript
const availableMetrics = ref<{ name: string; label: string }[]>([])
const selectedMetrics = reactive(new Set<string>(['annualized_return', 'sharpe_ratio', 'max_drawdown', 'win_rate']))
const metricsLoading = ref(false)
const ANALYZER_LABELS: Record<string, string> = {
  net_value: '净值', ProfitAna: '每日盈亏', annualized_return: '年化收益',
  sharpe_ratio: '夏普比率', max_drawdown: '最大回撤', win_rate: '胜率',
  hold_pct: '仓位占比', order_count: '订单数', signal_count: '信号数',
  sortino_ratio: 'Sortino 比率', calmar_ratio: 'Calmar 比率', volatility: '波动率',
  underwater_time: '水下时间', var_cvar: 'VaR', skew_kurtosis: '偏度/峰度',
  consecutive_pnl: '连续盈亏', trade_win_rate: '交易胜率', avg_win_loss_ratio: '盈亏比',
  profit_factor: '利润因子', avg_holding_period: '平均持仓天数', max_consecutive_losses: '最大连续亏损',
}

const toggleMetric = (name: string) => {
  if (selectedMetrics.has(name)) {
    if (selectedMetrics.size > 1) selectedMetrics.delete(name)
  } else {
    selectedMetrics.add(name)
  }
}

const metricLabel = (name: string) => availableMetrics.value.find(m => m.name === name)?.label || ANALYZER_LABELS[name] || name
```

- [ ] **Step 2: 添加 fetchAvailableMetrics 方法**

在 `fetchBacktestList` 之后添加：

```typescript
const fetchAvailableMetrics = async () => {
  if (!config.taskId) { availableMetrics.value = []; return }
  metricsLoading.value = true
  try {
    const res = await validationApi.availableMetrics({
      task_id: config.taskId,
      portfolio_id: props.portfolioId || '',
    })
    availableMetrics.value = (res as any).data?.metrics || []
    // 保留已选但仍在可用列表中的
    const names = new Set(availableMetrics.value.map(m => m.name))
    for (const s of Array.from(selectedMetrics)) {
      if (!names.has(s)) selectedMetrics.delete(s)
    }
  } catch { /* ignore */ }
  finally { metricsLoading.value = false }
}
```

- [ ] **Step 3: 添加 watch 在 taskId 变化时获取可用指标**

在 `fetchAvailableMetrics` 之后添加：

```typescript
watch(() => config.taskId, () => {
  fetchAvailableMetrics()
})
```

- [ ] **Step 4: 修改 runAnalysis 传递 metrics 参数**

将 `runAnalysis` 方法中的 `validationApi.segmentStability(...)` 调用改为：

```typescript
const res = await validationApi.segmentStability({
  task_id: config.taskId,
  portfolio_id: props.portfolioId || '',
  n_segments: segments.length ? segments : undefined,
  metrics: Array.from(selectedMetrics),
})
```

- [ ] **Step 5: 在 template 中添加指标选择器**

在分段数 `form-group` 的 `</div>` 之后（"开始分析"按钮之前），添加新的 form-group：

```html
<div class="form-group">
  <label class="form-label">
    分析指标
    <span v-if="availableMetrics.length" class="metric-count">已选 {{ selectedMetrics.size }} / {{ availableMetrics.length }}</span>
  </label>
  <div class="segment-tags" v-if="availableMetrics.length">
    <button
      v-for="m in availableMetrics"
      :key="m.name"
      class="segment-tag"
      :class="{ active: selectedMetrics.has(m.name) }"
      @click="toggleMetric(m.name)"
    >{{ m.label }}</button>
  </div>
  <div v-else class="metric-placeholder">
    {{ config.taskId ? '加载中...' : '请先选择任务' }}
  </div>
</div>
```

- [ ] **Step 6: 修改概览图 initOverviewChart 为动态指标渲染**

将 `initOverviewChart` 方法替换为：

```typescript
const CHART_COLORS = ['#3b82f6', '#eab308', '#ef4444', '#22c55e', '#a855f7', '#f97316', '#06b6d4', '#ec4899']

const initOverviewChart = () => {
  if (!overviewChartRef.value || !result.value) return
  if (overviewChart) overviewChart.dispose()

  overviewChart = echarts.init(overviewChartRef.value)

  const windows = result.value.windows
  const metrics = windows[0]?.available_metrics || []
  const xData = windows.map((w: any) => `${w.n_segments}段`)

  const series = metrics.map((metric: string, idx: number) => ({
    name: metricLabel(metric),
    type: 'line',
    data: windows.map((w: any) => {
      const avg = w.segments.reduce((s: number, seg: any) => s + (seg[metric] || 0), 0) / w.segments.length
      return avg.toFixed(4)
    }),
    yAxisIndex: Math.min(idx, 2),
    itemStyle: { color: CHART_COLORS[idx % CHART_COLORS.length] },
    lineStyle: { width: 2 },
    symbol: 'circle',
    symbolSize: 8,
  }))

  const yAxes = [
    {
      type: 'value',
      name: metrics.length > 0 ? metricLabel(metrics[0]) : '',
      nameTextStyle: { color: CHART_COLORS[0], fontSize: 11 },
      axisLabel: { color: CHART_COLORS[0] },
      splitLine: { lineStyle: { color: '#2a2a3e' } },
    },
    {
      type: 'value',
      name: metrics.length > 1 ? metricLabel(metrics[1]) : '',
      nameTextStyle: { color: CHART_COLORS[1], fontSize: 11 },
      axisLabel: { color: CHART_COLORS[1] },
      splitLine: { show: false },
    },
    {
      type: 'value',
      name: metrics.length > 2 ? metricLabel(metrics[2]) : '',
      nameTextStyle: { color: CHART_COLORS[2], fontSize: 11 },
      axisLabel: { color: CHART_COLORS[2] },
      splitLine: { show: false },
      offset: 60,
    },
  ].slice(0, Math.min(metrics.length, 3))

  overviewChart.setOption({
    backgroundColor: '#1a1a2e',
    tooltip: { trigger: 'axis' },
    legend: {
      data: metrics.map((m: string) => metricLabel(m)),
      textStyle: { color: 'rgba(255,255,255,0.6)', fontSize: 12 },
      top: 0,
    },
    grid: { top: 40, right: 120, bottom: 30, left: 60 },
    xAxis: {
      type: 'category',
      data: xData,
      axisLabel: { color: 'rgba(255,255,255,0.6)' },
      axisLine: { lineStyle: { color: '#2a2a3e' } },
    },
    yAxis: yAxes,
    series,
  })
}
```

- [ ] **Step 7: 修改详情图 initDetailCharts 为动态指标渲染**

将 `initDetailCharts` 方法替换为：

```typescript
const initDetailCharts = () => {
  if (!result.value) return
  detailCharts.forEach(c => c.dispose())
  detailCharts.clear()

  for (const w of result.value.windows) {
    const el = detailChartRefs.value.get(w.n_segments)
    if (!el) continue

    const chart = echarts.init(el)
    detailCharts.set(w.n_segments, chart)

    const metrics = w.available_metrics || []
    const xData = w.segments.map((_: any, i: number) => `段${i + 1}`)

    const series = metrics.map((metric: string, idx: number) => ({
      name: metricLabel(metric),
      type: 'line',
      data: w.segments.map((seg: any) => (seg[metric] ?? 0).toFixed(4)),
      yAxisIndex: Math.min(idx, 1),
      itemStyle: { color: CHART_COLORS[idx % CHART_COLORS.length] },
      lineStyle: { width: 2 },
      symbol: 'circle',
      symbolSize: 6,
    }))

    chart.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      legend: {
        data: metrics.map((m: string) => metricLabel(m)),
        textStyle: { color: 'rgba(255,255,255,0.6)', fontSize: 11 },
        top: 0,
      },
      grid: { top: 36, right: 60, bottom: 24, left: 50 },
      xAxis: {
        type: 'category',
        data: xData,
        axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 11 },
        axisLine: { lineStyle: { color: '#2a2a3e' } },
      },
      yAxis: metrics.length > 1 ? [
        {
          type: 'value',
          name: metricLabel(metrics[0]),
          nameTextStyle: { color: CHART_COLORS[0], fontSize: 11 },
          axisLabel: { color: CHART_COLORS[0] },
          splitLine: { lineStyle: { color: '#2a2a3e' } },
        },
        {
          type: 'value',
          name: metricLabel(metrics[1]),
          nameTextStyle: { color: CHART_COLORS[1], fontSize: 11 },
          axisLabel: { color: CHART_COLORS[1] },
          splitLine: { show: false },
        },
      ] : [{
        type: 'value',
        splitLine: { lineStyle: { color: '#2a2a3e' } },
      }],
      series,
    })
  }
}
```

- [ ] **Step 8: 修改详情表格为动态列**

将模板中详情卡片的 `<table class="data-table">` 区块替换为：

```html
<table class="data-table">
  <thead>
    <tr>
      <th>段</th>
      <th v-for="metric in (w.available_metrics || [])" :key="metric">{{ metricLabel(metric) }}</th>
    </tr>
  </thead>
  <tbody>
    <tr v-for="(seg, i) in w.segments" :key="i">
      <td>{{ i + 1 }}</td>
      <td v-for="metric in (w.available_metrics || [])" :key="metric">
        {{ formatMetricValue(seg[metric]) }}
      </td>
    </tr>
  </tbody>
</table>
```

- [ ] **Step 9: 在 script 中添加 formatMetricValue 辅助方法**

在 `metricLabel` 函数之后添加：

```typescript
const formatMetricValue = (val: number | undefined) => {
  if (val === undefined || val === null) return '-'
  if (Math.abs(val) < 10) return val.toFixed(4)
  return val.toFixed(2)
}
```

- [ ] **Step 10: 添加指标选择器样式**

在 `<style scoped>` 中添加：

```css
.metric-count {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.35);
  margin-left: 8px;
  font-weight: 400;
}

.metric-placeholder {
  color: rgba(255, 255, 255, 0.35);
  font-size: 13px;
  padding: 6px 0;
}
```

- [ ] **Step 11: Commit**

```bash
cd /home/kaoru/Ginkgo && git add web-ui/src/views/portfolio/validation/SegmentStability.vue && git commit -m "feat: add dynamic metric selector and update charts for segment stability"
```

---

### Task 6: 浏览器验证

- [ ] **Step 1: 确认 API 服务和 Web UI 开发服务器运行中**

```bash
# API 日志
tail -5 /tmp/ginkgo-api.log

# Web UI 日志
tail -5 /tmp/webui.log
```

- [ ] **Step 2: 用 Playwright 验证完整流程**

1. 打开验证页面
2. 选择回测任务 → 确认指标 tag 选择器自动加载
3. 选择分段数 + 选择部分指标
4. 点击"开始分析" → 确认概览图和详情图正确渲染所选指标
5. 确认数据表格列动态匹配所选指标

- [ ] **Step 3: Vite 构建验证**

```bash
cd /home/kaoru/Ginkgo/web-ui && npx vite build 2>&1 | tail -5
```

- [ ] **Step 4: Commit and push**

```bash
cd /home/kaoru/Ginkgo && git push github master
```

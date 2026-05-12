# Portfolio 列表绩效展示 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在组合列表页卡片上直接展示绩效指标（年化收益/Sharpe/最大回撤/胜率）和关联组合摘要，无需点进详情页。

**Architecture:** 后端三层改动——aggregator 写回 Portfolio → service 新增 update_performance → API 返回指标+关联。前端卡片 body 替换为 2x2 绩效网格，底部增加关联摘要条。

**Tech Stack:** Python/FastAPI (后端), Vue 3 + TypeScript (前端), MySQL (MPortfolio), SQLAlchemy (ORM)

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `src/ginkgo/data/services/portfolio_service.py` | Modify | 新增 `update_performance()` 方法 |
| `src/ginkgo/trading/analysis/backtest_result_aggregator.py` | Modify | 回测完成时调用 `update_performance()` |
| `api/api/portfolio.py` | Modify | 列表 API 返回绩效指标 + 关联摘要 |
| `api/api/deployment.py` | Read | 参考部署 API 获取关联关系 |
| `web-ui/src/api/modules/portfolio.ts` | Modify | Portfolio 类型增加绩效+关联字段 |
| `web-ui/src/views/portfolio/PortfolioList.vue` | Modify | 卡片绩效网格 + 关联摘要条 |

---

### Task 1: PortfolioService 新增 update_performance 方法

**Files:**
- Modify: `src/ginkgo/data/services/portfolio_service.py`

- [ ] **Step 1: 在 PortfolioService 中新增 update_performance 方法**

在 `update()` 方法之后（约 line 280）添加：

```python
def update_performance(
    self,
    portfolio_id: str,
    annual_return: float = None,
    sharpe_ratio: float = None,
    max_drawdown: float = None,
    win_rate: float = None,
    total_trades: int = None,
    winning_trades: int = None,
) -> ServiceResult:
    """更新 Portfolio 绩效指标字段"""
    try:
        updates = {}
        if annual_return is not None:
            updates["total_profit"] = annual_return  # annual_return 存入 total_profit 字段
        if sharpe_ratio is not None:
            updates["sharpe_ratio"] = sharpe_ratio
        if max_drawdown is not None:
            updates["max_drawdown"] = max_drawdown
        if win_rate is not None:
            updates["win_rate"] = win_rate
        if total_trades is not None:
            updates["total_trades"] = total_trades
        if winning_trades is not None:
            updates["winning_trades"] = winning_trades

        if not updates:
            return ServiceResult.success(data=None, message="No fields to update")

        result = self._crud_repo.modify(uuid=portfolio_id, **updates)
        if result:
            return ServiceResult.success(data=result, message="Performance updated")
        return ServiceResult.error("Portfolio not found")
    except Exception as e:
        return ServiceResult.error(f"Failed to update performance: {e}")
```

注意：MPortfolio 模型没有 `annual_return` 字段，需检查是否需要新增字段或复用 `total_profit`。

- [ ] **Step 2: 确认 MPortfolio 模型是否有 annual_return 字段**

运行: `grep -n "annual_return" src/ginkgo/data/models/model_portfolio.py`

如果没有 `annual_return` 字段，需要在 model 中新增：

在 `model_portfolio.py` 的性能指标区域（`win_rate` 之后）添加：

```python
annual_return: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 4), default=0.00)
```

同时在该文件的 `update()` 方法的 `str` dispatch 中增加：

```python
if annual_return is not None:
    self.annual_return = annual_return
```

- [ ] **Step 3: 修正 update_performance 方法**

如果 Step 2 新增了 `annual_return` 字段，修正 Step 1 的方法，将 `annual_return` 直接写入对应字段而非 `total_profit`：

```python
if annual_return is not None:
    updates["annual_return"] = annual_return
```

- [ ] **Step 4: 运行数据库迁移**

由于新增了模型字段，需要重新 init 表：

```bash
ginkgo system config set --debug on
ginkgo data init
```

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/data/services/portfolio_service.py src/ginkgo/data/models/model_portfolio.py
git commit -m "feat: add update_performance to PortfolioService + annual_return field"
```

---

### Task 2: 回测完成时同步写 Portfolio

**Files:**
- Modify: `src/ginkgo/trading/analysis/backtest_result_aggregator.py`

- [ ] **Step 1: 在 aggregate_and_save 末尾添加 Portfolio 同步逻辑**

在 `aggregate_and_save` 方法中，`GLOG.INFO(f"Backtest results saved for task: {task_id}")` （约 line 143）之前插入：

```python
# 同步绩效指标到 MPortfolio
try:
    from ginkgo.data.containers import container as data_container
    portfolio_svc = data_container.services.portfolio()
    perf_result = portfolio_svc.update_performance(
        portfolio_id=portfolio_id,
        annual_return=metrics.get("annual_return", 0.0),
        sharpe_ratio=metrics.get("sharpe_ratio", 0.0),
        max_drawdown=metrics.get("max_drawdown", 0.0),
        win_rate=metrics.get("trade_win_rate", metrics.get("win_rate", 0.0)),
        total_trades=stats.get("total_orders", 0),
        winning_trades=None,  # 暂无 winning_trades 统计
    )
    if not perf_result.is_success():
        GLOG.WARN(f"Failed to sync performance to portfolio {portfolio_id}: {perf_result.error}")
except Exception as e:
    GLOG.WARN(f"Failed to sync performance to portfolio {portfolio_id}: {e}")
```

用 try/except 包裹，失败不影响主流程。

- [ ] **Step 2: Commit**

```bash
git add src/ginkgo/trading/analysis/backtest_result_aggregator.py
git commit -m "feat: sync backtest metrics to MPortfolio on completion"
```

---

### Task 3: API 列表接口返回绩效指标

**Files:**
- Modify: `api/api/portfolio.py`

- [ ] **Step 1: 导入依赖并新增辅助函数**

在 `api/api/portfolio.py` 顶部导入区域添加：

```python
from ginkgo.data.cruds.backtest_task_crud import BacktestTaskCRUD
from ginkgo.data.cruds.deployment_crud import DeploymentCRUD
```

在文件中添加辅助函数：

```python
def _get_latest_backtest_metrics(portfolio_id: str) -> dict:
    """获取 portfolio 最新已完成回测的绩效指标"""
    try:
        from ginkgo.data.containers import container
        task_crud = container.cruds.backtest_task()
        tasks = task_crud.find(
            filters={"portfolio_id": portfolio_id, "status": "completed"},
            order_by="create_at",
            desc_order=True,
            page_size=1,
        )
        if tasks and len(tasks) > 0:
            t = tasks[0]
            return {
                "annual_return": getattr(t, "annual_return", None),
                "sharpe_ratio": getattr(t, "sharpe_ratio", None),
                "max_drawdown": getattr(t, "max_drawdown", None),
                "win_rate": getattr(t, "win_rate", None),
                "backtest_count": 1,  # will be overwritten
                "last_backtest_date": t.create_at.isoformat() if hasattr(t, "create_at") else None,
            }
    except Exception:
        pass
    return {}


def _count_backtests(portfolio_id: str) -> int:
    """统计 portfolio 的回测次数"""
    try:
        from ginkgo.data.containers import container
        task_crud = container.cruds.backtest_task()
        return task_crud.count(filters={"portfolio_id": portfolio_id}) or 0
    except Exception:
        return 0


def _get_related_portfolios(portfolio_id: str, mode: int) -> list:
    """获取关联组合摘要"""
    try:
        from ginkgo.data.containers import container
        deployment_crud = container.cruds.deployment()
        related = []

        if mode == 0:  # BACKTEST: 查找部署出去的 PAPER/LIVE
            deployments = deployment_crud.find(filters={"source_portfolio_id": portfolio_id})
            if deployments:
                portfolio_svc = get_portfolio_service()
                for dep in deployments:
                    target_id = dep.target_portfolio_id
                    target_list = portfolio_svc.get(portfolio_id=target_id)
                    if target_list and target_list.data:
                        t = target_list.data[0]
                        related.append({
                            "uuid": t.uuid,
                            "name": t.name,
                            "mode": "PAPER" if t.mode == 1 else "LIVE",
                            "state": _map_state(t.state),
                            "annual_return": float(getattr(t, "annual_return", 0) or 0),
                            "max_drawdown": float(getattr(t, "max_drawdown", 0) or 0),
                        })
        else:  # PAPER/LIVE: 查找来源回测
            deployments = deployment_crud.find(filters={"target_portfolio_id": portfolio_id})
            if deployments:
                portfolio_svc = get_portfolio_service()
                source_id = deployments[0].source_portfolio_id
                source_list = portfolio_svc.get(portfolio_id=source_id)
                if source_list and source_list.data:
                    s = source_list.data[0]
                    # 获取回测指标
                    bt_metrics = _get_latest_backtest_metrics(source_id)
                    related.append({
                        "uuid": s.uuid,
                        "name": s.name,
                        "mode": "BACKTEST",
                        "state": _map_state(s.state),
                        "annual_return": bt_metrics.get("annual_return", 0),
                        "max_drawdown": bt_metrics.get("max_drawdown", 0),
                        "relation": "source",
                    })
                # 同组其他部署
                for dep in deployments:
                    if dep.target_portfolio_id != portfolio_id:
                        other_list = portfolio_svc.get(portfolio_id=dep.target_portfolio_id)
                        if other_list and other_list.data:
                            o = other_list.data[0]
                            if o.uuid != portfolio_id:
                                related.append({
                                    "uuid": o.uuid,
                                    "name": o.name,
                                    "mode": "PAPER" if o.mode == 1 else "LIVE",
                                    "state": _map_state(o.state),
                                    "annual_return": float(getattr(o, "annual_return", 0) or 0),
                                    "max_drawdown": float(getattr(o, "max_drawdown", 0) or 0),
                                })
        return related
    except Exception:
        return []
```

- [ ] **Step 2: 修改 list_portfolios 响应序列化**

在 `list_portfolios` 函数中，替换响应构建部分（约 lines 98-109）：

```python
portfolios_data = []
for p in result.data:
    mode_val = _map_mode(p.mode)
    mode_int = p.mode

    # 绩效指标
    metrics = {}
    if mode_int == 0:  # BACKTEST
        metrics = _get_latest_backtest_metrics(p.uuid)
        metrics["backtest_count"] = _count_backtests(p.uuid)
    else:  # PAPER/LIVE
        metrics = {
            "annual_return": float(getattr(p, "annual_return", 0) or 0),
            "sharpe_ratio": float(getattr(p, "sharpe_ratio", 0) or 0),
            "max_drawdown": float(getattr(p, "max_drawdown", 0) or 0),
            "win_rate": float(getattr(p, "win_rate", 0) or 0),
        }

    # 关联组合
    related = _get_related_portfolios(p.uuid, mode_int)

    portfolios_data.append({
        "uuid": p.uuid,
        "name": p.name,
        "mode": mode_val,
        "state": _map_state(p.state),
        "config_locked": _check_frozen(p.uuid),
        # 绩效指标
        "annual_return": metrics.get("annual_return"),
        "sharpe_ratio": metrics.get("sharpe_ratio"),
        "max_drawdown": metrics.get("max_drawdown"),
        "win_rate": metrics.get("win_rate"),
        # 元信息
        "backtest_count": metrics.get("backtest_count", 0),
        "last_backtest_date": metrics.get("last_backtest_date"),
        # 关联
        "related": related,
        "created_at": p.create_at.isoformat(),
    })
```

- [ ] **Step 3: 验证 API 响应**

启动 API 服务器并请求列表接口：

```bash
ginkgo serve api 2>&1 | tee /tmp/ginkgo-api.log &
curl -s http://localhost:8000/api/v1/portfolios/ | python -m json.tool | head -40
```

确认响应包含 `annual_return`、`sharpe_ratio`、`max_drawdown`、`win_rate`、`related` 字段。

- [ ] **Step 4: Commit**

```bash
git add api/api/portfolio.py
git commit -m "feat: return performance metrics and related portfolios in list API"
```

---

### Task 4: 前端 Portfolio 类型更新

**Files:**
- Modify: `web-ui/src/api/modules/portfolio.ts`

- [ ] **Step 1: 更新 Portfolio 接口**

在 `portfolio.ts` 的 `Portfolio` 接口中增加字段：

```typescript
export interface RelatedPortfolio {
  uuid: string
  name: string
  mode: string
  state: string
  annual_return?: number | null
  max_drawdown?: number | null
  relation?: string
}

export interface Portfolio {
  uuid: string
  name: string
  desc?: string
  mode: number | string
  state: number | string
  initial_cash?: number
  current_cash?: number
  net_value?: number
  config_locked?: boolean
  // 绩效指标
  annual_return?: number | null
  sharpe_ratio?: number | null
  max_drawdown?: number | null
  win_rate?: number | null
  // 元信息
  backtest_count?: number
  last_backtest_date?: string | null
  // 关联组合
  related?: RelatedPortfolio[]
  // 原有字段
  positions?: any
  risk_alerts?: any
  components?: any
  created_at?: string
  updated_at?: string
}
```

- [ ] **Step 2: Commit**

```bash
git add web-ui/src/api/modules/portfolio.ts
git commit -m "feat: add performance metrics types to Portfolio interface"
```

---

### Task 5: 前端卡片绩效网格 + 关联摘要条

**Files:**
- Modify: `web-ui/src/views/portfolio/PortfolioList.vue`

- [ ] **Step 1: 替换卡片 body 为绩效网格**

将 `<div class="card-body">` 区域（约 lines 116-129）替换为：

```html
<div class="card-body">
  <div class="metrics-grid">
    <div class="metric">
      <span class="label">{{ getReturnLabel(portfolio.mode) }}</span>
      <span class="value" :class="getValueClass(portfolio.annual_return)">
        {{ formatPercent(portfolio.annual_return) }}
      </span>
    </div>
    <div class="metric">
      <span class="label">Sharpe</span>
      <span class="value" :class="getSharpeClass(portfolio.sharpe_ratio)">
        {{ formatDecimal(portfolio.sharpe_ratio) }}
      </span>
    </div>
    <div class="metric">
      <span class="label">最大回撤</span>
      <span class="value negative">
        {{ formatDrawdown(portfolio.max_drawdown) }}
      </span>
    </div>
    <div class="metric">
      <span class="label">胜率</span>
      <span class="value" :class="getWinRateClass(portfolio.win_rate)">
        {{ formatPercent(portfolio.win_rate) }}
      </span>
    </div>
  </div>
</div>
```

- [ ] **Step 2: 替换卡片 footer 并增加关联摘要条**

将 `<div class="card-footer">` 区域（约 lines 130-138）替换为：

```html
<!-- 底部信息栏 -->
<div class="card-footer">
  <span class="footer-tag" :class="`tag-${getModeColorClass(portfolio.mode)}`">
    {{ formatMode(portfolio.mode) }}
  </span>
  <span class="footer-tag" :class="`tag-${getStateColorClass(portfolio.state)}`">
    {{ formatState(portfolio.state) }}
  </span>
  <span class="date">{{ formatShortDate(portfolio.created_at) }}</span>
</div>
<!-- 关联摘要条 -->
<div v-if="portfolio.related && portfolio.related.length > 0" class="related-bar">
  <div
    v-for="rel in portfolio.related"
    :key="rel.uuid"
    class="related-card"
    :class="`related-${rel.mode.toLowerCase()}`"
    @click.stop="viewDetail({ uuid: rel.uuid })"
  >
    <div class="related-header">
      <span class="related-mode">{{ formatRelatedMode(rel.mode) }}</span>
      <span v-if="rel.state" class="related-state">{{ rel.state }}</span>
    </div>
    <div class="related-metrics">
      <span>收益 <strong :class="getValueClass(rel.annual_return)">{{ formatPercent(rel.annual_return) }}</strong></span>
      <span>回撤 <strong class="negative">{{ formatDrawdown(rel.max_drawdown) }}</strong></span>
    </div>
  </div>
</div>
```

- [ ] **Step 3: 添加格式化辅助函数**

在 `<script setup>` 中添加：

```typescript
const getReturnLabel = (mode: any) => {
  const m = typeof mode === 'string' ? mode.toUpperCase() : mode
  return m === 'BACKTEST' || m === 0 ? '年化收益' : '累计收益'
}

const formatPercent = (val: any) => {
  if (val === null || val === undefined || val === 0) return '--'
  const n = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(n)) return '--'
  const sign = n > 0 ? '+' : ''
  return `${sign}${(n * 100).toFixed(2)}%`
}

const formatDecimal = (val: any) => {
  if (val === null || val === undefined || val === 0) return '--'
  const n = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(n)) return '--'
  return n.toFixed(2)
}

const formatDrawdown = (val: any) => {
  if (val === null || val === undefined || val === 0) return '--'
  const n = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(n)) return '--'
  return `-${(Math.abs(n) * 100).toFixed(1)}%`
}

const getValueClass = (val: any) => {
  if (val === null || val === undefined) return 'neutral'
  const n = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(n) || n === 0) return 'neutral'
  return n > 0 ? 'positive' : 'negative'
}

const getSharpeClass = (val: any) => {
  if (val === null || val === undefined) return 'neutral'
  const n = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(n) || n === 0) return 'neutral'
  if (n < 0.5) return 'warning'
  return n > 0 ? 'positive' : 'negative'
}

const getWinRateClass = (val: any) => {
  if (val === null || val === undefined) return 'neutral'
  const n = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(n) || n === 0) return 'neutral'
  return n >= 0.5 ? 'positive' : 'warning'
}

const formatRelatedMode = (mode: string) => {
  const map: Record<string, string> = {
    'BACKTEST': '来源回测',
    'PAPER': '模拟',
    'LIVE': '实盘',
  }
  return map[mode] || mode
}
```

注意：检查后端返回的 `annual_return` 等值是小数（0.1617）还是百分比（16.17）。如果是小数，`formatPercent` 需要乘 100（如上代码）。如果是百分比数值，去掉 `* 100`。

- [ ] **Step 4: 添加 CSS 样式**

在 `<style scoped>` 中添加：

```css
.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 16px;
  padding: 10px;
  background: var(--bg-card-inner, #12122a);
  border-radius: 6px;
}

.metrics-grid .metric .label {
  font-size: 10px;
  color: #888;
}

.metrics-grid .metric .value {
  font-size: 16px;
  font-weight: 700;
}

.value.positive { color: #4caf50; }
.value.negative { color: #f44336; }
.value.warning { color: #ff9800; }
.value.neutral { color: #555; }

/* 关联摘要条 */
.related-bar {
  display: flex;
  gap: 8px;
  padding: 10px 0 0;
  border-top: 1px solid #252540;
  margin-top: 10px;
}

.related-card {
  flex: 1;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.related-card:hover { opacity: 0.8; }

.related-backtest {
  background: #0f0f2a;
  border: 1px solid #20203a;
}

.related-paper {
  background: #1e1e0a;
  border: 1px solid #3a3520;
}

.related-live {
  background: #0a1e1a;
  border: 1px solid #203a2a;
}

.related-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.related-mode { font-size: 10px; font-weight: 600; }
.related-backtest .related-mode { color: #7c8aff; }
.related-paper .related-mode { color: #ff9800; }
.related-live .related-mode { color: #4caf50; }

.related-state { font-size: 9px; color: #4caf50; }

.related-metrics {
  display: flex;
  gap: 10px;
  font-size: 9px;
  color: #888;
}

.related-metrics strong { font-size: 11px; }
```

- [ ] **Step 5: 验证前端效果**

启动 WebUI 开发服务器，在浏览器中查看组合列表页：

```bash
ginkgo serve webui 2>&1 | tee /tmp/webui.log &
```

确认：
1. 绩效指标 2x2 网格正确显示
2. 无数据时显示灰色 `--`
3. 关联摘要条正确显示（有 deploy 关系的卡片）
4. Mode 颜色区分正确
5. 摘要条可点击跳转

- [ ] **Step 6: Commit**

```bash
git add web-ui/src/views/portfolio/PortfolioList.vue web-ui/src/api/modules/portfolio.ts
git commit -m "feat: portfolio list card with performance metrics and related summary"
```

---

### Task 6: 集成验证

- [ ] **Step 1: 端到端验证**

1. 运行一次回测，确认 `MPortfolio` 的绩效字段被更新：
```bash
# 用 ginkgo CLI 运行回测
ginkgo backtest run <backtest_id>
# 检查数据库
python -c "
from ginkgo.data.containers import container
svc = container.services.portfolio()
r = svc.get(portfolio_id='<portfolio_uuid>')
p = r.data[0]
print(f'annual_return={p.annual_return}, sharpe={p.sharpe_ratio}, drawdown={p.max_drawdown}, win_rate={p.win_rate}')
"
```

2. 打开 WebUI 组合列表页，确认回测组合卡片显示绩效指标

3. 如有 deploy 关系，确认关联摘要条显示正确

- [ ] **Step 2: 最终 Commit & Push**

```bash
git push all master
```

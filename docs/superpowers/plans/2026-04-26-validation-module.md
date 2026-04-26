# Validation Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement segment stability and Monte Carlo validation for backtest results, exposed via API and WebUI.

**Architecture:** ValidationService calculates metrics from existing analyzer_record data (no re-run needed). API routes call the service, frontend components display results in the ValidationTab sub-tabs.

**Tech Stack:** Python (numpy), FastAPI, Vue 3 + TypeScript

---

## File Structure

```
src/ginkgo/data/
├── services/
│   └── validation_service.py         [新] 计算逻辑（分段稳定性、蒙特卡洛）
└── containers.py                     [改] 注册 ValidationService

api/
├── api/
│   └── validation.py                 [新] API 路由
└── main.py                           [改] 注册 router

tests/
├── unit/
│   └── test_validation_service.py    [新] 单元测试
└── api/
    └── test_validation_api.py        [新] API 测试

web-ui/src/
├── api/modules/
│   └── validation.ts                 [改] 补充分段稳定性接口
└── views/
    └── portfolio/
        ├── tabs/
        │   └── ValidationTab.vue     [改] 增加分段稳定性子标签，更新导入路径
        └── validation/               [新] 验证组件目录
            └── SegmentStability.vue  [新] 分段稳定性组件
```

**图例:** [新]=新增  [改]=修改

---

### Task 1: ValidationService - segment_stability 方法

**Files:**
- Create: `src/ginkgo/data/services/validation_service.py`
- Create: `tests/unit/test_validation_service.py`

- [ ] **Step 1: 写分段计算测试**

```python
# tests/unit/test_validation_service.py
import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


def _make_net_value_records(start_date, daily_returns, portfolio_id="pf-001", task_id="task-001"):
    """辅助函数：构造 net_value 模拟记录列表"""
    records = []
    value = 1.0
    dt = datetime.strptime(start_date, "%Y-%m-%d")
    for r in daily_returns:
        value *= (1 + r)
        rec = MagicMock()
        rec.value = value
        rec.business_timestamp = dt
        rec.portfolio_id = portfolio_id
        rec.task_id = task_id
        rec.name = "net_value"
        records.append(rec)
        dt += timedelta(days=1)
    return records


class TestSegmentStability:
    def test_split_into_equal_segments(self):
        """242 个交易日分成 4 段，每段应约 60~61 天"""
        from ginkgo.data.services.validation_service import ValidationService
        svc = ValidationService.__new__(ValidationService)
        returns = np.array([0.01] * 242)
        segments = svc._split_returns(returns, 4)
        assert len(segments) == 4
        # 每段长度之和等于总长度
        assert sum(len(s) for s in segments) == 242

    def test_stability_score_high_when_consistent(self):
        """各段收益一致时，稳定性评分应接近 1"""
        from ginkgo.data.services.validation_service import ValidationService
        svc = ValidationService.__new__(ValidationService)
        # 每段收益都是 +1%
        segment_returns = [0.01, 0.01, 0.01, 0.01]
        score = svc._calc_stability_score(segment_returns)
        assert score > 0.99

    def test_stability_score_low_when_inconsistent(self):
        """各段收益差异大时，稳定性评分应较低"""
        from ginkgo.data.services.validation_service import ValidationService
        svc = ValidationService.__new__(ValidationService)
        segment_returns = [0.08, 0.02, -0.03, 0.01]
        score = svc._calc_stability_score(segment_returns)
        assert score < 0.6

    def test_stability_score_zero_when_near_zero_returns(self):
        """平均绝对收益 < 0.001 时返回 0"""
        from ginkgo.data.services.validation_service import ValidationService
        svc = ValidationService.__new__(ValidationService)
        segment_returns = [0.0001, -0.0001, 0.0002, -0.0001]
        score = svc._calc_stability_score(segment_returns)
        assert score == 0

    def test_segment_metrics(self):
        """计算单段的收益、夏普、最大回撤"""
        from ginkgo.data.services.validation_service import ValidationService
        svc = ValidationService.__new__(ValidationService)
        # 5天，每天 +1%
        daily_returns = np.array([0.01, 0.01, 0.01, 0.01, 0.01])
        metrics = svc._calc_segment_metrics(daily_returns)
        assert metrics["total_return"] > 0.04  # ~5.1%
        assert metrics["sharpe"] is not None
        assert metrics["max_drawdown"] >= 0  # 回撤是正值表示亏损幅度
        assert metrics["win_rate"] == 1.0  # 全部正收益

    @patch("ginkgo.data.services.validation_service.ValidationService._get_net_value_records")
    def test_segment_stability_multi_window(self, mock_get_records):
        """多窗口分段稳定性端到端测试"""
        from ginkgo.data.services.validation_service import ValidationService
        # 构造 120 天净值为缓慢上涨的数据
        daily_returns = [0.002] * 120
        records = _make_net_value_records("2024-01-02", daily_returns, task_id="test-task")
        mock_get_records.return_value = records

        svc = ValidationService.__new__(ValidationService)
        result = svc.segment_stability(task_id="test-task", portfolio_id="pf-001", n_segments_list=[2, 4])

        assert result.is_success()
        data = result.data
        assert len(data["windows"]) == 2
        assert data["windows"][0]["n_segments"] == 2
        assert data["windows"][1]["n_segments"] == 4
        # 一致上涨的数据稳定性应较高
        for w in data["windows"]:
            assert w["stability_score"] > 0.5
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/unit/test_validation_service.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: 实现 ValidationService**

```python
# src/ginkgo/data/services/validation_service.py
# Upstream: API Server (validation routes)
# Downstream: BaseService, AnalyzerRecordCRUD
# Role: 回测验证计算服务（分段稳定性、蒙特卡洛模拟）

import numpy as np
from typing import List, Optional
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.libs import GLOG


class ValidationService(BaseService):
    """回测验证服务：基于已有 analyzer_record 数据计算验证指标"""

    def __init__(self, analyzer_record_crud=None):
        super().__init__(crud_repo=analyzer_record_crud)
        self._analyzer_crud = analyzer_record_crud

    def _get_net_value_records(self, task_id: str, portfolio_id: str):
        """获取指定任务的 net_value 记录，按 business_timestamp 升序"""
        records = self._analyzer_crud.get_by_task_id(
            task_id=task_id,
            portfolio_id=portfolio_id,
            analyzer_name="net_value",
            page_size=10000,
        )
        # 记录默认按 timestamp 降序，反转为升序
        return list(reversed(records))

    @staticmethod
    def _records_to_returns(records) -> np.ndarray:
        """将 net_value 记录转为日收益率数组"""
        values = np.array([float(r.value) for r in records])
        return np.diff(values) / values[:-1]

    @staticmethod
    def _split_returns(returns: np.ndarray, n_segments: int) -> List[np.ndarray]:
        """将收益率数组等分为 n_segments 段"""
        length = len(returns)
        base_size = length // n_segments
        remainder = length % n_segments
        segments = []
        start = 0
        for i in range(n_segments):
            size = base_size + (1 if i < remainder else 0)
            segments.append(returns[start:start + size])
            start += size
        return segments

    @staticmethod
    def _calc_segment_metrics(daily_returns: np.ndarray) -> dict:
        """计算单段的关键指标"""
        if len(daily_returns) == 0:
            return {"total_return": 0, "sharpe": 0, "max_drawdown": 0, "win_rate": 0}

        # 累计收益
        cumulative = np.cumprod(1 + daily_returns)
        total_return = cumulative[-1] - 1

        # 夏普比率（年化）
        std = np.std(daily_returns)
        if std == 0:
            sharpe = 0.0
        else:
            sharpe = float(np.mean(daily_returns) / std * np.sqrt(252))

        # 最大回撤
        peak = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - peak) / peak
        max_drawdown = float(-np.min(drawdown)) if len(drawdown) > 0 else 0.0

        # 胜率
        win_rate = float(np.sum(daily_returns > 0) / len(daily_returns))

        return {
            "total_return": round(float(total_return), 6),
            "sharpe": round(sharpe, 4),
            "max_drawdown": round(max_drawdown, 6),
            "win_rate": round(win_rate, 4),
        }

    @staticmethod
    def _calc_stability_score(segment_returns: List[float]) -> float:
        """计算稳定性评分，含阈值保护"""
        mean_abs = np.mean(np.abs(segment_returns))
        if mean_abs < 0.001:
            return 0.0
        score = 1.0 - float(np.std(segment_returns) / mean_abs)
        return max(0.0, round(score, 4))

    def segment_stability(
        self,
        task_id: str,
        portfolio_id: str,
        n_segments_list: Optional[List[int]] = None,
    ) -> ServiceResult:
        """分段稳定性验证"""
        if n_segments_list is None:
            n_segments_list = [2, 4, 8]

        try:
            records = self._get_net_value_records(task_id, portfolio_id)
            if len(records) < 10:
                return ServiceResult.error("数据不足：net_value 记录少于 10 条")

            returns = self._records_to_returns(records)

            windows = []
            for n in n_segments_list:
                if n > len(returns):
                    continue
                segments = self._split_returns(returns, n)
                seg_metrics = [self._calc_segment_metrics(s) for s in segments]
                seg_returns = [m["total_return"] for m in seg_metrics]
                stability_score = self._calc_stability_score(seg_returns)

                windows.append({
                    "n_segments": n,
                    "segments": seg_metrics,
                    "stability_score": stability_score,
                })

            if not windows:
                return ServiceResult.error("分段数均大于数据长度，无法计算")

            return ServiceResult.success(data={"windows": windows})

        except Exception as e:
            GLOG.ERROR(f"分段稳定性计算失败: {e}")
            return ServiceResult.error(f"计算失败: {e}")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/unit/test_validation_service.py -v`
Expected: 6 passed

- [ ] **Step 5: 提交**

```bash
git add src/ginkgo/data/services/validation_service.py tests/unit/test_validation_service.py
git commit -m "feat: add ValidationService with segment_stability method"
```

---

### Task 2: ValidationService - monte_carlo 方法

**Files:**
- Modify: `src/ginkgo/data/services/validation_service.py`
- Modify: `tests/unit/test_validation_service.py`

- [ ] **Step 1: 写蒙特卡洛测试**

追加到 `tests/unit/test_validation_service.py`：

```python
class TestMonteCarlo:
    @patch("ginkgo.data.services.validation_service.ValidationService._get_net_value_records")
    def test_monte_carlo_basic(self, mock_get_records):
        """蒙特卡洛模拟基本流程"""
        from ginkgo.data.services.validation_service import ValidationService
        # 构造 100 天数据
        daily_returns = [0.005] * 50 + [-0.003] * 50
        records = _make_net_value_records("2024-01-02", daily_returns, task_id="test-task")
        mock_get_records.return_value = records

        svc = ValidationService.__new__(ValidationService)
        result = svc.monte_carlo(
            task_id="test-task",
            portfolio_id="pf-001",
            n_simulations=1000,
            confidence=0.95,
        )

        assert result.is_success()
        data = result.data
        assert "var" in data
        assert "cvar" in data
        assert "actual_return" in data
        assert "percentile" in data
        assert "loss_probability" in data
        assert 0 <= data["percentile"] <= 100
        assert data["loss_probability"] >= 0

    def test_monte_carlo_var_cvar(self):
        """VaR 应小于 CVaR（绝对值）"""
        from ginkgo.data.services.validation_service import ValidationService
        svc = ValidationService.__new__(ValidationService)
        np.random.seed(42)
        simulated_returns = np.random.normal(0.001, 0.02, 10000)
        actual_return = 0.05
        result = svc._calc_monte_carlo_stats(simulated_returns, actual_return, 0.95)
        # CVaR 是尾部均值，损失应 >= VaR
        assert result["cvar"] <= result["var"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/unit/test_validation_service.py::TestMonteCarlo -v`
Expected: FAIL (AttributeError: no monte_carlo method)

- [ ] **Step 3: 实现 monte_carlo 方法**

追加到 `src/ginkgo/data/services/validation_service.py` 的 `ValidationService` 类中：

```python
    @staticmethod
    def _calc_monte_carlo_stats(
        simulated_returns: np.ndarray,
        actual_return: float,
        confidence: float,
    ) -> dict:
        """从模拟收益分布计算统计指标"""
        sorted_returns = np.sort(simulated_returns)
        n = len(sorted_returns)

        # VaR: 置信水平对应的分位数
        var_idx = int(n * (1 - confidence))
        var = float(sorted_returns[var_idx])

        # CVaR: 尾部均值
        cvar = float(np.mean(sorted_returns[:var_idx + 1]))

        # 损失概率
        loss_probability = float(np.sum(simulated_returns < 0) / n)

        # 实际收益在模拟分布中的百分位
        percentile = float(np.searchsorted(sorted_returns, actual_return) / n * 100)

        return {
            "var": round(var, 6),
            "cvar": round(cvar, 6),
            "loss_probability": round(loss_probability, 4),
            "percentile": round(percentile, 2),
        }

    def monte_carlo(
        self,
        task_id: str,
        portfolio_id: str,
        n_simulations: int = 10000,
        confidence: float = 0.95,
    ) -> ServiceResult:
        """蒙特卡洛模拟验证"""
        try:
            records = self._get_net_value_records(task_id, portfolio_id)
            if len(records) < 10:
                return ServiceResult.error("数据不足：net_value 记录少于 10 条")

            returns = self._records_to_returns(records)
            actual_return = float(np.prod(1 + returns) - 1)

            # Bootstrap：有放回抽样
            n_days = len(returns)
            simulated_returns = np.empty(n_simulations)
            for i in range(n_simulations):
                sampled = np.random.choice(returns, size=n_days, replace=True)
                simulated_returns[i] = float(np.prod(1 + sampled) - 1)

            stats = self._calc_monte_carlo_stats(simulated_returns, actual_return, confidence)
            stats["actual_return"] = round(actual_return, 6)
            stats["n_simulations"] = n_simulations

            # 分布直方图数据（分桶）
            hist, bin_edges = np.histogram(simulated_returns, bins=50)
            stats["distribution"] = {
                "counts": hist.tolist(),
                "bins": [round(float(b), 6) for b in bin_edges.tolist()],
            }

            return ServiceResult.success(data=stats)

        except Exception as e:
            GLOG.ERROR(f"蒙特卡洛模拟失败: {e}")
            return ServiceResult.error(f"模拟失败: {e}")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/unit/test_validation_service.py -v`
Expected: 8 passed

- [ ] **Step 5: 提交**

```bash
git add src/ginkgo/data/services/validation_service.py tests/unit/test_validation_service.py
git commit -m "feat: add monte_carlo method to ValidationService"
```

---

### Task 3: 注册 ValidationService 到容器

**Files:**
- Modify: `src/ginkgo/data/containers.py`

- [ ] **Step 1: 在 containers.py 中注册**

在 `containers.py` 的 import 区域添加：

```python
from ginkgo.data.services.validation_service import ValidationService
```

在 Container 类的 service 注册区域添加：

```python
    validation_service = providers.Singleton(
        ValidationService,
        analyzer_record_crud=providers.Singleton(get_crud, "analyzer_record"),
    )
```

- [ ] **Step 2: 验证导入**

Run: `python -c "from ginkgo.data.containers import container; svc = container.validation_service(); print(type(svc))"`
Expected: `<class 'ginkgo.data.services.validation_service.ValidationService'>`

- [ ] **Step 3: 提交**

```bash
git add src/ginkgo/data/containers.py
git commit -m "feat: register ValidationService in DI container"
```

---

### Task 4: 创建 API 路由

**Files:**
- Create: `api/api/validation.py`
- Modify: `api/main.py`

- [ ] **Step 1: 创建 validation.py**

```python
# api/api/validation.py
from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel, Field

from core.logging import logger
from core.response import ok
from core.exceptions import BusinessError


router = APIRouter()


class SegmentStabilityRequest(BaseModel):
    task_id: str = Field(..., description="回测任务 UUID")
    portfolio_id: str = Field(..., description="组合 UUID")
    n_segments: Optional[List[int]] = Field(default=[2, 4, 8], description="分段数列表")


class MonteCarloRequest(BaseModel):
    task_id: str = Field(..., description="回测任务 UUID")
    portfolio_id: str = Field(..., description="组合 UUID")
    n_simulations: int = Field(default=10000, ge=100, le=100000, description="模拟次数")
    confidence: float = Field(default=0.95, ge=0.8, le=0.99, description="置信水平")


def get_validation_service():
    from ginkgo.data.containers import container
    return container.validation_service()


@router.post("/segment-stability")
async def segment_stability(req: SegmentStabilityRequest):
    try:
        svc = get_validation_service()
        result = svc.segment_stability(
            task_id=req.task_id,
            portfolio_id=req.portfolio_id,
            n_segments_list=req.n_segments,
        )
        if not result.is_success():
            raise BusinessError(result.error)
        return ok(data=result.data)
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"分段稳定性接口异常: {e}")
        raise BusinessError(f"分段稳定性计算失败: {e}")


@router.post("/monte-carlo")
async def monte_carlo(req: MonteCarloRequest):
    try:
        svc = get_validation_service()
        result = svc.monte_carlo(
            task_id=req.task_id,
            portfolio_id=req.portfolio_id,
            n_simulations=req.n_simulations,
            confidence=req.confidence,
        )
        if not result.is_success():
            raise BusinessError(result.error)
        return ok(data=result.data)
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"蒙特卡洛接口异常: {e}")
        raise BusinessError(f"蒙特卡洛模拟失败: {e}")
```

- [ ] **Step 2: 在 main.py 中注册路由**

在 `api/main.py` 的 import 区域添加：

```python
from api import validation
```

在 router 注册区域添加：

```python
app.include_router(validation.router, prefix=f"{API_PREFIX}/validation", tags=["validation"])
```

- [ ] **Step 3: 验证 API 启动**

Run: `python -c "from api.main import app; print([r.path for r in app.routes if 'validation' in str(r.path)])"`
Expected: 包含 `/api/v1/validation/segment-stability` 和 `/api/v1/validation/monte-carlo`

- [ ] **Step 4: 提交**

```bash
git add api/api/validation.py api/main.py
git commit -m "feat: add validation API routes for segment stability and monte carlo"
```

---

### Task 5: 前端 API 模块更新

**Files:**
- Modify: `web-ui/src/api/modules/validation.ts`

- [ ] **Step 1: 更新 validation.ts**

在现有文件中补充分段稳定性接口定义和方法：

```typescript
// 在接口定义区域追加
export interface SegmentStabilityConfig {
  task_id: string
  portfolio_id: string
  n_segments?: number[]  // 默认 [2, 4, 8]
}

export interface SegmentStabilityResult {
  windows: {
    n_segments: number
    segments: {
      total_return: number
      sharpe: number
      max_drawdown: number
      win_rate: number
    }[]
    stability_score: number
  }[]
}

// 在 validationApi 对象中追加方法
segmentStability(config: SegmentStabilityConfig): Promise<SegmentStabilityResult> {
  return request.post('/api/v1/validation/segment-stability', {
    task_id: config.task_id,
    portfolio_id: config.portfolio_id,
    n_segments: config.n_segments || [2, 4, 8],
  })
},
```

同时更新现有的 `monteCarlo` 方法使其调用新的后端端点：

```typescript
monteCarlo(config: MonteCarloConfig): Promise<MonteCarloResult> {
  return request.post('/api/v1/validation/monte-carlo', {
    task_id: config.backtest_id,
    portfolio_id: config.portfolio_id,
    n_simulations: config.n_simulations || 10000,
    confidence: config.confidence || 0.95,
  })
},
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd web-ui && npx tsc --noEmit src/api/modules/validation.ts 2>&1 | head -5`
Expected: 无错误

- [ ] **Step 3: 提交**

```bash
git add web-ui/src/api/modules/validation.ts
git commit -m "feat: add segment stability API method to validation.ts"
```

---

### Task 6: SegmentStability.vue 组件

**Files:**
- Create: `web-ui/src/views/portfolio/validation/SegmentStability.vue`

- [ ] **Step 1: 创建组件**

```vue
<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">
        <span class="tag tag-green">验证</span>
        分段稳定性
      </h1>
      <p class="page-description">将回测区间等分为多段，对比各段表现是否一致</p>
    </div>

    <div class="card">
      <div class="card-header"><h3>分析配置</h3></div>
      <div class="card-body">
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">回测任务</label>
            <select class="form-select" v-model="config.taskId">
              <option value="">请选择任务</option>
              <option v-for="t in backtestList" :key="t.uuid" :value="t.uuid">
                {{ t.name || t.uuid?.slice(0, 8) }} ({{ t.status }})
              </option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">分段数</label>
            <input class="form-input" v-model="segmentsInput" placeholder="2, 4, 8" />
          </div>
          <div class="form-group" style="align-self: flex-end;">
            <button class="btn-primary" :disabled="loading || !config.taskId" @click="runAnalysis">
              {{ loading ? '分析中...' : '开始分析' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <template v-if="result">
      <div class="stats-grid">
        <div class="stat-card" v-for="w in result.windows" :key="w.n_segments">
          <div class="stat-value">{{ w.n_segments }} 段</div>
          <div class="stat-label">稳定性评分</div>
          <div class="stat-value" :class="scoreClass(w.stability_score)">
            {{ (w.stability_score * 100).toFixed(1) }}%
          </div>
        </div>
      </div>

      <div class="card" v-for="w in result.windows" :key="'detail-' + w.n_segments">
        <div class="card-header">
          <h3>{{ w.n_segments }} 段分析</h3>
          <span :class="scoreClass(w.stability_score)">评分 {{ (w.stability_score * 100).toFixed(1) }}%</span>
        </div>
        <div class="card-body">
          <table class="data-table">
            <thead>
              <tr>
                <th>段</th>
                <th>收益</th>
                <th>夏普</th>
                <th>最大回撤</th>
                <th>胜率</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(seg, i) in w.segments" :key="i">
                <td>{{ i + 1 }}</td>
                <td :class="seg.total_return >= 0 ? 'stat-success' : 'stat-danger'">
                  {{ (seg.total_return * 100).toFixed(2) }}%
                </td>
                <td>{{ seg.sharpe.toFixed(2) }}</td>
                <td class="stat-danger">{{ (seg.max_drawdown * 100).toFixed(2) }}%</td>
                <td>{{ (seg.win_rate * 100).toFixed(1) }}%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <div v-else-if="!loading" class="card">
      <div class="empty-state">选择回测任务并点击分析</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { validationApi } from '@/api/modules/validation'
import { backtestApi } from '@/api/modules/backtest'

const loading = ref(false)
const result = ref<any>(null)
const backtestList = ref<any[]>([])
const segmentsInput = ref('2, 4, 8')
const config = reactive({
  taskId: '',
  portfolioId: '',
})

const scoreClass = (score: number) => {
  if (score >= 0.7) return 'stat-success'
  if (score >= 0.4) return 'stat-warning'
  return 'stat-danger'
}

const runAnalysis = async () => {
  if (!config.taskId) return
  loading.value = true
  result.value = null
  try {
    const segments = segmentsInput.value.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n))
    const task = backtestList.value.find(t => t.uuid === config.taskId)
    const portfolioId = task?.portfolio_id || config.portfolioId
    const res = await validationApi.segmentStability({
      task_id: config.taskId,
      portfolio_id: portfolioId,
      n_segments: segments.length ? segments : undefined,
    })
    result.value = res.data
  } catch (e: any) {
    alert('分析失败: ' + (e.message || e))
  } finally {
    loading.value = false
  }
}

const fetchBacktestList = async () => {
  try {
    const res = await backtestApi.getList({ page: 1, page_size: 50, status: 'completed' })
    backtestList.value = res.data?.items || []
  } catch { /* ignore */ }
}

onMounted(() => { fetchBacktestList() })
</script>

<style scoped>
.stat-warning { color: #eab308; }
.stat-success { color: #22c55e; }
.stat-danger { color: #ef4444; }
</style>
```

- [ ] **Step 2: 提交**

```bash
git add web-ui/src/views/portfolio/validation/SegmentStability.vue
git commit -m "feat: add SegmentStability.vue component"
```

---

### Task 7: 更新 ValidationTab.vue + 迁移 MonteCarlo

**Files:**
- Move: `web-ui/src/views/stage2/MonteCarlo.vue` → `web-ui/src/views/portfolio/validation/MonteCarlo.vue`
- Modify: `web-ui/src/views/portfolio/tabs/ValidationTab.vue`

- [ ] **Step 1: 迁移 MonteCarlo.vue**

```bash
mkdir -p web-ui/src/views/portfolio/validation
cp web-ui/src/views/stage2/MonteCarlo.vue web-ui/src/views/portfolio/validation/MonteCarlo.vue
```

注意：stage2/MonteCarlo.vue 暂时保留（避免破坏其他可能的引用），后续统一清理。

- [ ] **Step 2: 更新 ValidationTab.vue**

```vue
<template>
  <div class="validation-tab">
    <div class="sub-tab-bar">
      <button
        v-for="sub in subTabs"
        :key="sub.key"
        class="sub-tab-item"
        :class="{ active: activeSub === sub.key }"
        @click="activeSub = sub.key"
      >
        {{ sub.label }}
      </button>
    </div>

    <div class="sub-tab-content">
      <SegmentStability v-if="activeSub === 'segment'" />
      <MonteCarlo v-else-if="activeSub === 'montecarlo'" />
      <WalkForward v-else-if="activeSub === 'walkforward'" />
      <Sensitivity v-else-if="activeSub === 'sensitivity'" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import SegmentStability from '@/views/portfolio/validation/SegmentStability.vue'
import MonteCarlo from '@/views/portfolio/validation/MonteCarlo.vue'
import WalkForward from '@/views/stage2/WalkForward.vue'
import Sensitivity from '@/views/stage2/Sensitivity.vue'

const activeSub = ref('segment')

const subTabs = [
  { key: 'segment', label: '分段稳定性' },
  { key: 'montecarlo', label: '蒙特卡洛' },
  { key: 'walkforward', label: 'Walk Forward' },
  { key: 'sensitivity', label: '敏感性分析' },
]
</script>

<style scoped>
.validation-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sub-tab-bar {
  display: flex;
  gap: 0;
  border-bottom: 1px solid #2a2a3e;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.sub-tab-item {
  padding: 8px 16px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.sub-tab-item:hover {
  color: rgba(255, 255, 255, 0.8);
}

.sub-tab-item.active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
  font-weight: 600;
}

.sub-tab-content {
  flex: 1;
  overflow: auto;
}
</style>
```

- [ ] **Step 3: 验证前端编译**

Run: `cd web-ui && npx vue-tsc --noEmit 2>&1 | head -10`
Expected: 无错误

- [ ] **Step 4: 提交**

```bash
git add web-ui/src/views/portfolio/validation/MonteCarlo.vue web-ui/src/views/portfolio/tabs/ValidationTab.vue
git commit -m "feat: update ValidationTab with segment stability, migrate MonteCarlo"
```

---

## Self-Review

**1. Spec coverage:**
- 分段稳定性（多窗口）→ Task 1 + 4 + 6
- 蒙特卡洛模拟 → Task 2 + 4
- API 端点 → Task 3 + 4
- ValidationService 注册 → Task 3
- 前端组件 → Task 5 + 6 + 7
- 参数鲁棒性/滚动前进/因子稳定性 → 设计文档标记为后续实现，不在本计划范围

**2. Placeholder scan:** 无 TBD/TODO/待实现。所有步骤含完整代码。

**3. Type consistency:**
- `segment_stability()` 参数：task_id, portfolio_id, n_segments_list
- API 层 Pydantic：SegmentStabilityRequest.task_id, portfolio_id, n_segments
- 前端 TypeScript：SegmentStabilityConfig.task_id, portfolio_id, n_segments
- ✅ 一致

**4. 变更文件树审查:**

```
src/ginkgo/data/
├── services/
│   └── validation_service.py         [新]
└── containers.py                     [改]

api/
├── api/
│   └── validation.py                 [新]
└── main.py                           [改]

tests/
├── unit/
│   └── test_validation_service.py    [新]

web-ui/src/
├── api/modules/
│   └── validation.ts                 [改]
└── views/
    └── portfolio/
        ├── tabs/
        │   └── ValidationTab.vue     [改]
        └── validation/
            ├── SegmentStability.vue  [新]
            └── MonteCarlo.vue        [移] 从 stage2/ 复制

图例: [新]=新增  [改]=修改  [移]=迁移
```

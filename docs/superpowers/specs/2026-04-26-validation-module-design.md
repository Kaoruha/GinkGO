# 组合详情"验证"Tab 设计方案

## 策略能力特征（后续优化，当前不实现）

策略不按类型硬分类，而是通过类属性声明能力标志位，决定哪些验证方法适用。子类只需覆盖与基类不同的属性：

```python
class BaseStrategy:
    # 是否需要训练/拟合阶段（多因子权重拟合、神经网络训练）
    requires_fit = False

    # 是否有可扫描的可调参数（如 lookback_period、top_n 等）
    has_tunable_params = True

    # 是否输出因子得分（策略 cal() 中产出各股票的因子评分）
    uses_factors = False
```

**当前方案：** UI 显示所有验证方法，不做自动过滤。用户选择了不适用的方法时，后端返回错误提示。能力标志位的自动检测留待验证功能成熟后实现。

## 验证方法矩阵

| 方法 | 原理 |
|------|------|
| **分段稳定性** | 固定参数，切时段，看表现是否一致 |
| **蒙特卡洛** | 对日收益率 bootstrap，评估收益分布 |
| **参数鲁棒性** | 扰动参数，看策略对参数是否敏感 |
| **滚动前进** | 训练期拟合→测试期验证，检测过拟合 |
| **因子稳定性** | 因子 IC 值在不同时段是否衰减 |

## 五个验证模块详细设计

### 1. 分段稳定性（通用）

**适用：所有策略**

将回测区间等分为 N 段，每段独立计算收益、夏普、最大回撤，看各段表现是否一致。

**输入：**
- 已完成的回测任务 UUID
- 分段数（默认 4）
- 分段方式：等交易日数（默认）/ 等时间

**计算逻辑：**
```
完整区间: 2024-01-02 ~ 2024-12-31
分成 4 段:
  Q1: 收益 +3.2%, 夏普 1.8, 最大回撤 -4.1%
  Q2: 收益 +1.1%, 夏普 0.9, 最大回撤 -6.3%
  Q3: 收益 -0.8%, 夏普 -0.3, 最大回撤 -8.2%
  Q4: 收益 +2.5%, 夏普 1.2, 最大回撤 -5.0%

mean_abs = mean(|各段收益|)
稳定性评分 = 0 if mean_abs < 0.001 else max(0, 1 - std(各段收益) / mean_abs)
# mean_abs < 0.001 时收益过小，无法判断稳定性
# max(0, ...) 防止评分出现负值
```

**数据来源：** 已有 `analyzer_record` 表中 net_value 的每日记录，按日期分段提取，无需重跑回测。

**输出：**
- 各段关键指标表格（收益、夏普、回撤、胜率）
- 稳定性评分（0~1，越高越稳定）
- 各段净值曲线叠加对比图

---

### 2. 蒙特卡洛模拟（通用）

**适用：所有策略**

从回测的日收益率序列中随机有放回抽样，拼成等长的新序列，重复 N 次，统计收益分布。

**输入：**
- 已完成的回测任务 UUID
- 模拟次数（默认 10000）
- 置信水平（90% / 95% / 99%）

**计算逻辑：**
```
实际日收益率: [+0.02, -0.01, +0.03, +0.01, -0.02, ...]  (共 242 天)

模拟 #1: 随机抽 242 天 → 累计净值 1.05
模拟 #2: 随机抽 242 天 → 累计净值 0.93
...
模拟 #10000 → 统计分布

实际收益 vs 模拟分布的百分位:
  - 实际比 95% 的模拟都好 → 策略大概率有真本事
  - 实际只比 30% 的模拟好 → 大概率是运气
```

**数据来源：** `analyzer_record` 中 net_value 的每日记录，计算日收益率后做 bootstrap。无需重跑回测。

**输出：**
- 模拟收益分布直方图（标注实际收益位置）
- VaR / CVaR / 损失概率
- 实际收益在模拟分布中的百分位

---

### 3. 参数鲁棒性（规则型 + 多因子）

**适用：有可调参数的策略**

固定其他参数，扫描一个参数的多个值，每个值跑一次完整回测，对比结果。

**输入：**
- 组合 UUID
- 参数名（从绑定的组件参数中自动提取）
- 参数扫描范围：起始值、终止值、步长
- 回测日期范围

**计算逻辑：**
```
策略: MomentumStrategy(lookback_period=?, top_n=5)
扫描 lookback_period: 10, 15, 20, 25, 30

  10 → 收益 +4.2%, 夏普 1.1
  15 → 收益 +6.8%, 夏普 1.5
  20 → 收益 +8.0%, 夏普 1.8  ← 当前参数
  25 → 收益 +7.5%, 夏普 1.6
  30 → 收益 +5.1%, 夏普 1.2

鲁棒性评分 = 1 - (max - min) / max
  → (8.0 - 4.2) / 8.0 = 0.475 → 评分 0.525（中等）
```

**实现方式：** 创建 N 个回测任务（修改参数），等待完成，聚合结果。每个参数值 = 一次完整回测。

**输出：**
- 参数-收益/夏普/回撤 对应表
- 参数敏感性曲线图
- 鲁棒性评分

---

### 4. 滚动前进（多因子 + 神经网络）

**适用：有拟合/训练阶段的策略**

将时间线分为多折，每折在训练期拟合参数/训练模型，在测试期验证效果。核心目的是检测策略是否存在过拟合——如果训练期表现好但测试期表现大幅退化，说明策略参数/模型对历史数据过度适配。

#### 4.1 两种窗口模式

**扩展窗口（Anchored Walk Forward）：**
- 训练期从起始点开始，逐折扩展，测试期紧随其后
- 适合数据量较少的场景，充分利用历史数据
```
Fold 1: 训练 [T0──T1) → 测试 [T1──T2)
Fold 2: 训练 [T0─────T2) → 测试 [T2──T3)
Fold 3: 训练 [T0──────────T3) → 测试 [T3──T4)
Fold 4: 训练 [T0───────────────T4) → 测试 [T4──T5)
```

**滚动窗口（Rolling Walk Forward）：**
- 训练期固定长度，逐折向前滚动，测试期紧随其后
- 适合数据量充足的场景，每折训练集大小一致
```
Fold 1: 训练 [T0──T1) → 测试 [T1──T2)
Fold 2: 训练 [T1──T2) → 测试 [T2──T3)
Fold 3: 训练 [T2──T3) → 测试 [T3──T4)
Fold 4: 训练 [T3──T4) → 测试 [T4──T5)
```

#### 4.2 输入参数

- 组合 UUID
- 折数（默认 5）
- 训练期比例（默认 70%）
- 窗口模式：扩展窗口 / 滚动窗口（默认扩展窗口）
- 回测日期范围（start_date, end_date）

#### 4.3 日期切分算法

```python
def split_walk_forward(start_date, end_date, n_folds=5, train_ratio=0.7, mode="anchored"):
    """将日期范围切分为 N 折训练+测试区间"""
    total_days = (end_date - start_date).days

    if mode == "anchored":
        # 扩展窗口：训练期从起点开始逐折增长
        # 每折测试期长度 = 总可用天数 / n_folds
        test_period = total_days * (1 - train_ratio) / n_folds
        folds = []
        for i in range(n_folds):
            train_end = start_date + timedelta(days=total_days * train_ratio + test_period * i)
            test_end = train_end + timedelta(days=test_period)
            folds.append({
                "fold": i + 1,
                "train_start": start_date,
                "train_end": train_end,
                "test_start": train_end,
                "test_end": min(test_end, end_date),
            })
    elif mode == "rolling":
        # 滚动窗口：每折训练期固定长度，整体向前滚动
        fold_period = total_days / n_folds
        train_period = fold_period * train_ratio
        test_period = fold_period * (1 - train_ratio)
        folds = []
        for i in range(n_folds):
            fold_start = start_date + timedelta(days=fold_period * i)
            folds.append({
                "fold": i + 1,
                "train_start": fold_start,
                "train_end": fold_start + timedelta(days=train_period),
                "test_start": fold_start + timedelta(days=train_period),
                "test_end": fold_start + timedelta(days=fold_period),
            })
    return folds
```

#### 4.4 策略接口扩展

当前 `BaseStrategy` 没有 fit 接口，需要扩展以支持训练阶段。只有需要训练的策略（多因子权重拟合、神经网络训练）才需要实现。

```python
class BaseStrategy:
    # 现有方法
    def cal(self, portfolio_info, event) -> List[Signal]: ...

    # capabilities 类属性（见上方定义）

    # 新增：训练/拟合接口（requires_fit=True 的策略必须实现）
    def fit(self, train_data: pd.DataFrame) -> None:
        """在训练数据上拟合策略参数/模型。
        Args:
            train_data: 训练期的行情数据（含 OHLCV 等），具体格式由子类定义
        """
        pass

    def get_fitted_params(self) -> dict:
        """导出拟合后的参数，用于持久化和传递给测试期。"""
        return {}

    def set_fitted_params(self, params: dict) -> None:
        """导入拟合参数，用于测试期初始化策略。"""
        pass
```

**多因子策略示例：**
```python
class MultiFactorStrategy(BaseStrategy):
    def __init__(self, factors, top_n=10):
        self.factors = factors       # 候选因子列表
        self.weights = None          # 拟合后的因子权重
        self.top_n = top_n

    requires_fit = True
    uses_factors = True
    # has_tunable_params 继承基类默认值 True

    def fit(self, train_data):
        """在训练期用 IC 加权确定因子权重"""
        ic_values = {}
        for factor in self.factors:
            ic_values[factor] = compute_ic(factor, train_data)
        total_ic = sum(abs(v) for v in ic_values.values())
        self.weights = {f: abs(v)/total_ic for f, v in ic_values.items()}

    def get_fitted_params(self):
        return {"weights": self.weights}

    def set_fitted_params(self, params):
        self.weights = params["weights"]

    def cal(self, portfolio_info, event):
        # 使用 self.weights 进行因子打分选股
        ...
```

**神经网络策略示例：**
```python
class LSTMStrategy(BaseStrategy):
    def __init__(self, lookback=60):
        self.model = None
        self.lookback = lookback

    requires_fit = True
    # has_tunable_params 继承基类默认值 True
    # uses_factors 继承基类默认值 False

    def fit(self, train_data):
        """在训练期训练 LSTM 模型"""
        X, y = self._prepare_sequences(train_data)
        self.model = self._build_model()
        self.model.fit(X, y, epochs=50)

    def get_fitted_params(self):
        # 模型较大时存文件路径，小模型可序列化
        path = f"/tmp/model_{uuid4()}.pkl"
        joblib.dump(self.model, path)
        return {"model_path": path}

    def set_fitted_params(self, params):
        self.model = joblib.load(params["model_path"])
```

#### 4.5 引擎集成

新增 `WalkForwardProcessor` 编排层，负责切分日期、创建子任务、收集结果。

```python
class WalkForwardProcessor:
    def __init__(self, portfolio_id, n_folds=5, train_ratio=0.7, mode="anchored"):
        self.portfolio_id = portfolio_id
        self.n_folds = n_folds
        self.train_ratio = train_ratio
        self.mode = mode

    def run(self, start_date, end_date):
        """执行 Walk Forward 验证"""
        portfolio = load_portfolio(self.portfolio_id)
        strategy = portfolio.get_strategy()

        if not strategy.requires_fit:
            raise ValueError("策略不需要训练阶段，不适用 Walk Forward 验证")

        folds = split_walk_forward(start_date, end_date, self.n_folds, self.train_ratio, self.mode)

        results = []
        for fold_info in folds:
            # 阶段 1: 训练 — 用训练期数据运行回测，让策略积累数据
            train_engine = create_backtest_engine(
                portfolio_id=self.portfolio_id,
                start_date=fold_info["train_start"],
                end_date=fold_info["train_end"],
            )
            train_engine.run()
            train_strategy = train_engine.portfolio.get_strategy()

            # 导出拟合参数
            fitted_params = train_strategy.get_fitted_params()

            # 阶段 2: 测试 — 用拟合参数在测试期验证
            test_engine = create_backtest_engine(
                portfolio_id=self.portfolio_id,
                start_date=fold_info["test_start"],
                end_date=fold_info["test_end"],
            )
            test_strategy = test_engine.portfolio.get_strategy()
            test_strategy.set_fitted_params(fitted_params)
            test_engine.run()

            # 收集结果
            results.append({
                "fold": fold_info["fold"],
                "train_period": f"{fold_info['train_start']} ~ {fold_info['train_end']}",
                "test_period": f"{fold_info['test_start']} ~ {fold_info['test_end']}",
                "train_return": get_period_return(train_engine),
                "test_return": get_period_return(test_engine),
                "train_sharpe": get_sharpe(train_engine),
                "test_sharpe": get_sharpe(test_engine),
                "train_max_drawdown": get_max_drawdown(train_engine),
                "test_max_drawdown": get_max_drawdown(test_engine),
            })

        # 计算退化度
        avg_train = statistics.mean(r["train_return"] for r in results)
        avg_test = statistics.mean(r["test_return"] for r in results)
        degradation = (avg_train - avg_test) / avg_train if abs(avg_train) >= 0.001 else abs(avg_train - avg_test)
        # |avg_train| < 0.001 时用绝对差值代替比率，退化度仅供参考

        return {"folds": results, "degradation": degradation}
```

#### 4.6 存储设计

Walk Forward 结果可存储在 MySQL 中，表结构：

```sql
CREATE TABLE m_walk_forward_result (
    uuid VARCHAR(36) PRIMARY KEY,
    portfolio_id VARCHAR(36) NOT NULL,       -- 关联的组合
    job_id VARCHAR(36) NOT NULL,             -- 验证任务 ID
    fold INT NOT NULL,                       -- 折序号
    train_start DATE NOT NULL,
    train_end DATE NOT NULL,
    test_start DATE NOT NULL,
    test_end DATE NOT NULL,
    train_return DECIMAL(10,4),              -- 训练期收益
    test_return DECIMAL(10,4),               -- 测试期收益
    train_sharpe DECIMAL(8,4),
    test_sharpe DECIMAL(8,4),
    train_max_drawdown DECIMAL(10,4),
    test_max_drawdown DECIMAL(10,4),
    fitted_params TEXT,                      -- JSON: 拟合参数快照
    mode VARCHAR(16),                        -- anchored / rolling
    create_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_portfolio (portfolio_id),
    INDEX idx_job (job_id)
);
```

#### 4.7 输出

- 各折训练/测试收益对比表（含夏普、最大回撤）
- 退化度（0~1，越低越好；>0.5 表示严重过拟合）
- 训练 vs 测试收益散点图
- 各折净值曲线叠加
- 拟合参数稳定性报告（各折参数是否一致）

#### 4.8 当前状态

**未实现。** 前置依赖：
1. `BaseStrategy` 增加 `requires_fit`/`has_tunable_params`/`uses_factors` 类属性 + `fit()`/`get_fitted_params()`/`set_fitted_params()` 接口
2. 各具体策略类实现训练逻辑（多因子 IC 拟合、神经网络训练）
3. 回测引擎支持两阶段执行模式（训练阶段 + 测试阶段）
4. `WalkForwardProcessor` 编排层实现
5. 异步任务管理（N 折 = N 次回测，需任务队列支持）

---

### 5. 因子稳定性（多因子）

**适用：多因子策略**

将回测区间分为 N 段，每段计算各因子的 IC 值（因子得分与未来收益的秩相关系数），看 IC 在不同时段是否稳定。IC 持续衰减说明因子可能失效。

**输入：**
- 已完成的回测任务 UUID
- 分段数（默认 4）
- IC 计算方式：Spearman 秩相关（默认）/ Pearson

**计算逻辑：**
```
因子 A: Q1 IC=0.05, Q2 IC=0.04, Q3 IC=0.03, Q4 IC=0.06 → 均值 0.045, 稳定
因子 B: Q1 IC=0.08, Q2 IC=0.02, Q3 IC=-0.01, Q4 IC=0.01 → 均值 0.025, 衰减

稳定性评分 = 1 - std(各段IC) / mean(|各段IC|)
  （同分段稳定性公式，含 mean_abs < 0.001 阈值保护）
```

**数据来源：** 需要策略在 `cal()` 时输出每只股票的因子得分，写入 analyzer_record。当前引擎尚不支持此数据采集。

**输出：**
- 各因子在各段的 IC 值表格
- IC 时序趋势图（按因子分组）
- 因子稳定性评分
- 衰减因子告警（IC 均值 < 0.02 或趋势为负）

#### 当前状态

**未实现。** 前置依赖：
1. 多因子策略模块实现，策略 `cal()` 输出因子得分
2. 回测引擎支持因子得分采集与存储
3. IC 计算工具函数

---

## UI 结构

```
验证 Tab
├── 顶部：回测任务选择器（选择要验证的已完成回测）
├── 子标签页（当前全部显示，后续根据策略能力自动过滤）
│   ├── 分段稳定性
│   ├── 蒙特卡洛
│   ├── 参数鲁棒性
│   ├── 滚动前进
│   └── 因子稳定性
└── 综合评分面板（汇总所有已执行验证的评分）
```

## 数据流

```
分段稳定性 / 蒙特卡洛（无需重跑）:
  analyzer_record(net_value) → 提取日收益率 → 统计计算 → 结果

参数鲁棒性（需重跑 N 次）:
  修改参数 → 创建 N 个回测任务 → 等待完成 → 聚合 N 份结果 → 对比

滚动前进（需重跑 N 折 + fit 接口）:
  切分日期 → N 折(训练+测试) → 每折创建回测任务 → 聚合 → 计算退化度

因子稳定性（需因子得分数据）:
  analyzer_record(factor_scores) → 按段计算 IC → 统计衰减趋势
```

## 实现优先级

1. **分段稳定性** — 纯后处理，基于已有 analyzer_record，无需新 API，无需重跑回测
2. **蒙特卡洛** — 纯后处理，同上
3. **参数鲁棒性** — 需要多任务编排（批量创建回测）
4. **滚动前进** — 最复杂，需要策略层支持 fit 接口
5. **因子稳定性** — 依赖因子策略模块，当前不实现

## 后端 API 设计

```
# 分段稳定性（基于已有数据，秒级返回）
POST /api/v1/validation/segment-stability
  Body: { task_id, n_segments: 4 }
  Response: { segments: [...], stability_score: 0.75 }

# 蒙特卡洛（基于已有数据，秒级返回）
POST /api/v1/validation/monte-carlo
  Body: { task_id, n_simulations: 10000, confidence: 0.95 }
  Response: { var, cvar, loss_probability, percentile, distribution: [...] }

# 参数鲁棒性（触发 N 次回测，异步）
POST /api/v1/validation/parameter-robustness
  Body: { portfolio_id, param_name, param_range: [start, end, step], start_date, end_date }
  Response: { job_id }

GET /api/v1/validation/parameter-robustness/{job_id}
  Response: { status, results: [{param_value, return, sharpe, max_drawdown}], robustness_score }

# 滚动前进（触发 N 折回测，异步）
POST /api/v1/validation/walk-forward
  Body: { portfolio_id, n_folds: 5, train_ratio: 0.7, start_date, end_date }
  Response: { job_id }

GET /api/v1/validation/walk-forward/{job_id}
  Response: { status, folds: [{fold, train_return, test_return}], degradation }

# 因子稳定性（基于已有数据，秒级返回）
POST /api/v1/validation/factor-stability
  Body: { task_id, n_segments: 4, ic_method: "spearman" }
  Response: { factors: [{name, ic_values: [...], stability_score, trend}], alerts: [...] }
```
```

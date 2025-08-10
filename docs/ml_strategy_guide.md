# ML策略使用指南

## 概述

Ginkgo现在支持机器学习策略，可以轻松地将训练好的ML模型集成到回测系统中。ML策略框架提供了：

- **StrategyMLBase**: ML策略基类，提供模型加载、特征工程、预测等核心功能
- **StrategyMLPredictor**: 具体的ML预测策略实现，包含风险管理和头寸管理

## 快速开始

### 1. 基本使用

```python
from ginkgo.backtest.strategy.strategies import StrategyMLPredictor

# 创建ML策略实例
strategy = StrategyMLPredictor(
    name="MyMLStrategy",
    model_path="path/to/trained_model.pkl",  # 训练好的模型路径
    prediction_horizon=5,                    # 预测5天后的收益
    confidence_threshold=0.7,                # 最小置信度70%
    return_threshold=0.02,                   # 预测收益率阈值2%
    risk_management=True,                    # 启用风险管理
    stop_loss_ratio=0.05,                   # 5%止损
    take_profit_ratio=0.10                  # 10%止盈
)

# 策略会自动处理：
# - 从市场事件中提取特征
# - 使用模型进行预测
# - 根据预测结果生成交易信号
# - 执行风险管理规则
```

### 2. 高级定制

```python
# 自定义特征工程配置
feature_config = {
    'processor': {
        'scaling_method': 'robust',      # 使用Robust标准化
        'imputation_method': 'median',   # 中位数填充缺失值
        'feature_selection': True,       # 启用特征选择
        'n_features': 30                 # 选择30个最重要特征
    },
    'factors': {
        'use_talib': True               # 使用TA-Lib加速计算
    },
    'min_confidence': 0.8               # 最小置信度80%
}

strategy = StrategyMLPredictor(
    name="AdvancedMLStrategy",
    model_path="advanced_model.pkl",
    feature_config=feature_config,
    position_sizing="proportional",      # 按预测强度调整头寸
    max_position_ratio=0.15             # 单个股票最大持仓15%
)
```

### 3. 自定义ML策略

```python
from ginkgo.backtest.strategy.strategies import StrategyMLBase
from ginkgo.enums import DIRECTION_TYPES

class CustomMLStrategy(StrategyMLBase):
    """自定义ML策略"""
    
    def __init__(self, **kwargs):
        super().__init__(name="CustomMLStrategy", **kwargs)
        self.load_model("my_custom_model.pkl")
    
    def generate_signals_from_prediction(self, portfolio_info, code, prediction_result):
        """自定义信号生成逻辑"""
        prediction = prediction_result['prediction']
        confidence = prediction_result['confidence']
        
        # 自定义信号生成规则
        if prediction > 0.03 and confidence > 0.9:
            # 高置信度强买入信号
            return [self._create_signal(
                portfolio_info, code, DIRECTION_TYPES.LONG, 
                f"STRONG_BUY_pred:{prediction:.4f}_conf:{confidence:.3f}"
            )]
        elif prediction < -0.03 and confidence > 0.9:
            # 高置信度强卖出信号  
            return [self._create_signal(
                portfolio_info, code, DIRECTION_TYPES.SHORT,
                f"STRONG_SELL_pred:{prediction:.4f}_conf:{confidence:.3f}"
            )]
        
        return []  # 其他情况不生成信号

# 使用自定义策略
strategy = CustomMLStrategy()
```

## 模型要求

### 支持的模型类型

ML策略支持所有实现了 `IModel` 接口的模型：
- LightGBM
- XGBoost  
- Scikit-learn模型
- 自定义模型

### 模型训练要求

1. **特征一致性**: 模型训练时使用的特征必须与策略中的Alpha因子一致
2. **目标变量**: 推荐使用未来N日收益率作为预测目标
3. **数据格式**: 使用ginkgo的数据格式进行训练以确保兼容性

### 示例训练脚本

```python
from ginkgo.quant_ml.models import LightGBMModel
from ginkgo.quant_ml.features import FeatureProcessor, AlphaFactors
from ginkgo.data import get_bars_page_filtered

# 1. 数据准备
bars = get_bars_page_filtered(
    code="000001.SZ",
    start="20200101", 
    end="20231231",
    adjusted=True
)

# 转换为DataFrame
data = pd.DataFrame([{
    'timestamp': bar.timestamp,
    'open': bar.open,
    'high': bar.high, 
    'low': bar.low,
    'close': bar.close,
    'volume': bar.volume
} for bar in bars])

# 2. 特征工程
alpha_factors = AlphaFactors()
features_data = alpha_factors.calculate_all_factors(data)

# 3. 创建目标变量（5日后收益率）
features_data['target'] = (
    features_data['close'].shift(-5) / features_data['close'] - 1
)

# 4. 数据清洗和分割
clean_data = features_data.dropna()
split_idx = int(len(clean_data) * 0.8)

feature_cols = [col for col in clean_data.columns 
                if col not in ['timestamp', 'target', 'open', 'high', 'low', 'close', 'volume']]

X_train = clean_data.iloc[:split_idx][feature_cols]
y_train = clean_data.iloc[:split_idx][['target']]
X_test = clean_data.iloc[split_idx:][feature_cols]
y_test = clean_data.iloc[split_idx:][['target']]

# 5. 特征预处理
processor = FeatureProcessor(scaling_method='standard')
X_train_processed = processor.fit_transform(X_train, y_train)
X_test_processed = processor.transform(X_test)

# 6. 模型训练
model = LightGBMModel(task="regression")
model.fit(X_train_processed, y_train, 
          eval_set=[(X_test_processed, y_test)])

# 7. 保存模型
model.save("my_trained_model.pkl")
```

## 监控和调试

### 策略性能监控

```python
# 获取策略摘要
summary = strategy.get_strategy_summary()
print(f"模型已加载: {summary['model_loaded']}")
print(f"活跃持仓: {summary['active_positions']}")

# 获取性能指标
metrics = strategy.get_performance_metrics()
print(f"方向准确率: {metrics.get('direction_accuracy', 'N/A')}")
print(f"信息系数: {metrics.get('information_coefficient', 'N/A')}")

# 获取持仓信息
positions = strategy.get_position_info()
for code, info in positions.items():
    print(f"{code}: 进场价格={info['entry_price']}, 持仓天数={info['duration']}")
```

### 模型热重载

```python
# 更新模型而不重启策略
strategy.reload_model()

# 更新策略参数
strategy.set_signal_threshold(0.03)  # 调整信号阈值

# 更新特征配置
new_config = {
    'processor': {'scaling_method': 'minmax'},
    'min_confidence': 0.75
}
strategy.set_feature_config(new_config)
```

## 最佳实践

1. **模型版本管理**: 为模型文件使用版本化命名，如 `model_v1.2_20240101.pkl`

2. **特征稳定性**: 确保模型训练和策略使用相同的特征计算逻辑

3. **风险管理**: 始终启用风险管理，设置合理的止损止盈比例

4. **性能监控**: 定期检查模型性能指标，及时发现模型衰减

5. **参数优化**: 根据不同市场环境调整置信度阈值和信号阈值

6. **回测验证**: 在实盘部署前充分回测验证策略效果

## 注意事项

- ML策略需要额外的依赖库（scikit-learn、lightgbm等）
- 首次运行时需要计算大量历史特征，可能较慢
- 模型预测结果会被缓存以提高性能
- 建议在开发环境中启用详细日志进行调试

通过这个ML策略框架，您可以轻松地将各种机器学习模型集成到Ginkgo的回测系统中，实现从模型训练到策略部署的完整流程。
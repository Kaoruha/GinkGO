# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: PredictionStrategy预测策略基于机器学习实现交易预测支持ML策略
# Origin: ADR-022 原则6 · ML 策略三变体统一。原继承 quant_ml/strategies/ml_strategy_base.py 的同名死类
#         （已删）；现继承 trading/strategies/ml_strategy_base.py 的统一 MLStrategyBase。本类
#         自带在线训练/再训流程（quant_ml 域 Bar 事件驱动，与 trading 域的 data_feeder 流程不同），
#         故 __init__/cal 及特征管线在本类内就地实现，不依赖父类实现细节。




"""
预测策略实现

基于机器学习模型预测股价未来收益率的具体策略实现。

历史：原继承 quant_ml 域的 MLStrategyBase（已随 ADR-022 原则6 三变体统一删除）。
现继承 trading 域的统一 MLStrategyBase。在线训练/再训/特征管线逻辑随迁入本类，
保持原运行时行为（Bar 事件驱动）。
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime, timedelta

from ginkgo.trading.strategies.ml_strategy_base import MLStrategyBase
from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.entities import Signal
from ginkgo.entities import Bar
from ginkgo.enums import DIRECTION_TYPES, STRATEGY_TYPES
from ginkgo.libs import GLOG
from ginkgo.quant_ml.features import FeatureProcessor, AlphaFactors


class PredictionStrategy(MLStrategyBase):
    """
    预测策略

    基于ML模型预测未来N期收益率，根据预测结果生成买卖信号。

    注：继承 trading 域统一 MLStrategyBase 以满足 ADR-022 原则6 单根命名。
    本类携带 quant_ml 域特有的在线训练/再训管线（Bar 事件驱动 + feature_data 累积），
    故 __init__/cal 及特征相关 helper 在本类内实现，与父类（data_feeder 桥接层）职责不同。
    """

    def __init__(self,
                 name: str = "PredictionStrategy",
                 prediction_horizon: int = 5,
                 min_prediction_confidence: float = 0.6,
                 position_sizing_method: str = "equal_weight",
                 max_position_size: float = 0.1,
                 model: Optional[Any] = None,
                 feature_processor: Optional[FeatureProcessor] = None,
                 lookback_period: int = 252,
                 retrain_frequency: int = 60,
                 signal_threshold: float = 0.01,
                 **kwargs):
        """
        初始化预测策略

        Args:
            name: 策略名称
            prediction_horizon: 预测时间窗口（天）
            min_prediction_confidence: 最小预测置信度
            position_sizing_method: 头寸大小确定方法
            max_position_size: 最大头寸比例
            model: 机器学习模型
            feature_processor: 特征处理器
            lookback_period: 训练数据回看期
            retrain_frequency: 重新训练频率（天）
            signal_threshold: 信号生成阈值
            **kwargs: 其他参数
        """
        # 绕过 MLStrategyBase 的 data_feeder 桥接初始化（本类走 Bar 事件管线，非 data_feeder 流程）；
        # 直接调用 BaseStrategy 完成名称/上下文注册，保持与原 quant_ml 基类一致的初始化语义。
        BaseStrategy.__init__(self, name)

        self.model = model
        self.feature_processor = feature_processor or FeatureProcessor()
        self.alpha_factors = AlphaFactors()

        # 训练参数
        self.lookback_period = lookback_period
        self.retrain_frequency = retrain_frequency
        self.signal_threshold = signal_threshold

        # 策略状态
        self.last_train_date = None
        self.feature_data = pd.DataFrame()
        self.predictions = pd.DataFrame()

        # 性能跟踪
        self.prediction_accuracy = []
        self.signal_performance = []

        self.strategy_type = STRATEGY_TYPES.ML

        # 本类特有参数
        self.prediction_horizon = prediction_horizon
        self.min_prediction_confidence = min_prediction_confidence
        self.position_sizing_method = position_sizing_method
        self.max_position_size = max_position_size

        GLOG.INFO(f"初始化预测策略: {name}, 预测期: {prediction_horizon}天, 回看期: {lookback_period}天, 重训频率: {retrain_frequency}天")

    def cal(self, portfolio_info: Any = None, event: Any = None) -> List[Signal]:
        """
        策略主计算方法（事件驱动模式）

        Args:
            portfolio_info: 投资组合信息
            event: 市场事件

        Returns:
            List[Signal]: 生成的交易信号
        """
        try:
            signals = []

            if event is None or not hasattr(event, 'data'):
                return signals

            current_bar = event.data
            if not isinstance(current_bar, Bar):
                return signals

            current_date = current_bar.timestamp.date()

            # 更新特征数据
            self._update_feature_data(current_bar)

            # 检查是否需要重新训练
            if self._should_retrain(current_date):
                self._retrain_model()
                self.last_train_date = current_date

            # 生成预测和信号
            if self.model and self.model.is_trained:
                prediction = self._generate_prediction(current_bar)
                if prediction is not None:
                    signal = self._generate_signal_from_prediction(
                        current_bar, prediction, portfolio_info
                    )
                    if signal:
                        signals.append(signal)

            return signals

        except Exception as e:
            GLOG.ERROR(f"ML策略计算失败: {e}")
            return []

    def _update_feature_data(self, bar: Bar) -> None:
        """更新特征数据"""
        try:
            # 将Bar对象转换为DataFrame行
            bar_data = {
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume,
                'code': bar.code
            }

            # 添加到特征数据
            new_row = pd.DataFrame([bar_data])

            if self.feature_data.empty:
                self.feature_data = new_row
            else:
                self.feature_data = pd.concat([self.feature_data, new_row], ignore_index=True)

            # 保持数据长度
            max_length = self.lookback_period + 100  # 额外缓冲
            if len(self.feature_data) > max_length:
                self.feature_data = self.feature_data.tail(max_length).reset_index(drop=True)

            # 计算技术因子
            if len(self.feature_data) >= 20:  # 最少需要20个数据点
                self.feature_data = self.alpha_factors.calculate_all_factors(self.feature_data)

        except Exception as e:
            GLOG.ERROR(f"特征数据更新失败: {e}")

    def _should_retrain(self, current_date: datetime.date) -> bool:
        """判断是否需要重新训练模型"""
        if self.last_train_date is None:
            return True

        if self.model is None or not self.model.is_trained:
            return True

        days_since_training = (current_date - self.last_train_date).days
        return days_since_training >= self.retrain_frequency

    def _retrain_model(self) -> None:
        """重新训练模型"""
        try:
            if len(self.feature_data) < self.lookback_period:
                GLOG.WARN(f"训练数据不足: {len(self.feature_data)} < {self.lookback_period}")
                return

            GLOG.INFO("开始重新训练ML模型")

            # 准备训练数据
            train_data = self.feature_data.tail(self.lookback_period).copy()
            features, targets = self._prepare_training_data(train_data)

            if features.empty or targets.empty:
                GLOG.WARN("训练数据准备失败")
                return

            # 特征处理
            features_processed = self.feature_processor.fit_transform(features, targets)

            # 训练模型
            if self.model:
                self.model.fit(features_processed, targets)
                GLOG.INFO(f"模型训练完成，特征数: {features_processed.shape[1]}")

                # 记录训练性能
                if hasattr(self.model, 'get_training_info'):
                    train_info = self.model.get_training_info()
                    GLOG.INFO(f"训练信息: {train_info}")

        except Exception as e:
            GLOG.ERROR(f"模型重训失败: {e}")

    def _generate_prediction(self, bar: Bar) -> Optional[float]:
        """生成预测结果"""
        try:
            if len(self.feature_data) < 50:  # 需要足够的历史数据
                return None

            # 获取最新特征
            latest_features = self._get_latest_features()
            if latest_features is None or latest_features.empty:
                return None

            # 特征预处理
            features_processed = self.feature_processor.transform(latest_features)

            # 模型预测
            prediction = self.model.predict(features_processed)

            if isinstance(prediction, pd.DataFrame):
                pred_value = prediction.iloc[0, 0]
            else:
                pred_value = float(prediction[0])

            # 记录预测结果
            self.predictions = pd.concat([
                self.predictions,
                pd.DataFrame({
                    'timestamp': [bar.timestamp],
                    'prediction': [pred_value],
                    'actual_price': [bar.close]
                })
            ], ignore_index=True).tail(1000)  # 保持预测历史

            return pred_value

        except Exception as e:
            GLOG.ERROR(f"预测生成失败: {e}")
            return None

    def _get_latest_features(self) -> Optional[pd.DataFrame]:
        """获取最新的特征数据"""
        if self.feature_data.empty:
            return None

        try:
            # 获取最新一行数据的特征
            latest_data = self.feature_data.tail(1).copy()

            # 排除非特征列
            exclude_cols = ['timestamp', 'code']
            feature_cols = [col for col in latest_data.columns if col not in exclude_cols]

            features = latest_data[feature_cols]

            # 删除包含NaN的列
            features = features.dropna(axis=1)

            return features

        except Exception as e:
            GLOG.ERROR(f"获取最新特征失败: {e}")
            return None

    def _prepare_training_data(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        准备训练数据

        创建特征和目标变量，目标变量为未来N期收益率
        """
        try:
            if len(data) < self.prediction_horizon + 20:
                GLOG.WARN("数据长度不足以创建训练集")
                return pd.DataFrame(), pd.DataFrame()

            # 计算未来收益率作为目标变量
            data = data.copy()
            data['future_return'] = (
                data['close'].shift(-self.prediction_horizon) / data['close'] - 1
            )

            # 移除包含NaN的行
            valid_data = data.dropna()

            if len(valid_data) < 50:
                GLOG.WARN("有效训练数据不足")
                return pd.DataFrame(), pd.DataFrame()

            # 排除目标变量和非特征列
            exclude_cols = [
                'timestamp', 'code', 'future_return',
                'open', 'high', 'low', 'close', 'volume'  # 原始价格数据
            ]

            feature_cols = [col for col in valid_data.columns if col not in exclude_cols]

            # 特征数据
            features = valid_data[feature_cols].copy()

            # 目标变量
            targets = valid_data[['future_return']].copy()

            # 数据质量检查
            features = features.select_dtypes(include=[np.number])  # 只保留数值列
            features = features.replace([np.inf, -np.inf], np.nan)  # 替换无穷值
            features = features.dropna(axis=1, how='all')  # 删除全NaN的列

            # 确保特征和目标对齐
            common_idx = features.index.intersection(targets.index)
            features = features.loc[common_idx]
            targets = targets.loc[common_idx]

            GLOG.INFO(f"训练数据准备完成，特征数: {features.shape[1]}, 样本数: {len(features)}")

            return features, targets

        except Exception as e:
            GLOG.ERROR(f"训练数据准备失败: {e}")
            return pd.DataFrame(), pd.DataFrame()

    def _generate_signal_from_prediction(self, bar: Bar, prediction: float, portfolio_info: Any) -> Optional[Signal]:
        """
        从预测结果生成交易信号
        """
        try:
            # 预测置信度检查
            if abs(prediction) < self.signal_threshold:
                return None

            # 确定交易方向
            if prediction > self.signal_threshold:
                direction = DIRECTION_TYPES.LONG
                signal_strength = min(prediction, 1.0)
            elif prediction < -self.signal_threshold:
                direction = DIRECTION_TYPES.SHORT
                signal_strength = min(abs(prediction), 1.0)
            else:
                return None

            # 计算信号置信度
            confidence = self._calculate_signal_confidence(prediction, bar)

            if confidence < self.min_prediction_confidence:
                GLOG.DEBUG(f"信号置信度不足: {confidence:.3f}")
                return None

            # 计算头寸大小
            position_size = self._calculate_position_size(
                prediction, signal_strength, confidence, portfolio_info
            )

            if position_size <= 0:
                return None

            # 创建交易信号
            signal = Signal(
                code=bar.code,
                direction=direction,
                size=position_size,
                timestamp=bar.timestamp,
                price=bar.close
            )

            # 添加策略信息
            signal.strategy_name = self.name
            signal.prediction = prediction
            signal.confidence = confidence
            signal.signal_strength = signal_strength

            GLOG.DEBUG(f"生成信号: {bar.code}, 方向: {direction.name}, 大小: {position_size:.4f}, 预测: {prediction:.4f}")

            return signal

        except Exception as e:
            GLOG.ERROR(f"信号生成失败: {e}")
            return None

    def _calculate_signal_confidence(self, prediction: float, bar: Bar) -> float:
        """
        计算信号置信度

        基于多个因素计算信号的置信度：
        - 预测值的绝对大小
        - 历史预测准确性
        - 市场波动率
        """
        try:
            # 基础置信度基于预测值大小
            base_confidence = min(abs(prediction) * 2, 1.0)

            # 历史准确性调整
            if len(self.predictions) > 20:
                recent_predictions = self.predictions.tail(20)
                if 'actual_return' in recent_predictions.columns:
                    # 计算历史准确性
                    pred_direction = np.sign(recent_predictions['prediction'])
                    actual_direction = np.sign(recent_predictions['actual_return'])
                    accuracy = np.mean(pred_direction == actual_direction)

                    # 根据准确性调整置信度
                    accuracy_multiplier = max(0.5, accuracy * 2)
                    base_confidence *= accuracy_multiplier

            # 市场波动率调整
            if len(self.feature_data) > 20:
                recent_returns = self.feature_data['close'].pct_change().tail(20)
                volatility = recent_returns.std()

                # 高波动时降低置信度
                vol_adjustment = max(0.7, 1 - volatility * 10)
                base_confidence *= vol_adjustment

            return np.clip(base_confidence, 0.0, 1.0)

        except Exception as e:
            GLOG.WARN(f"置信度计算失败: {e}")
            return 0.5  # 默认置信度

    def _calculate_position_size(self,
                                prediction: float,
                                signal_strength: float,
                                confidence: float,
                                portfolio_info: Any) -> float:
        """
        计算头寸大小
        """
        try:
            if self.position_sizing_method == "equal_weight":
                # 等权重
                base_size = self.max_position_size
            elif self.position_sizing_method == "prediction_weighted":
                # 基于预测强度加权
                base_size = self.max_position_size * signal_strength
            elif self.position_sizing_method == "confidence_weighted":
                # 基于置信度加权
                base_size = self.max_position_size * confidence
            elif self.position_sizing_method == "combined":
                # 综合权重
                base_size = self.max_position_size * signal_strength * confidence
            else:
                base_size = self.max_position_size

            # 风险调整
            risk_multiplier = self._calculate_risk_multiplier(portfolio_info)
            adjusted_size = base_size * risk_multiplier

            return max(0.001, min(adjusted_size, self.max_position_size))

        except Exception as e:
            GLOG.WARN(f"头寸大小计算失败: {e}")
            return 0.01  # 默认小头寸

    def _calculate_risk_multiplier(self, portfolio_info: Any) -> float:
        """
        计算风险乘数

        根据当前投资组合状态调整头寸大小
        """
        try:
            # 如果没有投资组合信息，返回默认值
            if portfolio_info is None:
                return 1.0

            risk_multiplier = 1.0

            # 检查当前持仓集中度
            if hasattr(portfolio_info, 'positions'):
                total_positions = len(portfolio_info.positions)
                if total_positions > 20:  # 持仓过于分散
                    risk_multiplier *= 0.8
                elif total_positions < 5:  # 持仓过于集中
                    risk_multiplier *= 1.2

            # 检查当前收益状态
            if hasattr(portfolio_info, 'total_return'):
                if portfolio_info.total_return < -0.1:  # 亏损超过10%
                    risk_multiplier *= 0.7  # 降低风险
                elif portfolio_info.total_return > 0.2:  # 盈利超过20%
                    risk_multiplier *= 0.9  # 适当降低风险

            # 检查现金比例
            if hasattr(portfolio_info, 'cash_ratio'):
                if portfolio_info.cash_ratio < 0.05:  # 现金不足5%
                    risk_multiplier *= 0.5  # 大幅降低风险

            return np.clip(risk_multiplier, 0.1, 2.0)

        except Exception as e:
            GLOG.WARN(f"风险乘数计算失败: {e}")
            return 1.0

    def update_prediction_accuracy(self, actual_returns: pd.Series) -> None:
        """
        更新预测准确性

        Args:
            actual_returns: 实际收益率数据
        """
        try:
            if self.predictions.empty:
                return

            # 匹配预测和实际收益
            for idx, row in self.predictions.iterrows():
                timestamp = row['timestamp']
                prediction = row['prediction']

                # 查找对应的实际收益率
                if timestamp in actual_returns.index:
                    actual_return = actual_returns[timestamp]
                    self.predictions.loc[idx, 'actual_return'] = actual_return

                    # 计算预测误差
                    error = abs(prediction - actual_return)
                    self.predictions.loc[idx, 'prediction_error'] = error

            # 更新策略性能指标
            self._update_performance_metrics()

        except Exception as e:
            GLOG.ERROR(f"预测准确性更新失败: {e}")

    def _update_performance_metrics(self) -> None:
        """更新策略性能指标"""
        try:
            if 'actual_return' not in self.predictions.columns:
                return

            valid_predictions = self.predictions.dropna(subset=['actual_return'])

            if len(valid_predictions) < 10:
                return

            # 方向预测准确率
            pred_direction = np.sign(valid_predictions['prediction'])
            actual_direction = np.sign(valid_predictions['actual_return'])
            direction_accuracy = np.mean(pred_direction == actual_direction)

            # 信息系数
            ic = valid_predictions['prediction'].corr(valid_predictions['actual_return'])

            # 平均绝对误差
            mae = valid_predictions['prediction_error'].mean()

            # 记录性能指标
            self.signal_performance.append({
                'timestamp': datetime.now(),
                'direction_accuracy': direction_accuracy,
                'information_coefficient': ic,
                'mean_absolute_error': mae,
                'prediction_count': len(valid_predictions)
            })

            # 保持性能历史长度
            if len(self.signal_performance) > 100:
                self.signal_performance = self.signal_performance[-100:]

            GLOG.INFO(f"策略性能更新 - 方向准确率: {direction_accuracy:.3f}, IC: {ic:.3f}, MAE: {mae:.4f}")

        except Exception as e:
            GLOG.WARN(f"性能指标更新失败: {e}")

    def get_strategy_metrics(self) -> Dict[str, Any]:
        """获取策略指标"""
        metrics = {
            'model_trained': self.model.is_trained if self.model else False,
            'last_train_date': self.last_train_date,
            'feature_count': self.feature_data.shape[1] if not self.feature_data.empty else 0,
            'data_points': len(self.feature_data),
            'predictions_count': len(self.predictions)
        }

        # 计算预测准确性
        if len(self.predictions) > 10:
            try:
                recent_predictions = self.predictions.tail(50)
                if 'actual_return' in recent_predictions.columns:
                    # 计算方向预测准确率
                    pred_direction = np.sign(recent_predictions['prediction'])
                    actual_direction = np.sign(recent_predictions['actual_return'])
                    accuracy = np.mean(pred_direction == actual_direction)
                    metrics['direction_accuracy'] = accuracy

                    # 计算信息系数(IC)
                    ic = recent_predictions['prediction'].corr(recent_predictions['actual_return'])
                    metrics['information_coefficient'] = ic
            except Exception as e:
                GLOG.WARN(f"计算预测准确性失败: {e}")

        return metrics

    def get_strategy_summary(self) -> Dict[str, Any]:
        """获取策略摘要"""
        base_metrics = self.get_strategy_metrics()

        strategy_specific = {
            'prediction_horizon': self.prediction_horizon,
            'min_prediction_confidence': self.min_prediction_confidence,
            'position_sizing_method': self.position_sizing_method,
            'max_position_size': self.max_position_size
        }

        # 添加最近性能指标
        if self.signal_performance:
            latest_performance = self.signal_performance[-1]
            strategy_specific.update({
                'latest_direction_accuracy': latest_performance['direction_accuracy'],
                'latest_information_coefficient': latest_performance['information_coefficient'],
                'latest_mean_absolute_error': latest_performance['mean_absolute_error']
            })

        base_metrics.update(strategy_specific)
        return base_metrics

    def __str__(self) -> str:
        return f"PredictionStrategy(name={self.name}, model={self.model.__class__.__name__ if self.model else None})"

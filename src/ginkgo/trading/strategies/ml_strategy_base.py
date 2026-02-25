# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: ML strategy base class with cal/initialize/finalize methods






"""
机器学习策略基类

提供ML模型与回测系统的桥接，支持模型加载、特征工程、
预测和信号生成的完整流程，继承自BaseStrategy以保持
与现有回测架构的兼容性。
"""

import os
import datetime
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union, Any, Tuple
from decimal import Decimal
from abc import abstractmethod

from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.enums import DIRECTION_TYPES, MODEL_TYPES
from ginkgo.libs import GLOG
from ginkgo.data import get_bars

# 尝试导入ML模块
try:
    from ginkgo.core.interfaces.model_interface import IModel
    from ginkgo.quant_ml.features import FeatureProcessor, AlphaFactors
    ML_AVAILABLE = True
except ImportError as e:
    GLOG.WARN(f"ML模块不可用: {e}")
    ML_AVAILABLE = False
    IModel = None
    FeatureProcessor = None
    AlphaFactors = None


class StrategyMLBase(BaseStrategy):
    """
    机器学习策略基类
    
    提供ML模型接入回测系统的统一框架，支持：
    - 模型加载和管理
    - 自动特征提取
    - 预测结果转换为交易信号
    - 模型性能监控
    """
    
    __abstract__ = False

    def __init__(
        self,
        name: str = "MLStrategy",
        model_path: Optional[str] = None,
        signal_threshold: float = 0.01,
        position_sizing: str = "fixed",
        max_position_ratio: float = 0.1,
        lookback_days: int = 252,
        feature_config: Optional[Dict] = None,
        enable_monitoring: bool = True,
        *args,
        **kwargs,
    ):
        """
        初始化ML策略
        
        Args:
            name: 策略名称
            model_path: 模型文件路径
            signal_threshold: 信号生成阈值
            position_sizing: 头寸管理方法 ("fixed", "proportional", "kelly")
            max_position_ratio: 最大持仓比例
            lookback_days: 历史数据回看天数
            feature_config: 特征工程配置
            enable_monitoring: 是否启用模型监控
        """
        super(StrategyMLBase, self).__init__(name, *args, **kwargs)
        
        if not ML_AVAILABLE:
            self.log("WARNING", "ML模块不可用，MLBaseStrategy 将以受限模式运行")
            # 在ML模块不可用时，仍然可以创建策略实例，但功能受限
            self._model = None
            self._feature_processor = None
            self._alpha_factors = None
            
            # 设置基本属性
            self._model_path = model_path
            self._model_info = {}
            self._signal_threshold = signal_threshold
            self._position_sizing = position_sizing
            self._max_position_ratio = max_position_ratio
            self._lookback_days = lookback_days
            self._feature_config = feature_config or {}
            self._feature_cache = {}
            self._prediction_cache = {}
            self._enable_monitoring = enable_monitoring
            self._prediction_history = []
            self._performance_metrics = {}
            
            self.log("INFO", f"初始化受限模式ML策略: {name}")
            return
        
        # 模型相关
        self._model: Optional[IModel] = None
        self._model_path: Optional[str] = model_path
        self._model_info: Dict[str, Any] = {}
        
        # 特征工程
        self._feature_processor: Optional[FeatureProcessor] = None
        self._alpha_factors: Optional[AlphaFactors] = None
        self._feature_config = feature_config or {}
        self._lookback_days = lookback_days
        
        # 信号生成
        self._signal_threshold = signal_threshold
        self._position_sizing = position_sizing
        self._max_position_ratio = max_position_ratio
        
        # 数据缓存
        self._feature_cache: Dict[str, pd.DataFrame] = {}
        self._prediction_cache: Dict[str, Dict] = {}
        
        # 性能监控
        self._enable_monitoring = enable_monitoring
        self._prediction_history: List[Dict] = []
        self._performance_metrics: Dict[str, float] = {}
        
        # 初始化组件
        self._initialize_components()
        
        # 加载模型
        if model_path:
            self.load_model(model_path)
        
        self.log("INFO", f"初始化ML策略: {name}")

    def _initialize_components(self) -> None:
        """初始化特征工程组件"""
        try:
            # 初始化特征处理器
            processor_config = self._feature_config.get('processor', {})
            self._feature_processor = FeatureProcessor(**processor_config)
            
            # 初始化Alpha因子计算器
            factors_config = self._feature_config.get('factors', {})
            self._alpha_factors = AlphaFactors(**factors_config)
            
            self.log("DEBUG", "特征工程组件初始化完成")
            
        except Exception as e:
            self.log("ERROR", f"特征工程组件初始化失败: {e}")
            raise e

    def load_model(self, model_path: str) -> bool:
        """
        加载训练好的ML模型
        
        Args:
            model_path: 模型文件路径
            
        Returns:
            bool: 是否加载成功
        """
        try:
            if not os.path.exists(model_path):
                self.log("ERROR", f"模型文件不存在: {model_path}")
                return False
            
            # 加载模型
            self._model = IModel.load(model_path)
            self._model_path = model_path
            
            if not self._model.is_trained:
                self.log("WARNING", "加载的模型尚未训练")
                return False
            
            # 获取模型信息
            self._model_info = self._model.get_metadata()
            
            self.log("INFO", f"模型加载成功: {model_path}")
            self.log("INFO", f"模型信息: {self._model_info.get('name', 'Unknown')}, "
                           f"类型: {self._model_info.get('model_type', 'Unknown')}, "
                           f"特征数: {self._model_info.get('feature_count', 0)}")
            
            return True
            
        except Exception as e:
            self.log("ERROR", f"模型加载失败: {e}")
            return False

    def reload_model(self) -> bool:
        """重新加载模型"""
        if self._model_path:
            return self.load_model(self._model_path)
        else:
            self.log("WARNING", "没有指定模型路径，无法重新加载")
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return self._model_info.copy()

    def is_model_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self._model is not None and self._model.is_trained

    def extract_features(self, code: str, current_time: datetime.datetime, 
                        history_data: Optional[pd.DataFrame] = None) -> Optional[pd.DataFrame]:
        """
        提取特征数据
        
        Args:
            code: 股票代码
            current_time: 当前时间
            history_data: 历史数据（可选，如果不提供则自动获取）
            
        Returns:
            pd.DataFrame: 提取的特征数据
        """
        try:
            # 检查缓存
            cache_key = f"{code}_{current_time.strftime('%Y%m%d')}"
            if cache_key in self._feature_cache:
                cached_features = self._feature_cache[cache_key]
                if len(cached_features) > 0:
                    return cached_features.tail(1)  # 返回最新一行
            
            # 获取历史数据
            if history_data is None:
                start_date = current_time - datetime.timedelta(days=self._lookback_days)
                history_data = get_bars(code, start_date, current_time, as_dataframe=True)
            
            if history_data is None or len(history_data) == 0:
                self.log("WARNING", f"无法获取 {code} 的历史数据")
                return None
            
            # 计算Alpha因子
            features_data = self._alpha_factors.calculate_all_factors(history_data)
            
            if len(features_data) == 0:
                self.log("WARNING", f"特征计算失败: {code}")
                return None
            
            # 缓存特征数据
            self._feature_cache[cache_key] = features_data
            
            # 限制缓存大小
            if len(self._feature_cache) > 100:
                # 删除最旧的缓存项
                oldest_key = min(self._feature_cache.keys())
                del self._feature_cache[oldest_key]
            
            self.log("DEBUG", f"特征提取完成: {code}, 特征数: {features_data.shape[1]}")
            
            return features_data.tail(1)  # 返回最新一行
            
        except Exception as e:
            self.log("ERROR", f"特征提取失败: {code}, {e}")
            return None

    def predict(self, features: pd.DataFrame, code: str) -> Optional[Dict]:
        """
        使用模型进行预测
        
        Args:
            features: 特征数据
            code: 股票代码
            
        Returns:
            Dict: 预测结果，包含prediction, confidence等
        """
        try:
            if not self.is_model_loaded():
                self.log("WARNING", "模型未加载，无法进行预测")
                return None
            
            if features.empty:
                return None
            
            # 特征预处理
            if self._feature_processor.is_fitted:
                processed_features = self._feature_processor.transform(features)
            else:
                # 如果特征处理器未拟合，尝试使用原始特征
                processed_features = features
            
            # 模型预测
            prediction = self._model.predict(processed_features)
            
            if isinstance(prediction, pd.DataFrame):
                pred_value = float(prediction.iloc[0, 0])
            else:
                pred_value = float(prediction[0])
            
            # 计算置信度（简单版本）
            confidence = min(abs(pred_value) / self._signal_threshold, 1.0)
            
            result = {
                'prediction': pred_value,
                'confidence': confidence,
                'timestamp': __import__('ginkgo.trading.time.clock', fromlist=['now']).now(),
                'code': code
            }
            
            self.log("DEBUG", f"预测完成: {code}, 预测值: {pred_value:.4f}, 置信度: {confidence:.3f}")
            
            return result
            
        except Exception as e:
            self.log("ERROR", f"预测失败: {code}, {e}")
            return None

    def generate_signals_from_prediction(self, portfolio_info, code: str, 
                                       prediction_result: Dict) -> List[Signal]:
        """
        从预测结果生成交易信号
        
        Args:
            portfolio_info: 投资组合信息
            code: 股票代码
            prediction_result: 预测结果
            
        Returns:
            List[Signal]: 生成的信号列表
        """
        try:
            signals = []
            
            prediction = prediction_result['prediction']
            confidence = prediction_result['confidence']
            
            # 信号阈值检查
            if abs(prediction) < self._signal_threshold:
                return signals
            
            # 置信度检查
            min_confidence = self._feature_config.get('min_confidence', 0.6)
            if confidence < min_confidence:
                return signals
            
            # 确定交易方向
            if prediction > self._signal_threshold:
                direction = DIRECTION_TYPES.LONG
                reason = f"ML_BUY_pred:{prediction:.4f}_conf:{confidence:.3f}"
            elif prediction < -self._signal_threshold:
                direction = DIRECTION_TYPES.SHORT
                reason = f"ML_SELL_pred:{prediction:.4f}_conf:{confidence:.3f}"
            else:
                return signals
            
            # 检查当前持仓状态
            has_position = code in portfolio_info.get("positions", {})
            
            # 根据持仓状态决定是否生成信号
            if direction == DIRECTION_TYPES.LONG and not has_position:
                # 买入信号
                signals.append(self._create_signal(
                    portfolio_info, code, direction, reason
                ))
            elif direction == DIRECTION_TYPES.SHORT and has_position:
                # 卖出信号
                signals.append(self._create_signal(
                    portfolio_info, code, direction, reason
                ))
            
            return signals
            
        except Exception as e:
            self.log("ERROR", f"信号生成失败: {code}, {e}")
            return []

    def _create_signal(self, portfolio_info, code: str,
                      direction: DIRECTION_TYPES, reason: str):
        """创建交易信号"""
        # 使用基类方法创建信号（自动填充 run_id 等上下文）
        signal = self.create_signal(
            code=code,
            direction=direction,
            reason=reason,
            business_timestamp=portfolio_info.get("now"),
        )

        # 添加ML特定信息
        signal.strategy_name = self.name
        signal.model_type = self._model_info.get('model_type', 'Unknown')

        self.log("INFO", f"生成ML信号: {code} {direction.value} - {reason}")

        return signal

    def update_performance_monitoring(self, code: str, prediction: float, 
                                    actual_return: Optional[float] = None) -> None:
        """
        更新性能监控
        
        Args:
            code: 股票代码
            prediction: 预测值
            actual_return: 实际收益率（如果可用）
        """
        try:
            if not self._enable_monitoring:
                return
            
            record = {
                'timestamp': __import__('ginkgo.trading.time.clock', fromlist=['now']).now(),
                'code': code,
                'prediction': prediction,
                'actual_return': actual_return
            }
            
            self._prediction_history.append(record)
            
            # 限制历史记录长度
            if len(self._prediction_history) > 1000:
                self._prediction_history = self._prediction_history[-500:]
            
            # 计算性能指标
            if len(self._prediction_history) >= 20:
                self._calculate_performance_metrics()
                
        except Exception as e:
            self.log("ERROR", f"性能监控更新失败: {e}")

    def _calculate_performance_metrics(self) -> None:
        """计算性能指标"""
        try:
            recent_records = self._prediction_history[-100:]  # 最近100个预测
            
            predictions = [r['prediction'] for r in recent_records if r['actual_return'] is not None]
            actuals = [r['actual_return'] for r in recent_records if r['actual_return'] is not None]
            
            if len(predictions) < 10:
                return
            
            # 方向准确率
            pred_directions = [1 if p > 0 else -1 for p in predictions]
            actual_directions = [1 if a > 0 else -1 for a in actuals]
            direction_accuracy = np.mean([p == a for p, a in zip(pred_directions, actual_directions)])
            
            # 信息系数 (IC)
            ic = np.corrcoef(predictions, actuals)[0, 1] if len(predictions) > 1 else 0
            
            # 更新性能指标
            self._performance_metrics.update({
                'direction_accuracy': direction_accuracy,
                'information_coefficient': ic,
                'prediction_count': len(predictions),
                'last_update': __import__('ginkgo.trading.time.clock', fromlist=['now']).now()
            })
            
            self.log("DEBUG", f"性能指标更新 - 方向准确率: {direction_accuracy:.3f}, IC: {ic:.3f}")
            
        except Exception as e:
            self.log("ERROR", f"性能指标计算失败: {e}")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return self._performance_metrics.copy()

    def cal(self, portfolio_info, event, *args, **kwargs) -> List[Signal]:
        """
        策略主计算方法（事件驱动）
        
        Args:
            portfolio_info: 投资组合信息
            event: 市场事件
            
        Returns:
            List[Signal]: 生成的信号列表
        """
        super(StrategyMLBase, self).cal(portfolio_info, event)
        
        try:
            # 检查模型是否可用
            if not self.is_model_loaded():
                return []
            
            code = event.code
            current_time = event.timestamp if hasattr(event, 'timestamp') else self.now
            
            # 提取特征
            features = self.extract_features(code, current_time)
            if features is None or features.empty:
                return []
            
            # 进行预测
            prediction_result = self.predict(features, code)
            if prediction_result is None:
                return []
            
            # 生成信号
            signals = self.generate_signals_from_prediction(
                portfolio_info, code, prediction_result
            )
            
            # 更新监控（如果有实际收益率信息）
            self.update_performance_monitoring(
                code, prediction_result['prediction']
            )
            
            return signals
            
        except Exception as e:
            self.log("ERROR", f"ML策略计算失败: {e}")
            return []

    def set_signal_threshold(self, threshold: float) -> None:
        """设置信号生成阈值"""
        self._signal_threshold = threshold
        self.log("INFO", f"信号阈值更新为: {threshold}")

    def set_feature_config(self, config: Dict) -> None:
        """设置特征配置"""
        self._feature_config = config
        # 重新初始化特征工程组件
        self._initialize_components()
        self.log("INFO", "特征配置已更新")

    def get_strategy_summary(self) -> Dict[str, Any]:
        """获取策略摘要信息"""
        return {
            'name': self.name,
            'model_loaded': self.is_model_loaded(),
            'model_info': self._model_info,
            'signal_threshold': self._signal_threshold,
            'position_sizing': self._position_sizing,
            'performance_metrics': self._performance_metrics,
            'feature_cache_size': len(self._feature_cache),
            'prediction_history_size': len(self._prediction_history)
        }

    def __str__(self) -> str:
        model_name = self._model_info.get('name', 'No Model') if self._model_info else 'No Model'
        return f"MLStrategy(name={self.name}, model={model_name})"

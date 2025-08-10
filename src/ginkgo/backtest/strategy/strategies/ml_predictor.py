"""
ML预测策略示例

基于机器学习模型的股价预测策略，展示如何使用StrategyMLBase
构建具体的ML交易策略。
"""

import datetime
import pandas as pd
from typing import List, Dict, Optional
from decimal import Decimal

from .ml_strategy_base import StrategyMLBase
from ...entities.signal import Signal
from ....enums import DIRECTION_TYPES


class StrategyMLPredictor(StrategyMLBase):
    """
    ML预测策略
    
    基于已训练的机器学习模型预测股价未来收益率，
    根据预测结果生成买卖信号的具体策略实现。
    """
    
    __abstract__ = False

    def __init__(
        self,
        name: str = "MLPredictor",
        model_path: Optional[str] = None,
        prediction_horizon: int = 5,  # 预测天数
        confidence_threshold: float = 0.7,  # 置信度阈值
        return_threshold: float = 0.02,  # 收益率阈值
        risk_management: bool = True,
        stop_loss_ratio: float = 0.05,  # 止损比例
        take_profit_ratio: float = 0.10,  # 止盈比例
        *args,
        **kwargs,
    ):
        """
        初始化ML预测策略
        
        Args:
            name: 策略名称
            model_path: ML模型文件路径
            prediction_horizon: 预测时间窗口（天）
            confidence_threshold: 最小置信度阈值
            return_threshold: 预测收益率阈值
            risk_management: 是否启用风险管理
            stop_loss_ratio: 止损比例
            take_profit_ratio: 止盈比例
        """
        # 设置特征工程配置
        feature_config = kwargs.pop('feature_config', {
            'processor': {
                'scaling_method': 'standard',
                'imputation_method': 'mean',
                'feature_selection': True,
                'n_features': 50
            },
            'factors': {
                'use_talib': True
            },
            'min_confidence': confidence_threshold
        })
        
        super(StrategyMLPredictor, self).__init__(
            name=name,
            model_path=model_path,
            signal_threshold=return_threshold,
            feature_config=feature_config,
            *args,
            **kwargs,
        )
        
        # 如果ML模块不可用，策略仍可创建但功能受限
        if not hasattr(self, '_model') or self._model is None:
            self.log("WARNING", "ML模块不可用，预测策略将以受限模式运行")
            # 设置默认值
            self._prediction_horizon = prediction_horizon
            self._confidence_threshold = confidence_threshold
            self._return_threshold = return_threshold
            self._risk_management = risk_management
            self._stop_loss_ratio = Decimal(str(stop_loss_ratio))
            self._take_profit_ratio = Decimal(str(take_profit_ratio))
            self._entry_prices = {}
            self._entry_times = {}
            self._position_directions = {}
            return
        
        self._prediction_horizon = prediction_horizon
        self._confidence_threshold = confidence_threshold
        self._return_threshold = return_threshold
        self._risk_management = risk_management
        self._stop_loss_ratio = Decimal(str(stop_loss_ratio))
        self._take_profit_ratio = Decimal(str(take_profit_ratio))
        
        # 策略状态跟踪
        self._entry_prices: Dict[str, float] = {}  # 记录进场价格
        self._entry_times: Dict[str, datetime.datetime] = {}  # 记录进场时间
        self._position_directions: Dict[str, DIRECTION_TYPES] = {}  # 记录持仓方向
        
        self.log("INFO", f"初始化ML预测策略: {name}")
        self.log("INFO", f"参数 - 预测期:{prediction_horizon}天, 置信度阈值:{confidence_threshold}, 收益率阈值:{return_threshold}")

    def generate_signals_from_prediction(self, portfolio_info, code: str, 
                                       prediction_result: Dict) -> List[Signal]:
        """
        从预测结果生成交易信号（重写父类方法以实现特定逻辑）
        
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
            
            self.log("DEBUG", f"处理预测结果: {code}, 预测:{prediction:.4f}, 置信度:{confidence:.3f}")
            
            # 首先检查风险管理信号
            if self._risk_management:
                risk_signals = self._check_risk_management(portfolio_info, code)
                if risk_signals:
                    signals.extend(risk_signals)
                    return signals  # 风险管理优先
            
            # 置信度检查
            if confidence < self._confidence_threshold:
                self.log("DEBUG", f"置信度不足: {code}, {confidence:.3f} < {self._confidence_threshold}")
                return signals
            
            # 预测收益率阈值检查
            if abs(prediction) < self._return_threshold:
                self.log("DEBUG", f"预测收益率不足: {code}, {abs(prediction):.4f} < {self._return_threshold}")
                return signals
            
            # 检查当前持仓状态
            positions = portfolio_info.get("positions", {})
            has_position = code in positions
            
            # 生成交易信号
            if prediction > self._return_threshold and not has_position:
                # 看涨信号 - 买入
                reason = (f"ML_LONG_pred:{prediction:.4f}_conf:{confidence:.3f}_"
                         f"horizon:{self._prediction_horizon}d")
                
                signal = self._create_signal(
                    portfolio_info, code, DIRECTION_TYPES.LONG, reason
                )
                
                # 记录进场信息
                current_price = self._get_current_price(portfolio_info, code)
                if current_price:
                    self._entry_prices[code] = current_price
                    self._entry_times[code] = portfolio_info["now"]
                    self._position_directions[code] = DIRECTION_TYPES.LONG
                
                signals.append(signal)
                
            elif prediction < -self._return_threshold and has_position:
                # 看跌信号或持仓卖出
                if code in self._position_directions and self._position_directions[code] == DIRECTION_TYPES.LONG:
                    reason = (f"ML_SHORT_pred:{prediction:.4f}_conf:{confidence:.3f}_"
                             f"horizon:{self._prediction_horizon}d")
                    
                    signal = self._create_signal(
                        portfolio_info, code, DIRECTION_TYPES.SHORT, reason
                    )
                    
                    # 清除进场信息
                    self._cleanup_position_info(code)
                    
                    signals.append(signal)
            
            elif prediction < -self._return_threshold and not has_position:
                # 纯做空信号（如果策略支持做空）
                if self._is_short_selling_allowed():
                    reason = (f"ML_SHORT_pred:{prediction:.4f}_conf:{confidence:.3f}_"
                             f"horizon:{self._prediction_horizon}d")
                    
                    signal = self._create_signal(
                        portfolio_info, code, DIRECTION_TYPES.SHORT, reason
                    )
                    
                    # 记录做空进场信息
                    current_price = self._get_current_price(portfolio_info, code)
                    if current_price:
                        self._entry_prices[code] = current_price
                        self._entry_times[code] = portfolio_info["now"]
                        self._position_directions[code] = DIRECTION_TYPES.SHORT
                    
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.log("ERROR", f"ML预测信号生成失败: {code}, {e}")
            return []

    def _check_risk_management(self, portfolio_info, code: str) -> List[Signal]:
        """
        检查风险管理规则
        
        Returns:
            List[Signal]: 风险管理信号
        """
        signals = []
        
        try:
            if code not in self._entry_prices:
                return signals
            
            current_price = self._get_current_price(portfolio_info, code)
            if not current_price:
                return signals
            
            entry_price = self._entry_prices[code]
            position_direction = self._position_directions.get(code)
            
            if position_direction == DIRECTION_TYPES.LONG:
                # 多头持仓风险管理
                price_change = (current_price - entry_price) / entry_price
                
                # 止损
                if price_change <= -float(self._stop_loss_ratio):
                    reason = f"STOP_LOSS_entry:{entry_price:.2f}_current:{current_price:.2f}_loss:{price_change:.3f}"
                    signal = self._create_signal(
                        portfolio_info, code, DIRECTION_TYPES.SHORT, reason
                    )
                    signals.append(signal)
                    self.log("INFO", f"触发止损: {code}, {reason}")
                
                # 止盈
                elif price_change >= float(self._take_profit_ratio):
                    reason = f"TAKE_PROFIT_entry:{entry_price:.2f}_current:{current_price:.2f}_profit:{price_change:.3f}"
                    signal = self._create_signal(
                        portfolio_info, code, DIRECTION_TYPES.SHORT, reason
                    )
                    signals.append(signal)
                    self.log("INFO", f"触发止盈: {code}, {reason}")
            
            elif position_direction == DIRECTION_TYPES.SHORT:
                # 空头持仓风险管理
                price_change = (entry_price - current_price) / entry_price
                
                # 止损（空头）
                if price_change <= -float(self._stop_loss_ratio):
                    reason = f"SHORT_STOP_LOSS_entry:{entry_price:.2f}_current:{current_price:.2f}_loss:{price_change:.3f}"
                    signal = self._create_signal(
                        portfolio_info, code, DIRECTION_TYPES.LONG, reason
                    )
                    signals.append(signal)
                    self.log("INFO", f"空头止损: {code}, {reason}")
                
                # 止盈（空头）
                elif price_change >= float(self._take_profit_ratio):
                    reason = f"SHORT_TAKE_PROFIT_entry:{entry_price:.2f}_current:{current_price:.2f}_profit:{price_change:.3f}"
                    signal = self._create_signal(
                        portfolio_info, code, DIRECTION_TYPES.LONG, reason
                    )
                    signals.append(signal)
                    self.log("INFO", f"空头止盈: {code}, {reason}")
            
            # 如果生成了风险管理信号，清理持仓信息
            if signals:
                self._cleanup_position_info(code)
                
        except Exception as e:
            self.log("ERROR", f"风险管理检查失败: {code}, {e}")
        
        return signals

    def _get_current_price(self, portfolio_info, code: str) -> Optional[float]:
        """获取当前价格"""
        try:
            positions = portfolio_info.get("positions", {})
            if code in positions:
                return float(positions[code].price)
            
            # 如果没有持仓，尝试从其他途径获取当前价格
            # 这里可以根据实际情况实现
            return None
            
        except Exception as e:
            self.log("ERROR", f"获取当前价格失败: {code}, {e}")
            return None

    def _is_short_selling_allowed(self) -> bool:
        """检查是否允许做空（可以根据策略配置或市场规则决定）"""
        # 这里可以根据实际需求实现
        return False  # 默认不允许做空

    def _cleanup_position_info(self, code: str) -> None:
        """清理持仓信息"""
        self._entry_prices.pop(code, None)
        self._entry_times.pop(code, None)
        self._position_directions.pop(code, None)

    def get_position_info(self) -> Dict[str, Dict]:
        """获取持仓信息"""
        position_info = {}
        
        for code in self._entry_prices:
            position_info[code] = {
                'entry_price': self._entry_prices.get(code),
                'entry_time': self._entry_times.get(code),
                'direction': self._position_directions.get(code),
                'duration': (datetime.datetime.now() - self._entry_times.get(code, datetime.datetime.now())).days
            }
        
        return position_info

    def get_strategy_summary(self) -> Dict[str, any]:
        """获取策略摘要（扩展父类方法）"""
        base_summary = super().get_strategy_summary()
        
        # 添加预测策略特定信息
        base_summary.update({
            'prediction_horizon': self._prediction_horizon,
            'confidence_threshold': self._confidence_threshold,
            'return_threshold': self._return_threshold,
            'risk_management_enabled': self._risk_management,
            'stop_loss_ratio': float(self._stop_loss_ratio),
            'take_profit_ratio': float(self._take_profit_ratio),
            'active_positions': len(self._entry_prices),
            'position_info': self.get_position_info()
        })
        
        return base_summary

    def __str__(self) -> str:
        model_name = self._model_info.get('name', 'No Model') if self._model_info else 'No Model'
        return (f"MLPredictor(name={self.name}, model={model_name}, "
                f"horizon={self._prediction_horizon}d, threshold={self._return_threshold})")
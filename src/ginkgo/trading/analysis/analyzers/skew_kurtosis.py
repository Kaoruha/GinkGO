from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import RECORDSTAGE_TYPES
import pandas as pd
import numpy as np
from scipy import stats


class SkewKurtosis(BaseAnalyzer):
    """偏度/峰度分析器 - 分析收益率分布的偏斜程度和尖峭程度"""
    
    __abstract__ = False

    def __init__(self, name: str = "skew_kurtosis", window: int = 252, *args, **kwargs):
        super(SkewKurtosis, self).__init__(name, *args, **kwargs)
        # 在每天结束时激活计算
        self.add_active_stage(RECORDSTAGE_TYPES.ENDDAY)
        # 在每天结束时记录到数据库
        self.set_record_stage(RECORDSTAGE_TYPES.ENDDAY)
        
        # 配置参数
        self._window = window  # 滚动窗口大小
        
        # 内部状态
        self._returns = []
        self._last_worth = None

    def _do_activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """计算偏度值（存储偏度，峰度通过属性获取）"""
        current_worth = portfolio_info.get("worth", 0)
        
        if self._last_worth is None:
            self._last_worth = current_worth
            skewness = 0.0
        else:
            # 计算日收益率
            if self._last_worth > 0:
                daily_return = (current_worth - self._last_worth) / self._last_worth
                self._returns.append(daily_return)
                
                # 保持窗口大小
                if len(self._returns) > self._window:
                    self._returns.pop(0)
                
                # 计算偏度 (需要至少30个数据点)
                if len(self._returns) >= 30:
                    returns_array = np.array(self._returns)
                    skewness = stats.skew(returns_array)
                else:
                    skewness = 0.0
            else:
                skewness = 0.0
            
            self._last_worth = current_worth
        
        self.add_data(skewness)

    def _do_record(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """记录偏度到数据库"""
        self.add_record()

    @property
    def current_skewness(self) -> float:
        """当前偏度值（只读属性）"""
        return self.current_value

    @property
    def current_kurtosis(self) -> float:
        """当前峰度值（只读属性）"""
        if len(self._returns) >= 30:
            returns_array = np.array(self._returns)
            return float(stats.kurtosis(returns_array))
        return 0.0

    @property
    def excess_kurtosis(self) -> float:
        """超额峰度值（峰度-3）（只读属性）"""
        return self.current_kurtosis - 3.0

    @property
    def distribution_description(self) -> str:
        """分布特征描述（只读属性）"""
        skew = self.current_skewness
        kurt = self.current_kurtosis
        
        # 偏度解释
        if skew > 0.5:
            skew_desc = "右偏分布（大幅盈利概率较高）"
        elif skew < -0.5:
            skew_desc = "左偏分布（大幅亏损概率较高）"
        else:
            skew_desc = "近似对称分布"
        
        # 峰度解释
        if kurt > 3.5:
            kurt_desc = "尖峭分布（极端收益频繁）"
        elif kurt < 2.5:
            kurt_desc = "平坦分布（极端收益较少）"
        else:
            kurt_desc = "正态分布特征"
        
        return f"{skew_desc}, {kurt_desc}"

    @property
    def returns_count(self) -> int:
        """收益率数据点数量（只读属性）"""
        return len(self._returns)

    @property
    def is_normal_distribution(self) -> bool:
        """是否接近正态分布（只读属性）"""
        skew = abs(self.current_skewness)
        kurt = abs(self.current_kurtosis - 3.0)  # 正态分布峰度为3
        
        # 简单的正态性判断
        return skew < 0.5 and kurt < 0.5 and len(self._returns) >= 30
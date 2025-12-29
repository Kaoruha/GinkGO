# Upstream: Trading Strategies, Analysis Modules, Backtest Engines
# Downstream: ClickHouse, MySQL, MongoDB
# Role: Parameter Metadata Service服务提供ParameterMetadataService参数元数据管理和查询






"""
Parameter Metadata Service - 参数元数据服务

管理组件参数的元数据信息，包括参数名称、类型、描述等。
提供参数索引到参数名称的映射功能，用于改善用户界面显示。
优先使用动态参数提取，回退到预定义映射。
"""

from typing import Dict, List, Optional, Any
from ginkgo.libs import GLOG
from ginkgo.data.services.base_service import BaseService
from ginkgo.data.services.component_parameter_extractor import get_component_parameter_names, get_component_parameter_name


class ParameterMetadataService(BaseService):
    """参数元数据服务"""

    def __init__(self):
        # 不需要CRUD依赖，这是一个纯服务层
        pass

    def get_component_parameter_names(self, component_name: str, file_type: str = None, file_path: str = None) -> Dict[int, str]:
        """
        根据组件名称获取参数名称映射

        优先使用动态参数提取，回退到预定义映射。

        Args:
            component_name: 组件名称（如 "fixed_selector", "random_choice"）
            file_type: 文件类型（可选，用于更精确的匹配）
            file_path: 文件路径（可选，用于动态分析）

        Returns:
            Dict[int, str]: 参数索引到参数名称的映射，如 {0: "codes", 1: "volume"}
        """
        # 标准化组件名称（去除前缀和后缀）
        clean_name = self._normalize_component_name(component_name)

        # 1. 优先尝试动态参数提取（使用数据库内容）
        try:
            dynamic_params = get_component_parameter_names(clean_name, None, file_type, None)
            if dynamic_params:
                GLOG.DEBUG(f"使用动态提取的参数映射 {clean_name}: {dynamic_params}")
                return dynamic_params
        except Exception as e:
            GLOG.DEBUG(f"动态参数提取失败 {clean_name}: {e}")

        # 2. 回退到预定义映射
        GLOG.DEBUG(f"回退到预定义参数映射 {clean_name}")
        if file_type:
            return self._get_params_by_type_and_name(clean_name, file_type)
        else:
            return self._get_params_by_name(clean_name)

    def _normalize_component_name(self, component_name: str) -> str:
        """标准化组件名称"""
        # 移除常见前缀
        prefixes = ["present_", "preset_", "test_"]
        for prefix in prefixes:
            if component_name.startswith(prefix):
                component_name = component_name[len(prefix):]

        # 移除常见后缀
        suffixes = ["_strategy", "_selector", "_sizer", "_analyzer", "_risk"]
        for suffix in suffixes:
            if component_name.endswith(suffix):
                component_name = component_name[:-len(suffix)]

        return component_name

    def _get_params_by_type_and_name(self, component_name: str, file_type: str) -> Dict[int, str]:
        """根据文件类型和组件名称获取参数映射"""
        # 定义参数映射规则
        strategy_params = {
            "random_signal": {0: "buy_probability", 1: "sell_probability"},  # RandomSignalStrategy 买入/卖出概率
            "bollinger_bands": {0: "period", 1: "std_dev"},
            "moving_average": {0: "short_period", 1: "long_period"},
            "rsi": {0: "period", 1: "overbought", 2: "oversold"},
            "macd": {0: "fast_period", 1: "slow_period", 2: "signal_period"},
            "trend_follow": {0: "short_ma", 1: "long_ma"},
        }

        selector_params = {
            "fixed": {0: "codes"},
            "universe": {0: "codes"},
            "random": {0: "count", 1: "seed"},
            "sector": {0: "sector_code"},
            "market_cap": {0: "min_cap", 1: "max_cap"},
        }

        sizer_params = {
            "fixed": {0: "volume"},
            "percent": {0: "percent"},
            "volatility": {0: "base_volume", 1: "volatility_factor"},
            "kelly": {0: "win_rate", 1: "avg_win", 2: "avg_loss"},
            "atr": {0: "atr_multiplier", 1: "risk_percent"},
        }

        risk_manager_params = {
            "position_ratio": {0: "max_ratio", 1: "max_total_ratio"},
            "loss_limit": {0: "loss_limit"},
            "profit_limit": {0: "profit_limit"},
            "max_drawdown": {0: "max_drawdown"},
            "var": {0: "confidence_level", 1: "time_horizon"},
        }

        analyzer_params = {
            "sharpe": {},  # 无参数
            "max_drawdown": {},
            "calmar": {},
            "profit_loss": {},
            "win_rate": {},
        }

        # 根据文件类型选择对应的参数映射
        if file_type.lower() in ["strategy", "strategies"]:
            return strategy_params.get(component_name, {})
        elif file_type.lower() in ["selector", "selectors"]:
            return selector_params.get(component_name, {})
        elif file_type.lower() in ["sizer", "sizers"]:
            return sizer_params.get(component_name, {})
        elif file_type.lower() in ["risk_manager", "risk_managers", "risk"]:
            return risk_manager_params.get(component_name, {})
        elif file_type.lower() in ["analyzer", "analyzers"]:
            return analyzer_params.get(component_name, {})
        else:
            return {}

    def _get_params_by_name(self, component_name: str) -> Dict[int, str]:
        """仅根据组件名称推断参数映射（通过名称模式匹配）"""
        param_mappings = {
            # Strategy components
            "random_signal": {0: "buy_probability", 1: "sell_probability"},  # RandomSignalStrategy
            "bollinger": {0: "period", 1: "std_dev"},
            "moving": {0: "short_period", 1: "long_period"},
            "ma": {0: "short_period", 1: "long_period"},
            "rsi": {0: "period", 1: "overbought", 2: "oversold"},
            "macd": {0: "fast_period", 1: "slow_period", 2: "signal_period"},
            "trend": {0: "short_ma", 1: "long_ma"},

            # Selector components
            "fixed": {0: "codes"},
            "selector": {0: "codes"},
            "universe": {0: "codes"},
            "random": {0: "count", 1: "seed"},
            "sector": {0: "sector_code"},
            "market": {0: "min_cap", 1: "max_cap"},
            "cap": {0: "min_cap", 1: "max_cap"},

            # Sizer components
            "sizer": {0: "volume"},
            "fixed_sizer": {0: "volume"},
            "percent": {0: "percent"},
            "volatility": {0: "base_volume", 1: "volatility_factor"},
            "kelly": {0: "win_rate", 1: "avg_win", 2: "avg_loss"},
            "atr": {0: "atr_multiplier", 1: "risk_percent"},

            # Risk Manager components
            "risk": {},
            "position": {0: "max_ratio", 1: "max_total_ratio"},
            "ratio": {0: "max_ratio", 1: "max_total_ratio"},
            "loss": {0: "loss_limit"},
            "profit": {0: "profit_limit"},
            "drawdown": {0: "max_drawdown"},
            "var": {0: "confidence_level", 1: "time_horizon"},

            # Analyzer components
            "sharpe": {},
            "max_dd": {},
            "calmar": {},
            "pl": {},
            "profit_loss": {},
            "win": {},
        }

        # 查找最佳匹配
        for pattern, params in param_mappings.items():
            if pattern in component_name.lower() or component_name.lower() in pattern:
                return params

        # 如果没有匹配，返回空映射
        return {}

    def get_parameter_display_name(self, component_name: str, param_index: int,
                                  param_value: str = None, file_type: str = None, file_path: str = None) -> str:
        """
        获取参数的显示名称

        Args:
            component_name: 组件名称
            param_index: 参数索引
            param_value: 参数值（可选，用于推断参数类型）
            file_type: 文件类型（可选）
            file_path: 文件路径（可选，用于动态分析）

        Returns:
            str: 参数显示名称，如果无法映射则返回索引
        """
        # 优先尝试动态参数提取
        try:
            dynamic_name = get_component_parameter_name(component_name, param_index, file_path, file_type)
            if dynamic_name and dynamic_name != f"param_{param_index}":
                return dynamic_name
        except Exception as e:
            GLOG.DEBUG(f"动态参数名称提取失败: {e}")

        # 回退到预定义映射
        param_names = self.get_component_parameter_names(component_name, file_type, file_path)

        if param_index in param_names:
            return param_names[param_index]
        else:
            # 尝试根据值推断参数名称
            if param_value:
                inferred_name = self._infer_param_name_from_value(param_value)
                if inferred_name:
                    return inferred_name

            # 无法推断则返回索引
            return f"param_{param_index}"

    def _infer_param_name_from_value(self, param_value: str) -> Optional[str]:
        """根据参数值推断参数名称"""
        # 股票代码模式
        if (len(param_value) == 6 and param_value.isdigit()) or \
           (len(param_value) == 9 and '.' in param_value and param_value.count('.') == 1):
            return "codes"

        # 整数模式（可能是股数）
        if param_value.isdigit() and len(param_value) >= 3:
            return "volume"

        # 浮点数模式（可能是概率或比例）
        try:
            float_val = float(param_value)
            if 0 <= float_val <= 1:
                return "probability" if float_val < 0.5 else "ratio"
            elif 0 < float_val <= 100:
                return "percent"
        except ValueError:
            pass

        return None

    def format_parameter_for_display(self, component_name: str, param_index: int,
                                    param_value: str, file_type: str = None) -> str:
        """
        格式化参数用于显示

        Args:
            component_name: 组件名称
            param_index: 参数索引
            param_value: 参数值
            file_type: 文件类型

        Returns:
            str: 格式化的参数字符串，如 "codes: 000001.SZ" 或 "[0]: 1000"
        """
        param_name = self.get_parameter_display_name(
            component_name, param_index, param_value, file_type
        )

        # 格式化参数值
        formatted_value = self._format_param_value(param_value)

        return f"{param_name}: {formatted_value}"

    def _format_param_value(self, param_value: str) -> str:
        """格式化参数值以提高可读性"""
        # 股票代码格式
        if len(param_value) == 6 and param_value.isdigit():
            return f"{param_value}.SZ"  # 默认为深圳股票

        # 数字格式化
        try:
            if '.' in param_value:
                float_val = float(param_value)
                if float_val.is_integer():
                    return str(int(float_val))
                else:
                    # 保留2位小数
                    return f"{float_val:.2f}"
            else:
                int_val = int(param_value)
                # 大数字添加千分位
                if int_val >= 1000:
                    return f"{int_val:,}"
                return str(int_val)
        except ValueError:
            pass

        return param_value
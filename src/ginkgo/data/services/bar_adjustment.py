# Upstream: BarService (调用复权计算逻辑)
# Downstream: AdjustfactorService (复权因子数据来源)、ModelList/MBar (数据格式)
# Role: BarAdjustment K线价格复权计算模块，提供前复权/后复权/多股票批量复权功能


"""
Bar 价格复权计算模块

从 BarService 中提取的复权相关逻辑，包含：
- 单股票复权（DataFrame和ModelList两种格式）
- 高性能矩阵化复权计算
- 多股票批量复权
- DataFrame/ModelList 互转工具
"""

from typing import List, Any

import pandas as pd

from ginkgo.enums import ADJUSTMENT_TYPES
from ginkgo.libs import GLOG, to_decimal


# ==================== DataFrame/ModelList 转换工具 ====================


def convert_modellist_to_dataframe(bars_data) -> pd.DataFrame:
    """
    将ModelList转换为DataFrame

    Args:
        bars_data: ModelList数据

    Returns:
        DataFrame格式数据
    """
    if isinstance(bars_data, pd.DataFrame):
        return bars_data.copy()

    if hasattr(bars_data, 'to_dataframe'):
        return bars_data.to_dataframe()

    # 手动转换
    return pd.DataFrame([{
        'code': bar.code,
        'timestamp': bar.timestamp,
        'open': float(bar.open),
        'high': float(bar.high),
        'low': float(bar.low),
        'close': float(bar.close),
        'volume': bar.volume,
        'amount': float(bar.amount) if bar.amount else 0,
        'frequency': getattr(bar, 'frequency', None),
        'adjustflag': getattr(bar, 'adjustflag', None)
    } for bar in bars_data])


def convert_dataframe_to_modellist(df: pd.DataFrame, crud_repo) -> 'ModelList':
    """
    将DataFrame转换为ModelList

    Args:
        df: DataFrame数据
        crud_repo: CRUD仓库实例，用于创建ModelList

    Returns:
        ModelList格式数据
    """
    if df.empty:
        from ginkgo.data.crud.model_conversion import ModelList
        return ModelList([], crud_repo)

    try:
        from ginkgo.data.models.model_bar import MBar
        from ginkgo.libs.data.number import to_decimal
        from ginkgo.data.crud.model_conversion import ModelList

        bars = []
        for _, row in df.iterrows():
            bar = MBar()
            bar.code = row['code']
            bar.timestamp = row['timestamp']
            bar.open = to_decimal(row['open'])
            bar.high = to_decimal(row['high'])
            bar.low = to_decimal(row['low'])
            bar.close = to_decimal(row['close'])
            bar.volume = int(row['volume'])
            bar.amount = to_decimal(row['amount']) if pd.notna(row.get('amount')) else None

            # 保持其他字段（如果存在）
            if 'frequency' in row and pd.notna(row['frequency']):
                bar.frequency = row['frequency']
            if 'adjustflag' in row and pd.notna(row['adjustflag']):
                bar.adjustflag = row['adjustflag']

            bars.append(bar)

        return ModelList(bars, crud_repo)

    except Exception as e:
        GLOG.ERROR(f"Failed to convert DataFrame to ModelList: {e}")
        # 返回空ModelList
        from ginkgo.data.crud.model_conversion import ModelList
        return ModelList([], crud_repo)


# ==================== 复权因子获取 ====================


def get_precomputed_adjustment_factors(
    code: str,
    dates,
    adjustment_type: ADJUSTMENT_TYPES,
    adjustfactor_service,
) -> pd.DataFrame:
    """
    获取预计算的复权系数

    Args:
        code: 股票代码
        dates: 需要查询的日期数组
        adjustment_type: 复权类型
        adjustfactor_service: 复权因子服务实例

    Returns:
        DataFrame包含timestamp和复权系数列
    """
    try:
        # 确定复权因子列名
        if adjustment_type == ADJUSTMENT_TYPES.FORE:
            factor_column = 'foreadjustfactor'
        else:  # ADJUSTMENT_TYPES.BACK
            factor_column = 'backadjustfactor'

        # 调用AdjustfactorService获取预计算复权因子
        # TODO: 实现get_precomputed_factors方法
        # 目前使用原始adjustfactor数据作为fallback
        start_date = min(dates)
        end_date = max(dates)

        # 获取原始adjustfactor数据
        result = adjustfactor_service.get(
            code=code, start_date=start_date, end_date=end_date
        )

        if not result.success or len(result.data) == 0:
            return pd.DataFrame(columns=['timestamp', factor_column])

        # 使用ServiceResult.data中的ModelList转换为DataFrame
        df_factors = result.data.to_dataframe()

        if df_factors.empty:
            return pd.DataFrame(columns=['timestamp', factor_column])

        # 简化处理：目前假设fore/back因子需要基于adjustfactor计算
        # TODO: 替换为真正的预计算因子查询
        if factor_column in df_factors.columns:
            # 如果已经有预计算的因子，直接返回
            return df_factors[['timestamp', factor_column]].copy()
        else:
            # 基于adjustfactor计算临时因子（仅用于测试）
            if 'adjustfactor' in df_factors.columns and not df_factors.empty():
                latest_factor = df_factors['adjustfactor'].iloc[-1]
                if adjustment_type == ADJUSTMENT_TYPES.FORE:
                    # 前复权系数 = 最新因子 / 历史因子
                    df_factors[factor_column] = latest_factor / df_factors['adjustfactor']
                else:
                    # 后复权系数 = 历史因子 / 最早因子
                    earliest_factor = df_factors['adjustfactor'].iloc[0]
                    df_factors[factor_column] = df_factors['adjustfactor'] / earliest_factor

                return df_factors[['timestamp', factor_column]].copy()

        return pd.DataFrame(columns=['timestamp', factor_column])

    except Exception as e:
        GLOG.ERROR(f"Failed to get precomputed adjustment factors for {code}: {e}")
        return pd.DataFrame(columns=['timestamp', 'foreadjustfactor', 'backadjustfactor'])


# ==================== 核心复权计算 ====================


def calculate_adjusted_prices(
    bars_df: pd.DataFrame,
    adjustfactors_df: pd.DataFrame,
    adjustment_type: ADJUSTMENT_TYPES,
) -> pd.DataFrame:
    """
    计算价格复权后的K线数据（使用复权因子DataFrame）

    Args:
        bars_df: K线数据DataFrame
        adjustfactors_df: 复权因子DataFrame
        adjustment_type: 复权类型

    Returns:
        复权后的DataFrame
    """
    adjusted_df = bars_df.copy()

    # 选择复权因子列
    if adjustment_type == ADJUSTMENT_TYPES.FORE:
        factor_column = "foreadjustfactor"
    elif adjustment_type == ADJUSTMENT_TYPES.BACK:
        factor_column = "backadjustfactor"
    else:
        return adjusted_df  # 无需复权

    # 合并K线数据和复权因子
    merged_df = pd.merge(adjusted_df, adjustfactors_df[["timestamp", factor_column]], on="timestamp", how="left")

    # 填充缺失复权因子为1.0（无复权）
    merged_df[factor_column] = merged_df[factor_column].fillna(1.0)

    # 复权计算 - 应用到价格字段（OHLC）
    price_columns = ["open", "high", "low", "close"]
    for col in price_columns:
        if col in merged_df.columns:
            merged_df[col] = merged_df[col] * merged_df[factor_column]

    # 成交额也需要复权调整
    if "amount" in merged_df.columns:
        merged_df["amount"] = merged_df["amount"] * merged_df[factor_column]

    # 成交量保持不变
    # 删除临时复权因子列
    result_df = merged_df.drop(columns=[factor_column])

    return result_df


def apply_matrix_adjustment(
    bars_df: pd.DataFrame,
    factors_df: pd.DataFrame,
    adjustment_type: ADJUSTMENT_TYPES,
) -> pd.DataFrame:
    """
    高性能矩阵化复权计算

    利用pandas向量化操作，批量应用复权因子到所有价格数据

    Args:
        bars_df: K线数据DataFrame
        factors_df: 复权因子DataFrame
        adjustment_type: 复权类型

    Returns:
        复权后的DataFrame
    """
    if bars_df.empty or factors_df.empty:
        return bars_df

    try:
        # 确定复权因子列名
        factor_column = 'foreadjustfactor' if adjustment_type == ADJUSTMENT_TYPES.FORE else 'backadjustfactor'

        # 合并K线数据和复权系数
        merged_df = bars_df.merge(
            factors_df[['timestamp', factor_column]],
            on='timestamp',
            how='left'
        )

        # 填充缺失复权系数为1.0（无复权）
        merged_df[factor_column] = merged_df[factor_column].fillna(1.0)

        # 向量化复权计算 - 一次性应用到所有价格字段
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in merged_df.columns:
                merged_df[col] = merged_df[col] * merged_df[factor_column]

        # 成交额也需要复权调整
        if 'amount' in merged_df.columns:
            merged_df['amount'] = merged_df['amount'] * merged_df[factor_column]

        # 删除临时复权系数列，返回干净的DataFrame
        result_df = merged_df.drop(columns=[factor_column])

        return result_df

    except Exception as e:
        GLOG.ERROR(f"Failed to apply matrix adjustment: {e}")
        return bars_df


# ==================== 单股票复权（含格式转换） ====================


def apply_price_adjustment(
    bars_data,
    code: str,
    adjustment_type: ADJUSTMENT_TYPES,
    adjustfactor_service,
) -> Any:
    """
    对K线数据应用价格复权（支持DataFrame和ModelList输入）

    Args:
        bars_data: 原始K线数据（DataFrame或ModelList）
        code: 股票代码
        adjustment_type: 复权类型
        adjustfactor_service: 复权因子服务实例

    Returns:
        复权后的K线数据（与输入格式一致）
    """
    if not code:
        GLOG.ERROR("Stock code required for price adjustment")
        return bars_data

    # 处理空数据
    if (isinstance(bars_data, pd.DataFrame) and bars_data.empty) or (
        isinstance(bars_data, list) and len(bars_data) == 0
    ):
        return bars_data

    try:
        # 转换为DataFrame进行计算
        if isinstance(bars_data, pd.DataFrame):
            bars_df = bars_data.copy()
        else:
            # 将模型列表转换为DataFrame
            bars_df = pd.DataFrame(
                [
                    {
                        "code": bar.code,
                        "timestamp": bar.timestamp,
                        "open": float(bar.open),
                        "high": float(bar.high),
                        "low": float(bar.low),
                        "close": float(bar.close),
                        "volume": bar.volume,
                        "amount": float(bar.amount),
                    }
                    for bar in bars_data
                ]
            )

        if bars_df.empty:
            return bars_data

        # 获取相同日期范围的复权因子
        start_date = bars_df["timestamp"].min()
        end_date = bars_df["timestamp"].max()

        adjustfactors_result = adjustfactor_service.get(
            code=code, start_date=start_date, end_date=end_date
        )

        if not adjustfactors_result.success or not adjustfactors_result.data:
            GLOG.DEBUG(f"No adjustment factors found for {code}, returning original data")
            return bars_data

        # 将ModelList转换为DataFrame
        adjustfactors_df = adjustfactors_result.data.to_dataframe()

        if adjustfactors_df.empty:
            GLOG.DEBUG(f"No adjustment factors found for {code}, returning original data")
            return bars_data

        # 应用复权因子
        adjusted_df = calculate_adjusted_prices(bars_df, adjustfactors_df, adjustment_type)

        # 以原始格式返回
        if isinstance(bars_data, pd.DataFrame):
            return adjusted_df
        else:
            # 转换回模型列表
            from ginkgo.data.models.model_bar import MBar

            adjusted_bars = []
            for _, row in adjusted_df.iterrows():
                bar = MBar()
                bar.code = row["code"]
                bar.timestamp = row["timestamp"]
                bar.open = to_decimal(row["open"])
                bar.high = to_decimal(row["high"])
                bar.low = to_decimal(row["low"])
                bar.close = to_decimal(row["close"])
                bar.volume = int(row["volume"])
                bar.amount = to_decimal(row["amount"])
                adjusted_bars.append(bar)
            return adjusted_bars

    except Exception as e:
        GLOG.ERROR(f"Failed to apply price adjustment for {code}: {e}")
        return bars_data


def apply_price_adjustment_to_modellist(
    bars_data,
    code: str,
    adjustment_type: ADJUSTMENT_TYPES,
    adjustfactor_service,
    crud_repo,
) -> Any:
    """
    对ModelList应用复权计算，返回ModelList格式

    内部使用DataFrame进行高性能矩阵化计算，但最终转换为ModelList保持接口一致性

    Args:
        bars_data: 原始K线数据ModelList
        code: 股票代码
        adjustment_type: 复权类型
        adjustfactor_service: 复权因子服务实例
        crud_repo: CRUD仓库实例，用于创建ModelList

    Returns:
        复权后的K线数据ModelList
    """
    if not code:
        GLOG.ERROR("Stock code required for price adjustment")
        return bars_data

    # 处理空数据
    if not bars_data:
        return bars_data

    try:
        # Step 1: 转换为DataFrame进行高性能计算
        df_bars = convert_modellist_to_dataframe(bars_data)

        if df_bars.empty:
            return bars_data

        # Step 2: 获取预计算的复权系数
        factors_df = get_precomputed_adjustment_factors(
            code=code,
            dates=df_bars['timestamp'].unique(),
            adjustment_type=adjustment_type,
            adjustfactor_service=adjustfactor_service,
        )

        if factors_df.empty:
            GLOG.DEBUG(f"No precomputed adjustment factors found for {code}, returning original data")
            return bars_data

        # Step 3: 矩阵化复权计算
        adjusted_df = apply_matrix_adjustment(df_bars, factors_df, adjustment_type)

        # Step 4: 转换回ModelList格式
        adjusted_modellist = convert_dataframe_to_modellist(adjusted_df, crud_repo)

        return adjusted_modellist

    except Exception as e:
        GLOG.ERROR(f"Failed to apply price adjustment for {code}: {e}")
        return bars_data


# ==================== 多股票批量复权 ====================

# TODO: 多股票复权方法性能优化
# 当前多股票批量复权实现存在性能问题，在大数据量处理时效率较低
# 需要优化的方向：
# 1. 批量复权因子获取，避免逐股票查询
# 2. 向量化计算替代逐行处理
# 3. 内存使用优化，减少数据复制
# 4. 并行处理多股票复权
# 未来版本需要重构以提升批量处理性能


def apply_price_adjustment_multi_stock(
    bars_data,
    adjustment_type: ADJUSTMENT_TYPES,
    adjustfactor_service,
    crud_repo=None,
) -> Any:
    """
    对多股票K线数据批量应用价格复权

    按股票代码分组，逐个应用复权因子

    Args:
        bars_data: 多股票K线数据（DataFrame或ModelList）
        adjustment_type: 复权类型
        adjustfactor_service: 复权因子服务实例
        crud_repo: CRUD仓库实例（ModelList格式时需要）

    Returns:
        复权后的K线数据（与输入格式一致）
    """
    # 处理空数据
    if (isinstance(bars_data, pd.DataFrame) and bars_data.empty) or (
        isinstance(bars_data, list) and len(bars_data) == 0
    ):
        return bars_data

    try:
        if isinstance(bars_data, pd.DataFrame):
            # DataFrame处理 - 按股票代码分组
            if "code" not in bars_data.columns:
                GLOG.ERROR("Cannot apply multi-stock adjustment: 'code' column missing")
                return bars_data

            # 按股票代码分组并逐个复权
            adjusted_dfs = []
            unique_codes = bars_data["code"].unique()

            GLOG.INFO(f"Applying {adjustment_type.value} adjustment to {len(unique_codes)} stocks")

            for code in unique_codes:
                stock_data = bars_data[bars_data["code"] == code].copy()
                adjusted_stock_data = apply_price_adjustment(stock_data, code, adjustment_type, adjustfactor_service)
                adjusted_dfs.append(adjusted_stock_data)

            # 合并所有复权后的数据
            result_df = pd.concat(adjusted_dfs, ignore_index=True)

            # 按原始顺序排序（timestamp和code）
            if "timestamp" in result_df.columns:
                result_df = result_df.sort_values(["timestamp", "code"])

            return result_df

        else:
            # ModelList处理 - 按股票代码分组
            if not hasattr(bars_data[0], "code"):
                GLOG.ERROR("Cannot apply multi-stock adjustment: models missing 'code' attribute")
                return bars_data

            # 按股票代码分组
            code_to_models = {}
            for bar in bars_data:
                code = bar.code
                if code not in code_to_models:
                    code_to_models[code] = []
                code_to_models[code].append(bar)

            # 对每只股票的数据应用复权
            adjusted_models = []
            unique_codes = list(code_to_models.keys())

            GLOG.INFO(f"Applying {adjustment_type.value} adjustment to {len(unique_codes)} stocks")

            for code in unique_codes:
                stock_models = code_to_models[code]
                adjusted_stock_models = apply_price_adjustment(
                    stock_models, code, adjustment_type, adjustfactor_service
                )
                adjusted_models.extend(adjusted_stock_models)

            # 保持原始顺序
            return adjusted_models

    except Exception as e:
        GLOG.ERROR(f"Failed to apply multi-stock price adjustment: {e}")
        return bars_data

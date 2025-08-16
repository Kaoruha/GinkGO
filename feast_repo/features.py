#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Feast特征定义文件 - 基于ClickHouse的日线数据特征
"""
from datetime import timedelta
from feast import Entity, FeatureView, ValueType
from feast.types import Float64, Int64, String
from feast import Field
from feast.infra.offline_stores.contrib.clickhouse_offline_store.clickhouse_source import ClickhouseSource

# 定义股票实体 - 使用code作为实体键
stock_entity = Entity(
    name="code", 
    value_type=ValueType.STRING, 
    description="股票代码实体，如000001.SZ"
)

# 定义ClickHouse数据源 - 指向ginkgo.bar表
stock_daily_source = ClickhouseSource(
    name="stock_daily_source",
    table="ginkgo.bar",  # 使用现有的MBar表
    timestamp_field="timestamp",  # MBar模型的timestamp字段
    # 注意：ClickHouse中没有update_at字段，使用timestamp作为创建时间
    # 或者可以不指定created_timestamp_column让Feast使用当前时间
    description="日线数据源，来自ClickHouse ginkgo.bar表"
)

# 定义日线数据特征视图
stock_daily_features = FeatureView(
    name="stock_daily_features",
    entities=[stock_entity],
    ttl=timedelta(days=30),  # 特征TTL设为30天
    schema=[
        # 基础OHLCV字段（来自MBar模型）
        Field(name="open", dtype=Float64, description="开盘价"),
        Field(name="high", dtype=Float64, description="最高价"),
        Field(name="low", dtype=Float64, description="最低价"),
        Field(name="close", dtype=Float64, description="收盘价"),
        Field(name="volume", dtype=Int64, description="成交量"),
        Field(name="amount", dtype=Float64, description="成交金额"),
        Field(name="frequency", dtype=Int64, description="数据频率"),
        
        # 派生特征（可以在查询时计算）
        # 这些字段需要在ClickHouse中预先计算或使用视图计算
        # Field(name="price_range", dtype=Float64, description="价格波动范围(high-low)"),
        # Field(name="price_change", dtype=Float64, description="价格变化(close-open)"),  
        # Field(name="price_change_pct", dtype=Float64, description="价格变化百分比"),
        # Field(name="amplitude", dtype=Float64, description="振幅((high-low)/close*100)"),
    ],
    online=True,  # 启用在线服务
    source=stock_daily_source,
    tags={
        "team": "ginkgo", 
        "source": "clickhouse", 
        "data_type": "stock_daily",
        "version": "v1.0"
    },
)

# 可选：定义派生特征视图（如果需要复杂计算的特征）
# 注意：这需要在ClickHouse中创建相应的视图或使用计算字段
"""
示例：如果要添加技术指标特征，可以创建额外的特征视图：

stock_technical_features = FeatureView(
    name="stock_technical_features", 
    entities=[stock_entity],
    ttl=timedelta(days=7),
    schema=[
        Field(name="ma5", dtype=Float64, description="5日均线"),
        Field(name="ma10", dtype=Float64, description="10日均线"),
        Field(name="ma20", dtype=Float64, description="20日均线"),
        Field(name="rsi", dtype=Float64, description="相对强弱指数"),
    ],
    source=stock_technical_source,  # 需要单独的数据源
    tags={"team": "ginkgo", "feature_type": "technical"},
)
"""

# 导出特征定义，供feast apply使用
__all__ = [
    "stock_entity",
    "stock_daily_source", 
    "stock_daily_features",
]
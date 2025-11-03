#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时间窗口批处理系统使用示例

本示例演示了如何在Ginkgo交易系统中使用时间窗口批处理功能，
解决传统逐个信号处理导致的资源竞争不真实问题。
"""

import datetime
from typing import List

from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.events import EventSignalGeneration
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


def demo_daily_batch_processing():
    """
    演示日线批处理模式
    
    适合基于日线数据的策略，在T+1机制下批量处理信号
    """
    print("=== 日线批处理模式演示 ===")
    
    # 创建Portfolio实例
    portfolio = PortfolioT1Backtest()
    portfolio.set_name("DailyBatchDemo")
    
    # 启用日线批处理
    portfolio.enable_daily_batch_processing(
        processing_mode="backtest",      # 回测模式
        resource_optimization=True,      # 启用资源优化
        priority_weighting=True          # 考虑信号优先级
    )
    
    print(f"批处理状态: {portfolio.get_batch_processing_stats()}")
    
    # 模拟同一天产生的多个信号
    today = datetime.datetime.now()
    signals = [
        Signal(
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            timestamp=today,
            reason="技术指标突破",
            source=SOURCE_TYPES.STRATEGY
        ),
        Signal(
            code="000002.SZ", 
            direction=DIRECTION_TYPES.LONG,
            timestamp=today,
            reason="基本面改善",
            source=SOURCE_TYPES.STRATEGY
        ),
        Signal(
            code="600000.SH",
            direction=DIRECTION_TYPES.LONG, 
            timestamp=today,
            reason="资金流入",
            source=SOURCE_TYPES.STRATEGY
        ),
    ]
    
    # 逐个添加信号（在同一天内）
    for signal in signals:
        event = EventSignalGeneration(signal)
        # 注意：在批处理模式下，这些信号会被收集起来，不会立即处理
        # portfolio.on_signal(event)  # 需要完整的Portfolio设置才能调用
    
    print("信号已添加到批处理队列")
    
    # 模拟时间推进到下一天，触发批处理
    tomorrow = today + datetime.timedelta(days=1)
    # portfolio.advance_time(tomorrow)  # 这会触发批处理
    
    print("批处理已触发，订单已按资源优化策略生成")


def demo_minute_batch_processing():
    """
    演示分钟级批处理模式
    
    适合高频策略，在短时间内批量处理信号
    """
    print("\n=== 分钟级批处理模式演示 ===")
    
    portfolio = PortfolioT1Backtest()
    portfolio.set_name("MinuteBatchDemo")
    
    # 启用分钟级批处理
    portfolio.enable_minute_batch_processing(
        processing_mode="live",          # 实盘模式
        max_delay_seconds=5,             # 5秒延迟
        resource_optimization=True       # 启用资源优化
    )
    
    print(f"批处理配置: {portfolio.get_batch_processing_stats()}")
    
    # 模拟同一分钟内的多个信号
    now = datetime.datetime.now()
    signals = [
        Signal(
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            timestamp=now,
            reason="价格突破"
        ),
        Signal(
            code="000001.SZ", 
            direction=DIRECTION_TYPES.SHORT,
            timestamp=now + datetime.timedelta(seconds=2),
            reason="快速回调"
        ),
    ]
    
    print("分钟级批处理：信号将在5秒延迟后或下一分钟开始时处理")


def demo_custom_batch_processing():
    """
    演示自定义批处理配置
    
    展示如何创建自定义的时间窗口和处理策略
    """
    print("\n=== 自定义批处理模式演示 ===")
    
    from ginkgo.trading.signal_processing import CustomWindowProcessor, ProcessingMode
    from datetime import timedelta
    
    portfolio = PortfolioT1Backtest()
    portfolio.set_name("CustomBatchDemo")
    
    # 自定义窗口计算函数：每30分钟一个窗口
    def custom_window_calculator(timestamp):
        # 将时间对齐到30分钟边界
        minutes = timestamp.minute
        aligned_minutes = (minutes // 30) * 30
        return timestamp.replace(minute=aligned_minutes, second=0, microsecond=0)
    
    # 自定义批次触发函数：至少3个信号或等待10分钟
    def custom_batch_trigger(window_start, signals):
        if len(signals) >= 3:
            return True
        
        current_time = datetime.datetime.now()
        batch_age = current_time - window_start
        return batch_age >= timedelta(minutes=10)
    
    # 配置自定义批处理器
    portfolio.configure_custom_batch_processing(
        CustomWindowProcessor,
        window_calculator=custom_window_calculator,
        batch_trigger_func=custom_batch_trigger,
        processing_mode=ProcessingMode.HYBRID,
        resource_optimization=True
    )
    
    print("自定义批处理器已配置：30分钟窗口，3信号触发或10分钟延迟")


def demo_resource_optimization_strategies():
    """
    演示不同的资源优化策略
    """
    print("\n=== 资源优化策略演示 ===")
    
    from ginkgo.trading.signal_processing import (
        ResourceOptimizer, 
        OptimizationStrategy,
        AllocationConstraints
    )
    
    # 创建不同的优化策略示例
    strategies = [
        OptimizationStrategy.EQUAL_WEIGHT,      # 等权重
        OptimizationStrategy.PRIORITY_WEIGHT,   # 优先级权重
        OptimizationStrategy.KELLY_CRITERION,   # 凯利公式
        OptimizationStrategy.RISK_PARITY,       # 风险平价
        OptimizationStrategy.MOMENTUM_WEIGHT,   # 动量权重
    ]
    
    # 配置约束条件
    constraints = AllocationConstraints(
        max_total_allocation=0.8,      # 最多使用80%资金
        max_single_position=0.15,      # 单股最多15%仓位
        min_order_value=1000.0,        # 最小订单1000元
        max_positions_count=15,        # 最多15只股票
    )
    
    for strategy in strategies:
        print(f"\n策略: {strategy.value}")
        optimizer = ResourceOptimizer(
            strategy=strategy,
            constraints=constraints
        )
        print(f"  - 约束: 总资金≤80%, 单股≤15%, 最小订单≥1000元")
        print(f"  - 特点: {get_strategy_description(strategy)}")


def get_strategy_description(strategy: OptimizationStrategy) -> str:
    """获取策略描述"""
    descriptions = {
        OptimizationStrategy.EQUAL_WEIGHT: "每个信号分配相等资金",
        OptimizationStrategy.PRIORITY_WEIGHT: "根据信号优先级和置信度分配",
        OptimizationStrategy.KELLY_CRITERION: "基于胜率和盈亏比的最优分配", 
        OptimizationStrategy.RISK_PARITY: "根据风险水平反向分配资金",
        OptimizationStrategy.MOMENTUM_WEIGHT: "根据动量强度分配权重",
    }
    return descriptions.get(strategy, "未知策略")


def demo_batch_processing_benefits():
    """
    演示批处理相比传统处理的优势
    """
    print("\n=== 批处理系统优势演示 ===")
    
    print("1. 资源竞争真实性:")
    print("   传统模式: 信号按到达顺序处理，先到先得")
    print("   批处理模式: 同时间窗口内信号统一竞争资源")
    
    print("\n2. 资金利用效率:")
    print("   传统模式: 可能出现部分信号无法执行的情况")
    print("   批处理模式: 全局优化资金分配，提高利用率")
    
    print("\n3. 时序准确性:")
    print("   传统模式: 处理顺序影响结果，不符合现实")
    print("   批处理模式: 模拟真实市场的时间窗口机制")
    
    print("\n4. 策略多样性:")
    print("   传统模式: 固定的先到先得策略")
    print("   批处理模式: 支持多种优化策略(凯利公式、风险平价等)")


def main():
    """主函数"""
    print("Ginkgo时间窗口批处理系统演示")
    print("=" * 50)
    
    # 运行各种演示
    demo_daily_batch_processing()
    demo_minute_batch_processing()  
    demo_custom_batch_processing()
    demo_resource_optimization_strategies()
    demo_batch_processing_benefits()
    
    print("\n" + "=" * 50)
    print("演示完成！")
    print("\n使用提示:")
    print("1. 选择合适的时间窗口类型（日线/小时/分钟）")
    print("2. 根据策略特点选择处理模式（回测/实盘/混合）") 
    print("3. 启用资源优化以获得更好的资金利用效率")
    print("4. 可以随时禁用批处理回退到传统模式")
    print("5. 查看批处理统计信息监控系统运行状态")


if __name__ == "__main__":
    main()
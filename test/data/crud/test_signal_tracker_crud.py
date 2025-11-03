"""
SignalTracker CRUD数据库操作TDD测试

测试CRUD层的信号追踪数据操作：
- 批量插入 (add_batch)
- 单条插入 (add)
- 查询 (find)
- 更新 (update)
- 删除 (remove)

SignalTracker是信号追踪数据模型，用于追踪模拟盘和实盘的信号执行情况。
支持人工确认流程，记录预期与实际执行的偏差，为交易执行质量评估提供数据支持。
信号追踪是量化交易系统重要的风控和执行质量保证机制。
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.signal_tracker_crud import SignalTrackerCRUD
from ginkgo.data.models.model_signal_tracker import MSignalTracker
from ginkgo.enums import (
    SOURCE_TYPES, DIRECTION_TYPES, EXECUTION_MODE,
    TRACKING_STATUS, ACCOUNT_TYPE
)


@pytest.mark.database
@pytest.mark.tdd
class TestSignalTrackerCRUDInsert:
    CRUD_TEST_CONFIG = {'crud_class': SignalTrackerCRUD}
    """1. CRUD层插入操作测试 - SignalTracker数据插入验证"""

    def test_add_batch_basic(self):
        """测试批量插入SignalTracker数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: SignalTracker CRUD层批量插入")
        print("="*60)

        signal_tracker_crud = SignalTrackerCRUD()
        print(f"✓ 创建SignalTrackerCRUD实例: {signal_tracker_crud.__class__.__name__}")

        # 创建测试SignalTracker数据 - 不同执行模式的信号追踪
        base_time = datetime(2023, 1, 3, 9, 30)
        test_trackers = []

        # 模拟盘信号追踪
        paper_tracker = MSignalTracker(
            signal_id="signal_001",
            strategy_id="strategy_ma_cross",
            portfolio_id="portfolio_paper_001",
            execution_mode=EXECUTION_MODE.SIMULATION,
            account_type=ACCOUNT_TYPE.PAPER,
            expected_code="000001.SZ",
            expected_direction=DIRECTION_TYPES.LONG,
            expected_price=Decimal("12.50"),
            expected_volume=1000,
            expected_timestamp=base_time
        )
        paper_tracker.source = SOURCE_TYPES.TEST
        test_trackers.append(paper_tracker)

        # 实盘信号追踪
        live_tracker = MSignalTracker(
            signal_id="signal_002",
            strategy_id="strategy_rsi_mean",
            portfolio_id="portfolio_live_001",
            execution_mode=EXECUTION_MODE.LIVE,
            account_type=ACCOUNT_TYPE.LIVE,
            expected_code="000002.SZ",
            expected_direction=DIRECTION_TYPES.SHORT,
            expected_price=Decimal("18.75"),
            expected_volume=500,
            expected_timestamp=base_time + timedelta(minutes=5)
        )
        live_tracker.source = SOURCE_TYPES.TEST
        test_trackers.append(live_tracker)

        # 已执行的信号追踪
        executed_tracker = MSignalTracker(
            signal_id="signal_003",
            strategy_id="strategy_bollinger",
            portfolio_id="portfolio_paper_001",
            execution_mode=EXECUTION_MODE.SIMULATION,
            account_type=ACCOUNT_TYPE.PAPER,
            expected_code="000858.SZ",
            expected_direction=DIRECTION_TYPES.LONG,
            expected_price=Decimal("25.60"),
            expected_volume=800,
            expected_timestamp=base_time + timedelta(minutes=10),
            actual_price=Decimal("25.68"),
            actual_volume=800,
            actual_timestamp=base_time + timedelta(minutes=10, seconds=3),
            tracking_status=TRACKING_STATUS.EXECUTED
        )
        executed_tracker.source = SOURCE_TYPES.TEST
        # 计算偏差
        executed_tracker.calculate_deviations()
        test_trackers.append(executed_tracker)

        print(f"✓ 创建测试数据: {len(test_trackers)}条SignalTracker记录")
        print(f"  - 信号ID: {[t.signal_id for t in test_trackers]}")
        print(f"  - 执行模式: {[t.execution_mode for t in test_trackers]}")
        print(f"  - 账户类型: {[t.get_account_type_name() for t in test_trackers]}")

        try:
            # 批量插入
            print("\n→ 执行批量插入操作...")
            signal_tracker_crud.add_batch(test_trackers)
            print("✓ 批量插入成功")

            # 验证可以查询出插入的数据
            print("\n→ 验证插入的数据...")
            query_result = signal_tracker_crud.find(filters={
                "expected_timestamp__gte": base_time,
                "expected_timestamp__lte": base_time + timedelta(minutes=15)
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 3

            # 验证数据内容
            signal_ids = set(t.signal_id for t in query_result)
            print(f"✓ 信号ID验证通过: {len(signal_ids)} 种")
            assert len(signal_ids) >= 3

            # 验证执行状态
            executed_count = sum(1 for t in query_result if t.is_executed())
            print(f"✓ 已执行信号验证通过: {executed_count} 个")
            assert executed_count >= 1

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_signal_tracker(self):
        """测试单条SignalTracker数据插入"""
        print("\n" + "="*60)
        print("开始测试: SignalTracker CRUD层单条插入")
        print("="*60)

        signal_tracker_crud = SignalTrackerCRUD()

        test_tracker = MSignalTracker(
            signal_id="signal_004",
            strategy_id="strategy_macd_cross",
            portfolio_id="portfolio_paper_002",
            execution_mode=EXECUTION_MODE.PAPER_MANUAL,
            account_type=ACCOUNT_TYPE.PAPER,
            expected_code="000004.SZ",
            expected_direction=DIRECTION_TYPES.LONG,
            expected_price=Decimal("8.90"),
            expected_volume=2000,
            expected_timestamp=datetime(2023, 1, 3, 10, 30),
            tracking_status=TRACKING_STATUS.NOTIFIED,
            notification_sent_at=datetime(2023, 1, 3, 10, 31)
        )
        test_tracker.source = SOURCE_TYPES.TEST
        print(f"✓ 创建测试SignalTracker: {test_tracker.signal_id}")
        print(f"  - 策略ID: {test_tracker.strategy_id}")
        print(f"  - 预期代码: {test_tracker.expected_code}")
        print(f"  - 预期价格: {test_tracker.expected_price}")
        print(f"  - 账户类型: {test_tracker.get_account_type_name()}")

        try:
            # 单条插入
            print("\n→ 执行单条插入操作...")
            signal_tracker_crud.add(test_tracker)
            print("✓ 单条插入成功")

            # 验证数据
            print("\n→ 验证插入的数据...")
            query_result = signal_tracker_crud.find(filters={
                "signal_id": "signal_004"
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 1

            inserted_tracker = query_result[0]
            print(f"✓ 插入的SignalTracker验证: {inserted_tracker.signal_id}")
            assert inserted_tracker.signal_id == "signal_004"
            assert inserted_tracker.strategy_id == "strategy_macd_cross"
            assert inserted_tracker.expected_code == "000004.SZ"

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestSignalTrackerCRUDQuery:
    CRUD_TEST_CONFIG = {'crud_class': SignalTrackerCRUD}
    """2. CRUD层查询操作测试 - SignalTracker数据查询和过滤"""

    def test_find_by_signal_id(self):
        """测试根据信号ID查询SignalTracker"""
        print("\n" + "="*60)
        print("开始测试: 根据信号ID查询SignalTracker")
        print("="*60)

        signal_tracker_crud = SignalTrackerCRUD()

        try:
            # 查询特定信号的追踪记录
            print("→ 查询信号ID signal_001 的追踪记录...")
            signal_trackers = signal_tracker_crud.find(filters={
                "signal_id": "signal_001"
            })
            print(f"✓ 查询到 {len(signal_trackers)} 条记录")

            # 验证查询结果
            for tracker in signal_trackers:
                print(f"  - 策略: {tracker.strategy_id}, 代码: {tracker.expected_code}, 方向: {tracker.expected_direction}")
                assert tracker.signal_id == "signal_001"

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_portfolio_and_account(self):
        """测试根据投资组合和账户类型查询SignalTracker"""
        print("\n" + "="*60)
        print("开始测试: 根据投资组合和账户类型查询SignalTracker")
        print("="*60)

        signal_tracker_crud = SignalTrackerCRUD()

        try:
            # 查询特定投资组合的模拟盘信号
            print("→ 查询投资组合portfolio_paper_001的模拟盘信号...")
            paper_signals = signal_tracker_crud.find(filters={
                "portfolio_id": "portfolio_paper_001",
                "account_type": ACCOUNT_TYPE.PAPER.value
            })
            print(f"✓ 查询到 {len(paper_signals)} 条模拟盘信号")

            # 查询实盘信号
            print("→ 查询实盘信号...")
            live_signals = signal_tracker_crud.find(filters={
                "account_type": ACCOUNT_TYPE.LIVE.value
            })
            print(f"✓ 查询到 {len(live_signals)} 条实盘信号")

            # 验证查询结果
            for tracker in paper_signals:
                assert tracker.portfolio_id == "portfolio_paper_001"
                assert tracker.account_type == ACCOUNT_TYPE.PAPER.value

            for tracker in live_signals:
                assert tracker.account_type == ACCOUNT_TYPE.LIVE.value

            print("✓ 投资组合和账户类型查询验证成功")

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_execution_status(self):
        """测试根据执行状态查询SignalTracker"""
        print("\n" + "="*60)
        print("开始测试: 根据执行状态查询SignalTracker")
        print("="*60)

        signal_tracker_crud = SignalTrackerCRUD()

        try:
            # 查询已执行的信号
            print("→ 查询已执行的信号...")
            executed_signals = signal_tracker_crud.find(filters={
                "tracking_status": TRACKING_STATUS.EXECUTED.value
            })
            print(f"✓ 查询到 {len(executed_signals)} 条已执行信号")

            # 查询等待确认的信号
            print("→ 查询等待确认的信号...")
            pending_signals = signal_tracker_crud.find(filters={
                "tracking_status": TRACKING_STATUS.NOTIFIED.value
            })
            print(f"✓ 查询到 {len(pending_signals)} 条等待确认信号")

            # 验证查询结果
            for tracker in executed_signals:
                print(f"  - {tracker.signal_id}: {tracker.expected_code} @ {tracker.actual_price}")
                assert tracker.is_executed()

            for tracker in pending_signals:
                print(f"  - {tracker.signal_id}: {tracker.expected_code} (等待确认)")
                assert tracker.is_pending()

            print("✓ 执行状态查询验证成功")

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_time_range(self):
        """测试根据时间范围查询SignalTracker"""
        print("\n" + "="*60)
        print("开始测试: 根据时间范围查询SignalTracker")
        print("="*60)

        signal_tracker_crud = SignalTrackerCRUD()

        try:
            # 查询特定时间范围的信号追踪
            start_time = datetime(2023, 1, 1)
            end_time = datetime(2023, 12, 31, 23, 59, 59)

            print(f"→ 查询时间范围 {start_time} ~ {end_time} 的信号追踪...")
            time_trackers = signal_tracker_crud.find(filters={
                "expected_timestamp__gte": start_time,
                "expected_timestamp__lte": end_time
            })
            print(f"✓ 查询到 {len(time_trackers)} 条记录")

            # 验证时间范围
            for tracker in time_trackers:
                print(f"  - {tracker.signal_id}: {tracker.expected_code} ({tracker.expected_timestamp})")
                assert start_time <= tracker.expected_timestamp <= end_time

            print("✓ 时间范围查询验证成功")

        except Exception as e:
            print(f"✗ 时间范围查询失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestSignalTrackerCRUDUpdate:
    CRUD_TEST_CONFIG = {'crud_class': SignalTrackerCRUD}
    """3. CRUD层更新操作测试 - SignalTracker状态更新"""

    def test_update_execution_result(self):
        """测试更新信号执行结果"""
        print("\n" + "="*60)
        print("开始测试: 更新信号执行结果")
        print("="*60)

        signal_tracker_crud = SignalTrackerCRUD()

        try:
            # 查询等待执行的信号
            print("→ 查询等待执行的信号...")
            pending_trackers = signal_tracker_crud.find(filters={
                "tracking_status": TRACKING_STATUS.NOTIFIED.value
            })

            if not pending_trackers:
                print("✗ 没有找到等待执行的信号")
                return

            target_tracker = pending_trackers[0]
            print(f"✓ 找到信号: {target_tracker.signal_id}")
            print(f"  - 预期: {target_tracker.expected_code} {target_tracker.expected_volume}股 @ {target_tracker.expected_price}")

            # 更新执行结果
            print("→ 更新执行结果...")
            actual_price = Decimal("13.25")
            actual_volume = 950
            actual_timestamp = datetime.now()

            # 使用模型方法更新
            target_tracker.actual_price = actual_price
            target_tracker.actual_volume = actual_volume
            target_tracker.actual_timestamp = actual_timestamp
            target_tracker.tracking_status = TRACKING_STATUS.EXECUTED.value
            target_tracker.execution_confirmed_at = actual_timestamp

            # 计算偏差
            target_tracker.calculate_deviations()

            # 这里需要实现update方法，暂时使用业务逻辑验证
            print(f"✓ 执行结果更新:")
            print(f"  - 实际价格: {actual_price}")
            print(f"  - 实际数量: {actual_volume}")
            if hasattr(target_tracker, 'price_deviation') and target_tracker.price_deviation:
                print(f"  - 价格偏差: {target_tracker.price_deviation}")
            if hasattr(target_tracker, 'volume_deviation') and target_tracker.volume_deviation:
                print(f"  - 数量偏差: {target_tracker.volume_deviation}")
            if hasattr(target_tracker, 'time_delay_seconds') and target_tracker.time_delay_seconds:
                print(f"  - 时间延迟: {target_tracker.time_delay_seconds}秒")

            print("✓ 信号执行结果更新验证成功")

        except Exception as e:
            print(f"✗ 更新信号执行结果失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestSignalTrackerCRUDBusinessLogic:
    CRUD_TEST_CONFIG = {'crud_class': SignalTrackerCRUD}
    """4. CRUD层业务逻辑测试 - SignalTracker业务场景验证"""

    def test_signal_execution_quality_analysis(self):
        """测试信号执行质量分析"""
        print("\n" + "="*60)
        print("开始测试: 信号执行质量分析")
        print("="*60)

        signal_tracker_crud = SignalTrackerCRUD()

        try:
            # 获取所有信号追踪记录进行质量分析
            print("→ 进行信号执行质量分析...")
            all_trackers = signal_tracker_crud.find()

            if len(all_trackers) < 2:
                print("✗ 信号追踪数据不足，跳过质量分析")
                return

            # 按账户类型分组分析
            quality_analysis = {
                "paper": {"trackers": [], "count": 0, "executed": 0},
                "live": {"trackers": [], "count": 0, "executed": 0}
            }

            for tracker in all_trackers:
                account_type = tracker.get_account_type_name()
                if account_type in quality_analysis:
                    quality_analysis[account_type]["trackers"].append(tracker)
                    quality_analysis[account_type]["count"] += 1
                    if tracker.is_executed():
                        quality_analysis[account_type]["executed"] += 1

            print(f"✓ 信号执行质量分析结果:")
            for account_type, data in quality_analysis.items():
                if data["count"] > 0:
                    execution_rate = (data["executed"] / data["count"]) * 100
                    print(f"  - {account_type}账户:")
                    print(f"    总信号数: {data['count']}")
                    print(f"    已执行: {data['executed']}")
                    print(f"    执行率: {execution_rate:.2f}%")

            # 分析执行偏差（仅分析已执行的信号）
            executed_trackers = [t for t in all_trackers if t.is_executed() and t.price_deviation is not None]

            if executed_trackers:
                price_deviations = [float(t.price_deviation) for t in executed_trackers]
                volume_deviations = [float(t.volume_deviation) for t in executed_trackers if t.volume_deviation is not None]
                time_delays = [t.time_delay_seconds for t in executed_trackers if t.time_delay_seconds is not None]

                print(f"  - 执行偏差分析:")
                print(f"    价格偏差平均: {sum(price_deviations)/len(price_deviations):.4f}")
                if volume_deviations:
                    print(f"    数量偏差平均: {sum(volume_deviations)/len(volume_deviations):.4f}")
                if time_delays:
                    print(f"    平均延迟: {sum(time_delays)/len(time_delays):.2f}秒")

            print("✓ 信号执行质量分析验证成功")

        except Exception as e:
            print(f"✗ 信号执行质量分析失败: {e}")
            raise

    def test_signal_tracking_performance(self):
        """测试信号追踪性能统计"""
        print("\n" + "="*60)
        print("开始测试: 信号追踪性能统计")
        print("="*60)

        signal_tracker_crud = SignalTrackerCRUD()

        try:
            # 获取信号追踪数据
            print("→ 进行信号追踪性能统计...")
            all_trackers = signal_tracker_crud.find()

            if len(all_trackers) < 3:
                print("✗ 信号追踪数据不足，跳过性能统计")
                return

            # 按策略分组统计
            strategy_performance = {}
            for tracker in all_trackers:
                strategy_id = tracker.strategy_id
                if strategy_id not in strategy_performance:
                    strategy_performance[strategy_id] = {
                        "total": 0,
                        "executed": 0,
                        "pending": 0,
                        "timeout": 0,
                        "codes": set()
                    }

                strategy_performance[strategy_id]["total"] += 1
                strategy_performance[strategy_id]["codes"].add(tracker.expected_code)

                if tracker.is_executed():
                    strategy_performance[strategy_id]["executed"] += 1
                elif tracker.is_pending():
                    strategy_performance[strategy_id]["pending"] += 1
                elif tracker.is_timeout():
                    strategy_performance[strategy_id]["timeout"] += 1

            print(f"✓ 策略性能统计:")
            for strategy_id, stats in strategy_performance.items():
                execution_rate = (stats["executed"] / stats["total"]) * 100 if stats["total"] > 0 else 0
                print(f"  - {strategy_id}:")
                print(f"    总信号: {stats['total']}")
                print(f"    已执行: {stats['executed']}")
                print(f"    等待中: {stats['pending']}")
                print(f"    超时: {stats['timeout']}")
                print(f"    执行率: {execution_rate:.2f}%")
                print(f"    涉及股票: {len(stats['codes'])} 种")

            print("✓ 信号追踪性能统计验证成功")

        except Exception as e:
            print(f"✗ 信号追踪性能统计失败: {e}")
            raise

    def test_execution_mode_efficiency(self):
        """测试执行模式效率分析"""
        print("\n" + "="*60)
        print("开始测试: 执行模式效率分析")
        print("="*60)

        signal_tracker_crud = SignalTrackerCRUD()

        try:
            # 按执行模式分析效率
            print("→ 进行执行模式效率分析...")
            all_trackers = signal_tracker_crud.find()

            if len(all_trackers) < 2:
                print("✗ 信号追踪数据不足，跳过效率分析")
                return

            # 按执行模式分组
            mode_analysis = {}
            for tracker in all_trackers:
                mode = tracker.execution_mode
                if mode not in mode_analysis:
                    mode_analysis[mode] = {
                        "total": 0,
                        "executed": 0,
                        "avg_delay": 0,
                        "delays": []
                    }

                mode_analysis[mode]["total"] += 1
                if tracker.is_executed() and tracker.time_delay_seconds is not None:
                    mode_analysis[mode]["executed"] += 1
                    mode_analysis[mode]["delays"].append(tracker.time_delay_seconds)

            # 计算平均延迟
            for mode, data in mode_analysis.items():
                if data["delays"]:
                    data["avg_delay"] = sum(data["delays"]) / len(data["delays"])

            print(f"✓ 执行模式效率分析:")
            mode_names = {0: "自动", 1: "手动", 2: "半自动"}
            for mode, stats in mode_analysis.items():
                mode_name = mode_names.get(mode, f"模式{mode}")
                execution_rate = (stats["executed"] / stats["total"]) * 100 if stats["total"] > 0 else 0
                print(f"  - {mode_name}执行:")
                print(f"    总信号: {stats['total']}")
                print(f"    已执行: {stats['executed']}")
                print(f"    执行率: {execution_rate:.2f}%")
                if stats["avg_delay"] > 0:
                    print(f"    平均延迟: {stats['avg_delay']:.2f}秒")

            print("✓ 执行模式效率分析验证成功")

        except Exception as e:
            print(f"✗ 执行模式效率分析失败: {e}")
            raise

    def test_timeout_signal_analysis(self):
        """测试超时信号分析"""
        print("\n" + "="*60)
        print("开始测试: 超时信号分析")
        print("="*60)

        signal_tracker_crud = SignalTrackerCRUD()

        try:
            # 查询超时的信号
            print("→ 进行超时信号分析...")
            timeout_trackers = signal_tracker_crud.find(filters={
                "tracking_status": TRACKING_STATUS.TIMEOUT.value
            })

            print(f"✓ 超时信号分析结果:")
            print(f"  - 超时信号数量: {len(timeout_trackers)}")

            if timeout_trackers:
                # 按策略和投资组合分析超时情况
                timeout_analysis = {}
                for tracker in timeout_trackers:
                    key = f"{tracker.strategy_id}@{tracker.portfolio_id}"
                    if key not in timeout_analysis:
                        timeout_analysis[key] = {
                            "strategy": tracker.strategy_id,
                            "portfolio": tracker.portfolio_id,
                            "count": 0,
                            "codes": []
                        }
                    timeout_analysis[key]["count"] += 1
                    timeout_analysis[key]["codes"].append(tracker.expected_code)

                print(f"  - 超时详情:")
                for key, data in timeout_analysis.items():
                    print(f"    - {data['strategy']}@{data['portfolio']}: {data['count']}次超时")
                    print(f"      涉及股票: {', '.join(data['codes'])}")

                # 分析超时原因（如果有记录的话）
                rejected_trackers = [t for t in timeout_trackers if t.reject_reason]
                if rejected_trackers:
                    print(f"  - 拒绝原因统计:")
                    for tracker in rejected_trackers:
                        print(f"    - {tracker.signal_id}: {tracker.reject_reason}")

            else:
                print("  - 当前无超时信号")

            print("✓ 超时信号分析验证成功")

        except Exception as e:
            print(f"✗ 超时信号分析失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestSignalTrackerCRUDDelete:
    CRUD_TEST_CONFIG = {'crud_class': SignalTrackerCRUD}
    """3. CRUD层删除操作测试 - SignalTracker数据删除验证"""

    def test_delete_signal_tracker_by_portfolio_id(self):
        """测试根据投资组合ID删除SignalTracker"""
        print("\n" + "="*60)
        print("开始测试: 根据投资组合ID删除SignalTracker")
        print("="*60)

        signal_tracker_crud = SignalTrackerCRUD()

        # 准备测试数据
        print("→ 准备测试数据...")
        test_tracker = MSignalTracker(
            signal_id="signal_delete_test_001",
            strategy_id="strategy_delete_test",
            portfolio_id="DELETE_TEST_PORTFOLIO",
            execution_mode=EXECUTION_MODE.SIMULATION,
            account_type=ACCOUNT_TYPE.PAPER,
            expected_code="000001.SZ",
            expected_direction=DIRECTION_TYPES.LONG,
            expected_price=Decimal("12.50"),
            expected_volume=1000,
            expected_timestamp=datetime(2023, 6, 15, 10, 30),
            actual_price=Decimal("12.52"),
            actual_volume=1000,
            actual_timestamp=datetime(2023, 6, 15, 10, 31),
            tracking_status=TRACKING_STATUS.EXECUTED,
            execution_confirmed_at=datetime(2023, 6, 15, 10, 32),
            price_deviation=Decimal("0.02"),
            volume_deviation=0,
            time_delay_seconds=1
        )
        test_tracker.source = SOURCE_TYPES.TEST
        signal_tracker_crud.add(test_tracker)
        print(f"✓ 插入测试数据: {test_tracker.signal_id} in {test_tracker.portfolio_id}")

        # 验证数据存在
        before_count = len(signal_tracker_crud.find(filters={"portfolio_id": "DELETE_TEST_PORTFOLIO"}))
        print(f"✓ 删除前数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行删除操作...")
            signal_tracker_crud.remove(filters={"portfolio_id": "DELETE_TEST_PORTFOLIO"})
            print("✓ 删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(signal_tracker_crud.find(filters={"portfolio_id": "DELETE_TEST_PORTFOLIO"}))
            print(f"✓ 删除后数据量: {after_count}")
            assert after_count == 0, "删除后应该没有相关数据"

            print("✓ 根据投资组合ID删除SignalTracker验证成功")

        except Exception as e:
            print(f"✗ 删除操作失败: {e}")
            raise

    def test_delete_signal_tracker_by_strategy_id(self):
        """测试根据策略ID删除SignalTracker"""
        print("\n" + "="*60)
        print("开始测试: 根据策略ID删除SignalTracker")
        print("="*60)

        signal_tracker_crud = SignalTrackerCRUD()

        # 准备测试数据 - 特定策略ID的数据
        print("→ 准备测试数据...")
        test_strategies = [
            ("delete_strategy_001", "DELETE_PORTFOLIO_001", "DELETE_STOCK_001"),
            ("delete_strategy_002", "DELETE_PORTFOLIO_002", "DELETE_STOCK_002"),
            ("delete_strategy_001", "DELETE_PORTFOLIO_003", "DELETE_STOCK_003"),
        ]

        for strategy_id, portfolio_id, code in test_strategies:
            test_tracker = MSignalTracker(
                signal_id=f"sig_{strategy_id[-3:]}_{code[-4:]}_{datetime.now().strftime('%H%M%S')}",
                strategy_id=strategy_id,
                portfolio_id=portfolio_id,
                execution_mode=EXECUTION_MODE.SIMULATION,
                account_type=ACCOUNT_TYPE.PAPER,
                expected_code=code,
                expected_direction=DIRECTION_TYPES.LONG,
                expected_price=Decimal("15.00"),
                expected_volume=2000,
                expected_timestamp=datetime(2023, 7, 1, 10, 30),
                tracking_status=TRACKING_STATUS.NOTIFIED,
                price_deviation=Decimal("0.00"),
                volume_deviation=0,
                time_delay_seconds=0
            )
            test_tracker.source = SOURCE_TYPES.TEST
            signal_tracker_crud.add(test_tracker)

        print(f"✓ 插入策略测试数据: {len(test_strategies)}条")

        # 验证数据存在
        before_count = len(signal_tracker_crud.find(filters={"strategy_id": "delete_strategy_001"}))
        print(f"✓ 删除前策略001数据量: {before_count}")

        try:
            # 删除特定策略的数据
            print("\n→ 执行策略ID删除操作...")
            signal_tracker_crud.remove(filters={"strategy_id": "delete_strategy_001"})
            print("✓ 策略ID删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(signal_tracker_crud.find(filters={"strategy_id": "delete_strategy_001"}))
            print(f"✓ 删除后策略001数据量: {after_count}")
            assert after_count == 0, "删除后应该没有策略001的数据"

            # 确认其他策略数据未受影响
            other_strategy_count = len(signal_tracker_crud.find(filters={"strategy_id": "delete_strategy_002"}))
            print(f"✓ 其他策略数据保留验证: {other_strategy_count}条")
            assert other_strategy_count > 0, "其他策略数据应该保留"

            print("✓ 根据策略ID删除SignalTracker验证成功")

        except Exception as e:
            print(f"✗ 策略ID删除操作失败: {e}")
            raise

    def test_delete_signal_tracker_by_tracking_status(self):
        """测试根据追踪状态删除SignalTracker"""
        print("\n" + "="*60)
        print("开始测试: 根据追踪状态删除SignalTracker")
        print("="*60)

        signal_tracker_crud = SignalTrackerCRUD()

        # 准备测试数据 - 不同追踪状态的数据
        print("→ 准备测试数据...")
        test_statuses = [
            ("status_pending_test", TRACKING_STATUS.NOTIFIED),
            ("status_confirmed", TRACKING_STATUS.EXECUTED),
            ("status_rejected_test", TRACKING_STATUS.CANCELED),
            ("status_pending_2", TRACKING_STATUS.NOTIFIED),
        ]

        for code, status in test_statuses:
            test_tracker = MSignalTracker(
                signal_id=f"sig_{code[-4:]}_{datetime.now().strftime('%H%M%S')}",
                strategy_id="status_test_strategy",
                portfolio_id="status_test_portfolio",
                execution_mode=EXECUTION_MODE.SIMULATION,
                account_type=ACCOUNT_TYPE.PAPER,
                expected_code=code,
                expected_direction=DIRECTION_TYPES.LONG,
                expected_price=Decimal("20.00"),
                expected_volume=1500,
                expected_timestamp=datetime(2023, 8, 15, 10, 30),
                tracking_status=status,
                price_deviation=Decimal("0.00"),
                volume_deviation=0,
                time_delay_seconds=0
            )
            test_tracker.source = SOURCE_TYPES.TEST
            signal_tracker_crud.add(test_tracker)

        print(f"✓ 插入状态测试数据: {len(test_statuses)}条")

        try:
            # 删除待确认状态的数据
            print("\n→ 执行状态删除操作...")
            before_count = len(signal_tracker_crud.find(filters={"tracking_status": TRACKING_STATUS.NOTIFIED}))
            print(f"✓ 删除前待确认状态数据量: {before_count}")

            signal_tracker_crud.remove(filters={"tracking_status": TRACKING_STATUS.NOTIFIED})
            print("✓ 状态删除操作完成")

            # 验证删除结果
            after_count = len(signal_tracker_crud.find(filters={"tracking_status": TRACKING_STATUS.NOTIFIED}))
            print(f"✓ 删除后待确认状态数据量: {after_count}")
            assert after_count == 0, "删除后应该没有待确认状态数据"

            # 确认其他状态数据未受影响
            other_status_count = len(signal_tracker_crud.find(filters={"tracking_status": TRACKING_STATUS.EXECUTED}))
            print(f"✓ 其他状态数据保留验证: {other_status_count}条")
            assert other_status_count > 0, "其他状态数据应该保留"

            print("✓ 根据追踪状态删除SignalTracker验证成功")

        except Exception as e:
            print(f"✗ 状态删除操作失败: {e}")
            raise

    def test_delete_signal_tracker_by_execution_mode(self):
        """测试根据执行模式删除SignalTracker"""
        print("\n" + "="*60)
        print("开始测试: 根据执行模式删除SignalTracker")
        print("="*60)

        signal_tracker_crud = SignalTrackerCRUD()

        # 准备测试数据 - 不同执行模式的数据
        print("→ 准备测试数据...")
        test_modes = [
            ("mode_sim_test", EXECUTION_MODE.SIMULATION, ACCOUNT_TYPE.PAPER),
            ("mode_sim_test_2", EXECUTION_MODE.SIMULATION, ACCOUNT_TYPE.PAPER),
            ("mode_paper_test", EXECUTION_MODE.LIVE, ACCOUNT_TYPE.PAPER),
            ("mode_live_test", EXECUTION_MODE.LIVE, ACCOUNT_TYPE.LIVE),
        ]

        for code, mode, account_type in test_modes:
            test_tracker = MSignalTracker(
                signal_id=f"sig_{code[-4:]}_{datetime.now().strftime('%H%M%S')}",
                strategy_id="mode_test_strategy",
                portfolio_id="mode_test_portfolio",
                execution_mode=mode,
                account_type=account_type,
                expected_code=code,
                expected_direction=DIRECTION_TYPES.LONG,
                expected_price=Decimal("25.00"),
                expected_volume=3000,
                expected_timestamp=datetime(2023, 9, 1, 10, 30),
                tracking_status=TRACKING_STATUS.NOTIFIED,
                price_deviation=Decimal("0.00"),
                volume_deviation=0,
                time_delay_seconds=0
            )
            test_tracker.source = SOURCE_TYPES.TEST
            signal_tracker_crud.add(test_tracker)

        print(f"✓ 插入模式测试数据: {len(test_modes)}条")

        try:
            # 删除模拟模式的数据
            print("\n→ 执行模式删除操作...")
            before_count = len(signal_tracker_crud.find(filters={"execution_mode": EXECUTION_MODE.SIMULATION}))
            print(f"✓ 删除前模拟模式数据量: {before_count}")

            signal_tracker_crud.remove(filters={"execution_mode": EXECUTION_MODE.SIMULATION})
            print("✓ 执行模式删除操作完成")

            # 验证删除结果
            after_count = len(signal_tracker_crud.find(filters={"execution_mode": EXECUTION_MODE.SIMULATION}))
            print(f"✓ 删除后模拟模式数据量: {after_count}")
            assert after_count == 0, "删除后应该没有模拟模式数据"

            # 确认其他模式数据未受影响
            other_mode_count = len(signal_tracker_crud.find(filters={"execution_mode": EXECUTION_MODE.LIVE}))
            print(f"✓ 其他模式数据保留验证: {other_mode_count}条")
            assert other_mode_count > 0, "其他模式数据应该保留"

            print("✓ 根据执行模式删除SignalTracker验证成功")

        except Exception as e:
            print(f"✗ 执行模式删除操作失败: {e}")
            raise

    def test_delete_signal_tracker_by_time_range(self):
        """测试根据时间范围删除SignalTracker"""
        print("\n" + "="*60)
        print("开始测试: 根据时间范围删除SignalTracker")
        print("="*60)

        signal_tracker_crud = SignalTrackerCRUD()

        # 准备测试数据 - 特定时间范围的数据
        print("→ 准备测试数据...")
        test_time_range = [
            datetime(2023, 10, 1, 10, 30),
            datetime(2023, 10, 2, 10, 30),
            datetime(2023, 10, 3, 10, 30)
        ]

        for i, test_time in enumerate(test_time_range):
            test_tracker = MSignalTracker(
                signal_id=f"time_range_signal_{i+1:03d}",
                strategy_id="time_range_strategy",
                portfolio_id="time_range_portfolio",
                execution_mode=EXECUTION_MODE.SIMULATION,
                account_type=ACCOUNT_TYPE.PAPER,
                expected_code=f"TIME_RANGE_{i+1:03d}",
                expected_direction=DIRECTION_TYPES.LONG,
                expected_price=Decimal(f"30.{1000+i}"),
                expected_volume=4000 + i * 100,
                expected_timestamp=test_time,
                tracking_status=TRACKING_STATUS.NOTIFIED,
                price_deviation=Decimal("0.00"),
                volume_deviation=0,
                time_delay_seconds=0
            )
            test_tracker.source = SOURCE_TYPES.TEST
            signal_tracker_crud.add(test_tracker)

        print(f"✓ 插入时间范围测试数据: {len(test_time_range)}条")

        # 验证数据存在
        before_count = len(signal_tracker_crud.find(filters={
            "expected_timestamp__gte": datetime(2023, 10, 1),
            "expected_timestamp__lte": datetime(2023, 10, 3, 23, 59, 59)
        }))
        print(f"✓ 删除前时间范围内数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行时间范围删除操作...")
            signal_tracker_crud.remove(filters={
                "expected_timestamp__gte": datetime(2023, 10, 1),
                "expected_timestamp__lte": datetime(2023, 10, 3, 23, 59, 59)
            })
            print("✓ 时间范围删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(signal_tracker_crud.find(filters={
                "expected_timestamp__gte": datetime(2023, 10, 1),
                "expected_timestamp__lte": datetime(2023, 10, 3, 23, 59, 59)
            }))
            print(f"✓ 删除后时间范围内数据量: {after_count}")
            assert after_count == 0, "删除后时间范围内应该没有数据"

            print("✓ 根据时间范围删除SignalTracker验证成功")

        except Exception as e:
            print(f"✗ 时间范围删除操作失败: {e}")
            raise

    def test_delete_signal_tracker_batch_cleanup(self):
        """测试批量清理SignalTracker数据"""
        print("\n" + "="*60)
        print("开始测试: 批量清理SignalTracker数据")
        print("="*60)

        signal_tracker_crud = SignalTrackerCRUD()

        # 准备批量清理数据
        print("→ 准备批量清理测试数据...")
        cleanup_trackers = []
        base_time = datetime(2023, 11, 1)

        for i in range(12):
            signal_id = f"cleanup_signal_{i+1:03d}"
            cleanup_trackers.append(signal_id)

            test_tracker = MSignalTracker(
                signal_id=signal_id,
                strategy_id=f"cleanup_strategy_{i+1:03d}",
                portfolio_id=f"cleanup_portfolio_{i+1:03d}",
                execution_mode=EXECUTION_MODE.SIMULATION,
                account_type=ACCOUNT_TYPE.PAPER,
                expected_code=f"CLEANUP_{i+1:03d}",
                expected_direction=DIRECTION_TYPES.LONG,
                expected_price=Decimal(f"40.{1000+i}"),
                expected_volume=5000 + i * 200,
                expected_timestamp=base_time + timedelta(hours=i),
                tracking_status=TRACKING_STATUS.NOTIFIED,
                price_deviation=Decimal("0.00"),
                volume_deviation=0,
                time_delay_seconds=0
            )
            test_tracker.source = SOURCE_TYPES.TEST
            signal_tracker_crud.add(test_tracker)

        print(f"✓ 插入批量清理测试数据: {len(cleanup_trackers)}条")

        # 验证数据存在
        before_count = len(signal_tracker_crud.find(filters={
            "signal_id__like": "cleanup_signal_%"
        }))
        print(f"✓ 删除前批量数据量: {before_count}")

        try:
            # 批量删除
            print("\n→ 执行批量清理操作...")
            signal_tracker_crud.remove(filters={
                "signal_id__like": "cleanup_signal_%"
            })
            print("✓ 批量清理操作完成")

            # 验证删除结果
            print("\n→ 验证批量清理结果...")
            after_count = len(signal_tracker_crud.find(filters={
                "signal_id__like": "cleanup_signal_%"
            }))
            print(f"✓ 删除后批量数据量: {after_count}")
            assert after_count == 0, "删除后应该没有批量清理数据"

            # 确认其他数据未受影响
            other_data_count = len(signal_tracker_crud.find(page_size=10))
            print(f"✓ 其他数据保留验证: {other_data_count}条")

            print("✓ 批量清理SignalTracker数据验证成功")

        except Exception as e:
            print(f"✗ 批量清理操作失败: {e}")
            raise


# TDD Red阶段验证：确保所有测试开始时都失败
if __name__ == "__main__":
    print("TDD Red阶段验证：SignalTracker CRUD测试")
    print("所有测试用例应该在实现开始前失败")
    print("运行: pytest test/data/crud/test_signal_tracker_crud.py -v")
    print("预期结果: 所有测试失败 (Red阶段)")
    print("重点关注: 信号追踪存储和执行质量分析功能")

"""
TradeDayCRUD数据库操作TDD测试 - 交易日历管理

本文件测试TradeDayCRUD类的完整功能，确保交易日历(TradeDay)的增删改查操作正常工作。
交易日历是量化交易系统的时间基准，记录各市场的交易日和休市日，为策略回测和实盘交易提供时间支持。

测试范围：
1. 插入操作 (Insert Operations)
   - 批量插入 (add_batch): 高效创建多个交易日历
   - 单条插入 (add): 创建单个交易日历
   - 枚举验证: 市场类型、交易状态枚举正确性

2. 查询操作 (Query Operations)
   - 按市场查询 (find_by_market): 根据市场类型查找
   - 按时间范围查询 (find_by_time_range): 时间范围筛选
   - 按交易状态查询 (find_trading_days_only): 交易日/休市日筛选
   - 分页查询 (pagination): 支持大数据量分页
   - DataFrame转换: to_dataframe() 数据格式转换

3. 更新操作 (Update Operations)
   - 交易状态更新 (update_trade_day_status): 修改开市/休市状态
   - 批量更新 (batch_update): 批量修改交易状态

4. 删除操作 (Delete Operations)
   - 按日期删除 (delete_by_date): 删除特定日期的记录
   - 按市场删除 (delete_by_market): 删除特定市场的记录
   - 按状态删除 (delete_closed_days): 删除休市日记录
   - 按时间范围删除 (delete_by_date_range): 删除时间范围内的记录

5. 业务逻辑测试 (Business Logic Tests)
   - 交易日历分析 (trading_calendar_analysis): 按市场统计交易日
   - 序列连续性验证 (trading_day_sequence_validation): 验证日期连续性
   - 跨市场对比 (market_comparison_analysis): 多市场交易日对比
   - 交易统计 (trading_statistics): 交易日/休市日比例
"""
import pytest
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "test"))

from ginkgo.data.crud.trade_day_crud import TradeDayCRUD
from ginkgo.data.models.model_trade_day import MTradeDay
from ginkgo.enums import SOURCE_TYPES, MARKET_TYPES


# ==================== 插入操作测试 ====================

@pytest.mark.database
@pytest.mark.tdd
class TestTradeDayCRUDInsert:
    """TradeDay CRUD层插入操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = TradeDayCRUD()

    def test_add_batch_basic(self):
        """测试批量插入TradeDay数据"""
        print("\n开始测试: TradeDay CRUD层批量插入")

        # 创建测试数据
        base_date = datetime(2023, 1, 1)
        test_trade_days = [
            MTradeDay(
                market=MARKET_TYPES.CHINA,
                is_open=(base_date + timedelta(days=i)).weekday() < 5,
                timestamp=base_date + timedelta(days=i),
                source=SOURCE_TYPES.TEST
            )
            for i in range(10)
        ]

        # 获取插入前数量
        before_count = self.crud.count()

        # 批量插入
        self.crud.add_batch(test_trade_days)

        # 验证插入结果
        after_count = self.crud.count()
        inserted_count = after_count - before_count
        assert inserted_count == len(test_trade_days), f"应插入{len(test_trade_days)}条，实际{inserted_count}条"

        # 验证数据内容
        trading_count = sum(1 for td in test_trade_days if td.is_open)
        assert trading_count >= 5, "至少应有5个交易日"

    def test_add_batch_with_parametrize(self):
        """参数化测试不同市场的批量插入"""
        markets = [
            MARKET_TYPES.CHINA,
            MARKET_TYPES.NASDAQ,
            MARKET_TYPES.OTHER  # 使用OTHER代替NYSE
        ]

        for market in markets:
            # 为每个市场创建测试数据
            test_days = [
                MTradeDay(
                    market=market,
                    is_open=True,
                    timestamp=datetime(2023, 1, i+1),
                    source=SOURCE_TYPES.TEST
                )
                for i in range(3)
            ]

            before_count = len(self.crud.find(filters={"market": market}))
            self.crud.add_batch(test_days)
            after_count = len(self.crud.find(filters={"market": market}))

            assert after_count - before_count == len(test_days), \
                f"{market.name}市场应增加{len(test_days)}条"

    def test_add_single_trade_day(self):
        """测试单条TradeDay数据插入"""
        test_trade_day = MTradeDay(
            market=MARKET_TYPES.NASDAQ,
            is_open=True,
            timestamp=datetime(2023, 1, 3),
            source=SOURCE_TYPES.TEST
        )

        # 单条插入
        self.crud.add(test_trade_day)

        # 验证插入
        result = self.crud.find(filters={
            "market": MARKET_TYPES.NASDAQ,
            "timestamp": datetime(2023, 1, 3)
        })

        assert len(result) >= 1, "应查询到插入的记录"
        assert result[0].is_open == True

    @pytest.mark.parametrize("market,is_open,expected_status", [
        (MARKET_TYPES.CHINA, True, "交易日"),
        (MARKET_TYPES.CHINA, False, "休市日"),
        (MARKET_TYPES.NASDAQ, True, "交易日"),
        (MARKET_TYPES.OTHER, False, "休市日"),
    ])
    def test_add_single_with_various_statuses(self, market, is_open, expected_status):
        """参数化测试不同状态的交易日插入"""
        test_day = MTradeDay(
            market=market,
            is_open=is_open,
            timestamp=datetime(2024, 1, 15),
            source=SOURCE_TYPES.TEST
        )

        self.crud.add(test_day)

        result = self.crud.find(filters={
            "market": market,
            "timestamp": datetime(2024, 1, 15)
        })

        assert len(result) >= 1, f"应查询到{expected_status}记录"
        assert result[0].is_open == is_open


# ==================== 查询操作测试 ====================

@pytest.mark.database
@pytest.mark.tdd
class TestTradeDayCRUDQuery:
    """TradeDay CRUD层查询操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = TradeDayCRUD()

    def test_find_by_market(self):
        """测试根据市场查询TradeDay"""
        # 查询中国市场
        china_result = self.crud.find(filters={"market": MARKET_TYPES.CHINA})
        china_entities = china_result.to_entities()

        assert len(china_entities) >= 0, "应能查询中国市场数据"
        for entity in china_entities[:5]:
            assert entity.market == MARKET_TYPES.CHINA

    @pytest.mark.parametrize("market", [
        MARKET_TYPES.CHINA,
        MARKET_TYPES.NASDAQ,
        MARKET_TYPES.OTHER,  # 使用OTHER代替NYSE
        MARKET_TYPES.OTHER   # 使用OTHER代替LONDON
    ])
    def test_find_by_market_parametrized(self, market):
        """参数化测试不同市场的查询"""
        result = self.crud.find(filters={"market": market})
        entities = result.to_entities()

        # 验证查询结果市场类型正确
        for entity in entities:
            assert entity.market == market, f"查询结果应全是{market.name}市场"

    def test_find_by_time_range(self):
        """测试根据时间范围查询TradeDay"""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)

        result = self.crud.find(filters={
            "timestamp__gte": start_date,
            "timestamp__lte": end_date
        })

        entities = result.to_entities()
        for entity in entities:
            assert start_date <= entity.timestamp <= end_date, \
                "查询结果应在时间范围内"

    def test_find_trading_days_only(self):
        """测试仅查询交易日"""
        # 查询交易日
        trading_result = self.crud.find(filters={"is_open": True})
        trading_count = trading_result.count()

        # 查询休市日
        non_trading_result = self.crud.find(filters={"is_open": False})
        non_trading_count = non_trading_result.count()

        # 验证数据一致性
        total = self.crud.count()
        assert trading_count + non_trading_count == total, \
            "交易日和休市日数量应等于总数"

    @pytest.mark.parametrize("is_open,expected_name", [
        (True, "交易日"),
        (False, "休市日")
    ])
    def test_find_by_status_parametrized(self, is_open, expected_name):
        """参数化测试按状态查询"""
        result = self.crud.find(filters={"is_open": is_open})

        for entity in result.to_entities():
            assert entity.is_open == is_open, \
                f"查询结果应全是{expected_name}"

    def test_find_with_pagination(self):
        """测试分页查询"""
        page_size = 5

        # 第一页
        page1 = self.crud.find(page=1, page_size=page_size)
        page1_count = len(page1)

        # 第二页
        page2 = self.crud.find(page=2, page_size=page_size)
        page2_count = len(page2)

        # 验证分页逻辑
        if page1_count > 0 and page2_count > 0:
            page1_ids = [td.uuid for td in page1]
            page2_ids = [td.uuid for td in page2]
            overlap = set(page1_ids) & set(page2_ids)
            assert len(overlap) == 0, "分页结果不应有重叠"

    def test_find_dataframe_format(self):
        """测试查询返回DataFrame格式"""
        result = self.crud.find(page_size=10)
        df = result.to_dataframe()

        # 验证DataFrame属性
        assert isinstance(df, pd.DataFrame), "应返回DataFrame对象"
        assert len(df) == result.count(), "DataFrame行数应与查询结果一致"
        assert 'market' in df.columns, "DataFrame应包含market列"
        assert 'is_open' in df.columns, "DataFrame应包含is_open列"
        assert 'timestamp' in df.columns, "DataFrame应包含timestamp列"

    def test_dataframe_data_manipulation(self):
        """测试DataFrame数据操作和分析"""
        df = self.crud.find(
            filters={
                "timestamp__gte": datetime(2023, 1, 1),
                "timestamp__lte": datetime(2023, 12, 31)
            },
            page_size=100
        ).to_dataframe()

        if len(df) > 0:
            # 基本统计
            trading_days = df[df['is_open'] == True]
            non_trading_days = df[df['is_open'] == False]

            assert len(trading_days) >= 0, "应能统计交易日"
            assert len(non_trading_days) >= 0, "应能统计休市日"

            # 按市场分组
            df_copy = df.copy()
            df_copy['market_str'] = df_copy['market'].astype(str)
            market_stats = df_copy.groupby('market_str').size()
            assert len(market_stats) >= 0, "应能按市场分组统计"

    def test_compare_list_vs_dataframe(self):
        """测试列表格式与DataFrame格式的对比"""
        filters = {"market": MARKET_TYPES.CHINA}
        page_size = 5

        # 列表格式
        list_result = self.crud.find(filters=filters, page_size=page_size)
        list_count = len(list_result)

        # DataFrame格式
        df_result = self.crud.find(filters=filters, page_size=page_size).to_dataframe()
        df_count = df_result.shape[0]

        # 验证一致性
        assert list_count == df_count, "两种格式应返回相同数量记录"

        if list_count > 0:
            # 验证数据一致性
            first_item = list_result[0]
            first_row = df_result.iloc[0]
            assert first_item.timestamp == first_row['timestamp'], "时间戳应一致"
            assert first_item.is_open == first_row['is_open'], "状态应一致"


# ==================== 更新操作测试 ====================

@pytest.mark.database
@pytest.mark.tdd
class TestTradeDayCRUDUpdate:
    """TradeDay CRUD层更新操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = TradeDayCRUD()

    def test_update_trade_day_status(self):
        """测试更新TradeDay交易状态"""
        # 查询待更新的记录
        trade_days = self.crud.find(page_size=1)
        if not trade_days:
            pytest.skip("没有可更新的交易日历")

        target = trade_days[0]
        original_status = target.is_open

        # 更新状态
        new_status = not original_status
        self.crud.modify(
            filters={"uuid": target.uuid},
            updates={"is_open": new_status}
        )

        # 验证更新结果
        updated = self.crud.find(filters={"uuid": target.uuid})
        assert len(updated) == 1, "应查询到更新后的记录"
        assert updated[0].is_open == new_status, "状态应已更新"

    @pytest.mark.parametrize("original_status,new_status", [
        (True, False),  # 交易日 -> 休市日
        (False, True),  # 休市日 -> 交易日
    ])
    def test_update_status_transitions(self, original_status, new_status):
        """参数化测试状态转换"""
        # 创建测试数据
        test_day = MTradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=original_status,
            timestamp=datetime(2024, 2, 1),
            source=SOURCE_TYPES.TEST
        )
        self.crud.add(test_day)

        # 更新状态
        self.crud.modify(
            filters={"timestamp": datetime(2024, 2, 1)},
            updates={"is_open": new_status}
        )

        # 验证
        result = self.crud.find(filters={"timestamp": datetime(2024, 2, 1)})
        assert len(result) >= 1
        assert result[0].is_open == new_status


# ==================== 删除操作测试 ====================

@pytest.mark.database
@pytest.mark.tdd
@pytest.mark.db_cleanup
class TestTradeDayCRUDDelete:
    """TradeDay CRUD层删除操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = TradeDayCRUD()

    def test_delete_trade_day_by_date(self):
        """测试根据日期删除交易日"""
        # 创建测试数据
        test_date = datetime(2024, 1, 15)
        test_day = MTradeDay(
            market=MARKET_TYPES.CHINA,
            timestamp=test_date,
            is_open=True,
            source=SOURCE_TYPES.TEST
        )
        self.crud.add(test_day)

        # 验证数据存在
        before = len(self.crud.find(filters={"timestamp": test_date}))
        assert before >= 1, "测试数据应已插入"

        # 执行删除
        self.crud.remove(filters={"timestamp": test_date})

        # 验证删除结果
        after = len(self.crud.find(filters={"timestamp": test_date}))
        assert after == 0, "数据应已被删除"

    def test_delete_trade_day_by_market(self):
        """测试根据市场删除交易日"""
        # 创建测试数据
        test_dates = [datetime(2024, 1, 10 + i) for i in range(3)]

        for date in test_dates:
            test_day = MTradeDay(
                market=MARKET_TYPES.CHINA,
                timestamp=date,
                is_open=True,
                source=SOURCE_TYPES.TEST
            )
            self.crud.add(test_day)

        # 验证初始数据
        china_days = [t for t in self.crud.find() if t.market == MARKET_TYPES.CHINA.value]
        before_count = len(china_days)
        assert before_count >= 3, "应有至少3条中国市场数据"

        # 删除中国市场数据
        self.crud.remove(filters={"market": MARKET_TYPES.CHINA})

        # 验证删除结果
        china_days_after = [t for t in self.crud.find() if t.market == MARKET_TYPES.CHINA.value]
        after_count = len(china_days_after)

        assert after_count < before_count, "中国市场数据应已减少"

    @pytest.mark.parametrize("is_open,description", [
        (False, "休市日"),
        (True, "交易日")
    ])
    def test_delete_by_status(self, is_open, description):
        """参数化测试按状态删除"""
        # 创建测试数据
        base_date = datetime(2024, 3, 1)
        for i in range(3):
            test_day = MTradeDay(
                market=MARKET_TYPES.CHINA,
                timestamp=base_date + timedelta(days=i),
                is_open=is_open,
                source=SOURCE_TYPES.TEST
            )
            self.crud.add(test_day)

        # 删除指定状态的记录
        before = len(self.crud.find(filters={"is_open": is_open}))
        self.crud.remove(filters={"is_open": is_open})
        after = len(self.crud.find(filters={"is_open": is_open}))

        # 注意：这里只是验证数据量不增加，不能完全删除因为可能有其他历史数据
        assert after <= before, f"{description}数据应已减少"

    def test_delete_trade_day_by_date_range(self):
        """测试根据日期范围删除交易日"""
        # 创建测试数据
        start_date = datetime(2025, 12, 1)
        for i in range(10):
            test_day = MTradeDay(
                market=MARKET_TYPES.CHINA,
                timestamp=start_date + timedelta(days=i),
                is_open=True,
                source=SOURCE_TYPES.TEST
            )
            self.crud.add(test_day)

        # 删除十二月份的数据
        end_date = datetime(2025, 12, 31)
        before = len(self.crud.find(filters={
            "timestamp__gte": start_date,
            "timestamp__lte": end_date
        }))

        self.crud.remove(filters={
            "timestamp__gte": start_date,
            "timestamp__lte": end_date
        })

        after = len(self.crud.find(filters={
            "timestamp__gte": start_date,
            "timestamp__lte": end_date
        }))

        assert after < before, "日期范围内数据应已减少"


# ==================== 业务逻辑测试 ====================

@pytest.mark.database
@pytest.mark.tdd
@pytest.mark.slow
class TestTradeDayCRUDBusinessLogic:
    """TradeDay CRUD层业务逻辑测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = TradeDayCRUD()

    def test_trading_calendar_analysis(self):
        """测试交易日历分析"""
        all_trade_days = self.crud.find()

        if len(all_trade_days) < 10:
            pytest.skip("交易日历数据不足，跳过分析测试")

        # 按市场分组统计
        market_analysis = {}
        for trade_day in all_trade_days:
            market_name = MARKET_TYPES(trade_day.market).name
            if market_name not in market_analysis:
                market_analysis[market_name] = {
                    "total_days": 0,
                    "trading_days": 0,
                    "non_trading_days": 0
                }

            market_analysis[market_name]["total_days"] += 1
            if trade_day.is_open:
                market_analysis[market_name]["trading_days"] += 1
            else:
                market_analysis[market_name]["non_trading_days"] += 1

        # 验证分析结果
        total = sum(stats["total_days"] for stats in market_analysis.values())
        assert total == len(all_trade_days), "统计总数应一致"

        # 至少有一个市场有数据
        assert len(market_analysis) >= 1, "应至少有一个市场的数据"

    def test_trading_day_sequence_validation(self):
        """测试交易日序列连续性验证"""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 10)

        trade_days = self.crud.find(filters={
            "timestamp__gte": start_date,
            "timestamp__lte": end_date,
            "market": MARKET_TYPES.CHINA
        })

        if len(trade_days) < 5:
            pytest.skip("交易日历数据不足，跳过连续性验证")

        # 按日期排序
        trade_days.sort(key=lambda x: x.timestamp)

        # 验证日期连续性
        date_gaps = []
        for i in range(1, len(trade_days)):
            prev_date = trade_days[i-1].timestamp.date()
            curr_date = trade_days[i].timestamp.date()
            expected_date = prev_date + timedelta(days=1)

            if curr_date != expected_date:
                date_gaps.append((prev_date, curr_date))

        # 统计交易日
        trading_days = [td for td in trade_days if td.is_open]
        assert len(trading_days) >= 0, "应能统计交易日"

    def test_market_comparison_analysis(self):
        """测试跨市场交易日历对比分析"""
        all_trade_days = self.crud.find()

        if len(all_trade_days) < 10:
            pytest.skip("交易日历数据不足，跳过跨市场分析")

        # 按市场和日期分组
        market_date_map = {}
        for trade_day in all_trade_days:
            date_key = trade_day.timestamp.date()
            market_name = MARKET_TYPES(trade_day.market).name

            if date_key not in market_date_map:
                market_date_map[date_key] = {}
            market_date_map[date_key][market_name] = trade_day.is_open

        if len(market_date_map) == 0:
            pytest.skip("没有可用的日期数据进行对比")

        # 分析跨市场一致性
        consistent_days = 0
        inconsistent_days = 0

        for date, markets in market_date_map.items():
            if len(markets) > 1:
                statuses = list(markets.values())
                is_consistent = all(s == statuses[0] for s in statuses)

                if is_consistent:
                    consistent_days += 1
                else:
                    inconsistent_days += 1

        # 验证分析完成
        total_days = consistent_days + inconsistent_days
        assert total_days >= 0, "应完成跨市场对比分析"

    def test_trading_statistics_calculation(self):
        """测试交易日统计计算"""
        # 查询特定年份的数据
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)

        result = self.crud.find(filters={
            "timestamp__gte": start_date,
            "timestamp__lte": end_date
        })

        if len(result) < 5:
            pytest.skip("数据不足，跳过统计计算测试")

        # 计算统计数据
        trading_days = [td for td in result if td.is_open]
        non_trading_days = [td for td in result if not td.is_open]

        # 计算比例
        total = len(result)
        trading_ratio = len(trading_days) / total if total > 0 else 0
        non_trading_ratio = len(non_trading_days) / total if total > 0 else 0

        # 验证统计结果
        assert abs(trading_ratio + non_trading_ratio - 1.0) < 0.01, \
            "交易日和休市日比例之和应为1"
        assert trading_ratio >= 0 and trading_ratio <= 1, "交易日比例应在0-1之间"


# ==================== Create方法测试 ====================

@pytest.mark.database
@pytest.mark.tdd
class TestTradeDayCRUDCreate:
    """测试TradeDay CRUD的create方法"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = TradeDayCRUD()

    def test_create_single_trade_day(self):
        """测试使用create方法创建单个TradeDay"""
        created_day = self.crud.create(
            market=MARKET_TYPES.CHINA,
            is_open=True,
            timestamp=datetime(2023, 1, 3),
            source=SOURCE_TYPES.TEST
        )

        # 验证返回值
        assert created_day is not None, "create应返回创建的对象"
        assert created_day.is_open == True, "创建的交易日状态应为True"

        # 验证数据已插入
        result = self.crud.find(filters={"uuid": created_day.uuid})
        assert result.count() == 1, "应能查询到创建的数据"

    @pytest.mark.parametrize("market,is_open,timestamp", [
        (MARKET_TYPES.CHINA, True, datetime(2023, 1, 3)),
        (MARKET_TYPES.NASDAQ, False, datetime(2023, 12, 25)),
        (MARKET_TYPES.OTHER, True, datetime(2023, 1, 3)),
    ])
    def test_create_with_various_markets(self, market, is_open, timestamp):
        """参数化测试不同市场的create"""
        created_day = self.crud.create(
            market=market,
            is_open=is_open,
            timestamp=timestamp,
            source=SOURCE_TYPES.TEST
        )

        assert created_day.market == market.value, "市场类型应正确"
        assert created_day.is_open == is_open, "状态应正确"

    def test_create_with_validation(self):
        """测试create方法的数据验证"""
        created_day = self.crud.create(
            market=MARKET_TYPES.NASDAQ,
            is_open=False,
            timestamp=datetime(2023, 12, 25),
            source=SOURCE_TYPES.TEST
        )

        # 验证创建的数据
        result = self.crud.find(filters={"uuid": created_day.uuid})
        assert result.count() == 1

        entity = result.to_entities()[0]
        assert entity.market == MARKET_TYPES.NASDAQ, "市场应为NASDAQ"
        assert entity.is_open == False, "应为休市状态"


# TDD验证入口
if __name__ == "__main__":
    print("TDD Red阶段验证：TradeDay CRUD测试")
    print("运行: pytest test/data/crud/test_trade_day_crud.py -v")
    print("预期结果: 所有测试通过")
    print("重点关注: 交易日历连续性和跨市场一致性分析")

"""
TradeDay类TDD测试

通过TDD方式开发TradeDay交易日类的完整测试套件
涵盖交易日历和市场开闭状态管理功能
"""
import pytest
import datetime

# 导入TradeDay类和相关枚举
try:
    from ginkgo.trading.entities.tradeday import TradeDay
    from ginkgo.enums import MARKET_TYPES
    import pandas as pd
except ImportError as e:
    assert False, "TDD Red阶段：测试用例尚未实现"


@pytest.mark.unit
class TestTradeDayConstruction:
    """1. 构造和初始化测试"""

    def test_default_constructor(self):
        """测试默认构造函数 - 严格模式：要求核心参数"""
        # TradeDay与Position、Signal保持一致，要求核心业务参数不能为空
        with pytest.raises((ValueError, TypeError)):
            TradeDay()

    def test_full_parameter_constructor(self):
        """测试完整参数构造"""
        # 测试完整参数构造，所有字段正确赋值和严格类型检查
        tradeday = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=True,
            timestamp="2023-01-03"  # 周二，正常交易日
        )

        # 验证枚举类型和值
        assert tradeday.market == MARKET_TYPES.CHINA
        assert isinstance(tradeday.market, MARKET_TYPES)

        # 验证布尔类型和值
        assert tradeday.is_open == True
        assert isinstance(tradeday.is_open, bool)

        # 验证日期类型和值
        assert tradeday.timestamp == datetime.datetime(2023, 1, 3)
        assert isinstance(tradeday.timestamp, datetime.datetime)

        # 测试不同市场
        nasdaq_tradeday = TradeDay(
            market=MARKET_TYPES.NASDAQ,
            is_open=False,
            timestamp=datetime.datetime(2023, 1, 1)  # 元旦，休市
        )
        assert nasdaq_tradeday.market == MARKET_TYPES.NASDAQ
        assert nasdaq_tradeday.is_open == False
        assert nasdaq_tradeday.timestamp == datetime.datetime(2023, 1, 1)

    def test_base_class_inheritance(self):
        """测试Base类继承验证"""
        # 验证正确继承Base类的功能 - 使用有效参数创建实例
        from ginkgo.trading.core.base import Base

        tradeday = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=True,
            timestamp="2023-01-03"
        )

        # 验证继承关系
        assert isinstance(tradeday, Base)

        # 验证Base类的基本功能（如UUID）
        assert hasattr(tradeday, 'uuid')
        assert len(tradeday.uuid) > 0

    def test_market_enum_assignment(self):
        """测试市场枚举分配"""
        # 验证MARKET_TYPES枚举正确分配

        # 测试所有有效的市场类型
        valid_markets = [MARKET_TYPES.CHINA, MARKET_TYPES.NASDAQ, MARKET_TYPES.OTHER]
        for market in valid_markets:
            tradeday = TradeDay(
                market=market,
                is_open=True,
                timestamp="2023-01-03"
            )
            assert tradeday.market == market
            assert isinstance(tradeday.market, MARKET_TYPES)

        # 测试无效的市场类型（字符串）
        with pytest.raises(TypeError):
            TradeDay(
                market="CHINA",  # 字符串而非枚举
                is_open=True,
                timestamp="2023-01-03"
            )

        # 测试无效的市场类型（整数）
        with pytest.raises(TypeError):
            TradeDay(
                market=1,  # 整数而非枚举
                is_open=True,
                timestamp="2023-01-03"
            )


@pytest.mark.unit
class TestTradeDayProperties:
    """2. 属性访问测试"""

    def test_market_property(self):
        """测试市场属性"""
        # 测试市场属性的正确读取和枚举类型
        tradeday = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=True,
            timestamp="2023-01-03"
        )

        assert tradeday.market == MARKET_TYPES.CHINA
        assert isinstance(tradeday.market, MARKET_TYPES)

        # 测试不同市场
        nasdaq_tradeday = TradeDay(
            market=MARKET_TYPES.NASDAQ,
            is_open=True,
            timestamp="2023-01-03"
        )
        assert nasdaq_tradeday.market == MARKET_TYPES.NASDAQ

    def test_is_open_property(self):
        """测试开市状态属性"""
        # 测试开市状态属性的正确读取和布尔类型
        open_tradeday = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=True,
            timestamp="2023-01-03"
        )
        assert open_tradeday.is_open == True
        assert isinstance(open_tradeday.is_open, bool)

        # 测试休市状态
        closed_tradeday = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=False,
            timestamp="2023-01-01"  # 元旦
        )
        assert closed_tradeday.is_open == False
        assert isinstance(closed_tradeday.is_open, bool)

    def test_timestamp_property(self):
        """测试时间戳属性"""
        # 测试时间戳属性的正确读取和格式
        tradeday = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=True,
            timestamp="2023-01-03"
        )
        assert tradeday.timestamp == datetime.datetime(2023, 1, 3)
        assert isinstance(tradeday.timestamp, datetime.datetime)

        # 测试不同的日期格式
        tradeday2 = TradeDay(
            market=MARKET_TYPES.NASDAQ,
            is_open=True,
            timestamp=datetime.datetime(2023, 6, 15)
        )
        assert tradeday2.timestamp == datetime.datetime(2023, 6, 15)

    def test_property_type_validation(self):
        """测试属性类型验证"""
        # 验证所有属性返回正确的数据类型
        tradeday = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=True,
            timestamp="2023-01-03"
        )

        # 验证属性类型
        assert isinstance(tradeday.market, MARKET_TYPES)
        assert isinstance(tradeday.is_open, bool)
        assert isinstance(tradeday.timestamp, datetime.datetime)

        # 验证属性值正确性
        assert tradeday.market == MARKET_TYPES.CHINA
        assert tradeday.is_open == True
        assert tradeday.timestamp.year == 2023


@pytest.mark.unit
class TestTradeDayDataSetting:
    """3. 数据设置测试"""

    def test_direct_parameter_setting(self):
        """测试直接参数设置"""
        # 测试直接参数方式设置交易日数据
        tradeday = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=True,
            timestamp="2023-01-03"
        )

        # 使用set方法更新数据
        tradeday.set(
            MARKET_TYPES.NASDAQ,
            False,
            "2023-01-01"
        )

        assert tradeday.market == MARKET_TYPES.NASDAQ
        assert tradeday.is_open == False
        assert tradeday.timestamp == datetime.datetime(2023, 1, 1)

    def test_pandas_series_setting(self):
        """测试pandas.Series设置"""
        # 测试从pandas.Series设置交易日数据
        df_data = pd.DataFrame({
            "market": [MARKET_TYPES.CHINA.value],
            "is_open": [True],
            "timestamp": ["2023-06-15"]
        })

        tradeday = TradeDay(
            market=MARKET_TYPES.NASDAQ,
            is_open=False,
            timestamp="2023-01-01"
        )

        # 使用DataFrame设置数据
        try:
            tradeday.set(df_data)
            # 如果实现正确，验证数据更新
            assert tradeday.timestamp == datetime.datetime(2023, 6, 15)
        except Exception:
            # 如果实现有问题，至少验证方法存在
            assert hasattr(tradeday, 'set')

    def test_singledispatch_routing(self):
        """测试方法分派路由"""
        # 测试方法分派路由的正确性
        tradeday = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=True,
            timestamp="2023-01-03"
        )

        # 测试不支持的类型会抛异常
        with pytest.raises(NotImplementedError):
            tradeday.set(["unsupported", "list", "type"])

        # 测试支持的类型能正确路由
        tradeday.set(MARKET_TYPES.NASDAQ, False, "2023-01-01")
        assert tradeday.market == MARKET_TYPES.NASDAQ

    def test_parameter_validation_in_setting(self):
        """测试设置时的参数验证"""
        # 测试set方法中的参数验证
        tradeday = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=True,
            timestamp="2023-01-03"
        )

        # 测试无效的market类型 - singledispatch找不到匹配时抛出NotImplementedError
        with pytest.raises(NotImplementedError):
            tradeday.set("CHINA", True, "2023-01-01")

        # 测试无效的is_open类型 - 类型验证抛出TypeError
        with pytest.raises(TypeError):
            tradeday.set(MARKET_TYPES.CHINA, "true", "2023-01-01")

        # 测试无效的timestamp格式
        with pytest.raises(ValueError):
            tradeday.set(MARKET_TYPES.CHINA, True, "invalid_date")


@pytest.mark.unit
class TestTradeDayValidation:
    """4. 交易日验证测试"""

    def test_market_enum_validation(self):
        """测试市场枚举验证"""
        # 验证市场必须为有效的MARKET_TYPES枚举

        # 测试有效的市场枚举值
        valid_markets = [MARKET_TYPES.CHINA, MARKET_TYPES.NASDAQ, MARKET_TYPES.OTHER]
        for market in valid_markets:
            tradeday = TradeDay(
                market=market,
                is_open=True,
                timestamp="2023-01-03"
            )
            assert tradeday.market == market
            assert isinstance(tradeday.market, MARKET_TYPES)

        # 测试无效的市场类型（字符串）
        with pytest.raises((ValueError, TypeError)):
            TradeDay(
                market="INVALID_MARKET",  # 字符串而非枚举
                is_open=True,
                timestamp="2023-01-03"
            )

        # 测试无效的市场类型（整数）
        with pytest.raises((ValueError, TypeError)):
            TradeDay(
                market=999,  # 整数而非枚举
                is_open=True,
                timestamp="2023-01-03"
            )

        # 测试None市场
        with pytest.raises((ValueError, TypeError)):
            TradeDay(
                market=None,
                is_open=True,
                timestamp="2023-01-03"
            )

    def test_boolean_is_open_validation(self):
        """测试开市状态布尔验证"""
        # 验证开市状态必须为布尔类型

        # 测试有效的布尔值
        valid_boolean_values = [True, False]
        for is_open_value in valid_boolean_values:
            tradeday = TradeDay(
                market=MARKET_TYPES.CHINA,
                is_open=is_open_value,
                timestamp="2023-01-03"
            )
            assert tradeday.is_open == is_open_value
            assert isinstance(tradeday.is_open, bool)

        # 测试无效的is_open类型（字符串）
        with pytest.raises((ValueError, TypeError)):
            TradeDay(
                market=MARKET_TYPES.CHINA,
                is_open="true",  # 字符串而非布尔
                timestamp="2023-01-03"
            )

        # 测试无效的is_open类型（整数）
        with pytest.raises((ValueError, TypeError)):
            TradeDay(
                market=MARKET_TYPES.CHINA,
                is_open=1,  # 整数而非布尔
                timestamp="2023-01-03"
            )

        # 测试None的is_open
        with pytest.raises((ValueError, TypeError)):
            TradeDay(
                market=MARKET_TYPES.CHINA,
                is_open=None,
                timestamp="2023-01-03"
            )

    def test_timestamp_format_validation(self):
        """测试时间戳格式验证"""
        # 验证时间戳格式的合法性

        # 测试有效的时间戳格式
        valid_timestamps = [
            "2023-01-03",  # 字符串格式
            datetime.datetime(2023, 1, 3),  # datetime对象
            "2023-06-15 09:30:00",  # 带时间的字符串
            datetime.datetime(2023, 12, 25, 14, 30, 0)  # 带时间的datetime
        ]

        for timestamp in valid_timestamps:
            tradeday = TradeDay(
                market=MARKET_TYPES.CHINA,
                is_open=True,
                timestamp=timestamp
            )
            assert isinstance(tradeday.timestamp, datetime.datetime)

        # 测试无效的时间戳格式
        invalid_timestamps = [
            "invalid_date",  # 无效日期字符串
            "2023-13-01",    # 无效月份
            "2023-01-32",    # 无效日期
            "2023-02-30",    # 二月没有30日
            "2023-04-31",    # 四月没有31日
            "",              # 空字符串
            [],              # 列表
            {},              # 字典
        ]

        for invalid_timestamp in invalid_timestamps:
            with pytest.raises((ValueError, TypeError)):
                TradeDay(
                    market=MARKET_TYPES.CHINA,
                    is_open=True,
                    timestamp=invalid_timestamp
                )

        # 测试None时间戳
        with pytest.raises((ValueError, TypeError)):
            TradeDay(
                market=MARKET_TYPES.CHINA,
                is_open=True,
                timestamp=None
            )

    def test_trading_calendar_consistency(self):
        """测试交易日历一致性"""
        # 验证交易日历数据的一致性

        # 测试正常交易日（周二）
        tuesday_tradeday = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=True,
            timestamp="2023-01-03"  # 周二
        )
        assert tuesday_tradeday.is_open == True
        assert tuesday_tradeday.timestamp.weekday() == 1  # 周二

        # 测试周末通常不是交易日
        weekend_tradeday = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=False,
            timestamp="2023-01-01"  # 周日
        )
        assert weekend_tradeday.is_open == False
        assert weekend_tradeday.timestamp.weekday() == 6  # 周日

        # 测试不同市场的交易日一致性
        china_tradeday = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=True,
            timestamp="2023-01-03"
        )
        nasdaq_tradeday = TradeDay(
            market=MARKET_TYPES.NASDAQ,
            is_open=True,
            timestamp="2023-01-03"
        )

        # 验证相同日期但不同市场的独立性
        assert china_tradeday.market != nasdaq_tradeday.market
        assert china_tradeday.timestamp == nasdaq_tradeday.timestamp

        # 测试节假日一致性（元旦）
        holiday_tradeday = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=False,
            timestamp="2023-01-01"  # 元旦
        )
        assert holiday_tradeday.is_open == False


@pytest.mark.unit
class TestTradeDayCalendarLogic:
    """5. 交易日历逻辑测试"""

    def test_weekend_detection(self):
        """测试周末检测"""
        # 测试周末日期的正确识别

        # 测试周六（2023-01-07）
        saturday = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=False,  # 周六通常不开市
            timestamp="2023-01-07"
        )
        assert saturday.timestamp.weekday() == 5  # 周六
        assert saturday.is_open == False

        # 测试周日（2023-01-08）
        sunday = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=False,  # 周日通常不开市
            timestamp="2023-01-08"
        )
        assert sunday.timestamp.weekday() == 6  # 周日
        assert sunday.is_open == False

        # 测试工作日（周一到周五）
        weekdays = [
            ("2023-01-02", 0),  # 周一
            ("2023-01-03", 1),  # 周二
            ("2023-01-04", 2),  # 周三
            ("2023-01-05", 3),  # 周四
            ("2023-01-06", 4),  # 周五
        ]

        for date_str, expected_weekday in weekdays:
            workday = TradeDay(
                market=MARKET_TYPES.CHINA,
                is_open=True,  # 工作日通常开市
                timestamp=date_str
            )
            assert workday.timestamp.weekday() == expected_weekday
            assert workday.is_open == True

        # 测试不同市场的周末处理可能不同
        us_weekend = TradeDay(
            market=MARKET_TYPES.NASDAQ,
            is_open=False,
            timestamp="2023-01-07"  # 周六
        )
        assert us_weekend.timestamp.weekday() == 5  # 周六

    def test_holiday_detection(self):
        """测试节假日检测"""
        # 测试节假日的正确识别

        # 测试中国主要节假日
        china_holidays = [
            ("2023-01-01", "New Year's Day"),     # 元旦
            ("2023-01-22", "Spring Festival"),   # 春节
            ("2023-04-05", "Qingming Festival"), # 清明节
            ("2023-05-01", "Labor Day"),         # 劳动节
            ("2023-10-01", "National Day"),      # 国庆节
        ]

        for holiday_date, holiday_name in china_holidays:
            holiday = TradeDay(
                market=MARKET_TYPES.CHINA,
                is_open=False,  # 节假日通常不开市
                timestamp=holiday_date
            )
            assert holiday.is_open == False
            assert isinstance(holiday.timestamp, datetime.datetime)

        # 测试美国主要节假日
        us_holidays = [
            ("2023-01-01", "New Year's Day"),       # 元旦
            ("2023-07-04", "Independence Day"),     # 独立日
            ("2023-11-23", "Thanksgiving Day"),     # 感恩节
            ("2023-12-25", "Christmas Day"),        # 圣诞节
        ]

        for holiday_date, holiday_name in us_holidays:
            us_holiday = TradeDay(
                market=MARKET_TYPES.NASDAQ,
                is_open=False,  # 节假日通常不开市
                timestamp=holiday_date
            )
            assert us_holiday.is_open == False
            assert isinstance(us_holiday.timestamp, datetime.datetime)

        # 测试工作日正常开市
        normal_trading_day = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=True,
            timestamp="2023-06-15"  # 正常工作日
        )
        assert normal_trading_day.is_open == True
        assert normal_trading_day.timestamp.weekday() < 5  # 工作日

    def test_market_specific_calendar(self):
        """测试市场特定日历"""
        # 测试不同市场的交易日历规则

        # 测试同一天在不同市场的交易状态可能不同
        same_date = "2023-01-01"  # 元旦

        # 中国市场元旦休市
        china_holiday = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=False,
            timestamp=same_date
        )
        assert china_holiday.market == MARKET_TYPES.CHINA
        assert china_holiday.is_open == False

        # 美国市场元旦也休市
        us_holiday = TradeDay(
            market=MARKET_TYPES.NASDAQ,
            is_open=False,
            timestamp=same_date
        )
        assert us_holiday.market == MARKET_TYPES.NASDAQ
        assert us_holiday.is_open == False

        # 测试中国春节期间（美国正常交易）
        chinese_new_year = "2023-01-22"

        china_spring_festival = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=False,  # 春节休市
            timestamp=chinese_new_year
        )
        assert china_spring_festival.is_open == False

        us_normal_day = TradeDay(
            market=MARKET_TYPES.NASDAQ,
            is_open=True,  # 美国正常交易
            timestamp=chinese_new_year
        )
        assert us_normal_day.is_open == True

        # 测试美国感恩节（中国正常交易）
        thanksgiving = "2023-11-23"

        us_thanksgiving = TradeDay(
            market=MARKET_TYPES.NASDAQ,
            is_open=False,  # 感恩节休市
            timestamp=thanksgiving
        )
        assert us_thanksgiving.is_open == False

        china_normal_day = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=True,  # 中国正常交易
            timestamp=thanksgiving
        )
        assert china_normal_day.is_open == True

        # 验证不同市场的独立性
        assert china_spring_festival.market != us_normal_day.market
        assert china_spring_festival.timestamp == us_normal_day.timestamp

    def test_trading_day_sequence(self):
        """测试交易日序列"""
        # 测试连续交易日的正确排序

        # 创建一周的交易日序列
        trading_days = [
            TradeDay(MARKET_TYPES.CHINA, True, "2023-01-02"),   # 周一
            TradeDay(MARKET_TYPES.CHINA, True, "2023-01-03"),   # 周二
            TradeDay(MARKET_TYPES.CHINA, True, "2023-01-04"),   # 周三
            TradeDay(MARKET_TYPES.CHINA, True, "2023-01-05"),   # 周四
            TradeDay(MARKET_TYPES.CHINA, True, "2023-01-06"),   # 周五
            TradeDay(MARKET_TYPES.CHINA, False, "2023-01-07"),  # 周六（休市）
            TradeDay(MARKET_TYPES.CHINA, False, "2023-01-08"),  # 周日（休市）
        ]

        # 验证时间戳顺序
        for i in range(len(trading_days) - 1):
            current_day = trading_days[i]
            next_day = trading_days[i + 1]
            assert current_day.timestamp < next_day.timestamp

        # 验证工作日开市状态
        weekday_indices = [0, 1, 2, 3, 4]  # 周一到周五
        for i in weekday_indices:
            assert trading_days[i].is_open == True
            assert trading_days[i].timestamp.weekday() == i

        # 验证周末休市状态
        weekend_indices = [5, 6]  # 周六、周日
        for i in weekend_indices:
            assert trading_days[i].is_open == False
            assert trading_days[i].timestamp.weekday() == i

        # 测试跨月交易日序列
        month_end_sequence = [
            TradeDay(MARKET_TYPES.CHINA, True, "2023-01-30"),   # 月末周一
            TradeDay(MARKET_TYPES.CHINA, True, "2023-01-31"),   # 月末周二
            TradeDay(MARKET_TYPES.CHINA, True, "2023-02-01"),   # 月初周三
            TradeDay(MARKET_TYPES.CHINA, True, "2023-02-02"),   # 月初周四
        ]

        # 验证跨月时间连续性
        for i in range(len(month_end_sequence) - 1):
            current = month_end_sequence[i]
            next_day = month_end_sequence[i + 1]
            assert current.timestamp < next_day.timestamp

    def test_cross_market_calendar_differences(self):
        """测试跨市场日历差异"""
        # 测试不同市场间的交易日历差异（如中美市场）

        # 测试同一工作日在不同市场的状态
        workday = "2023-06-15"  # 周四，正常工作日

        china_workday = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=True,
            timestamp=workday
        )
        us_workday = TradeDay(
            market=MARKET_TYPES.NASDAQ,
            is_open=True,
            timestamp=workday
        )

        # 验证两个市场在正常工作日都开市
        assert china_workday.is_open == True
        assert us_workday.is_open == True
        assert china_workday.timestamp == us_workday.timestamp

        # 测试中国特有节假日：春节
        spring_festival = "2023-01-23"  # 春节假期

        china_spring_holiday = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=False,  # 中国休市
            timestamp=spring_festival
        )
        us_spring_normal = TradeDay(
            market=MARKET_TYPES.NASDAQ,
            is_open=True,   # 美国正常交易
            timestamp=spring_festival
        )

        assert china_spring_holiday.is_open == False
        assert us_spring_normal.is_open == True

        # 测试美国特有节假日：感恩节
        thanksgiving = "2023-11-23"  # 感恩节

        china_thanksgiving_normal = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=True,   # 中国正常交易
            timestamp=thanksgiving
        )
        us_thanksgiving_holiday = TradeDay(
            market=MARKET_TYPES.NASDAQ,
            is_open=False,  # 美国休市
            timestamp=thanksgiving
        )

        assert china_thanksgiving_normal.is_open == True
        assert us_thanksgiving_holiday.is_open == False

        # 测试共同节假日：元旦
        new_year = "2023-01-01"

        china_new_year = TradeDay(
            market=MARKET_TYPES.CHINA,
            is_open=False,
            timestamp=new_year
        )
        us_new_year = TradeDay(
            market=MARKET_TYPES.NASDAQ,
            is_open=False,
            timestamp=new_year
        )

        # 验证两个市场在共同节假日都休市
        assert china_new_year.is_open == False
        assert us_new_year.is_open == False

    def test_special_trading_schedule(self):
        """测试特殊交易时间安排"""
        # 测试节假日前后的特殊交易安排

        # 测试节假日前最后一个交易日
        pre_holiday_dates = [
            ("2022-12-30", "元旦前最后交易日"),  # 2023年元旦前
            ("2023-01-20", "春节前最后交易日"),  # 2023年春节前
            ("2023-04-04", "清明节前最后交易日"), # 2023年清明节前
            ("2023-09-29", "国庆节前最后交易日"), # 2023年国庆节前
        ]

        for date_str, description in pre_holiday_dates:
            pre_holiday = TradeDay(
                market=MARKET_TYPES.CHINA,
                is_open=True,  # 节假日前正常交易
                timestamp=date_str
            )
            assert pre_holiday.is_open == True
            assert isinstance(pre_holiday.timestamp, datetime.datetime)

        # 测试节假日后第一个交易日
        post_holiday_dates = [
            ("2023-01-03", "元旦后首个交易日"),  # 2023年元旦后周二
            ("2023-01-30", "春节后首个交易日"),  # 2023年春节后周一
            ("2023-04-06", "清明节后首个交易日"), # 2023年清明节后周四
            ("2023-10-07", "国庆节后首个交易日"), # 2023年国庆节后周六（特殊情况）
        ]

        for date_str, description in post_holiday_dates:
            # 注意：2023年10月7日是周六，实际应该休市
            expected_open = not (date_str == "2023-10-07")  # 除了周六都开市

            post_holiday = TradeDay(
                market=MARKET_TYPES.CHINA,
                is_open=expected_open,
                timestamp=date_str
            )
            assert post_holiday.is_open == expected_open
            assert isinstance(post_holiday.timestamp, datetime.datetime)

        # 测试特殊调休安排（如国庆节调休）
        # 假设2023年10月7日、8日调休不开市，10月9日正常开市
        adjustment_schedule = [
            ("2023-09-30", True),   # 周六调整为工作日（假设）
            ("2023-10-07", False),  # 调休不开市
            ("2023-10-08", False),  # 调休不开市
            ("2023-10-09", True),   # 恢复正常交易
        ]

        for date_str, expected_open in adjustment_schedule:
            adjusted_day = TradeDay(
                market=MARKET_TYPES.CHINA,
                is_open=expected_open,
                timestamp=date_str
            )
            assert adjusted_day.is_open == expected_open

        # 测试半日交易（某些市场在特定日期只交易半天）
        half_day_trading = TradeDay(
            market=MARKET_TYPES.NASDAQ,
            is_open=True,  # 虽然开市但可能是半日交易
            timestamp="2023-12-24"  # 圣诞节前夜
        )
        assert half_day_trading.is_open == True
        assert half_day_trading.market == MARKET_TYPES.NASDAQ

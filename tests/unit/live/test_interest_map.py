"""
InterestMap 单元测试

测试 InterestMap 的核心功能：
1. 添加Portfolio订阅
2. 移除Portfolio订阅
3. 查询订阅某股票的Portfolio列表
4. 更新Portfolio订阅
5. 边界情况处理
6. 线程安全（基础验证）
"""

import pytest

from ginkgo.workers.execution_node.interest_map import InterestMap


@pytest.mark.unit
class TestInterestMapInitialization:
    """测试 InterestMap 初始化"""

    def test_init_creates_empty_map(self):
        """测试初始化创建空的interest_map"""
        interest_map = InterestMap()

        assert interest_map.interest_map == {}
        assert interest_map.size() == 0
        assert len(interest_map) == 0

        print(f"✅ InterestMap 初始化成功")

    def test_init_with_lock(self):
        """测试初始化创建锁"""
        interest_map = InterestMap()

        assert interest_map.lock is not None

        print(f"✅ InterestMap 锁初始化成功")


@pytest.mark.unit
class TestInterestMapAddPortfolio:
    """测试添加Portfolio订阅"""

    def test_add_portfolio_single_code(self):
        """测试添加单个股票代码订阅"""
        interest_map = InterestMap()

        interest_map.add_portfolio("portfolio_1", ["000001.SZ"])

        assert "000001.SZ" in interest_map
        assert "portfolio_1" in interest_map.get_portfolios("000001.SZ")

        print(f"✅ 添加单个股票代码订阅成功")

    def test_add_portfolio_multiple_codes(self):
        """测试添加多个股票代码订阅"""
        interest_map = InterestMap()

        codes = ["000001.SZ", "000002.SZ", "600000.SH"]
        interest_map.add_portfolio("portfolio_1", codes)

        assert interest_map.size() == 3
        assert interest_map.get_portfolios("000001.SZ") == ["portfolio_1"]
        assert interest_map.get_portfolios("000002.SZ") == ["portfolio_1"]
        assert interest_map.get_portfolios("600000.SH") == ["portfolio_1"]

        print(f"✅ 添加多个股票代码订阅成功")

    def test_add_multiple_portfolios_same_code(self):
        """测试多个Portfolio订阅同一股票"""
        interest_map = InterestMap()

        interest_map.add_portfolio("portfolio_1", ["000001.SZ"])
        interest_map.add_portfolio("portfolio_2", ["000001.SZ"])

        portfolios = interest_map.get_portfolios("000001.SZ")
        assert len(portfolios) == 2
        assert "portfolio_1" in portfolios
        assert "portfolio_2" in portfolios

        print(f"✅ 多个Portfolio订阅同一股票成功")

    def test_add_portfolio_duplicate_subscription(self):
        """测试重复订阅（幂等性）"""
        interest_map = InterestMap()

        interest_map.add_portfolio("portfolio_1", ["000001.SZ"])
        interest_map.add_portfolio("portfolio_1", ["000001.SZ"])

        portfolios = interest_map.get_portfolios("000001.SZ")
        assert portfolios == ["portfolio_1"]  # 不重复

        print(f"✅ 重复订阅幂等性正确")


@pytest.mark.unit
class TestInterestMapRemovePortfolio:
    """测试移除Portfolio订阅"""

    def test_remove_portfolio(self):
        """测试移除Portfolio订阅"""
        interest_map = InterestMap()

        interest_map.add_portfolio("portfolio_1", ["000001.SZ", "000002.SZ"])
        interest_map.remove_portfolio("portfolio_1", ["000001.SZ"])

        assert "000001.SZ" not in interest_map
        assert "000002.SZ" in interest_map

        print(f"✅ 移除Portfolio订阅成功")

    def test_remove_portfolio_last_subscriber(self):
        """测试移除最后一个订阅者时删除code条目"""
        interest_map = InterestMap()

        interest_map.add_portfolio("portfolio_1", ["000001.SZ"])
        interest_map.remove_portfolio("portfolio_1", ["000001.SZ"])

        assert "000001.SZ" not in interest_map
        assert interest_map.size() == 0

        print(f"✅ 移除最后一个订阅者时删除code条目")

    def test_remove_portfolio_nonexistent(self):
        """测试移除不存在的订阅（不报错）"""
        interest_map = InterestMap()

        # 不应该报错
        interest_map.remove_portfolio("portfolio_1", ["000001.SZ"])

        print(f"✅ 移除不存在的订阅不报错")


@pytest.mark.unit
class TestInterestMapGetPortfolios:
    """测试查询订阅的Portfolio列表"""

    def test_get_portfolios_existing_code(self):
        """测试查询存在的股票代码"""
        interest_map = InterestMap()

        interest_map.add_portfolio("portfolio_1", ["000001.SZ"])
        interest_map.add_portfolio("portfolio_2", ["000001.SZ"])

        portfolios = interest_map.get_portfolios("000001.SZ")
        assert len(portfolios) == 2
        assert "portfolio_1" in portfolios
        assert "portfolio_2" in portfolios

        print(f"✅ 查询存在的股票代码成功")

    def test_get_portfolios_nonexistent_code(self):
        """测试查询不存在的股票代码"""
        interest_map = InterestMap()

        portfolios = interest_map.get_portfolios("999999.SZ")

        assert portfolios == []

        print(f"✅ 查询不存在的股票代码返回空列表")

    def test_get_portfolios_after_remove(self):
        """测试移除后查询"""
        interest_map = InterestMap()

        interest_map.add_portfolio("portfolio_1", ["000001.SZ"])
        interest_map.add_portfolio("portfolio_2", ["000001.SZ"])
        interest_map.remove_portfolio("portfolio_1", ["000001.SZ"])

        portfolios = interest_map.get_portfolios("000001.SZ")
        assert portfolios == ["portfolio_2"]

        print(f"✅ 移除后查询正确")


@pytest.mark.unit
class TestInterestMapUpdatePortfolio:
    """测试更新Portfolio订阅"""

    def test_update_portfolio(self):
        """测试更新Portfolio订阅"""
        interest_map = InterestMap()

        old_codes = ["000001.SZ", "000002.SZ"]
        new_codes = ["600000.SH", "600036.SH"]

        interest_map.add_portfolio("portfolio_1", old_codes)
        interest_map.update_portfolio("portfolio_1", old_codes, new_codes)

        # 旧订阅应该被移除
        assert "000001.SZ" not in interest_map
        assert "000002.SZ" not in interest_map

        # 新订阅应该被添加
        assert interest_map.get_portfolios("600000.SH") == ["portfolio_1"]
        assert interest_map.get_portfolios("600036.SH") == ["portfolio_1"]

        print(f"✅ 更新Portfolio订阅成功")

    def test_update_portfolio_overlap(self):
        """测试更新时部分重叠"""
        interest_map = InterestMap()

        old_codes = ["000001.SZ", "000002.SZ"]
        new_codes = ["000002.SZ", "600000.SH"]  # 000002.SZ重叠

        interest_map.add_portfolio("portfolio_1", old_codes)
        interest_map.update_portfolio("portfolio_1", old_codes, new_codes)

        assert "000001.SZ" not in interest_map  # 被移除
        assert "000002.SZ" in interest_map  # 保留
        assert "600000.SH" in interest_map  # 新增

        print(f"✅ 更新Portfolio订阅（重叠）成功")


@pytest.mark.unit
class TestInterestMapGetAllSubscriptions:
    """测试获取Portfolio的所有订阅"""

    def test_get_all_subscriptions(self):
        """测试获取Portfolio订阅的所有股票"""
        interest_map = InterestMap()

        interest_map.add_portfolio("portfolio_1", ["000001.SZ", "000002.SZ"])
        interest_map.add_portfolio("portfolio_2", ["000002.SZ", "600000.SH"])

        subscriptions = interest_map.get_all_subscriptions("portfolio_1")
        assert set(subscriptions) == {"000001.SZ", "000002.SZ"}

        subscriptions = interest_map.get_all_subscriptions("portfolio_2")
        assert set(subscriptions) == {"000002.SZ", "600000.SH"}

        print(f"✅ 获取Portfolio的所有订阅成功")

    def test_get_all_subscriptions_empty(self):
        """测试获取空订阅的Portfolio"""
        interest_map = InterestMap()

        subscriptions = interest_map.get_all_subscriptions("portfolio_1")

        assert subscriptions == []

        print(f"✅ 获取空订阅返回空列表")


@pytest.mark.unit
class TestInterestMapUtilityMethods:
    """测试工具方法"""

    def test_size(self):
        """测试size方法"""
        interest_map = InterestMap()

        assert interest_map.size() == 0

        interest_map.add_portfolio("portfolio_1", ["000001.SZ", "000002.SZ"])
        assert interest_map.size() == 2

        interest_map.add_portfolio("portfolio_2", ["600000.SH"])
        assert interest_map.size() == 3

        print(f"✅ size方法正确")

    def test_len(self):
        """测试__len__方法"""
        interest_map = InterestMap()

        assert len(interest_map) == 0

        interest_map.add_portfolio("portfolio_1", ["000001.SZ"])
        assert len(interest_map) == 1

        print(f"✅ __len__方法正确")

    def test_contains(self):
        """测试__contains__方法"""
        interest_map = InterestMap()

        interest_map.add_portfolio("portfolio_1", ["000001.SZ"])

        assert "000001.SZ" in interest_map
        assert "999999.SZ" not in interest_map

        print(f"✅ __contains__方法正确")

    def test_clear(self):
        """测试clear方法"""
        interest_map = InterestMap()

        interest_map.add_portfolio("portfolio_1", ["000001.SZ", "000002.SZ"])
        assert interest_map.size() == 2

        interest_map.clear()
        assert interest_map.size() == 0
        assert interest_map.interest_map == {}

        print(f"✅ clear方法正确")

    def test_repr(self):
        """测试__repr__方法"""
        interest_map = InterestMap()

        interest_map.add_portfolio("portfolio_1", ["000001.SZ"])
        interest_map.add_portfolio("portfolio_2", ["000001.SZ"])

        repr_str = repr(interest_map)
        assert "InterestMap" in repr_str
        assert "codes=1" in repr_str  # 只有1个唯一代码
        assert "subscriptions=2" in repr_str  # 但有2个订阅

        print(f"✅ __repr__方法正确: {repr_str}")


@pytest.mark.unit
class TestInterestMapIntegration:
    """测试集成场景"""

    def test_multi_portfolio_scenario(self):
        """测试多Portfolio场景"""
        interest_map = InterestMap()

        # Portfolio1订阅：A股
        interest_map.add_portfolio("portfolio_1", ["000001.SZ", "000002.SZ", "600000.SH"])

        # Portfolio2订阅：港股
        interest_map.add_portfolio("portfolio_2", ["00700.HK", "00705.HK"])

        # Portfolio3订阅：美股
        interest_map.add_portfolio("portfolio_3", ["AAPL", "MSFT"])

        # 验证A股路由
        sz_portfolios = interest_map.get_portfolios("000001.SZ")
        assert sz_portfolios == ["portfolio_1"]

        # 验证港股路由
        hk_portfolios = interest_map.get_portfolios("00700.HK")
        assert hk_portfolios == ["portfolio_2"]

        # 验证美股路由
        us_portfolios = interest_map.get_portfolios("AAPL")
        assert us_portfolios == ["portfolio_3"]

        # 验证总代码数
        assert interest_map.size() == 7

        print(f"✅ 多Portfolio场景测试通过")

    def test_dynamic_subscription_update(self):
        """测试动态更新订阅"""
        interest_map = InterestMap()

        # 初始订阅
        interest_map.add_portfolio("portfolio_1", ["000001.SZ", "000002.SZ"])

        # 更新订阅
        old_codes = ["000001.SZ", "000002.SZ"]
        new_codes = ["600000.SH", "600036.SH", "600519.SH"]
        interest_map.update_portfolio("portfolio_1", old_codes, new_codes)

        # 验证新订阅
        assert interest_map.get_portfolios("600000.SH") == ["portfolio_1"]
        assert interest_map.get_portfolios("600036.SH") == ["portfolio_1"]
        assert interest_map.get_portfolios("600519.SH") == ["portfolio_1"]

        # 验证旧订阅已移除
        assert interest_map.get_portfolios("000001.SZ") == []

        print(f"✅ 动态更新订阅测试通过")

    def test_complex_subscription_overlap(self):
        """测试复杂的订阅重叠场景"""
        interest_map = InterestMap()

        # Portfolio1和Portfolio2都订阅000001.SZ
        interest_map.add_portfolio("portfolio_1", ["000001.SZ", "000002.SZ"])
        interest_map.add_portfolio("portfolio_2", ["000001.SZ", "600000.SH"])
        interest_map.add_portfolio("portfolio_3", ["000002.SZ", "600000.SH"])

        # 验证000001.SZ有2个订阅者
        assert len(interest_map.get_portfolios("000001.SZ")) == 2

        # 验证000002.SZ有2个订阅者
        assert len(interest_map.get_portfolios("000002.SZ")) == 2

        # 验证600000.SH有2个订阅者
        assert len(interest_map.get_portfolios("600000.SH")) == 2

        # 移除portfolio_1
        interest_map.remove_portfolio("portfolio_1", ["000001.SZ", "000002.SZ"])

        # 验证000001.SZ只剩1个订阅者
        assert interest_map.get_portfolios("000001.SZ") == ["portfolio_2"]

        # 验证000002.SZ只剩1个订阅者
        assert interest_map.get_portfolios("000002.SZ") == ["portfolio_3"]

        print(f"✅ 复杂订阅重叠场景测试通过")

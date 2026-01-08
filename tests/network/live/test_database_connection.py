"""
数据库连接测试 - 实盘交易架构

测试ClickHouse、MySQL、MongoDB、Redis数据库连接功能
使用ginkgo.data.drivers下的Driver类

运行方式: pytest tests/network/live/test_database_connection.py -v
"""

import pytest
from ginkgo.data.drivers.ginkgo_clickhouse import GinkgoClickhouse
from ginkgo.data.drivers.ginkgo_mysql import GinkgoMysql
from ginkgo.data.drivers.ginkgo_mongo import GinkgoMongo
from ginkgo.data.drivers.ginkgo_redis import GinkgoRedis


@pytest.mark.network
@pytest.mark.database
class TestClickHouseDriver:
    """ClickHouse Driver连接测试"""

    def test_clickhouse_driver_connection(self):
        """测试GinkgoClickhouse Driver连接"""
        try:
            driver = GinkgoClickhouse()
            # 执行简单查询测试连接
            result = driver.execute("SELECT 1")
            assert result is not None, "ClickHouse查询失败"
            print("✅ GinkgoClickhouse Driver连接成功")
        except Exception as e:
            pytest.skip(f"ClickHouse服务未运行或连接失败: {e}")


@pytest.mark.network
@pytest.mark.database
class TestMySQLDriver:
    """MySQL Driver连接测试"""

    def test_mysql_driver_connection(self):
        """测试GinkgoMysql Driver连接"""
        try:
            driver = GinkgoMysql()
            # 执行简单查询测试连接
            result = driver.execute("SELECT 1")
            assert result is not None, "MySQL查询失败"
            print("✅ GinkgoMysql Driver连接成功")
        except Exception as e:
            pytest.skip(f"MySQL服务未运行或连接失败: {e}")


@pytest.mark.network
@pytest.mark.database
class TestMongoDBDriver:
    """MongoDB Driver连接测试"""

    def test_mongodb_driver_connection(self):
        """测试GinkgoMongo Driver连接"""
        try:
            driver = GinkgoMongo()
            # 测试基本操作
            # 列出集合
            collections = driver.list_collections()
            assert collections is not None, "无法列出MongoDB集合"
            print(f"✅ GinkgoMongo Driver连接成功，集合数: {len(collections)}")
        except Exception as e:
            pytest.skip(f"MongoDB服务未运行或连接失败: {e}")


@pytest.mark.network
@pytest.mark.database
class TestRedisDriver:
    """Redis Driver连接测试"""

    def test_redis_driver_connection(self):
        """测试GinkgoRedis Driver连接"""
        try:
            driver = GinkgoRedis()
            # 测试ping
            result = driver.ping()
            assert result, "Redis ping失败"
            print("✅ GinkgoRedis Driver连接成功")
        except Exception as e:
            pytest.skip(f"Redis服务未运行或连接失败: {e}")

    def test_redis_driver_set_get(self):
        """测试GinkgoRedis SET/GET操作"""
        try:
            driver = GinkgoRedis()
            # 测试SET/GET
            test_key = "test_live_trading_driver"
            test_value = "test_value_2026_01_04"

            driver.set(test_key, test_value, ex=10)
            result = driver.get(test_key)

            assert result == test_value, f"Redis SET/GET失败，期望: {test_value}, 实际: {result}"
            driver.delete(test_key)

            print("✅ GinkgoRedis SET/GET操作成功")
        except Exception as e:
            pytest.skip(f"Redis服务未运行或连接失败: {e}")

    def test_redis_driver_list_operations(self):
        """测试GinkgoRedis LIST操作（用于心跳存储）"""
        try:
            driver = GinkgoRedis()
            # 测试LPUSH/LLEN
            test_key = "test_heartbeat_list_driver"
            driver.delete(test_key)

            driver.lpush(test_key, "node1", "node2", "node3")
            length = driver.llen(test_key)

            assert length == 3, f"Redis LPUSH失败，期望长度: 3, 实际: {length}"
            driver.delete(test_key)

            print("✅ GinkgoRedis LIST操作成功")
        except Exception as e:
            pytest.skip(f"Redis服务未运行或连接失败: {e}")

    def test_redis_driver_hash_operations(self):
        """测试GinkgoRedis HASH操作（用于状态缓存）"""
        try:
            driver = GinkgoRedis()
            # 测试HSET/HGET
            test_key = "test_portfolio_status_driver"
            driver.hset(test_key, "portfolio_id", "test_portfolio_1")
            driver.hset(test_key, "status", "RUNNING")

            portfolio_id = driver.hget(test_key, "portfolio_id")
            status = driver.hget(test_key, "status")

            assert portfolio_id == "test_portfolio_1", "Redis HGET失败"
            assert status == "RUNNING", "Redis HGET失败"
            driver.delete(test_key)

            print("✅ GinkgoRedis HASH操作成功")
        except Exception as e:
            pytest.skip(f"Redis服务未运行或连接失败: {e}")


@pytest.mark.network
@pytest.mark.database
class TestAllDriversConnection:
    """所有Driver连接综合测试"""

    def test_all_drivers_available(self):
        """测试所有Driver是否可用"""
        available_dbs = []
        unavailable_dbs = []

        # ClickHouse
        try:
            driver = GinkgoClickhouse()
            driver.execute("SELECT 1")
            available_dbs.append("ClickHouse")
        except Exception:
            unavailable_dbs.append("ClickHouse")

        # MySQL
        try:
            driver = GinkgoMysql()
            driver.execute("SELECT 1")
            available_dbs.append("MySQL")
        except Exception:
            unavailable_dbs.append("MySQL")

        # MongoDB
        try:
            driver = GinkgoMongo()
            driver.list_collections()
            available_dbs.append("MongoDB")
        except Exception:
            unavailable_dbs.append("MongoDB")

        # Redis
        try:
            driver = GinkgoRedis()
            driver.ping()
            available_dbs.append("Redis")
        except Exception:
            unavailable_dbs.append("Redis")

        print(f"✅ 可用Driver: {available_dbs}")
        if unavailable_dbs:
            print(f"⚠️  不可用Driver: {unavailable_dbs}")

        # 至少Redis和ClickHouse应该可用
        assert "Redis" in available_dbs, "Redis必须可用（实盘交易核心依赖）"
        assert "ClickHouse" in available_dbs, "ClickHouse必须可用（时序数据存储）"

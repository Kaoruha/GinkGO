"""
StockInfoCRUD数据库操作TDD测试 - 股票信息管理

本文件测试StockInfoCRUD类的完整功能，确保股票信息(StockInfo)的增删改查操作正常工作。
股票信息是量化交易的基础数据，记录股票的基本信息。

测试范围：
1. 插入操作 (Insert Operations)
   - 批量插入 (add_batch): 高效创建多个股票信息
   - 单条插入 (add): 创建单个股票信息

2. 查询操作 (Query Operations)
   - 按代码查询 (find_by_code): 查找特定股票
   - 按市场查询 (find_by_market): 查找特定市场股票

3. 更新操作 (Update Operations)
   - 信息更新 (update_info): 更新股票基本信息

4. 删除操作 (Delete Operations)
   - 按代码删除 (delete_by_code): 删除特定股票

TODO: 添加replace方法测试用例
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
from ginkgo.data.models.model_stock_info import MStockInfo
from ginkgo.enums import SOURCE_TYPES, MARKET_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestStockInfoCRUDInsert:
    """StockInfoCRUD层插入操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = StockInfoCRUD()

    def test_add_batch_basic(self):
        """测试批量插入StockInfo数据"""
        print("\n" + "="*60)
        print("开始测试: StockInfo CRUD层批量插入")
        print("="*60)

        # 创建测试StockInfo数据
        test_stocks = [
            MStockInfo(
                code="000001.SZ",
                name="平安银行",
                industry="银行",
                market=MARKET_TYPES.CHINA,
                list_date=datetime(1991, 4, 3),
                source=SOURCE_TYPES.TEST
            ),
            MStockInfo(
                code="000002.SZ",
                name="万科A",
                industry="房地产",
                market=MARKET_TYPES.CHINA,
                list_date=datetime(1991, 1, 29),
                source=SOURCE_TYPES.TEST
            )
        ]

        try:
            # 批量插入
            self.crud.add_batch(test_stocks)

            # 验证可以查询出插入的数据
            query_result = self.crud.find(filters={"code__in": ["000001.SZ", "000002.SZ"]})
            assert len(query_result) >= 2

            print("✓ 批量插入验证通过")

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_stock(self):
        """测试单条StockInfo数据插入"""
        test_stock = MStockInfo(
            code="000858.SZ",
            name="五粮液",
            industry="白酒",
            market=MARKET_TYPES.CHINA,
            list_date=datetime(1998, 4, 27),
            source=SOURCE_TYPES.TEST
        )

        try:
            # 单条插入
            result = self.crud.add(test_stock)

            # 验证返回值类型
            assert isinstance(result, MStockInfo), f"add()应返回MStockInfo对象，实际{type(result)}"

            # 验证数据
            query_result = self.crud.find(filters={"code": "000858.SZ"})
            assert len(query_result) >= 1

            print("✓ 单条插入验证通过")

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestStockInfoCRUDQuery:
    """StockInfoCRUD层查询操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = StockInfoCRUD()

    def test_find_by_code(self):
        """测试根据代码查询StockInfo"""
        try:
            stocks = self.crud.find(filters={"code": "000001.SZ"})
            print(f"✓ 查询到 {len(stocks)} 条记录")

            # 验证查询结果
            for stock in stocks:
                assert stock.code == "000001.SZ"

            print("✓ 按code查询验证通过")

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_market(self):
        """测试根据市场查询StockInfo"""
        try:
            stocks = self.crud.find(filters={"market": MARKET_TYPES.CHINA})
            print(f"✓ 中国市场查询到 {len(stocks)} 条记录")

            # 验证查询结果
            for stock in stocks:
                assert stock.market == MARKET_TYPES.CHINA

            print("✓ 按market查询验证通过")

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
@pytest.mark.db_cleanup
class TestStockInfoCRUDDelete:
    """StockInfoCRUD层删除操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = StockInfoCRUD()

    def test_delete_by_code(self):
        """测试按代码删除StockInfo"""
        try:
            # 创建测试数据
            test_stock = MStockInfo(
                code="TEST999.SZ",
                name="测试股票",
                industry="测试",
                market=MARKET_TYPES.CHINA,
                list_date=datetime(2023, 1, 1),
                source=SOURCE_TYPES.TEST
            )
            self.crud.add(test_stock)

            # 验证数据存在
            before = len(self.crud.find(filters={"code": "TEST999.SZ"}))
            assert before >= 1, "测试数据应已插入"

            # 执行删除
            self.crud.remove(filters={"code": "TEST999.SZ"})

            # 验证删除结果
            after = len(self.crud.find(filters={"code": "TEST999.SZ"}))
            assert after == 0, "数据应已被删除"

            print("✓ 按代码删除验证通过")

        except Exception as e:
            print(f"✗ 删除失败: {e}")
            raise


# TDD验证入口
if __name__ == "__main__":
    print("TDD Red阶段验证：StockInfo CRUD测试")
    print("运行: pytest test/data/crud/test_stock_info_crud_refactored.py -v")
    print("预期结果: 所有测试通过")

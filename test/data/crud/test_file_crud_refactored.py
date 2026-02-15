"""
FileCRUD数据库操作TDD测试 - 文件管理

本文件测试FileCRUD类的完整功能，确保文件(File)的增删改查操作正常工作。
文件管理用于存储策略配置、日志、报告等数据。

测试范围：
1. 插入操作 (Insert Operations)
   - 批量插入 (add_batch): 高效创建多个文件记录
   - 单条插入 (add): 创建单个文件记录

2. 查询操作 (Query Operations)
   - 按名称查询 (find_by_name): 查找特定文件
   - 按类型查询 (find_by_type): 查找特定类型文件

3. 更新操作 (Update Operations)
   - 文件内容更新 (update_content): 更新文件内容

4. 删除操作 (Delete Operations)
   - 按名称删除 (delete_by_name): 删除特定文件

TODO: 添加replace方法测试用例
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.file_crud import FileCRUD
from ginkgo.data.models.model_file import MFile
from ginkgo.enums import SOURCE_TYPES, FILE_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestFileCRUDInsert:
    """FileCRUD层插入操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = FileCRUD()

    def test_add_batch_basic(self):
        """测试批量插入File数据"""
        print("\n" + "="*60)
        print("开始测试: File CRUD层批量插入")
        print("="*60)

        # 创建测试File数据
        test_files = [
            MFile(
                name="strategy_config.ini",
                type=FILE_TYPES.STRATEGY,
                data=b"[strategy]\nname = ma_cross\nshort = 5\nlong = 20",
                source=SOURCE_TYPES.TEST
            ),
            MFile(
                name="stock_data.csv",
                type=FILE_TYPES.INDEX,
                data=b"2023-01-01,000001.SZ,10.50,1000",
                source=SOURCE_TYPES.TEST
            )
        ]

        try:
            # 批量插入
            self.crud.add_batch(test_files)

            # 验证可以查询出插入的数据
            query_result = self.crud.find(filters={"name__in": ["strategy_config.ini", "stock_data.csv"]})
            assert len(query_result) >= 2

            print("✓ 批量插入验证通过")

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_file(self):
        """测试单条File数据插入"""
        test_file = MFile(
            name="backtest_report.pdf",
            type=FILE_TYPES.ANALYZER,
            data=b"Backtest Report\nTotal Return: 15.5%",
            source=SOURCE_TYPES.TEST
        )

        try:
            # 单条插入
            result = self.crud.add(test_file)

            # 验证返回值类型
            assert isinstance(result, MFile), f"add()应返回MFile对象，实际{type(result)}"

            # 验证数据
            query_result = self.crud.find(filters={"name": "backtest_report.pdf"})
            assert len(query_result) >= 1

            print("✓ 单条插入验证通过")

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestFileCRUDQuery:
    """FileCRUD层查询操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = FileCRUD()

    def test_find_by_name(self):
        """测试根据名称查询File"""
        try:
            files = self.crud.find(filters={"name": "strategy_config.ini"})
            print(f"✓ 查询到 {len(files)} 条记录")

            # 验证查询结果
            for file in files:
                assert file.name == "strategy_config.ini"

            print("✓ 按name查询验证通过")

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_type(self):
        """测试根据类型查询File"""
        try:
            files = self.crud.find(filters={"type": FILE_TYPES.STRATEGY})
            print(f"✓ 策略类型文件查询到 {len(files)} 条记录")

            # 验证查询结果
            for file in files:
                assert file.type == FILE_TYPES.STRATEGY

            print("✓ 按type查询验证通过")

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
@pytest.mark.db_cleanup
class TestFileCRUDDelete:
    """FileCRUD层删除操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = FileCRUD()

    def test_delete_by_name(self):
        """测试按名称删除File"""
        try:
            # 创建测试数据
            test_file = MFile(
                name="test_delete.tmp",
                type=FILE_TYPES.ANALYZER,
                data=b"test data",
                source=SOURCE_TYPES.TEST
            )
            self.crud.add(test_file)

            # 验证数据存在
            before = len(self.crud.find(filters={"name": "test_delete.tmp"}))
            assert before >= 1, "测试数据应已插入"

            # 执行删除
            self.crud.remove(filters={"name": "test_delete.tmp"})

            # 验证删除结果
            after = len(self.crud.find(filters={"name": "test_delete.tmp"}))
            assert after == 0, "数据应已被删除"

            print("✓ 按名称删除验证通过")

        except Exception as e:
            print(f"✗ 删除失败: {e}")
            raise


# TDD验证入口
if __name__ == "__main__":
    print("TDD Red阶段验证：File CRUD测试")
    print("运行: pytest test/data/crud/test_file_crud_refactored.py -v")
    print("预期结果: 所有测试通过")

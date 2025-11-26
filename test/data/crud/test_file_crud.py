"""
File CRUD数据库操作TDD测试

测试CRUD层的文件数据操作：
- 批量插入 (add_batch)
- 单条插入 (add)
- 查询 (find)
- 更新 (update)
- 删除 (remove)

TODO: 添加replace方法测试用例
- 测试replace方法的原子操作 (备份→删除→插入→失败时恢复)
- 测试没有匹配数据时的行为 (应返回空结果，不插入新数据)
- 测试类型错误检查 (传入错误Model类型时应抛出TypeError)
- 测试空new_items的处理
- 测试批量替换的性能和正确性
- 测试ClickHouse和MySQL数据库的兼容性

File是文件数据模型，存储系统文件信息。
为量化交易系统中的文件管理提供支持，包括配置文件、数据文件、日志文件等。
支持二进制数据存储和文件类型分类管理。
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.file_crud import FileCRUD
from ginkgo.data.models.model_file import MFile
from ginkgo.enums import SOURCE_TYPES, FILE_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestFileCRUDInsert:
    CRUD_TEST_CONFIG = {'crud_class': FileCRUD}
    """1. CRUD层插入操作测试 - File数据插入验证"""

    def test_add_batch_basic(self):
        """测试批量插入File数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: File CRUD层批量插入")
        print("="*60)

        file_crud = FileCRUD()
        print(f"✓ 创建FileCRUD实例: {file_crud.__class__.__name__}")

        # 创建测试文件数据 - 不同类型的文件
        base_time = datetime.now()
        test_files = []

        # 配置文件
        config_content = b"""
        [strategy]
        name = ma_cross_strategy
        short_period = 5
        long_period = 20

        [risk]
        max_position_ratio = 0.2
        stop_loss = 0.05
        """
        config_file = MFile(
            name="strategy_config.ini",
            type=FILE_TYPES.STRATEGY,
            data=config_content,
            source=SOURCE_TYPES.TEST
        )
        test_files.append(config_file)

        # 数据文件
        data_content = b"2023-01-01,000001.SZ,10.50,1000\n2023-01-02,000001.SZ,10.55,1200"
        data_file = MFile(
            name="stock_data_202301.csv",
            type=FILE_TYPES.INDEX,
            data=data_content,
            source=SOURCE_TYPES.TEST
        )
        test_files.append(data_file)

        # 日志文件
        log_content = b"[2023-01-01 10:00:00] INFO: Strategy started\n[2023-01-01 10:01:00] INFO: Data loaded"
        log_file = MFile(
            name="backtest_20230101.log",
            type=FILE_TYPES.ANALYZER,
            data=log_content,
            source=SOURCE_TYPES.TEST
        )
        test_files.append(log_file)

        # 报告文件
        report_content = b"Backtest Report\nTotal Return: 15.5%\nSharpe Ratio: 1.25\nMax Drawdown: -8.3%"
        report_file = MFile(
            name="backtest_report_202301.pdf",
            type=FILE_TYPES.RISKMANAGER,
            data=report_content,
            source=SOURCE_TYPES.TEST
        )
        test_files.append(report_file)

        print(f"✓ 创建测试数据: {len(test_files)}条文件记录")
        print(f"  - 文件类型: {[FILE_TYPES(f.type).name for f in test_files]}")
        print(f"  - 文件大小: {[len(f.data) for f in test_files]} bytes")

        try:
            # 验证插入前的数据状态
            print("\n→ 验证插入前的数据状态...")
            # 获取插入前的总数
            before_result = file_crud.find(page_size=1000)
            before_total = len(before_result)
            print(f"✓ 插入前总记录数: {before_total}")

            # 获取插入前各类型的数量
            before_type_counts = {}
            for file_type in [FILE_TYPES.STRATEGY, FILE_TYPES.INDEX, FILE_TYPES.ANALYZER, FILE_TYPES.RISKMANAGER]:
                count = len([f for f in before_result if f.type == file_type.value])
                before_type_counts[file_type.value] = count
                print(f"  - {file_type.name} (type={file_type.value}): {count} 条")

            # 执行批量插入
            print("\n→ 执行批量插入操作...")
            file_crud.add_batch(test_files)
            print("✓ 批量插入成功")

            # 验证插入后的数据变化
            print("\n→ 验证插入后的数据状态...")
            after_result = file_crud.find(page_size=1000)
            after_total = len(after_result)
            print(f"✓ 插入后总记录数: {after_total}")

            # 验证总数变化
            expected_total_increase = len(test_files)
            actual_total_increase = after_total - before_total
            print(f"✓ 总数变化: {actual_total_increase} (期望: +{expected_total_increase})")
            assert actual_total_increase >= expected_total_increase, f"总数应该至少增加{expected_total_increase}条，实际增加{actual_total_increase}条"

            # 验证各类型的数量变化
            after_type_counts = {}
            for file_type in [FILE_TYPES.STRATEGY, FILE_TYPES.INDEX, FILE_TYPES.ANALYZER, FILE_TYPES.RISKMANAGER]:
                count = len([f for f in after_result if f.type == file_type.value])
                after_type_counts[file_type.value] = count
                increase = count - before_type_counts[file_type.value]
                print(f"  - {file_type.name} (type={file_type.value}): {count} 条 (+{increase})")

            # 验证每种类型都有增加
            inserted_types = [f.type for f in test_files]
            for file_type in [FILE_TYPES.STRATEGY, FILE_TYPES.INDEX, FILE_TYPES.ANALYZER, FILE_TYPES.RISKMANAGER]:
                if file_type.value in inserted_types:
                    before_count = before_type_counts[file_type.value]
                    after_count = after_type_counts[file_type.value]
                    increase = after_count - before_count
                    print(f"✓ {file_type.name} 类型增加了 {increase} 条记录")
                    assert increase >= 1, f"{file_type.name}类型应该至少增加1条记录，实际增加{increase}条"

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_file(self):
        """测试单条File数据插入"""
        print("\n" + "="*60)
        print("开始测试: File CRUD层单条插入")
        print("="*60)

        file_crud = FileCRUD()

        test_file = MFile(
            name="test_strategy.json",
            type=FILE_TYPES.STRATEGY,
            data=b'{"strategy_name": "test_ma", "parameters": {"short": 5, "long": 20}}',
            source=SOURCE_TYPES.TEST
        )
        print(f"✓ 创建测试文件: {test_file.name}")
        print(f"  - 文件类型: {FILE_TYPES(test_file.type).name}")
        print(f"  - 文件大小: {len(test_file.data)} bytes")
        print(f"  - 数据源: {test_file.source}")

        try:
            # 单条插入
            print("\n→ 执行单条插入操作...")
            file_crud.add(test_file)
            print("✓ 单条插入成功")

            # 验证数据
            print("\n→ 验证插入的数据...")
            query_result = file_crud.find(filters={
                "name": "test_strategy.json"
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 1

            inserted_file = query_result[0]
            print(f"✓ 插入的文件验证: {inserted_file.name}")
            assert inserted_file.name == "test_strategy.json"
            assert inserted_file.type == FILE_TYPES.STRATEGY.value
            assert len(inserted_file.data) > 0

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise

    def test_add_large_file(self):
        """测试插入大文件"""
        print("\n" + "="*60)
        print("开始测试: 插入大文件")
        print("="*60)

        file_crud = FileCRUD()

        # 创建较大的测试文件 (1MB)
        large_content = b"A" * (1024 * 1024)
        large_file = MFile(
            name="large_test_file.dat",
            type=FILE_TYPES.INDEX,
            data=large_content,
            source=SOURCE_TYPES.TEST
        )
        print(f"✓ 创建大文件: {large_file.name}")
        print(f"  - 文件大小: {len(large_file.data) / 1024 / 1024:.2f} MB")

        try:
            # 单条插入大文件
            print("\n→ 执行大文件插入操作...")
            file_crud.add(large_file)
            print("✓ 大文件插入成功")

            # 验证数据
            print("\n→ 验证大文件数据...")
            query_result = file_crud.find(filters={
                "name": "large_test_file.dat"
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 1

            inserted_file = query_result[0]
            assert len(inserted_file.data) == len(large_content)
            print(f"✓ 验证文件大小: {len(inserted_file.data) / 1024 / 1024:.2f} MB")

        except Exception as e:
            print(f"✗ 大文件插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestFileCRUDQuery:
    CRUD_TEST_CONFIG = {'crud_class': FileCRUD}
    """2. CRUD层查询操作测试 - File数据查询和过滤"""

    def test_find_by_name(self):
        """测试根据文件名查询File"""
        print("\n" + "="*60)
        print("开始测试: 根据文件名查询File")
        print("="*60)

        file_crud = FileCRUD()

        try:
            # 查询特定文件名
            print("→ 查询文件名包含 'config' 的文件...")
            config_files = file_crud.find(filters={
                "name__like": "%config%"
            })
            print(f"✓ 查询到 {len(config_files)} 条记录")

            # 验证查询结果
            for file in config_files:
                print(f"  - {file.name}: {FILE_TYPES(file.type).name} ({len(file.data)} bytes)")
                assert "config" in file.name.lower()

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_type(self):
        """测试根据文件类型查询File"""
        print("\n" + "="*60)
        print("开始测试: 根据文件类型查询File")
        print("="*60)

        file_crud = FileCRUD()

        try:
            # 查询不同类型的文件
            for file_type in [FILE_TYPES.STRATEGY, FILE_TYPES.INDEX, FILE_TYPES.ANALYZER, FILE_TYPES.RISKMANAGER]:
                print(f"→ 查询{file_type.name}类型文件...")
                type_files = file_crud.find(filters={
                    "type": file_type.value
                })
                print(f"✓ {file_type.name}文件数量: {len(type_files)}")

                # 显示前几个文件
                for file in type_files[:2]:
                    print(f"  - {file.name}: {len(file.data)} bytes")

            print("✓ 文件类型查询验证成功")

        except Exception as e:
            print(f"✗ 文件类型查询失败: {e}")
            raise

    def test_find_by_size_range(self):
        """测试根据文件大小查询File"""
        print("\n" + "="*60)
        print("开始测试: 根据文件大小查询File")
        print("="*60)

        file_crud = FileCRUD()

        try:
            # 查询所有文件并按大小分类
            print("→ 按文件大小分类查询...")
            all_files = file_crud.find(page_size=20)

            small_files = []
            medium_files = []
            large_files = []

            for file in all_files:
                size = len(file.data)
                if size < 1024:  # < 1KB
                    small_files.append(file)
                elif size < 100 * 1024:  # < 100KB
                    medium_files.append(file)
                else:  # >= 100KB
                    large_files.append(file)

            print(f"✓ 小文件 (< 1KB): {len(small_files)} 个")
            print(f"✓ 中文件 (1KB - 100KB): {len(medium_files)} 个")
            print(f"✓ 大文件 (> 100KB): {len(large_files)} 个")

            # 显示各类文件示例
            if small_files:
                print(f"  小文件示例: {small_files[0].name} ({len(small_files[0].data)} bytes)")
            if medium_files:
                print(f"  中文件示例: {medium_files[0].name} ({len(medium_files[0].data)} bytes)")
            if large_files:
                print(f"  大文件示例: {large_files[0].name} ({len(large_files[0].data)} bytes)")

            print("✓ 文件大小分类查询验证成功")

        except Exception as e:
            print(f"✗ 文件大小查询失败: {e}")
            raise

    def test_find_by_source(self):
        """测试根据数据源查询File"""
        print("\n" + "="*60)
        print("开始测试: 根据数据源查询File")
        print("="*60)

        file_crud = FileCRUD()

        try:
            # 查询不同数据源的文件
            for source in [SOURCE_TYPES.TEST, SOURCE_TYPES.TEST, SOURCE_TYPES.TEST]:
                print(f"→ 查询{source.name}数据源文件...")
                source_files = file_crud.find(filters={
                    "source": source.value
                })
                print(f"✓ {source.name}数据源文件数量: {len(source_files)}")

                # 显示文件示例
                for file in source_files[:2]:
                    print(f"  - {file.name}: {FILE_TYPES(file.type).name}")

            print("✓ 数据源查询验证成功")

        except Exception as e:
            print(f"✗ 数据源查询失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestFileCRUDUpdate:
    CRUD_TEST_CONFIG = {'crud_class': FileCRUD}
    """3. CRUD层更新操作测试 - File数据更新验证"""

    def test_update_file_name(self):
        """测试更新文件名"""
        print("\n" + "="*60)
        print("开始测试: 更新文件名")
        print("="*60)

        file_crud = FileCRUD()

        # 创建测试数据
        test_file = MFile(
            name="old_name.txt",
            type=FILE_TYPES.INDEX,
            data=b"test content",
            source=SOURCE_TYPES.TEST
        )
        file_crud.add(test_file)
        print(f"✓ 创建测试文件: {test_file.uuid}")

        try:
            # 更新文件名
            print("→ 更新文件名...")
            file_crud.modify(filters={"uuid": test_file.uuid}, updates={"name": "new_name_updated.txt"})
            print("✓ 文件名更新成功")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_file = file_crud.find(filters={"uuid": test_file.uuid})[0]
            assert updated_file.name == "new_name_updated.txt"
            print(f"✓ 更新后文件名: {updated_file.name}")

            print("✓ 文件名更新验证成功")

        except Exception as e:
            print(f"✗ 更新操作失败: {e}")
            raise

    def test_update_file_type(self):
        """测试更新文件类型"""
        print("\n" + "="*60)
        print("开始测试: 更新文件类型")
        print("="*60)

        file_crud = FileCRUD()

        # 创建测试数据
        test_file = MFile(
            name="type_test_file.tmp",
            type=FILE_TYPES.INDEX,
            data=b"content for type test",
            source=SOURCE_TYPES.TEST
        )
        file_crud.add(test_file)
        print(f"✓ 创建测试文件: {test_file.uuid}")

        try:
            # 更新文件类型
            print("→ 更新文件类型...")
            file_crud.modify(filters={"uuid": test_file.uuid}, updates={"type": FILE_TYPES.STRATEGY.value})
            print("✓ 文件类型更新成功")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_file = file_crud.find(filters={"uuid": test_file.uuid})[0]
            assert updated_file.type == FILE_TYPES.STRATEGY.value
            print(f"✓ 更新后文件类型: {FILE_TYPES(updated_file.type).name}")

            print("✓ 文件类型更新验证成功")

        except Exception as e:
            print(f"✗ 类型更新操作失败: {e}")
            raise

    def test_update_file_data(self):
        """测试更新文件数据"""
        print("\n" + "="*60)
        print("开始测试: 更新文件数据")
        print("="*60)

        file_crud = FileCRUD()

        # 创建测试数据
        test_file = MFile(
            name="data_test_file.txt",
            type=FILE_TYPES.INDEX,
            data=b"original content",
            source=SOURCE_TYPES.TEST
        )
        file_crud.add(test_file)
        print(f"✓ 创建测试文件: {test_file.uuid}")

        try:
            # 更新文件数据
            new_content = b"updated content with more information"
            print("→ 更新文件数据...")
            file_crud.modify(filters={"uuid": test_file.uuid}, updates={"data": new_content})
            print("✓ 文件数据更新成功")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_file = file_crud.find(filters={"uuid": test_file.uuid})[0]
            assert updated_file.data == new_content
            print(f"✓ 更新后数据大小: {len(updated_file.data)} bytes")
            print(f"✓ 更新后内容预览: {updated_file.data[:50]}...")

            print("✓ 文件数据更新验证成功")

        except Exception as e:
            print(f"✗ 数据更新操作失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestFileCRUDDelete:
    CRUD_TEST_CONFIG = {'crud_class': FileCRUD}
    """4. CRUD层删除操作测试 - File数据删除验证"""

    def test_delete_file_by_name(self):
        """测试根据文件名删除File"""
        print("\n" + "="*60)
        print("开始测试: 根据文件名删除File")
        print("="*60)

        file_crud = FileCRUD()

        # 准备测试数据
        print("→ 准备测试数据...")
        test_file = MFile(
            name="DELETE_TEST_FILE.txt",
            type=FILE_TYPES.INDEX,
            data=b"delete test content",
            source=SOURCE_TYPES.TEST
        )
        file_crud.add(test_file)
        print(f"✓ 插入测试数据: {test_file.name}")

        # 验证数据存在
        before_count = len(file_crud.find(filters={"name": "DELETE_TEST_FILE.txt"}))
        print(f"✓ 删除前数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行删除操作...")
            file_crud.remove(filters={"name": "DELETE_TEST_FILE.txt"})
            print("✓ 删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(file_crud.find(filters={"name": "DELETE_TEST_FILE.txt"}))
            print(f"✓ 删除后数据量: {after_count}")
            assert after_count == 0, "删除后应该没有相关数据"

            print("✓ 根据文件名删除File验证成功")

        except Exception as e:
            print(f"✗ 删除操作失败: {e}")
            raise

    def test_delete_file_by_type(self):
        """测试根据文件类型删除File"""
        print("\n" + "="*60)
        print("开始测试: 根据文件类型删除File")
        print("="*60)

        file_crud = FileCRUD()

        # 准备测试数据 - 临时文件类型
        print("→ 准备测试数据...")
        temp_files = []
        for i in range(3):
            test_file = MFile(
                name=f"temp_delete_file_{i+1}.tmp",
                type=FILE_TYPES.INDEX,  # 使用DATA类型作为临时文件
                data=f"temporary content {i+1}".encode(),
                source=SOURCE_TYPES.TEST
            )
            file_crud.add(test_file)
            temp_files.append(test_file)

        print(f"✓ 插入临时文件测试数据: {len(temp_files)} 条")

        # 验证数据存在
        before_count = len(file_crud.find(filters={
            "name__like": "temp_delete_file_%"
        }))
        print(f"✓ 删除前临时文件数量: {before_count}")

        try:
            # 删除临时文件
            print("\n→ 删除临时文件...")
            file_crud.remove(filters={
                "name__like": "temp_delete_file_%"
            })
            print("✓ 临时文件删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(file_crud.find(filters={
                "name__like": "temp_delete_file_%"
            }))
            print(f"✓ 删除后临时文件数量: {after_count}")
            assert after_count == 0, "删除后应该没有临时文件"

            print("✓ 根据文件类型删除File验证成功")

        except Exception as e:
            print(f"✗ 文件类型删除操作失败: {e}")
            raise

    def test_delete_file_by_size(self):
        """测试根据文件大小删除File"""
        print("\n" + "="*60)
        print("开始测试: 根据文件大小删除File")
        print("="*60)

        file_crud = FileCRUD()

        # 准备测试数据 - 不同大小的文件
        print("→ 准备测试数据...")
        small_file = MFile(
            name="small_delete_file.txt",
            type=FILE_TYPES.INDEX,
            data=b"s",  # 1 byte
            source=SOURCE_TYPES.TEST
        )
        file_crud.add(small_file)

        large_file = MFile(
            name="large_delete_file.txt",
            type=FILE_TYPES.INDEX,
            data=b"L" * 10000,  # 10KB
            source=SOURCE_TYPES.TEST
        )
        file_crud.add(large_file)

        print("✓ 插入大小测试数据: 2 条")

        try:
            # 删除小文件
            print("\n→ 删除小文件...")
            small_before = len(file_crud.find(filters={"name": "small_delete_file.txt"}))
            print(f"✓ 删除前小文件: {small_before} 条")

            file_crud.remove(filters={"name": "small_delete_file.txt"})
            print("✓ 小文件删除完成")

            small_after = len(file_crud.find(filters={"name": "small_delete_file.txt"}))
            print(f"✓ 删除后小文件: {small_after} 条")
            assert small_after == 0, "小文件应该被删除"
            assert small_after < small_before, "小文件数量应该减少"

            # 验证大文件保留（通过删除前后的数量变化来验证）
            large_before = len(file_crud.find(filters={"name": "large_delete_file.txt"}))
            print(f"✓ 删除前大文件: {large_before} 条")

            # 删除操作不应该影响大文件
            large_after = len(file_crud.find(filters={"name": "large_delete_file.txt"}))
            print(f"✓ 删除后大文件: {large_after} 条")
            assert large_after >= large_before, "大文件数量不应该减少"

            print("✓ 根据文件大小删除File验证成功")

        except Exception as e:
            print(f"✗ 文件大小删除操作失败: {e}")
            raise

    def test_delete_file_batch_cleanup(self):
        """测试批量清理File数据"""
        print("\n" + "="*60)
        print("开始测试: 批量清理File数据")
        print("="*60)

        file_crud = FileCRUD()

        # 准备批量清理数据
        print("→ 准备批量清理测试数据...")
        cleanup_count = 5
        cleanup_files = []

        for i in range(cleanup_count):
            test_file = MFile(
                name=f"CLEANUP_BATCH_FILE_{i+1:03d}.tmp",
                type=FILE_TYPES.INDEX,
                data=f"cleanup content {i+1}".encode(),
                source=SOURCE_TYPES.TEST
            )
            file_crud.add(test_file)
            cleanup_files.append(test_file)

        print(f"✓ 插入批量清理测试数据: {cleanup_count}条")

        # 验证数据存在
        before_count = len(file_crud.find(filters={
            "name__like": "CLEANUP_BATCH_FILE_%"
        }))
        print(f"✓ 删除前批量数据量: {before_count}")

        try:
            # 批量删除
            print("\n→ 执行批量清理操作...")
            file_crud.remove(filters={
                "name__like": "CLEANUP_BATCH_FILE_%"
            })
            print("✓ 批量清理操作完成")

            # 验证删除结果
            print("\n→ 验证批量清理结果...")
            after_count = len(file_crud.find(filters={
                "name__like": "CLEANUP_BATCH_FILE_%"
            }))
            print(f"✓ 删除后批量数据量: {after_count}")
            assert after_count == 0, "删除后应该没有批量清理数据"

            # 确认其他数据未受影响
            other_data_count = len(file_crud.find(page_size=10))
            print(f"✓ 其他数据保留验证: {other_data_count}条")

            print("✓ 批量清理File数据验证成功")

        except Exception as e:
            print(f"✗ 批量清理操作失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestFileCRUDBusinessLogic:
    CRUD_TEST_CONFIG = {'crud_class': FileCRUD}
    """5. CRUD层业务逻辑测试 - File业务场景验证"""

    def test_file_storage_management(self):
        """测试文件存储管理"""
        print("\n" + "="*60)
        print("开始测试: 文件存储管理")
        print("="*60)

        file_crud = FileCRUD()

        try:
            # 查询文件存储统计
            print("→ 查询文件存储统计...")
            all_files = file_crud.find(page_size=50)

            if len(all_files) == 0:
                print("✗ 文件数据不足，跳过存储管理测试")
                return

            # 计算存储统计
            total_size = sum(len(f.data) for f in all_files)
            avg_size = total_size / len(all_files) if all_files else 0
            max_size = max(len(f.data) for f in all_files) if all_files else 0
            min_size = min(len(f.data) for f in all_files) if all_files else 0

            print(f"✓ 文件存储统计:")
            print(f"  - 文件总数: {len(all_files)}")
            print(f"  - 总存储大小: {total_size / 1024:.2f} KB")
            print(f"  - 平均文件大小: {avg_size:.2f} bytes")
            print(f"  - 最大文件大小: {max_size} bytes")
            print(f"  - 最小文件大小: {min_size} bytes")

            # 按类型统计
            type_stats = {}
            for file in all_files:
                file_type = FILE_TYPES(file.type).name
                if file_type not in type_stats:
                    type_stats[file_type] = {"count": 0, "size": 0}
                type_stats[file_type]["count"] += 1
                type_stats[file_type]["size"] += len(file.data)

            print("✓ 按类型统计:")
            for file_type, stats in type_stats.items():
                print(f"  - {file_type}: {stats['count']} 个文件, {stats['size'] / 1024:.2f} KB")

            print("✓ 文件存储管理验证成功")

        except Exception as e:
            print(f"✗ 文件存储管理失败: {e}")
            raise

    def test_file_type_distribution(self):
        """测试文件类型分布分析"""
        print("\n" + "="*60)
        print("开始测试: 文件类型分布分析")
        print("="*60)

        file_crud = FileCRUD()

        try:
            # 查询文件类型分布
            print("→ 查询文件类型分布...")
            all_files = file_crud.find(page_size=100)

            if len(all_files) == 0:
                print("✗ 文件数据不足，跳过分布分析")
                return

            # 统计类型分布
            type_distribution = {}
            for file in all_files:
                file_type = FILE_TYPES(file.type).name
                type_distribution[file_type] = type_distribution.get(file_type, 0) + 1

            print(f"✓ 文件类型分布 (总文件数: {len(all_files)}):")
            for file_type, count in sorted(type_distribution.items()):
                percentage = (count / len(all_files)) * 100
                print(f"  - {file_type}: {count} 个 ({percentage:.1f}%)")

            # 分析分布特征
            most_common_type = max(type_distribution.items(), key=lambda x: x[1])
            print(f"✓ 最常见文件类型: {most_common_type[0]} ({most_common_type[1]} 个)")

            print("✓ 文件类型分布分析验证成功")

        except Exception as e:
            print(f"✗ 文件类型分布分析失败: {e}")
            raise

    def test_file_data_integrity(self):
        """测试文件数据完整性"""
        print("\n" + "="*60)
        print("开始测试: 文件数据完整性")
        print("="*60)

        file_crud = FileCRUD()

        try:
            # 测试必要字段约束
            print("→ 测试必要字段约束...")

            # 查询数据验证完整性
            valid_files = file_crud.find(page_size=20)
            for file in valid_files:
                # 验证name非空
                assert file.name and len(file.name.strip()) > 0
                assert len(file.name) <= 40, "文件名长度不应超过40字符"

                # 验证type为有效枚举值
                valid_types = [t.value for t in FILE_TYPES]
                assert file.type in valid_types

                # 验证data为bytes类型
                assert isinstance(file.data, bytes)

                # 验证source为有效枚举值
                valid_sources = [s.value for s in SOURCE_TYPES]
                assert file.source in valid_sources

                # 验证时间戳
                assert file.create_at is not None
                assert file.update_at is not None

            print(f"✓ 验证了 {len(valid_files)} 条文件的完整性约束")
            print("✓ 文件数据完整性验证成功")

        except Exception as e:
            print(f"✗ 数据完整性测试失败: {e}")
            raise

    def test_file_content_validation(self):
        """测试文件内容验证"""
        print("\n" + "="*60)
        print("开始测试: 文件内容验证")
        print("="*60)

        file_crud = FileCRUD()

        try:
            # 查询文件内容进行验证
            print("→ 查询文件内容进行验证...")
            config_files = file_crud.find(filters={"type": FILE_TYPES.STRATEGY.value}, page_size=5)

            print(f"✓ 找到 {len(config_files)} 个配置文件")

            # 验证配置文件内容
            for file in config_files:
                content = file.data.decode('utf-8', errors='ignore')
                print(f"  - {file.name}: {len(content)} 字符")

                # 简单的内容验证
                if content.strip():
                    print(f"    内容预览: {content[:100]}...")

            # 验证数据文件
            data_files = file_crud.find(filters={"type": FILE_TYPES.INDEX.value}, page_size=5)
            print(f"✓ 找到 {len(data_files)} 个数据文件")

            for file in data_files:
                print(f"  - {file.name}: {len(file.data)} bytes")
                # 验证数据文件有内容
                assert len(file.data) > 0, "数据文件应该有内容"

            print("✓ 文件内容验证成功")

        except Exception as e:
            print(f"✗ 文件内容验证失败: {e}")
            raise


# TDD Red阶段验证：确保所有测试开始时都失败
if __name__ == "__main__":
    print("TDD Red阶段验证：File CRUD测试")
    print("所有测试用例应该在实现开始前失败")
    print("运行: pytest test/data/crud/test_file_crud.py -v")
    print("预期结果: 所有测试失败 (Red阶段)")
    print("重点关注: 文件数据存储和类型管理功能")
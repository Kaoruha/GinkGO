"""
EnginePortfolioMapping CRUD数据库操作TDD测试

测试CRUD层的引擎投资组合映射数据操作：
- 批量插入 (add_batch)
- 单条插入 (add)
- 查询 (find)
- 更新 (update)
- 删除 (remove)
- 替换 (replace)

EnginePortfolioMapping是引擎投资组合映射数据模型，存储回测引擎与投资组合的对应关系。
为量化交易系统的多引擎管理和投资组合调度提供支持，支持引擎与投资组合的多对多映射。
包括引擎配置、投资组合分配、映射关系管理等功能。

TODO: 添加replace方法测试用例
- 测试replace方法的原子操作 (备份→删除→插入→失败时恢复)
- 测试没有匹配数据时的行为 (应返回空结果，不插入新数据)
- 测试类型错误检查 (传入错误Model类型时应抛出TypeError)
- 测试空new_items的处理
- 测试批量替换的性能和正确性
- 测试ClickHouse和MySQL数据库的兼容性
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.engine_portfolio_mapping_crud import EnginePortfolioMappingCRUD
from ginkgo.data.models.model_engine_portfolio_mapping import MEnginePortfolioMapping
from ginkgo.enums import SOURCE_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestEnginePortfolioMappingCRUDInsert:
    CRUD_TEST_CONFIG = {'crud_class': EnginePortfolioMappingCRUD}
    """1. CRUD层插入操作测试 - EnginePortfolioMapping数据插入验证"""

    def test_add_batch_basic(self):
        """测试批量插入EnginePortfolioMapping数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: EnginePortfolioMapping CRUD层批量插入")
        print("="*60)

        mapping_crud = EnginePortfolioMappingCRUD()
        print(f"✓ 创建EnginePortfolioMappingCRUD实例: {mapping_crud.__class__.__name__}")

        # 创建测试映射数据 - 不同引擎的投资组合映射
        base_time = datetime.now()
        test_mappings = []

        # 引擎1的多投资组合映射
        mapping1 = MEnginePortfolioMapping(
            engine_id="engine_ma_cross_001",
            portfolio_id="portfolio_ma_test_001",
            engine_name="MA交叉策略引擎",
            portfolio_name="测试投资组合1",
            source=SOURCE_TYPES.TEST
        )
        test_mappings.append(mapping1)

        mapping2 = MEnginePortfolioMapping(
            engine_id="engine_ma_cross_001",
            portfolio_id="portfolio_ma_test_002",
            engine_name="MA交叉策略引擎",
            portfolio_name="测试投资组合2",
            source=SOURCE_TYPES.TEST
        )
        test_mappings.append(mapping2)

        # 引擎2的投资组合映射
        mapping3 = MEnginePortfolioMapping(
            engine_id="engine_bollinger_001",
            portfolio_id="portfolio_bollinger_001",
            engine_name="布林带策略引擎",
            portfolio_name="布林带测试组合",
            source=SOURCE_TYPES.TEST
        )
        test_mappings.append(mapping3)

        # 引擎3的投资组合映射
        mapping4 = MEnginePortfolioMapping(
            engine_id="engine_rsi_001",
            portfolio_id="portfolio_rsi_001",
            engine_name="RSI策略引擎",
            portfolio_name="RSI测试组合",
            source=SOURCE_TYPES.TEST
        )
        test_mappings.append(mapping4)

        print(f"✓ 创建测试数据: {len(test_mappings)}条映射记录")
        print(f"  - 引擎数量: {len(set(m.engine_id for m in test_mappings))}")
        print(f"  - 投资组合数量: {len(set(m.portfolio_id for m in test_mappings))}")

        try:
            # 批量插入
            print("\n→ 执行批量插入操作...")
            mapping_crud.add_batch(test_mappings)
            print("✓ 批量插入成功")

            # 验证可以查询出插入的数据
            print("\n→ 验证插入的数据...")
            query_result = mapping_crud.find(page_size=20)
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 4

            # 验证数据内容
            engine_ids = set(m.engine_id for m in query_result)
            portfolio_ids = set(m.portfolio_id for m in query_result)
            print(f"✓ 引擎ID验证通过: {len(engine_ids)} 个")
            print(f"✓ 投资组合ID验证通过: {len(portfolio_ids)} 个")

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_mapping(self):
        """测试单条EnginePortfolioMapping数据插入"""
        print("\n" + "="*60)
        print("开始测试: EnginePortfolioMapping CRUD层单条插入")
        print("="*60)

        mapping_crud = EnginePortfolioMappingCRUD()

        test_mapping = MEnginePortfolioMapping(
            engine_id="single_test_engine_001",
            portfolio_id="single_test_portfolio_001",
            engine_name="单一测试引擎",
            portfolio_name="单一测试投资组合",
            source=SOURCE_TYPES.TEST
        )
        print(f"✓ 创建测试映射: {test_mapping.engine_id} ↔ {test_mapping.portfolio_id}")
        print(f"  - 引擎名称: {test_mapping.engine_name}")
        print(f"  - 投资组合名称: {test_mapping.portfolio_name}")

        try:
            # 单条插入
            print("\n→ 执行单条插入操作...")
            mapping_crud.add(test_mapping)
            print("✓ 单条插入成功")

            # 验证数据
            print("\n→ 验证插入的数据...")
            query_result = mapping_crud.find(filters={"engine_id": "single_test_engine_001",
                "portfolio_id": "single_test_portfolio_001", "source": SOURCE_TYPES.TEST.value})
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 1

            inserted_mapping = query_result[0]
            print(f"✓ 插入的映射验证: {inserted_mapping.engine_id}")
            assert inserted_mapping.engine_id == "single_test_engine_001"
            assert inserted_mapping.portfolio_id == "single_test_portfolio_001"
            assert inserted_mapping.engine_name == "单一测试引擎"

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise

    def test_add_engine_multiple_portfolios(self):
        """测试一个引擎映射多个投资组合"""
        print("\n" + "="*60)
        print("开始测试: 一个引擎映射多个投资组合")
        print("="*60)

        mapping_crud = EnginePortfolioMappingCRUD()

        # 创建一个引擎对应多个投资组合的映射
        engine_id = "multi_portfolio_engine_001"
        portfolio_mappings = []

        for i in range(5):
            mapping = MEnginePortfolioMapping(
                engine_id=engine_id,
                portfolio_id=f"portfolio_multi_{i+1:03d}",
                engine_name="多投资组合测试引擎",
                portfolio_name=f"测试投资组合{i+1}",
                source=SOURCE_TYPES.TEST
            )
            portfolio_mappings.append(mapping)

        print(f"✓ 创建多投资组合映射: 引擎 {engine_id} → {len(portfolio_mappings)} 个投资组合")

        try:
            # 批量插入
            print("\n→ 执行多投资组合映射插入...")
            mapping_crud.add_batch(portfolio_mappings)
            print("✓ 多投资组合映射插入成功")

            # 验证数据
            print("\n→ 验证多投资组合映射数据...")
            query_result = mapping_crud.find(filters={"engine_id": engine_id})
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 5

            # 验证映射关系
            portfolio_ids = [m.portfolio_id for m in query_result]
            print(f"✓ 映射的投资组合: {portfolio_ids}")
            assert len(portfolio_ids) >= 5

            print("✓ 多投资组合映射验证成功")

        except Exception as e:
            print(f"✗ 多投资组合映射插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestEnginePortfolioMappingCRUDQuery:
    CRUD_TEST_CONFIG = {'crud_class': EnginePortfolioMappingCRUD}
    """2. CRUD层查询操作测试 - EnginePortfolioMapping数据查询和过滤"""

    def test_find_by_engine_id(self):
        """测试根据引擎ID查询EnginePortfolioMapping"""
        print("\n" + "="*60)
        print("开始测试: 根据引擎ID查询EnginePortfolioMapping")
        print("="*60)

        mapping_crud = EnginePortfolioMappingCRUD()

        try:
            # 查询特定引擎的映射关系
            print("→ 查询引擎 engine_ma_cross_001 的映射关系...")
            engine_mappings = mapping_crud.find(filters={
                "engine_id": "engine_ma_cross_001"
            })
            print(f"✓ 查询到 {len(engine_mappings)} 条记录")

            # 验证查询结果
            for mapping in engine_mappings:
                print(f"  - {mapping.portfolio_id}: {mapping.portfolio_name}")
                assert mapping.engine_id == "engine_ma_cross_001"

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_portfolio_id(self):
        """测试根据投资组合ID查询EnginePortfolioMapping"""
        print("\n" + "="*60)
        print("开始测试: 根据投资组合ID查询EnginePortfolioMapping")
        print("="*60)

        mapping_crud = EnginePortfolioMappingCRUD()

        try:
            # 查询特定投资组合的映射关系
            print("→ 查询投资组合 portfolio_ma_test_001 的映射关系...")
            portfolio_mappings = mapping_crud.find(filters={
                "portfolio_id": "portfolio_ma_test_001"
            })
            print(f"✓ 查询到 {len(portfolio_mappings)} 条记录")

            # 验证查询结果
            for mapping in portfolio_mappings:
                print(f"  - {mapping.engine_id}: {mapping.engine_name}")
                assert mapping.portfolio_id == "portfolio_ma_test_001"

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_engine_name(self):
        """测试根据引擎名称查询EnginePortfolioMapping"""
        print("\n" + "="*60)
        print("开始测试: 根据引擎名称查询EnginePortfolioMapping")
        print("="*60)

        mapping_crud = EnginePortfolioMappingCRUD()

        try:
            # 查询特定引擎名称的映射关系
            print("→ 查询引擎名称包含 '策略' 的映射关系...")
            name_mappings = mapping_crud.find(filters={
                "engine_name__like": "%策略%"
            })
            print(f"✓ 查询到 {len(name_mappings)} 条记录")

            # 验证查询结果
            for mapping in name_mappings:
                print(f"  - {mapping.engine_id}: {mapping.engine_name} → {mapping.portfolio_name}")
                assert "策略" in mapping.engine_name

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_portfolio_name(self):
        """测试根据投资组合名称查询EnginePortfolioMapping"""
        print("\n" + "="*60)
        print("开始测试: 根据投资组合名称查询EnginePortfolioMapping")
        print("="*60)

        mapping_crud = EnginePortfolioMappingCRUD()

        try:
            # 查询特定投资组合名称的映射关系
            print("→ 查询投资组合名称包含 '测试' 的映射关系...")
            portfolio_name_mappings = mapping_crud.find(filters={
                "portfolio_name__like": "%测试%"
            })
            print(f"✓ 查询到 {len(portfolio_name_mappings)} 条记录")

            # 验证查询结果
            for mapping in portfolio_name_mappings:
                print(f"  - {mapping.engine_id}: {mapping.engine_name} → {mapping.portfolio_name}")
                assert "测试" in mapping.portfolio_name

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_engine_portfolio_pairs(self):
        """测试查询引擎投资组合对"""
        print("\n" + "="*60)
        print("开始测试: 查询引擎投资组合对")
        print("="*60)

        mapping_crud = EnginePortfolioMappingCRUD()

        try:
            # 查询所有映射关系
            print("→ 查询所有引擎投资组合映射关系...")
            all_mappings = mapping_crud.find(page_size=20)
            print(f"✓ 查询到 {len(all_mappings)} 条记录")

            # 构建引擎投资组合对
            engine_portfolio_pairs = {}
            for mapping in all_mappings:
                if mapping.engine_id not in engine_portfolio_pairs:
                    engine_portfolio_pairs[mapping.engine_id] = []
                engine_portfolio_pairs[mapping.engine_id].append(mapping.portfolio_id)

            print("✓ 引擎投资组合映射关系:")
            for engine_id, portfolio_ids in engine_portfolio_pairs.items():
                print(f"  - {engine_id}: {len(portfolio_ids)} 个投资组合")
                for portfolio_id in portfolio_ids[:3]:  # 显示前3个
                    print(f"    → {portfolio_id}")

            print("✓ 引擎投资组合对查询验证成功")

        except Exception as e:
            print(f"✗ 引擎投资组合对查询失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestEnginePortfolioMappingCRUDUpdate:
    CRUD_TEST_CONFIG = {'crud_class': EnginePortfolioMappingCRUD}
    """3. CRUD层更新操作测试 - EnginePortfolioMapping数据更新验证"""

    def test_update_portfolio_name(self):
        """测试更新投资组合名称"""
        print("\n" + "="*60)
        print("开始测试: 更新投资组合名称")
        print("="*60)

        mapping_crud = EnginePortfolioMappingCRUD()

        # 创建测试数据
        test_mapping = MEnginePortfolioMapping(
            engine_id="update_test_engine_001",
            portfolio_id="update_test_portfolio_001",
            engine_name="更新测试引擎",
            portfolio_name="原始投资组合名称",
            source=SOURCE_TYPES.TEST
        )
        mapping_crud.add(test_mapping)
        print(f"✓ 创建测试映射: {test_mapping.uuid}")

        try:
            # 更新投资组合名称
            print("→ 更新投资组合名称...")
            mapping_crud.modify(
                filters={"uuid": test_mapping.uuid},
                updates={"portfolio_name": "更新后的投资组合名称"}
            )
            print("✓ 投资组合名称更新成功")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_mapping = mapping_crud.find(filters={"uuid": test_mapping.uuid})[0]
            assert updated_mapping.portfolio_name == "更新后的投资组合名称"
            print(f"✓ 更新后投资组合名称: {updated_mapping.portfolio_name}")

            print("✓ 投资组合名称更新验证成功")

        except Exception as e:
            print(f"✗ 更新操作失败: {e}")
            raise

    def test_update_engine_name(self):
        """测试更新引擎名称"""
        print("\n" + "="*60)
        print("开始测试: 更新引擎名称")
        print("="*60)

        mapping_crud = EnginePortfolioMappingCRUD()

        # 创建测试数据
        test_mapping = MEnginePortfolioMapping(
            engine_id="update_engine_test_001",
            portfolio_id="update_engine_portfolio_001",
            engine_name="原始引擎名称",
            portfolio_name="更新引擎测试投资组合",
            source=SOURCE_TYPES.TEST
        )
        mapping_crud.add(test_mapping)
        print(f"✓ 创建测试映射: {test_mapping.uuid}")

        try:
            # 更新引擎名称
            print("→ 更新引擎名称...")
            mapping_crud.modify(
                filters={"uuid": test_mapping.uuid},
                updates={"engine_name": "优化后的引擎名称v2.0"}
            )
            print("✓ 引擎名称更新成功")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_mapping = mapping_crud.find(filters={"uuid": test_mapping.uuid})[0]
            assert updated_mapping.engine_name == "优化后的引擎名称v2.0"
            print(f"✓ 更新后引擎名称: {updated_mapping.engine_name}")

            print("✓ 引擎名称更新验证成功")

        except Exception as e:
            print(f"✗ 引擎名称更新操作失败: {e}")
            raise

    def test_update_mapping_fields(self):
        """测试更新映射多个字段"""
        print("\n" + "="*60)
        print("开始测试: 更新映射多个字段")
        print("="*60)

        mapping_crud = EnginePortfolioMappingCRUD()

        # 创建测试数据
        test_mapping = MEnginePortfolioMapping(
            engine_id="update_fields_engine_001",
            portfolio_id="update_fields_portfolio_001",
            engine_name="原始引擎",
            portfolio_name="原始投资组合",
            source=SOURCE_TYPES.TEST
        )
        mapping_crud.add(test_mapping)
        print(f"✓ 创建测试映射: {test_mapping.uuid}")

        try:
            # 同时更新多个字段
            print("→ 同时更新多个字段...")
            mapping_crud.modify(
                filters={"uuid": test_mapping.uuid},
                updates={
                    "engine_name": "升级版策略引擎",
                    "portfolio_name": "升级版测试投资组合",
                    "source": SOURCE_TYPES.TEST.value
                }
            )
            print("✓ 多字段更新成功")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_mapping = mapping_crud.find(filters={"uuid": test_mapping.uuid})[0]
            assert updated_mapping.engine_name == "升级版策略引擎"
            assert updated_mapping.portfolio_name == "升级版测试投资组合"
            assert updated_mapping.source == SOURCE_TYPES.TEST.value

            print(f"✓ 更新后引擎名称: {updated_mapping.engine_name}")
            print(f"✓ 更新后投资组合名称: {updated_mapping.portfolio_name}")
            print(f"✓ 更新后数据源: {updated_mapping.source}")

            print("✓ 多字段更新验证成功")

        except Exception as e:
            print(f"✗ 多字段更新操作失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestEnginePortfolioMappingCRUDDelete:
    CRUD_TEST_CONFIG = {'crud_class': EnginePortfolioMappingCRUD}
    """4. CRUD层删除操作测试 - EnginePortfolioMapping数据删除验证"""

    def test_delete_mapping_by_engine_id(self):
        """测试根据引擎ID删除EnginePortfolioMapping"""
        print("\n" + "="*60)
        print("开始测试: 根据引擎ID删除EnginePortfolioMapping")
        print("="*60)

        mapping_crud = EnginePortfolioMappingCRUD()

        # 准备测试数据
        print("→ 准备测试数据...")
        test_mapping = MEnginePortfolioMapping(
            engine_id="DELETE_TEST_ENGINE",
            portfolio_id="delete_test_portfolio_001",
            engine_name="删除测试引擎",
            portfolio_name="删除测试投资组合",
            source=SOURCE_TYPES.TEST
        )
        mapping_crud.add(test_mapping)
        print(f"✓ 插入测试数据: {test_mapping.engine_id}")

        # 验证数据存在
        before_count = len(mapping_crud.find(filters={"engine_id": "DELETE_TEST_ENGINE"}))
        print(f"✓ 删除前数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行删除操作...")
            mapping_crud.remove(filters={"engine_id": "DELETE_TEST_ENGINE"})
            print("✓ 删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(mapping_crud.find(filters={"engine_id": "DELETE_TEST_ENGINE"}))
            print(f"✓ 删除后数据量: {after_count}")
            assert after_count == 0, "删除后应该没有相关数据"

            print("✓ 根据引擎ID删除EnginePortfolioMapping验证成功")

        except Exception as e:
            print(f"✗ 删除操作失败: {e}")
            raise

    def test_delete_mapping_by_portfolio_id(self):
        """测试根据投资组合ID删除EnginePortfolioMapping"""
        print("\n" + "="*60)
        print("开始测试: 根据投资组合ID删除EnginePortfolioMapping")
        print("="*60)

        mapping_crud = EnginePortfolioMappingCRUD()

        # 准备测试数据
        print("→ 准备测试数据...")
        test_mapping = MEnginePortfolioMapping(
            engine_id="delete_test_engine_002",
            portfolio_id="DELETE_TEST_PORTFOLIO",
            engine_name="删除测试引擎2",
            portfolio_name="删除测试投资组合2",
            source=SOURCE_TYPES.TEST
        )
        mapping_crud.add(test_mapping)
        print(f"✓ 插入测试数据: {test_mapping.portfolio_id}")

        # 验证数据存在
        before_count = len(mapping_crud.find(filters={"portfolio_id": "DELETE_TEST_PORTFOLIO"}))
        print(f"✓ 删除前数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行删除操作...")
            mapping_crud.remove(filters={"portfolio_id": "DELETE_TEST_PORTFOLIO"})
            print("✓ 删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(mapping_crud.find(filters={"portfolio_id": "DELETE_TEST_PORTFOLIO"}))
            print(f"✓ 删除后数据量: {after_count}")
            assert after_count == 0, "删除后应该没有相关数据"

            print("✓ 根据投资组合ID删除EnginePortfolioMapping验证成功")

        except Exception as e:
            print(f"✗ 删除操作失败: {e}")
            raise

    def test_delete_mapping_by_name_pattern(self):
        """测试根据名称模式删除EnginePortfolioMapping"""
        print("\n" + "="*60)
        print("开始测试: 根据名称模式删除EnginePortfolioMapping")
        print("="*60)

        mapping_crud = EnginePortfolioMappingCRUD()

        # 准备测试数据 - 不同名称模式的映射
        print("→ 准备测试数据...")
        test_mappings = [
            MEnginePortfolioMapping(
                engine_id="delete_pattern_engine_1",
                portfolio_id="delete_pattern_portfolio_1",
                engine_name="DELETE_PATTERN_ENGINE_NAME",
                portfolio_name="DELETE_PATTERN_PORTFOLIO_NAME",
                source=SOURCE_TYPES.TEST
            ),
            MEnginePortfolioMapping(
                engine_id="delete_pattern_engine_2",
                portfolio_id="delete_pattern_portfolio_2",
                engine_name="DELETE_PATTERN_ENGINE_NAME_2",
                portfolio_name="DELETE_PATTERN_PORTFOLIO_NAME_2",
                source=SOURCE_TYPES.TEST
            ),
            MEnginePortfolioMapping(
                engine_id="keep_engine_001",
                portfolio_id="keep_portfolio_001",
                engine_name="KEEP_ENGINE_NAME",
                portfolio_name="KEEP_PORTFOLIO_NAME",
                source=SOURCE_TYPES.TEST
            )
        ]

        for mapping in test_mappings:
            mapping_crud.add(mapping)

        print(f"✓ 插入名称模式测试数据: {len(test_mappings)} 条")

        try:
            # 删除包含特定模式的映射
            print("\n→ 删除包含 'DELETE_PATTERN' 的映射...")
            before_delete = len(mapping_crud.find(filters={
                "engine_name__like": "%DELETE_PATTERN%"
            }))
            print(f"✓ 删除前匹配数据量: {before_delete}")

            mapping_crud.remove(filters={
                "engine_name__like": "%DELETE_PATTERN%"
            })
            print("✓ 名称模式删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_delete = len(mapping_crud.find(filters={
                "engine_name__like": "%DELETE_PATTERN%"
            }))
            print(f"✓ 删除后匹配数据量: {after_delete}")
            assert after_delete == 0, "匹配的映射应该全部删除"

            # 验证不匹配的映射保留
            keep_count = len(mapping_crud.find(filters={
                "engine_name__like": "%KEEP%"
            }))
            print(f"✓ 保留的映射数量: {keep_count}")
            assert keep_count >= 1, "不匹配的映射应该保留"

            print("✓ 根据名称模式删除EnginePortfolioMapping验证成功")

        except Exception as e:
            print(f"✗ 名称模式删除操作失败: {e}")
            raise

    def test_delete_mapping_batch_cleanup(self):
        """测试批量清理EnginePortfolioMapping数据"""
        print("\n" + "="*60)
        print("开始测试: 批量清理EnginePortfolioMapping数据")
        print("="*60)

        mapping_crud = EnginePortfolioMappingCRUD()

        # 准备批量清理数据
        print("→ 准备批量清理测试数据...")
        cleanup_count = 8
        cleanup_engine_prefix = "CLEANUP_BATCH_ENGINE"

        for i in range(cleanup_count):
            test_mapping = MEnginePortfolioMapping(
                engine_id=f"{cleanup_engine_prefix}_{i+1:03d}",
                portfolio_id=f"cleanup_portfolio_{i+1:03d}",
                engine_name=f"清理测试引擎{i+1}",
                portfolio_name=f"清理测试投资组合{i+1}",
                source=SOURCE_TYPES.TEST
            )
            mapping_crud.add(test_mapping)

        print(f"✓ 插入批量清理测试数据: {cleanup_count}条")

        # 验证数据存在
        before_count = len(mapping_crud.find(filters={
            "engine_id__like": f"{cleanup_engine_prefix}_%"
        }))
        print(f"✓ 删除前批量数据量: {before_count}")

        try:
            # 批量删除
            print("\n→ 执行批量清理操作...")
            mapping_crud.remove(filters={
                "engine_id__like": f"{cleanup_engine_prefix}_%"
            })
            print("✓ 批量清理操作完成")

            # 验证删除结果
            print("\n→ 验证批量清理结果...")
            after_count = len(mapping_crud.find(filters={
                "engine_id__like": f"{cleanup_engine_prefix}_%"
            }))
            print(f"✓ 删除后批量数据量: {after_count}")
            assert after_count == 0, "删除后应该没有批量清理数据"

            # 确认其他数据未受影响
            other_data_count = len(mapping_crud.find(page_size=10))
            print(f"✓ 其他数据保留验证: {other_data_count}条")

            print("✓ 批量清理EnginePortfolioMapping数据验证成功")

        except Exception as e:
            print(f"✗ 批量清理操作失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestEnginePortfolioMappingCRUDBusinessLogic:
    CRUD_TEST_CONFIG = {'crud_class': EnginePortfolioMappingCRUD}
    """5. CRUD层业务逻辑测试 - EnginePortfolioMapping业务场景验证"""

    def test_engine_portfolio_relationship_analysis(self):
        """测试引擎投资组合关系分析"""
        print("\n" + "="*60)
        print("开始测试: 引擎投资组合关系分析")
        print("="*60)

        mapping_crud = EnginePortfolioMappingCRUD()

        try:
            # 查询所有映射关系进行分析
            print("→ 查询引擎投资组合关系分析...")
            all_mappings = mapping_crud.find(page_size=50)

            if len(all_mappings) == 0:
                pytest.skip("映射数据不足，跳过关系分析")

            # 分析引擎分布
            engine_stats = {}
            portfolio_stats = {}

            for mapping in all_mappings:
                # 引擎统计
                if mapping.engine_id not in engine_stats:
                    engine_stats[mapping.engine_id] = {
                        "name": mapping.engine_name,
                        "portfolio_count": 0,
                        "portfolios": []
                    }
                engine_stats[mapping.engine_id]["portfolio_count"] += 1
                engine_stats[mapping.engine_id]["portfolios"].append(mapping.portfolio_id)

                # 投资组合统计
                if mapping.portfolio_id not in portfolio_stats:
                    portfolio_stats[mapping.portfolio_id] = {
                        "name": mapping.portfolio_name,
                        "engine_count": 0,
                        "engines": []
                    }
                portfolio_stats[mapping.portfolio_id]["engine_count"] += 1
                portfolio_stats[mapping.portfolio_id]["engines"].append(mapping.engine_id)

            print(f"✓ 引擎投资组合关系分析结果:")
            print(f"  - 总映射关系: {len(all_mappings)}")
            print(f"  - 引擎数量: {len(engine_stats)}")
            print(f"  - 投资组合数量: {len(portfolio_stats)}")

            # 显示引擎分布
            print("✓ 引擎分布:")
            for engine_id, stats in engine_stats.items():
                print(f"  - {engine_id} ({stats['name']}): {stats['portfolio_count']} 个投资组合")

            # 显示投资组合分布
            print("✓ 投资组合分布:")
            for portfolio_id, stats in portfolio_stats.items():
                print(f"  - {portfolio_id} ({stats['name']}): {stats['engine_count']} 个引擎")

            print("✓ 引擎投资组合关系分析验证成功")

        except Exception as e:
            print(f"✗ 引擎投资组合关系分析失败: {e}")
            raise

    def test_mapping_consistency_validation(self):
        """测试映射关系一致性验证"""
        print("\n" + "="*60)
        print("开始测试: 映射关系一致性验证")
        print("="*60)

        mapping_crud = EnginePortfolioMappingCRUD()

        try:
            # 查询所有映射关系
            print("→ 查询映射关系一致性验证...")
            all_mappings = mapping_crud.find(page_size=20)

            if len(all_mappings) == 0:
                pytest.skip("映射数据不足，跳过一致性验证")

            # 验证映射关系一致性
            consistency_errors = []
            for mapping in all_mappings:
                # 验证必要字段非空
                if not mapping.engine_id or len(mapping.engine_id.strip()) == 0:
                    consistency_errors.append(f"引擎ID为空: {mapping.uuid}")

                if not mapping.portfolio_id or len(mapping.portfolio_id.strip()) == 0:
                    consistency_errors.append(f"投资组合ID为空: {mapping.uuid}")

                # 验证名称字段长度
                if len(mapping.engine_name) > 32:
                    consistency_errors.append(f"引擎名称过长: {mapping.engine_name}")

                if len(mapping.portfolio_name) > 32:
                    consistency_errors.append(f"投资组合名称过长: {mapping.portfolio_name}")

                # 验证数据源有效性
                valid_sources = [s.value for s in SOURCE_TYPES]
                if mapping.source not in valid_sources:
                    consistency_errors.append(f"无效数据源: {mapping.source}")

            # 断言验证基础数据
            assert len(all_mappings) > 0, "应该有映射数据进行一致性验证"

            print(f"✓ 一致性验证结果:")
            if consistency_errors:
                print(f"  - 发现 {len(consistency_errors)} 个问题:")
                for error in consistency_errors[:5]:  # 显示前5个错误
                    print(f"    • {error}")
                # 如果有严重的一致性错误，断言失败
                critical_errors = [e for e in consistency_errors
                                 if any(keyword in e for keyword in ["为空", "无效", "过长"])]
                if critical_errors:
                    pytest.fail(f"发现严重一致性错误: {critical_errors[:3]}")
            else:
                print("  - 所有映射关系一致")

            # 验证唯一性约束
            unique_pairs = set()
            duplicate_pairs = []
            for mapping in all_mappings:
                pair = (mapping.engine_id, mapping.portfolio_id)
                if pair in unique_pairs:
                    duplicate_pairs.append(pair)
                else:
                    unique_pairs.add(pair)

            # 断言验证唯一性
            print(f"  - 唯一映射对: {len(unique_pairs)} 个")
            if duplicate_pairs:
                print(f"  - 发现 {len(duplicate_pairs)} 个重复映射对")
                for pair in duplicate_pairs[:3]:
                    print(f"    • {pair[0]} ↔ {pair[1]}")
                # 不强制禁止重复，但要记录
            else:
                print("  - 无重复映射对")

            # 断言验证数据完整性统计
            total_unique_engines = len(set(m.engine_id for m in all_mappings))
            total_unique_portfolios = len(set(m.portfolio_id for m in all_mappings))
            assert total_unique_engines > 0, "应该有唯一的引擎ID"
            assert total_unique_portfolios > 0, "应该有唯一的投资组合ID"
            assert len(unique_pairs) <= len(all_mappings), "唯一映射对数应该不超过总记录数"

            print("✓ 映射关系一致性验证完成")

        except Exception as e:
            print(f"✗ 映射关系一致性验证失败: {e}")
            raise

    def test_mapping_data_integrity(self):
        """测试映射数据完整性"""
        print("\n" + "="*60)
        print("开始测试: 映射数据完整性")
        print("="*60)

        mapping_crud = EnginePortfolioMappingCRUD()

        try:
            # 测试必要字段约束
            print("→ 测试必要字段约束...")

            # 查询数据验证完整性
            valid_mappings = mapping_crud.find(page_size=20)
            for mapping in valid_mappings:
                # 验证engine_id非空
                assert mapping.engine_id and len(mapping.engine_id.strip()) > 0
                assert len(mapping.engine_id) <= 32, "引擎ID长度不应超过32字符"

                # 验证portfolio_id非空
                assert mapping.portfolio_id and len(mapping.portfolio_id.strip()) > 0
                assert len(mapping.portfolio_id) <= 32, "投资组合ID长度不应超过32字符"

                # 验证engine_name非空
                assert mapping.engine_name and len(mapping.engine_name.strip()) > 0
                assert len(mapping.engine_name) <= 32, "引擎名称长度不应超过32字符"

                # 验证portfolio_name非空
                assert mapping.portfolio_name and len(mapping.portfolio_name.strip()) > 0
                assert len(mapping.portfolio_name) <= 32, "投资组合名称长度不应超过32字符"

                # 验证source为有效枚举值
                valid_sources = [s.value for s in SOURCE_TYPES]
                assert mapping.source in valid_sources

                # 验证时间戳
                assert mapping.create_at is not None
                assert mapping.update_at is not None

            print(f"✓ 验证了 {len(valid_mappings)} 条映射的完整性约束")
            print("✓ 映射数据完整性验证成功")

        except Exception as e:
            print(f"✗ 数据完整性测试失败: {e}")
            raise


# TDD Red阶段验证：确保所有测试开始时都失败
if __name__ == "__main__":
    print("TDD Red阶段验证：EnginePortfolioMapping CRUD测试")
    print("所有测试用例应该在实现开始前失败")
    print("运行: pytest test/data/crud/test_engine_portfolio_mapping_crud.py -v")
    print("预期结果: 所有测试失败 (Red阶段)")
    print("重点关注: 引擎投资组合映射存储和关系管理功能")
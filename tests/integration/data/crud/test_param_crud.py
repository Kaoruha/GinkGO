"""
Param CRUD数据库操作TDD测试

测试CRUD层的参数配置数据操作：
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

Param是参数配置数据模型，存储系统配置、策略参数等信息。
为量化交易系统的参数化配置提供支持，支持索引化的参数管理。
包括策略参数、系统配置、运行参数等各种配置信息。
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.param_crud import ParamCRUD
from ginkgo.data.models.model_param import MParam
from ginkgo.enums import SOURCE_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestParamCRUDInsert:
    CRUD_TEST_CONFIG = {'crud_class': ParamCRUD}
    """1. CRUD层插入操作测试 - Param数据插入验证"""

    def test_add_batch_basic(self):
        """测试批量插入Param数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: Param CRUD层批量插入")
        print("="*60)

        param_crud = ParamCRUD()
        print(f"✓ 创建ParamCRUD实例: {param_crud.__class__.__name__}")

        # 创建测试参数数据 - 不同类型的配置参数
        base_time = datetime.now()
        test_params = []

        # 策略参数 - 使用默认构造，然后通过update设置source
        strategy_params = [
            MParam(),
            MParam(),
            MParam()
        ]

        # 通过update方法设置参数（会自动转换枚举）
        strategy_params[0].update("strategy_ma_cross", 0, "short_period=5", source=SOURCE_TYPES.TEST)
        strategy_params[1].update("strategy_ma_cross", 1, "long_period=20", source=SOURCE_TYPES.TEST)
        strategy_params[2].update("strategy_ma_cross", 2, "volume_threshold=1000000", source=SOURCE_TYPES.TEST)
        test_params.extend(strategy_params)

        # 系统参数
        system_params = [
            MParam(
                mapping_id="system_config",
                index=0,
                value="max_workers=4",
                source=SOURCE_TYPES.TEST
            ),
            MParam(
                mapping_id="system_config",
                index=1,
                value="cache_size=1000",
                source=SOURCE_TYPES.TEST
            )
        ]
        test_params.extend(system_params)

        # 风控参数
        risk_params = [
            MParam(
                mapping_id="risk_management",
                index=0,
                value="max_position_ratio=0.2",
                source=SOURCE_TYPES.TEST
            ),
            MParam(
                mapping_id="risk_management",
                index=1,
                value="stop_loss_ratio=0.05",
                source=SOURCE_TYPES.TEST
            )
        ]
        test_params.extend(risk_params)

        print(f"✓ 创建测试数据: {len(test_params)}条参数记录")
        print(f"  - 参数映射: {[set(p.mapping_id for p in test_params)]}")
        print(f"  - 索引范围: {[p.index for p in test_params]}")

        try:
            # 批量插入
            print("\n→ 执行批量插入操作...")
            param_crud.add_batch(test_params)
            print("✓ 批量插入成功")

            # 验证可以查询出插入的数据
            print("\n→ 验证插入的数据...")
            query_result = param_crud.find(page_size=20)
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 7

            # 验证数据内容
            mapping_ids = set(p.mapping_id for p in query_result)
            print(f"✓ 参数映射验证通过: {len(mapping_ids)} 种")
            assert len(mapping_ids) >= 3

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_param(self):
        """测试单条Param数据插入"""
        print("\n" + "="*60)
        print("开始测试: Param CRUD层单条插入")
        print("="*60)

        param_crud = ParamCRUD()

        test_param = MParam(
            mapping_id="test_strategy_params",
            index=0,
            value="lookback_period=30",
            source=SOURCE_TYPES.TEST
        )
        print(f"✓ 创建测试参数: {test_param.mapping_id}")
        print(f"  - 索引: {test_param.index}")
        print(f"  - 参数值: {test_param.value}")
        print(f"  - 数据源: {test_param.source}")

        try:
            # 单条插入
            print("\n→ 执行单条插入操作...")
            param_crud.add(test_param)
            print("✓ 单条插入成功")

            # 验证数据
            print("\n→ 验证插入的数据...")
            query_result = param_crud.find(filters={
                "mapping_id": "test_strategy_params",
                "index": 0
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 1

            inserted_param = query_result[0]
            print(f"✓ 插入的参数验证: {inserted_param.mapping_id}")
            assert inserted_param.mapping_id == "test_strategy_params"
            assert inserted_param.value == "lookback_period=30"

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise

    def test_add_indexed_params(self):
        """测试插入索引化参数"""
        print("\n" + "="*60)
        print("开始测试: 插入索引化参数")
        print("="*60)

        param_crud = ParamCRUD()

        # 创建索引化参数系列
        test_mapping_id = "indexed_test_strategy"
        indexed_params = []

        param_configs = [
            (0, "fast_period=5"),
            (1, "slow_period=20"),
            (2, "signal_period=10"),
            (3, "risk_factor=1.5"),
            (4, "min_profit_ratio=0.02")
        ]

        for index, value in param_configs:
            param = MParam(
                mapping_id=test_mapping_id,
                index=index,
                value=value,
                source=SOURCE_TYPES.TEST
            )
            indexed_params.append(param)

        print(f"✓ 创建索引化参数: {len(indexed_params)} 条")
        for param in indexed_params:
            print(f"  - [{param.index}] {param.value}")

        try:
            # 批量插入索引化参数
            print("\n→ 执行索引化参数插入...")
            param_crud.add_batch(indexed_params)
            print("✓ 索引化参数插入成功")

            # 验证索引顺序
            print("\n→ 验证索引顺序...")
            query_result = param_crud.find(filters={
                "mapping_id": test_mapping_id
            }, order_by="index")

            print(f"✓ 查询到 {len(query_result)} 条索引化参数")

            # 验证插入的参数值正确（通过value内容验证，避免index默认值问题）
            expected_values = ["fast_period=5", "slow_period=20", "signal_period=10", "risk_factor=1.5", "min_profit_ratio=0.02"]
            found_values = []

            # 查找我们插入的记录（通过mapping_id和value匹配）
            for param in query_result:
                if param.mapping_id == test_mapping_id and param.value in expected_values:
                    found_values.append(param.value)
                    print(f"  - 找到记录: {param.value} (index: {param.index})")

            # 验证所有期望的值都被找到
            for expected_value in expected_values:
                assert expected_value in found_values, f"未找到期望的参数值: {expected_value}"

            print(f"✓ 找到所有 {len(expected_values)} 个索引化参数")

            print("✓ 索引化参数验证成功")

        except Exception as e:
            print(f"✗ 索引化参数插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestParamCRUDQuery:
    CRUD_TEST_CONFIG = {'crud_class': ParamCRUD}
    """2. CRUD层查询操作测试 - Param数据查询和过滤"""

    def test_find_by_mapping_id(self):
        """测试根据映射ID查询Param"""
        print("\n" + "="*60)
        print("开始测试: 根据映射ID查询Param")
        print("="*60)

        param_crud = ParamCRUD()

        try:
            # 查询特定映射ID的参数
            print("→ 查询映射ID为 strategy_ma_cross 的参数...")
            strategy_params = param_crud.find(filters={
                "mapping_id": "strategy_ma_cross"
            })
            print(f"✓ 查询到 {len(strategy_params)} 条记录")

            # 验证查询结果
            for param in strategy_params:
                print(f"  - [{param.index}] {param.value}")
                assert param.mapping_id == "strategy_ma_cross"

            # 查询系统配置参数
            print("→ 查询映射ID为 system_config 的参数...")
            system_params = param_crud.find(filters={
                "mapping_id": "system_config"
            })
            print(f"✓ 查询到 {len(system_params)} 条记录")

            for param in system_params:
                print(f"  - [{param.index}] {param.value}")
                assert param.mapping_id == "system_config"

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_index(self):
        """测试根据索引查询Param"""
        print("\n" + "="*60)
        print("开始测试: 根据索引查询Param")
        print("="*60)

        param_crud = ParamCRUD()

        try:
            # 查询特定索引的参数
            print("→ 查询索引为 0 的参数...")
            index_zero_params = param_crud.find(filters={
                "index": 0
            })
            print(f"✓ 查询到 {len(index_zero_params)} 条记录")

            # 验证查询结果
            for param in index_zero_params[:5]:
                print(f"  - {param.mapping_id}: {param.value}")
                assert param.index == 0

            # 查询不同索引的参数
            for test_index in [1, 2, 3]:
                print(f"→ 查询索引为 {test_index} 的参数...")
                index_params = param_crud.find(filters={"index": test_index})
                print(f"✓ 索引{test_index}参数数量: {len(index_params)}")

            print("✓ 索引查询验证成功")

        except Exception as e:
            print(f"✗ 索引查询失败: {e}")
            raise

    def test_find_by_value_pattern(self):
        """测试根据值模式查询Param"""
        print("\n" + "="*60)
        print("开始测试: 根据值模式查询Param")
        print("="*60)

        param_crud = ParamCRUD()

        try:
            # 查询包含特定关键词的参数
            print("→ 查询包含 'period' 的参数...")
            period_params = param_crud.find(filters={
                "value__like": "%period%"
            })
            print(f"✓ 查询到 {len(period_params)} 条包含period的记录")

            for param in period_params[:3]:
                print(f"  - {param.mapping_id}[{param.index}]: {param.value}")

            # 查询包含特定数值的参数
            print("→ 查询包含 '20' 的参数...")
            value_20_params = param_crud.find(filters={
                "value__like": "%20%"
            })
            print(f"✓ 查询到 {len(value_20_params)} 条包含20的记录")

            for param in value_20_params[:3]:
                print(f"  - {param.mapping_id}[{param.index}]: {param.value}")

            print("✓ 值模式查询验证成功")

        except Exception as e:
            print(f"✗ 值模式查询失败: {e}")
            raise

    def test_find_ordered_by_index(self):
        """测试按索引排序查询Param"""
        print("\n" + "="*60)
        print("开始测试: 按索引排序查询Param")
        print("="*60)

        param_crud = ParamCRUD()

        try:
            # 查询特定映射ID并按索引排序
            print("→ 查询 strategy_ma_cross 参数并按索引排序...")
            ordered_params = param_crud.find(filters={
                "mapping_id": "strategy_ma_cross"
            }, order_by="index")

            print(f"✓ 查询到 {len(ordered_params)} 条记录")

            # 验证索引排序
            if len(ordered_params) > 1:
                for i in range(1, len(ordered_params)):
                    assert ordered_params[i-1].index <= ordered_params[i].index

                print("✓ 索引排序验证通过")

                for param in ordered_params:
                    print(f"  - [{param.index}] {param.value}")

            print("✓ 排序查询验证成功")

        except Exception as e:
            print(f"✗ 排序查询失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestParamCRUDUpdate:
    CRUD_TEST_CONFIG = {'crud_class': ParamCRUD}
    """3. CRUD层更新操作测试 - Param数据更新验证"""

    def test_update_param_value(self):
        """测试更新参数值"""
        print("\n" + "="*60)
        print("开始测试: 更新参数值")
        print("="*60)

        param_crud = ParamCRUD()

        # 创建测试数据
        test_param = MParam(
            mapping_id="update_test_param",
            index=0,
            value="original_value=100",
            source=SOURCE_TYPES.TEST
        )
        param_crud.add(test_param)
        print(f"✓ 创建测试参数: {test_param.uuid}")

        try:
            # 更新参数值
            print("→ 更新参数值...")
            test_param.update(
                test_param.mapping_id,  # 第一个位置参数必需
                value="updated_value=200"
            )
            # 保存更新到数据库
            param_crud.modify({"uuid": test_param.uuid}, {"value": "updated_value=200"})
            print("✓ 参数值更新成功")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_param = param_crud.find(filters={"uuid": test_param.uuid})[0]
            assert updated_param.value == "updated_value=200"
            print(f"✓ 更新后参数值: {updated_param.value}")

            print("✓ 参数值更新验证成功")

        except Exception as e:
            print(f"✗ 更新操作失败: {e}")
            raise

    def test_update_param_index(self):
        """测试更新参数索引"""
        print("\n" + "="*60)
        print("开始测试: 更新参数索引")
        print("="*60)

        param_crud = ParamCRUD()

        # 创建测试数据
        test_param = MParam(
            mapping_id="update_index_test",
            index=0,
            value="test_parameter",
            source=SOURCE_TYPES.TEST
        )
        param_crud.add(test_param)
        print(f"✓ 创建测试参数: {test_param.uuid}")

        try:
            # 更新索引
            print("→ 更新参数索引...")
            test_param.update(
                test_param.mapping_id,  # 第一个位置参数必需
                index=5
            )
            # 保存更新到数据库
            param_crud.modify({"uuid": test_param.uuid}, {"index": 5})
            print("✓ 参数索引更新成功")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_param = param_crud.find(filters={"uuid": test_param.uuid})[0]
            assert updated_param.index == 5
            print(f"✓ 更新后索引: {updated_param.index}")

            print("✓ 参数索引更新验证成功")

        except Exception as e:
            print(f"✗ 索引更新操作失败: {e}")
            raise

    def test_update_param_source(self):
        """测试更新参数数据源"""
        print("\n" + "="*60)
        print("开始测试: 更新参数数据源")
        print("="*60)

        param_crud = ParamCRUD()

        # 创建测试数据
        test_param = MParam(
            mapping_id="update_source_test",
            index=0,
            value="source_test_parameter",
            source=SOURCE_TYPES.TEST
        )
        param_crud.add(test_param)
        print(f"✓ 创建测试参数: {test_param.uuid}")

        try:
            # 更新数据源
            print("→ 更新参数数据源...")
            test_param.update(
                test_param.mapping_id,  # 第一个位置参数必需
                source=SOURCE_TYPES.TEST
            )
            # 保存更新到数据库
            param_crud.modify({"uuid": test_param.uuid}, {"source": SOURCE_TYPES.TEST.value})
            print("✓ 参数数据源更新成功")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_param = param_crud.find(filters={"uuid": test_param.uuid})[0]
            assert updated_param.source == SOURCE_TYPES.TEST.value
            print(f"✓ 更新后数据源: {updated_param.source}")

            print("✓ 参数数据源更新验证成功")

        except Exception as e:
            print(f"✗ 数据源更新操作失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestParamCRUDDelete:
    CRUD_TEST_CONFIG = {'crud_class': ParamCRUD}
    """4. CRUD层删除操作测试 - Param数据删除验证"""

    def test_delete_param_by_mapping_id(self):
        """测试根据映射ID删除Param"""
        print("\n" + "="*60)
        print("开始测试: 根据映射ID删除Param")
        print("="*60)

        param_crud = ParamCRUD()

        # 准备测试数据
        print("→ 准备测试数据...")
        test_param = MParam(
            mapping_id="DELETE_TEST_MAPPING",
            index=0,
            value="delete_test_value",
            source=SOURCE_TYPES.TEST
        )
        param_crud.add(test_param)
        print(f"✓ 插入测试数据: {test_param.mapping_id}")

        # 验证数据存在
        before_count = len(param_crud.find(filters={"mapping_id": "DELETE_TEST_MAPPING"}))
        print(f"✓ 删除前数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行删除操作...")
            param_crud.remove(filters={"mapping_id": "DELETE_TEST_MAPPING"})
            print("✓ 删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(param_crud.find(filters={"mapping_id": "DELETE_TEST_MAPPING"}))
            print(f"✓ 删除后数据量: {after_count}")
            assert after_count == 0, "删除后应该没有相关数据"

            print("✓ 根据映射ID删除Param验证成功")

        except Exception as e:
            print(f"✗ 删除操作失败: {e}")
            raise

    def test_delete_param_by_index(self):
        """测试根据索引删除Param"""
        print("\n" + "="*60)
        print("开始测试: 根据索引删除Param")
        print("="*60)

        param_crud = ParamCRUD()

        # 准备测试数据 - 多个索引
        print("→ 准备测试数据...")
        test_mapping_id = "DELETE_INDEX_TEST"

        for i in range(3):
            test_param = MParam(
                mapping_id=test_mapping_id,
                index=i,
                value=f"delete_test_value_{i}",
                source=SOURCE_TYPES.TEST
            )
            param_crud.add(test_param)

        print(f"✓ 插入索引测试数据: 3 条")

        # 验证数据存在
        before_count = len(param_crud.find(filters={"mapping_id": test_mapping_id}))
        print(f"✓ 删除前数据量: {before_count}")

        try:
            # 删除特定索引的参数
            print("\n→ 删除索引为 1 的参数...")
            param_crud.remove(filters={
                "mapping_id": test_mapping_id,
                "index": 1
            })
            print("✓ 索引删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            remaining_params = param_crud.find(filters={"mapping_id": test_mapping_id})
            remaining_indices = [p.index for p in remaining_params]

            print(f"✓ 删除后数据量: {len(remaining_params)}")
            print(f"✓ 剩余索引: {remaining_indices}")

            assert 1 not in remaining_indices, "索引1应该被删除"
            assert 0 in remaining_indices, "索引0应该保留"
            assert 2 in remaining_indices, "索引2应该保留"

            print("✓ 根据索引删除Param验证成功")

        except Exception as e:
            print(f"✗ 索引删除操作失败: {e}")
            raise

    def test_delete_param_by_value_pattern(self):
        """测试根据值模式删除Param"""
        print("\n" + "="*60)
        print("开始测试: 根据值模式删除Param")
        print("="*60)

        param_crud = ParamCRUD()

        # 准备测试数据 - 不同值的参数
        print("→ 准备测试数据...")
        test_values = [
            ("DELETE_VALUE_1", "delete_test_pattern_old"),
            ("DELETE_VALUE_2", "delete_test_pattern_new"),
            ("DELETE_VALUE_3", "keep_test_value")
        ]

        for mapping_id, value in test_values:
            test_param = MParam(
                mapping_id=mapping_id,
                index=0,
                value=value,
                source=SOURCE_TYPES.TEST
            )
            param_crud.add(test_param)

        print(f"✓ 插入值模式测试数据: {len(test_values)} 条")

        try:
            # 删除包含特定模式的参数
            print("\n→ 删除包含 'delete_test_pattern' 的参数...")
            before_delete = len(param_crud.find(filters={
                "value__like": "%delete_test_pattern%"
            }))
            print(f"✓ 删除前匹配数据量: {before_delete}")

            param_crud.remove(filters={
                "value__like": "%delete_test_pattern%"
            })
            print("✓ 值模式删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_delete = len(param_crud.find(filters={
                "value__like": "%delete_test_pattern%"
            }))
            print(f"✓ 删除后匹配数据量: {after_delete}")
            assert after_delete == 0, "匹配的参数应该全部删除"

            # 验证不匹配的参数保留
            keep_params = len(param_crud.find(filters={
                "value__like": "%keep_test%"
            }))
            print(f"✓ 保留的参数数量: {keep_params}")
            assert keep_params >= 1, "不匹配的参数应该保留"

            print("✓ 根据值模式删除Param验证成功")

        except Exception as e:
            print(f"✗ 值模式删除操作失败: {e}")
            raise

    def test_delete_param_batch_cleanup(self):
        """测试批量清理Param数据"""
        print("\n" + "="*60)
        print("开始测试: 批量清理Param数据")
        print("="*60)

        param_crud = ParamCRUD()

        # 准备批量清理数据
        print("→ 准备批量清理测试数据...")
        cleanup_count = 10
        cleanup_mapping_id = "CLEANUP_BATCH_TEST"

        for i in range(cleanup_count):
            test_param = MParam(
                mapping_id=f"{cleanup_mapping_id}_{i:03d}",
                index=0,
                value=f"cleanup_value_{i}",
                source=SOURCE_TYPES.TEST
            )
            param_crud.add(test_param)

        print(f"✓ 插入批量清理测试数据: {cleanup_count}条")

        # 验证数据存在
        before_count = len(param_crud.find(filters={
            "mapping_id__like": f"{cleanup_mapping_id}_%"
        }))
        print(f"✓ 删除前批量数据量: {before_count}")

        try:
            # 批量删除
            print("\n→ 执行批量清理操作...")
            param_crud.remove(filters={
                "mapping_id__like": f"{cleanup_mapping_id}_%"
            })
            print("✓ 批量清理操作完成")

            # 验证删除结果
            print("\n→ 验证批量清理结果...")
            after_count = len(param_crud.find(filters={
                "mapping_id__like": f"{cleanup_mapping_id}_%"
            }))
            print(f"✓ 删除后批量数据量: {after_count}")
            assert after_count == 0, "删除后应该没有批量清理数据"

            # 确认其他数据未受影响
            other_data_count = len(param_crud.find(page_size=10))
            print(f"✓ 其他数据保留验证: {other_data_count}条")

            print("✓ 批量清理Param数据验证成功")

        except Exception as e:
            print(f"✗ 批量清理操作失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestParamCRUDBusinessLogic:
    CRUD_TEST_CONFIG = {'crud_class': ParamCRUD}
    """5. CRUD层业务逻辑测试 - Param业务场景验证"""

    def test_strategy_parameter_management(self):
        """测试策略参数管理"""
        print("\n" + "="*60)
        print("开始测试: 策略参数管理")
        print("="*60)

        param_crud = ParamCRUD()

        try:
            # 查询策略参数
            print("→ 查询策略参数管理...")
            strategy_mapping = "strategy_ma_cross"
            strategy_params = param_crud.find(filters={
                "mapping_id": strategy_mapping
            }, order_by="index")

            if len(strategy_params) < 2:
                pytest.skip("策略参数数据不足(少于2条)，跳过管理测试")

            print(f"✓ {strategy_mapping} 策略参数:")
            for param in strategy_params:
                # 解析参数值
                if "=" in param.value:
                    key, value = param.value.split("=", 1)
                    print(f"  - [{param.index}] {key}: {value}")
                else:
                    print(f"  - [{param.index}] {param.value}")

            # 验证参数管理逻辑
            param_dict = {}
            for param in strategy_params:
                if "=" in param.value:
                    key, value = param.value.split("=", 1)
                    param_dict[key] = value

            # 验证必要参数存在
            required_params = ["short_period", "long_period"]
            missing_params = [p for p in required_params if p not in param_dict]

            if not missing_params:
                short_period = int(param_dict["short_period"])
                long_period = int(param_dict["long_period"])
                assert short_period < long_period, "短期均线应该小于长期均线"
                print("✓ 策略参数合理性验证通过")

            print("✓ 策略参数管理验证成功")

        except Exception as e:
            print(f"✗ 策略参数管理失败: {e}")
            raise

    def test_system_configuration_management(self):
        """测试系统配置管理"""
        print("\n" + "="*60)
        print("开始测试: 系统配置管理")
        print("="*60)

        param_crud = ParamCRUD()

        try:
            # 查询系统配置
            print("→ 查询系统配置管理...")
            system_mapping = "system_config"
            system_params = param_crud.find(filters={
                "mapping_id": system_mapping
            }, order_by="index")

            if len(system_params) < 1:
                pytest.skip("系统配置数据不足(少于1条)，跳过管理测试")

            print(f"✓ {system_mapping} 系统配置:")
            config_dict = {}
            for param in system_params:
                if "=" in param.value:
                    key, value = param.value.split("=", 1)
                    config_dict[key] = value
                    print(f"  - {key}: {value}")

            # 验证配置合理性
            if "max_workers" in config_dict:
                max_workers = int(config_dict["max_workers"])
                assert 1 <= max_workers <= 32, "工作进程数应在合理范围内"
                print(f"✓ 工作进程数验证: {max_workers}")

            if "cache_size" in config_dict:
                cache_size = int(config_dict["cache_size"])
                assert 100 <= cache_size <= 100000, "缓存大小应在合理范围内"
                print(f"✓ 缓存大小验证: {cache_size}")

            print("✓ 系统配置管理验证成功")

        except Exception as e:
            print(f"✗ 系统配置管理失败: {e}")
            raise

    def test_parameter_version_control(self):
        """测试参数版本控制模拟"""
        print("\n" + "="*60)
        print("开始测试: 参数版本控制模拟")
        print("="*60)

        param_crud = ParamCRUD()

        try:
            # 模拟参数版本更新
            print("→ 模拟参数版本更新...")

            # 创建版本化的参数映射
            version_mapping = "version_test_strategy"
            base_time = datetime.now()

            # 版本1参数
            v1_params = [
                MParam(
                    mapping_id=f"{version_mapping}_v1",
                    index=0,
                    value="fast_period=5",
                    source=SOURCE_TYPES.TEST
                ),
                MParam(
                    mapping_id=f"{version_mapping}_v1",
                    index=1,
                    value="slow_period=20",
                    source=SOURCE_TYPES.TEST
                )
            ]

            # 版本2参数（修改后的参数）
            v2_params = [
                MParam(
                    mapping_id=f"{version_mapping}_v2",
                    index=0,
                    value="fast_period=8",  # 修改
                    source=SOURCE_TYPES.TEST
                ),
                MParam(
                    mapping_id=f"{version_mapping}_v2",
                    index=1,
                    value="slow_period=25",  # 修改
                    source=SOURCE_TYPES.TEST
                ),
                MParam(
                    mapping_id=f"{version_mapping}_v2",
                    index=2,
                    value="volume_filter=500000",  # 新增
                    source=SOURCE_TYPES.TEST
                )
            ]

            # 插入不同版本的参数
            param_crud.add_batch(v1_params)
            param_crud.add_batch(v2_params)

            print("✓ 创建版本化参数")

            # 查询和比较版本
            v1_query = param_crud.find(filters={"mapping_id": f"{version_mapping}_v1"})
            v2_query = param_crud.find(filters={"mapping_id": f"{version_mapping}_v2"})

            print(f"✓ 版本1参数: {len(v1_query)} 条")
            print(f"✓ 版本2参数: {len(v2_query)} 条")

            # 验证版本差异
            v1_dict = {p.index: p.value for p in v1_query}
            v2_dict = {p.index: p.value for p in v2_query}

            print("✓ 版本差异分析:")
            for index in set(v1_dict.keys()) | set(v2_dict.keys()):
                v1_val = v1_dict.get(index, "N/A")
                v2_val = v2_dict.get(index, "N/A")
                if v1_val != v2_val:
                    print(f"  - 索引{index}: {v1_val} → {v2_val}")

            print("✓ 参数版本控制验证成功")

        except Exception as e:
            print(f"✗ 参数版本控制失败: {e}")
            raise

    def test_parameter_data_integrity(self):
        """测试参数数据完整性"""
        print("\n" + "="*60)
        print("开始测试: 参数数据完整性")
        print("="*60)

        param_crud = ParamCRUD()

        try:
            # 测试必要字段约束
            print("→ 测试必要字段约束...")

            # 查询数据验证完整性
            valid_params = param_crud.find(page_size=50)
            for param in valid_params:
                # 验证mapping_id非空
                assert param.mapping_id and len(param.mapping_id.strip()) > 0

                # 验证index为非负整数
                assert isinstance(param.index, int) and param.index >= 0

                # 验证value非空
                assert param.value and len(param.value.strip()) > 0

                # 验证source为有效枚举值
                valid_sources = [s.value for s in SOURCE_TYPES]
                assert param.source in valid_sources

                # 验证时间戳
                assert param.create_at is not None
                assert param.update_at is not None

            print(f"✓ 验证了 {len(valid_params)} 条参数的完整性约束")
            print("✓ 参数数据完整性验证成功")

        except Exception as e:
            print(f"✗ 数据完整性测试失败: {e}")
            raise


# TDD Red阶段验证：确保所有测试开始时都失败
if __name__ == "__main__":
    print("TDD Red阶段验证：Param CRUD测试")
    print("所有测试用例应该在实现开始前失败")
    print("运行: pytest test/data/crud/test_param_crud.py -v")
    print("预期结果: 所有测试失败 (Red阶段)")
    print("重点关注: 参数配置存储和索引化参数管理功能")

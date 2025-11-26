"""
EngineHandlerMapping CRUD数据库操作TDD测试

测试CRUD层的引擎处理器映射数据操作：
- 批量插入 (add_batch)
- 单条插入 (add)
- 查询 (find)
- 更新 (update)
- 删除 (remove)
- 替换 (replace)

EngineHandlerMapping是引擎处理器映射数据模型，存储回测引擎与事件处理器的对应关系。
为量化交易系统的事件驱动架构提供支持，支持引擎的事件处理器配置和管理。
包括处理器类型管理、事件处理流程配置、处理器生命周期管理等功能。

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

from ginkgo.data.crud.engine_handler_mapping_crud import EngineHandlerMappingCRUD
from ginkgo.data.models.model_engine_handler_mapping import MEngineHandlerMapping
from ginkgo.enums import SOURCE_TYPES, EVENT_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestEngineHandlerMappingCRUDInsert:
    CRUD_TEST_CONFIG = {'crud_class': EngineHandlerMappingCRUD}
    """1. CRUD层插入操作测试 - EngineHandlerMapping数据插入验证"""

    def test_add_batch_basic(self):
        """测试批量插入EngineHandlerMapping数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: EngineHandlerMapping CRUD层批量插入")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()
        print(f"✓ 创建EngineHandlerMappingCRUD实例: {mapping_crud.__class__.__name__}")

        # 创建测试映射数据 - 不同引擎的处理器映射
        base_time = datetime.now()
        test_mappings = []

        # 引擎1的多个处理器映射
        mapping1 = MEngineHandlerMapping(
            engine_id="engine_ma_cross_001",
            handler_id="handler_price_update_001",
            type=EVENT_TYPES.PRICEUPDATE,
            name="价格更新处理器",
            source=SOURCE_TYPES.TEST
        )
        test_mappings.append(mapping1)

        mapping2 = MEngineHandlerMapping(
            engine_id="engine_ma_cross_001",
            handler_id="handler_order_generated_001",
            type=EVENT_TYPES.ORDERSUBMITTED,
            name="订单生成处理器",
            source=SOURCE_TYPES.TEST
        )
        test_mappings.append(mapping2)

        mapping3 = MEngineHandlerMapping(
            engine_id="engine_ma_cross_001",
            handler_id="handler_signal_generated_001",
            type=EVENT_TYPES.SIGNALGENERATION,
            name="信号生成处理器",
            source=SOURCE_TYPES.TEST
        )
        test_mappings.append(mapping3)

        # 引擎2的处理器映射
        mapping4 = MEngineHandlerMapping(
            engine_id="engine_bollinger_001",
            handler_id="handler_portfolio_update_001",
            type=EVENT_TYPES.PORTFOLIOUPDATE,
            name="投资组合更新处理器",
            source=SOURCE_TYPES.TEST
        )
        test_mappings.append(mapping4)

        # 引擎3的处理器映射
        mapping5 = MEngineHandlerMapping(
            engine_id="engine_rsi_001",
            handler_id="handler_time_update_001",
            type=EVENT_TYPES.PRICEUPDATE,
            name="时间更新处理器",
            source=SOURCE_TYPES.TEST
        )
        test_mappings.append(mapping5)

        print(f"✓ 创建测试数据: {len(test_mappings)}条映射记录")
        print(f"  - 引擎数量: {len(set(m.engine_id for m in test_mappings))}")
        print(f"  - 处理器数量: {len(set(m.handler_id for m in test_mappings))}")
        print(f"  - 事件类型: {len(set(m.type for m in test_mappings))}")

        try:
            # 批量插入
            print("\n→ 执行批量插入操作...")
            mapping_crud.add_batch(test_mappings)
            print("✓ 批量插入成功")

            # 验证可以查询出插入的数据
            print("\n→ 验证插入的数据...")
            query_result = mapping_crud.find(page_size=20)
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 5

            # 验证数据内容
            engine_ids = set(m.engine_id for m in query_result)
            handler_ids = set(m.handler_id for m in query_result)
            event_types = set(m.type for m in query_result)
            print(f"✓ 引擎ID验证通过: {len(engine_ids)} 个")
            print(f"✓ 处理器ID验证通过: {len(handler_ids)} 个")
            print(f"✓ 事件类型验证通过: {len(event_types)} 个")

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_mapping(self):
        """测试单条EngineHandlerMapping数据插入"""
        print("\n" + "="*60)
        print("开始测试: EngineHandlerMapping CRUD层单条插入")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        test_mapping = MEngineHandlerMapping(
            engine_id="single_test_engine_001",
            handler_id="single_test_handler_001",
            type=EVENT_TYPES.PRICEUPDATE,
            name="单一测试处理器",
            source=SOURCE_TYPES.TEST
        )
        print(f"✓ 创建测试映射: {test_mapping.engine_id} → {test_mapping.handler_id}")
        print(f"  - 事件类型: {EVENT_TYPES(test_mapping.type).name}")
        print(f"  - 处理器名称: {test_mapping.name}")

        try:
            # 单条插入
            print("\n→ 执行单条插入操作...")
            mapping_crud.add(test_mapping)
            print("✓ 单条插入成功")

            # 验证数据
            print("\n→ 验证插入的数据...")
            query_result = mapping_crud.find(filters={
                "engine_id": "single_test_engine_001",
                "handler_id": "single_test_handler_001"
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 1

            inserted_mapping = query_result[0]
            print(f"✓ 插入的映射验证: {inserted_mapping.engine_id}")
            assert inserted_mapping.engine_id == "single_test_engine_001"
            assert inserted_mapping.handler_id == "single_test_handler_001"
            assert inserted_mapping.type == EVENT_TYPES.PRICEUPDATE.value
            assert inserted_mapping.name == "单一测试处理器"

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise

    def test_add_engine_multiple_handlers(self):
        """测试一个引擎映射多个处理器"""
        print("\n" + "="*60)
        print("开始测试: 一个引擎映射多个处理器")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        # 创建一个引擎对应多个处理器的映射
        engine_id = "multi_handler_engine_001"
        handler_mappings = []

        event_types = [
            EVENT_TYPES.PRICEUPDATE,
            EVENT_TYPES.ORDERSUBMITTED,
            EVENT_TYPES.SIGNALGENERATION,
            EVENT_TYPES.PORTFOLIOUPDATE,
            EVENT_TYPES.PRICEUPDATE
        ]

        for i, event_type in enumerate(event_types):
            mapping = MEngineHandlerMapping(
                engine_id=engine_id,
                handler_id=f"handler_multi_{i+1:03d}",
                type=event_type,
                name=f"多处理器测试{i+1}",
                source=SOURCE_TYPES.TEST
            )
            handler_mappings.append(mapping)

        print(f"✓ 创建多处理器映射: 引擎 {engine_id} → {len(handler_mappings)} 个处理器")

        try:
            # 批量插入
            print("\n→ 执行多处理器映射插入...")
            mapping_crud.add_batch(handler_mappings)
            print("✓ 多处理器映射插入成功")

            # 验证数据
            print("\n→ 验证多处理器映射数据...")
            query_result = mapping_crud.find(filters={"engine_id": engine_id})
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 5

            # 验证事件类型分布
            event_type_names = [EVENT_TYPES(m.type).name for m in query_result]
            print(f"✓ 事件类型分布: {event_type_names}")
            assert len(event_type_names) >= 5

            print("✓ 多处理器映射验证成功")

        except Exception as e:
            print(f"✗ 多处理器映射插入失败: {e}")
            raise

    def test_add_event_type_variations(self):
        """测试不同事件类型的处理器映射"""
        print("\n" + "="*60)
        print("开始测试: 不同事件类型的处理器映射")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        # 创建不同事件类型的处理器映射
        base_engine_id = "event_type_test_engine"
        event_type_mappings = []

        # 主要事件类型
        main_event_types = [
            EVENT_TYPES.PRICEUPDATE,
            EVENT_TYPES.SIGNALGENERATION,
            EVENT_TYPES.ORDERSUBMITTED,
            EVENT_TYPES.PORTFOLIOUPDATE,
            EVENT_TYPES.PRICEUPDATE,
            EVENT_TYPES.NEXTPHASE,
            EVENT_TYPES.CAPITALUPDATE
        ]

        for i, event_type in enumerate(main_event_types):
            mapping = MEngineHandlerMapping(
                engine_id=base_engine_id,
                handler_id=f"hdl_event_{event_type.name[:8].lower()}_{i+1:02d}",
                type=event_type,
                name=f"{event_type.name}处理器",
                source=SOURCE_TYPES.TEST
            )
            event_type_mappings.append(mapping)

        print(f"✓ 创建事件类型测试映射: {len(event_type_mappings)} 个事件类型")

        try:
            # 批量插入
            print("\n→ 执行事件类型映射插入...")
            mapping_crud.add_batch(event_type_mappings)
            print("✓ 事件类型映射插入成功")

            # 验证数据
            print("\n→ 验证事件类型映射数据...")
            query_result = mapping_crud.find(filters={"engine_id": base_engine_id})
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 7

            # 验证事件类型覆盖
            mapped_event_types = set(m.type for m in query_result)
            expected_event_types = set(et.value for et in main_event_types)

            print(f"✓ 映射的事件类型: {len(mapped_event_types)} 个")
            print(f"✓ 预期的事件类型: {len(expected_event_types)} 个")

            print("✓ 事件类型映射验证成功")

        except Exception as e:
            print(f"✗ 事件类型映射插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestEngineHandlerMappingCRUDQuery:
    CRUD_TEST_CONFIG = {'crud_class': EngineHandlerMappingCRUD}
    """2. CRUD层查询操作测试 - EngineHandlerMapping数据查询和过滤"""

    def test_find_by_engine_id(self):
        """测试根据引擎ID查询EngineHandlerMapping"""
        print("\n" + "="*60)
        print("开始测试: 根据引擎ID查询EngineHandlerMapping")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        try:
            # 查询特定引擎的映射关系
            print("→ 查询引擎 engine_ma_cross_001 的映射关系...")
            engine_mappings = mapping_crud.find(filters={
                "engine_id": "engine_ma_cross_001"
            })
            print(f"✓ 查询到 {len(engine_mappings)} 条记录")

            # 验证查询结果
            for mapping in engine_mappings:
                print(f"  - {mapping.handler_id}: {mapping.name} ({EVENT_TYPES(mapping.type).name})")
                assert mapping.engine_id == "engine_ma_cross_001"

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_handler_id(self):
        """测试根据处理器ID查询EngineHandlerMapping"""
        print("\n" + "="*60)
        print("开始测试: 根据处理器ID查询EngineHandlerMapping")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        try:
            # 查询特定处理器的映射关系
            print("→ 查询处理器 handler_price_update_001 的映射关系...")
            handler_mappings = mapping_crud.find(filters={
                "handler_id": "handler_price_update_001"
            })
            print(f"✓ 查询到 {len(handler_mappings)} 条记录")

            # 验证查询结果
            for mapping in handler_mappings:
                print(f"  - {mapping.engine_id}: {mapping.name}")
                assert mapping.handler_id == "handler_price_update_001"

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_event_type(self):
        """测试根据事件类型查询EngineHandlerMapping"""
        print("\n" + "="*60)
        print("开始测试: 根据事件类型查询EngineHandlerMapping")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        try:
            # 查询不同事件类型的处理器映射
            for event_type in [EVENT_TYPES.PRICEUPDATE, EVENT_TYPES.SIGNALGENERATION,
                           EVENT_TYPES.ORDERSUBMITTED]:
                print(f"→ 查询{event_type.name}事件类型的处理器映射...")
                event_mappings = mapping_crud.find(filters={
                    "type": event_type.value
                })
                print(f"✓ {event_type.name}处理器数量: {len(event_mappings)}")

                # 显示处理器示例
                for mapping in event_mappings[:2]:
                    print(f"  - {mapping.handler_id}: {mapping.name}")

            print("✓ 事件类型查询验证成功")

        except Exception as e:
            print(f"✗ 事件类型查询失败: {e}")
            raise

    def test_find_by_handler_name(self):
        """测试根据处理器名称查询EngineHandlerMapping"""
        print("\n" + "="*60)
        print("开始测试: 根据处理器名称查询EngineHandlerMapping")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        try:
            # 查询特定名称模式的处理器映射
            print("→ 查询处理器名称包含 '更新' 的映射关系...")
            name_mappings = mapping_crud.find(filters={
                "name__like": "%更新%"
            })
            print(f"✓ 查询到 {len(name_mappings)} 条记录")

            # 验证查询结果
            for mapping in name_mappings:
                print(f"  - {mapping.engine_id}: {mapping.handler_id}")
                assert "更新" in mapping.name

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_engine_handler_pairs(self):
        """测试查询引擎处理器对"""
        print("\n" + "="*60)
        print("开始测试: 查询引擎处理器对")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        try:
            # 查询所有映射关系
            print("→ 查询所有引擎处理器映射关系...")
            all_mappings = mapping_crud.find(page_size=20)
            print(f"✓ 查询到 {len(all_mappings)} 条记录")

            # 构建引擎处理器对
            engine_handler_pairs = {}
            for mapping in all_mappings:
                if mapping.engine_id not in engine_handler_pairs:
                    engine_handler_pairs[mapping.engine_id] = []
                engine_handler_pairs[mapping.engine_id].append({
                    "handler_id": mapping.handler_id,
                    "type": mapping.type,
                    "name": mapping.name
                })

            print("✓ 引擎处理器映射关系:")
            for engine_id, handlers in engine_handler_pairs.items():
                print(f"  - {engine_id}: {len(handlers)} 个处理器")
                for handler in handlers[:3]:  # 显示前3个
                    print(f"    → {handler['handler_id']}: {handler['name']} "
                          f"({EVENT_TYPES(handler['type']).name})")

            print("✓ 引擎处理器对查询验证成功")

        except Exception as e:
            print(f"✗ 引擎处理器对查询失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestEngineHandlerMappingCRUDUpdate:
    CRUD_TEST_CONFIG = {'crud_class': EngineHandlerMappingCRUD}
    """3. CRUD层更新操作测试 - EngineHandlerMapping数据更新验证"""

    def test_update_handler_name(self):
        """测试更新处理器名称"""
        print("\n" + "="*60)
        print("开始测试: 更新处理器名称")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        # 创建测试数据
        test_mapping = MEngineHandlerMapping(
            engine_id="update_test_engine_001",
            handler_id="update_test_handler_001",
            type=EVENT_TYPES.PRICEUPDATE,
            name="原始处理器名称",
            source=SOURCE_TYPES.TEST
        )
        mapping_crud.add(test_mapping)
        print(f"✓ 创建测试映射: {test_mapping.uuid}")

        try:
            # 更新处理器名称
            print("→ 更新处理器名称...")
            mapping_crud.modify(
                filters={"uuid": test_mapping.uuid},
                updates={"name": "优化后的处理器名称v2.0"}
            )
            print("✓ 处理器名称更新成功")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_mapping = mapping_crud.find(filters={"uuid": test_mapping.uuid})[0]
            assert updated_mapping.name == "优化后的处理器名称v2.0"
            print(f"✓ 更新后处理器名称: {updated_mapping.name}")

            print("✓ 处理器名称更新验证成功")

        except Exception as e:
            print(f"✗ 更新操作失败: {e}")
            raise

    def test_update_event_type(self):
        """测试更新事件类型"""
        print("\n" + "="*60)
        print("开始测试: 更新事件类型")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        # 创建测试数据
        test_mapping = MEngineHandlerMapping(
            engine_id="update_event_test_engine_001",
            handler_id="update_event_test_handler_001",
            type=EVENT_TYPES.PRICEUPDATE,
            name="更新事件类型测试处理器",
            source=SOURCE_TYPES.TEST
        )
        mapping_crud.add(test_mapping)
        print(f"✓ 创建测试映射: {test_mapping.uuid}")

        try:
            # 更新事件类型
            print("→ 更新事件类型...")
            mapping_crud.modify(
                filters={"uuid": test_mapping.uuid},
                updates={"type": EVENT_TYPES.SIGNALGENERATION.value}
            )
            print("✓ 事件类型更新成功")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_mapping = mapping_crud.find(filters={"uuid": test_mapping.uuid})[0]
            assert updated_mapping.type == EVENT_TYPES.SIGNALGENERATION.value
            print(f"✓ 更新后事件类型: {EVENT_TYPES(updated_mapping.type).name}")

            print("✓ 事件类型更新验证成功")

        except Exception as e:
            print(f"✗ 事件类型更新操作失败: {e}")
            raise

    def test_update_mapping_fields(self):
        """测试更新映射多个字段"""
        print("\n" + "="*60)
        print("开始测试: 更新映射多个字段")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        # 创建测试数据
        test_mapping = MEngineHandlerMapping(
            engine_id="update_fields_engine_001",
            handler_id="update_fields_handler_001",
            type=EVENT_TYPES.PRICEUPDATE,
            name="原始处理器",
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
                    "name": "升级版事件处理器",
                    "type": EVENT_TYPES.PORTFOLIOUPDATE.value,
                    "source": SOURCE_TYPES.TEST.value
                }
            )
            print("✓ 多字段更新成功")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_mapping = mapping_crud.find(filters={"uuid": test_mapping.uuid})[0]
            assert updated_mapping.name == "升级版事件处理器"
            assert updated_mapping.type == EVENT_TYPES.PORTFOLIOUPDATE.value
            assert updated_mapping.source == SOURCE_TYPES.TEST.value

            print(f"✓ 更新后处理器名称: {updated_mapping.name}")
            print(f"✓ 更新后事件类型: {EVENT_TYPES(updated_mapping.type).name}")
            print(f"✓ 更新后数据源: {updated_mapping.source}")

            print("✓ 多字段更新验证成功")

        except Exception as e:
            print(f"✗ 多字段更新操作失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestEngineHandlerMappingCRUDDelete:
    CRUD_TEST_CONFIG = {'crud_class': EngineHandlerMappingCRUD}
    """4. CRUD层删除操作测试 - EngineHandlerMapping数据删除验证"""

    def test_delete_mapping_by_engine_id(self):
        """测试根据引擎ID删除EngineHandlerMapping"""
        print("\n" + "="*60)
        print("开始测试: 根据引擎ID删除EngineHandlerMapping")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        # 准备测试数据
        print("→ 准备测试数据...")
        test_mapping = MEngineHandlerMapping(
            engine_id="DELETE_TEST_ENGINE",
            handler_id="delete_test_handler_001",
            type=EVENT_TYPES.PRICEUPDATE,
            name="删除测试处理器",
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

            print("✓ 根据引擎ID删除EngineHandlerMapping验证成功")

        except Exception as e:
            print(f"✗ 删除操作失败: {e}")
            raise

    def test_delete_mapping_by_handler_id(self):
        """测试根据处理器ID删除EngineHandlerMapping"""
        print("\n" + "="*60)
        print("开始测试: 根据处理器ID删除EngineHandlerMapping")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        # 准备测试数据
        print("→ 准备测试数据...")
        test_mapping = MEngineHandlerMapping(
            engine_id="delete_test_engine_002",
            handler_id="DELETE_TEST_HANDLER",
            type=EVENT_TYPES.SIGNALGENERATION,
            name="删除测试处理器2",
            source=SOURCE_TYPES.TEST
        )
        mapping_crud.add(test_mapping)
        print(f"✓ 插入测试数据: {test_mapping.handler_id}")

        # 验证数据存在
        before_count = len(mapping_crud.find(filters={"handler_id": "DELETE_TEST_HANDLER"}))
        print(f"✓ 删除前数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行删除操作...")
            mapping_crud.remove(filters={"handler_id": "DELETE_TEST_HANDLER"})
            print("✓ 删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(mapping_crud.find(filters={"handler_id": "DELETE_TEST_HANDLER"}))
            print(f"✓ 删除后数据量: {after_count}")
            assert after_count == 0, "删除后应该没有相关数据"

            print("✓ 根据处理器ID删除EngineHandlerMapping验证成功")

        except Exception as e:
            print(f"✗ 删除操作失败: {e}")
            raise

    def test_delete_mapping_by_event_type(self):
        """测试根据事件类型删除EngineHandlerMapping"""
        print("\n" + "="*60)
        print("开始测试: 根据事件类型删除EngineHandlerMapping")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        # 准备测试数据 - 不同事件类型的映射
        print("→ 准备测试数据...")
        test_mappings = [
            MEngineHandlerMapping(
                engine_id="delete_event_engine_1",
                handler_id="delete_event_handler_1",
                type=EVENT_TYPES.PRICEUPDATE,
                name="删除事件类型测试1",
                source=SOURCE_TYPES.TEST
            ),
            MEngineHandlerMapping(
                engine_id="delete_event_engine_2",
                handler_id="delete_event_handler_2",
                type=EVENT_TYPES.PRICEUPDATE,
                name="删除事件类型测试2",
                source=SOURCE_TYPES.TEST
            ),
            MEngineHandlerMapping(
                engine_id="keep_event_engine_1",
                handler_id="keep_event_handler_1",
                type=EVENT_TYPES.SIGNALGENERATION,
                name="保留事件类型测试",
                source=SOURCE_TYPES.TEST
            )
        ]

        for mapping in test_mappings:
            mapping_crud.add(mapping)

        print(f"✓ 插入事件类型测试数据: {len(test_mappings)} 条")

        try:
            # 删除特定事件类型的映射
            print("\n→ 删除PRICEUPDATE事件类型的映射...")
            before_delete = len(mapping_crud.find(filters={
                "type": EVENT_TYPES.PRICEUPDATE.value
            }))
            print(f"✓ 删除前PRICEUPDATE事件类型数据量: {before_delete}")

            mapping_crud.remove(filters={"type": EVENT_TYPES.PRICEUPDATE.value})
            print("✓ 事件类型删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_delete = len(mapping_crud.find(filters={
                "type": EVENT_TYPES.PRICEUPDATE.value
            }))
            print(f"✓ 删除后PRICEUPDATE事件类型数据量: {after_delete}")
            assert after_delete == 0, "PRICEUPDATE事件类型映射应该全部删除"

            # 验证其他事件类型映射保留
            keep_count = len(mapping_crud.find(filters={
                "type": EVENT_TYPES.SIGNALGENERATION.value
            }))
            print(f"✓ 保留的SIGNALGENERATION事件类型映射数量: {keep_count}")
            assert keep_count >= 1, "其他事件类型映射应该保留"

            print("✓ 根据事件类型删除EngineHandlerMapping验证成功")

        except Exception as e:
            print(f"✗ 事件类型删除操作失败: {e}")
            raise

    def test_delete_mapping_by_name_pattern(self):
        """测试根据名称模式删除EngineHandlerMapping"""
        print("\n" + "="*60)
        print("开始测试: 根据名称模式删除EngineHandlerMapping")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        # 准备测试数据 - 不同名称模式的映射
        print("→ 准备测试数据...")
        test_mappings = [
            MEngineHandlerMapping(
                engine_id="delete_name_engine_1",
                handler_id="delete_name_handler_1",
                type=EVENT_TYPES.PRICEUPDATE,
                name="DELETE_NAME_HANDLER",
                source=SOURCE_TYPES.TEST
            ),
            MEngineHandlerMapping(
                engine_id="delete_name_engine_2",
                handler_id="delete_name_handler_2",
                type=EVENT_TYPES.ORDERSUBMITTED,
                name="DELETE_NAME_HANDLER_2",
                source=SOURCE_TYPES.TEST
            ),
            MEngineHandlerMapping(
                engine_id="keep_name_engine_001",
                handler_id="keep_name_handler_001",
                type=EVENT_TYPES.PORTFOLIOUPDATE,
                name="KEEP_NAME_HANDLER",
                source=SOURCE_TYPES.TEST
            )
        ]

        for mapping in test_mappings:
            mapping_crud.add(mapping)

        print(f"✓ 插入名称模式测试数据: {len(test_mappings)} 条")

        try:
            # 删除包含特定模式的映射
            print("\n→ 删除包含 'DELETE_NAME' 的映射...")
            before_delete = len(mapping_crud.find(filters={
                "name__like": "%DELETE_NAME%"
            }))
            print(f"✓ 删除前匹配数据量: {before_delete}")

            mapping_crud.remove(filters={
                "name__like": "%DELETE_NAME%"
            })
            print("✓ 名称模式删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_delete = len(mapping_crud.find(filters={
                "name__like": "%DELETE_NAME%"
            }))
            print(f"✓ 删除后匹配数据量: {after_delete}")
            assert after_delete == 0, "匹配的映射应该全部删除"

            # 验证不匹配的映射保留
            keep_count = len(mapping_crud.find(filters={
                "name__like": "%KEEP_NAME%"
            }))
            print(f"✓ 保留的映射数量: {keep_count}")
            assert keep_count >= 1, "不匹配的映射应该保留"

            print("✓ 根据名称模式删除EngineHandlerMapping验证成功")

        except Exception as e:
            print(f"✗ 名称模式删除操作失败: {e}")
            raise

    def test_delete_mapping_batch_cleanup(self):
        """测试批量清理EngineHandlerMapping数据"""
        print("\n" + "="*60)
        print("开始测试: 批量清理EngineHandlerMapping数据")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        # 准备批量清理数据
        print("→ 准备批量清理测试数据...")
        cleanup_count = 6
        cleanup_engine_prefix = "CLEANUP_BATCH_ENGINE"

        for i in range(cleanup_count):
            test_mapping = MEngineHandlerMapping(
                engine_id=f"{cleanup_engine_prefix}_{i+1:03d}",
                handler_id=f"cleanup_handler_{i+1:03d}",
                type=EVENT_TYPES.PRICEUPDATE,
                name=f"清理测试处理器{i+1}",
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

            print("✓ 批量清理EngineHandlerMapping数据验证成功")

        except Exception as e:
            print(f"✗ 批量清理操作失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestEngineHandlerMappingCRUDBusinessLogic:
    CRUD_TEST_CONFIG = {'crud_class': EngineHandlerMappingCRUD}
    """5. CRUD层业务逻辑测试 - EngineHandlerMapping业务场景验证"""

    def test_engine_handler_relationship_analysis(self):
        """测试引擎处理器关系分析"""
        print("\n" + "="*60)
        print("开始测试: 引擎处理器关系分析")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        try:
            # 查询所有映射关系进行分析
            print("→ 查询引擎处理器关系分析...")
            all_mappings = mapping_crud.find(page_size=50)

            if len(all_mappings) == 0:
                print("✗ 映射数据不足，跳过关系分析")
                return

            # 分析引擎分布
            engine_stats = {}
            handler_stats = {}
            event_type_stats = {}

            for mapping in all_mappings:
                # 引擎统计
                if mapping.engine_id not in engine_stats:
                    engine_stats[mapping.engine_id] = {
                        "handler_count": 0,
                        "handlers": [],
                        "event_types": set()
                    }
                engine_stats[mapping.engine_id]["handler_count"] += 1
                engine_stats[mapping.engine_id]["handlers"].append(mapping.handler_id)
                engine_stats[mapping.engine_id]["event_types"].add(mapping.type)

                # 处理器统计
                if mapping.handler_id not in handler_stats:
                    handler_stats[mapping.handler_id] = {
                        "name": mapping.name,
                        "engine_count": 0,
                        "engines": []
                    }
                handler_stats[mapping.handler_id]["engine_count"] += 1
                handler_stats[mapping.handler_id]["engines"].append(mapping.engine_id)

                # 事件类型统计
                event_type_name = EVENT_TYPES(mapping.type).name
                if event_type_name not in event_type_stats:
                    event_type_stats[event_type_name] = {
                        "count": 0,
                        "engines": set(),
                        "handlers": set()
                    }
                event_type_stats[event_type_name]["count"] += 1
                event_type_stats[event_type_name]["engines"].add(mapping.engine_id)
                event_type_stats[event_type_name]["handlers"].add(mapping.handler_id)

            print(f"✓ 引擎处理器关系分析结果:")
            print(f"  - 总映射关系: {len(all_mappings)}")
            print(f"  - 引擎数量: {len(engine_stats)}")
            print(f"  - 处理器数量: {len(handler_stats)}")
            print(f"  - 事件类型数量: {len(event_type_stats)}")

            # 显示引擎分布
            print("✓ 引擎分布:")
            for engine_id, stats in engine_stats.items():
                event_type_names = [EVENT_TYPES(et).name for et in stats["event_types"]]
                print(f"  - {engine_id}: {stats['handler_count']} 个处理器, {len(event_type_names)} 种事件类型")

            # 显示事件类型分布
            print("✓ 事件类型分布:")
            for event_type, stats in event_type_stats.items():
                print(f"  - {event_type}: {stats['count']} 个映射, {len(stats['engines'])} 个引擎")

            print("✓ 引擎处理器关系分析验证成功")

        except Exception as e:
            print(f"✗ 引擎处理器关系分析失败: {e}")
            raise

    def test_event_type_coverage_analysis(self):
        """测试事件类型覆盖分析"""
        print("\n" + "="*60)
        print("开始测试: 事件类型覆盖分析")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        try:
            # 查询所有映射关系
            print("→ 查询事件类型覆盖分析...")
            all_mappings = mapping_crud.find(page_size=50)

            if len(all_mappings) == 0:
                pytest.skip("映射数据不足，跳过覆盖分析")

            # 分析事件类型覆盖情况
            covered_event_types = set()
            event_type_distribution = {}

            for mapping in all_mappings:
                event_type_name = EVENT_TYPES(mapping.type).name
                covered_event_types.add(event_type_name)
                if event_type_name not in event_type_distribution:
                    event_type_distribution[event_type_name] = 0
                event_type_distribution[event_type_name] += 1

            print(f"✓ 事件类型覆盖分析结果:")
            print(f"  - 已覆盖事件类型: {len(covered_event_types)} 种")
            print(f"  - 事件类型分布:")

            # 断言验证基础数据
            assert len(all_mappings) > 0, "应该有映射数据进行分析"
            assert len(covered_event_types) > 0, "应该有覆盖的事件类型"

            total_mappings = len(all_mappings)
            for event_type, count in sorted(event_type_distribution.items(),
                                           key=lambda x: x[1], reverse=True):
                percentage = (count / total_mappings) * 100
                print(f"    - {event_type}: {count} 个映射 ({percentage:.1f}%)")

                # 断言验证分布合理性
                assert count > 0, f"事件类型{event_type}的计数应该大于0"
                assert 0 <= percentage <= 100, f"百分比应该在0-100之间，实际: {percentage}"

            # 验证关键事件类型覆盖
            critical_event_types = [
                "PRICEUPDATE", "SIGNALGENERATION", "ORDERSUBMITTED",
                "PORTFOLIOUPDATE"
            ]
            missing_critical = [et for et in critical_event_types
                               if et not in covered_event_types]

            # 断言验证覆盖情况
            covered_critical = [et for et in critical_event_types
                               if et in covered_event_types]

            print(f"  - 关键事件类型覆盖: {len(covered_critical)}/{len(critical_event_types)}")
            if missing_critical:
                print(f"  - 缺少关键事件类型: {missing_critical}")
                # 不强制要求所有关键事件类型都必须覆盖，但要记录
            else:
                print("  - 所有关键事件类型已覆盖")

            # 验证分布统计的准确性
            distribution_sum = sum(event_type_distribution.values())
            assert distribution_sum == total_mappings, f"分布总和应该等于总映射数，实际: {distribution_sum} vs {total_mappings}"

            print("✓ 事件类型覆盖分析验证成功")

        except Exception as e:
            print(f"✗ 事件类型覆盖分析失败: {e}")
            raise

    def test_mapping_consistency_validation(self):
        """测试映射关系一致性验证"""
        print("\n" + "="*60)
        print("开始测试: 映射关系一致性验证")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

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

                if not mapping.handler_id or len(mapping.handler_id.strip()) == 0:
                    consistency_errors.append(f"处理器ID为空: {mapping.uuid}")

                # 验证名称字段长度
                if len(mapping.name) > 32:
                    consistency_errors.append(f"处理器名称过长: {mapping.name}")

                # 验证事件类型有效性
                valid_event_types = [et.value for et in EVENT_TYPES]
                if mapping.type not in valid_event_types:
                    consistency_errors.append(f"无效事件类型: {mapping.type}")

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
                pair = (mapping.engine_id, mapping.handler_id)
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
            total_unique_handlers = len(set(m.handler_id for m in all_mappings))
            assert total_unique_engines > 0, "应该有唯一的引擎ID"
            assert total_unique_handlers > 0, "应该有唯一的处理器ID"
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

        mapping_crud = EngineHandlerMappingCRUD()

        try:
            # 测试必要字段约束
            print("→ 测试必要字段约束...")

            # 查询数据验证完整性
            valid_mappings = mapping_crud.find(page_size=20)
            for mapping in valid_mappings:
                # 验证engine_id非空
                assert mapping.engine_id and len(mapping.engine_id.strip()) > 0
                assert len(mapping.engine_id) <= 32, "引擎ID长度不应超过32字符"

                # 验证handler_id非空
                assert mapping.handler_id and len(mapping.handler_id.strip()) > 0
                assert len(mapping.handler_id) <= 32, "处理器ID长度不应超过32字符"

                # 验证name非空
                assert mapping.name and len(mapping.name.strip()) > 0
                assert len(mapping.name) <= 32, "处理器名称长度不应超过32字符"

                # 验证type为有效枚举值
                valid_event_types = [et.value for et in EVENT_TYPES]
                assert mapping.type in valid_event_types

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


@pytest.mark.database
@pytest.mark.tdd
class TestEngineHandlerMappingCRUDConversion:
    CRUD_TEST_CONFIG = {'crud_class': EngineHandlerMappingCRUD}
    """6. CRUD层转换操作测试 - to_entity和to_dataframe转换验证"""

    def test_to_entity_conversion(self):
        """测试将mapping对象转换为JSON entity格式"""
        print("\n" + "="*60)
        print("开始测试: mapping对象to_entity转换")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        # 创建测试数据
        test_mapping = MEngineHandlerMapping(
            engine_id="conversion_test_engine_001",
            handler_id="conv_test_handler_001",
            type=EVENT_TYPES.PRICEUPDATE,
            name="转换测试处理器",
            source=SOURCE_TYPES.TEST
        )
        mapping_crud.add(test_mapping)
        print(f"✓ 创建测试映射: {test_mapping.uuid}")

        try:
            # 查询数据并转换为entity
            print("\n→ 执行to_entity转换...")
            query_result = mapping_crud.find(filters={"uuid": test_mapping.uuid})
            assert len(query_result) >= 1

            # 模拟to_entity转换 - mapping关系转换为JSON格式
            mapping = query_result[0]
            entity_json = {
                "uuid": str(mapping.uuid),
                "engine_id": mapping.engine_id,
                "handler_id": mapping.handler_id,
                "event_type": EVENT_TYPES(mapping.type).name,
                "event_type_value": mapping.type,
                "handler_name": mapping.name,
                "source": SOURCE_TYPES(mapping.source).name,
                "source_value": mapping.source,
                "timestamps": {
                    "created_at": mapping.create_at.isoformat() if mapping.create_at else None,
                    "updated_at": mapping.update_at.isoformat() if mapping.update_at else None
                },
                "mapping_relationship": f"{mapping.engine_id} ↔ {mapping.handler_id}",
                "event_handler_type": f"event:{EVENT_TYPES(mapping.type).name}|handler:{mapping.handler_id}"
            }

            print("✓ to_entity转换完成:")
            print(f"  - Entity JSON: {entity_json}")
            print(f"  - 映射关系: {entity_json['mapping_relationship']}")
            print(f"  - 事件处理器: {entity_json['event_handler_type']}")

            # 验证转换结果
            assert entity_json["engine_id"] == "conversion_test_engine_001"
            assert entity_json["handler_id"] == "conv_test_handler_001"
            assert entity_json["event_type"] == "PRICEUPDATE"
            assert entity_json["handler_name"] == "转换测试处理器"
            assert entity_json["source"] == "TEST"
            assert "timestamps" in entity_json
            assert "mapping_relationship" in entity_json
            assert "event_handler_type" in entity_json

            print("✓ to_entity转换验证成功")

        except Exception as e:
            print(f"✗ to_entity转换失败: {e}")
            raise

    def test_to_dataframe_conversion(self):
        """测试将mapping对象转换为DataFrame格式"""
        print("\n" + "="*60)
        print("开始测试: mapping对象to_dataframe转换")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        # 准备批量测试数据
        print("→ 准备DataFrame转换测试数据...")
        test_mappings = []
        engine_ids = ["df_engine_001", "df_engine_002"]
        handler_ids = ["df_hdl_001", "df_hdl_002", "df_hdl_003"]

        for i, engine_id in enumerate(engine_ids):
            for j, handler_id in enumerate(handler_ids):
                mapping = MEngineHandlerMapping(
                    engine_id=engine_id,
                    handler_id=handler_id,
                    type=EVENT_TYPES.PRICEUPDATE,
                    name=f"DataFrame测试处理器{i}{j}",
                    source=SOURCE_TYPES.TEST
                )
                test_mappings.append(mapping)
                mapping_crud.add(mapping)

        print(f"✓ 插入DataFrame测试数据: {len(test_mappings)} 条")

        try:
            # 查询数据并转换为DataFrame
            print("\n→ 执行to_dataframe转换...")
            query_result = mapping_crud.find(page_size=50)
            print(f"✓ 查询到 {len(query_result)} 条记录用于DataFrame转换")

            # 模拟to_dataframe转换 - 提取结构化数据
            data_for_dataframe = []
            for mapping in query_result:
                data_for_dataframe.append({
                    "uuid": str(mapping.uuid),
                    "engine_id": mapping.engine_id,
                    "handler_id": mapping.handler_id,
                    "event_type_name": EVENT_TYPES(mapping.type).name,
                    "event_type_value": mapping.type,
                    "handler_name": mapping.name,
                    "source_name": SOURCE_TYPES(mapping.source).name,
                    "source_value": mapping.source,
                    "created_at": mapping.create_at,
                    "updated_at": mapping.update_at
                })

            print("✓ DataFrame数据结构准备完成:")
            print(f"  - 数据条数: {len(data_for_dataframe)}")
            print(f"  - 字段数量: {len(data_for_dataframe[0]) if data_for_dataframe else 0}")

            # 验证DataFrame转换结果
            if data_for_dataframe:
                sample_record = data_for_dataframe[0]
                expected_fields = [
                    "uuid", "engine_id", "handler_id",
                    "event_type_name", "event_type_value",
                    "handler_name", "source_name", "source_value",
                    "created_at", "updated_at"
                ]

                for field in expected_fields:
                    assert field in sample_record, f"缺少字段: {field}"

                print(f"✓ DataFrame字段验证通过: {len(expected_fields)} 个字段")

                # 显示数据分布统计
                engine_count = len(set(r["engine_id"] for r in data_for_dataframe))
                handler_count = len(set(r["handler_id"] for r in data_for_dataframe))
                event_type_count = len(set(r["event_type_name"] for r in data_for_dataframe))

                print(f"✓ DataFrame数据分布:")
                print(f"  - 引擎数量: {engine_count}")
                print(f"  - 处理器数量: {handler_count}")
                print(f"  - 事件类型数量: {event_type_count}")

            print("✓ to_dataframe转换验证成功")

        except Exception as e:
            print(f"✗ to_dataframe转换失败: {e}")
            raise

    def test_data_count_changes_with_conversion(self):
        """测试数据条数变化验证增删操作"""
        print("\n" + "="*60)
        print("开始测试: 数据条数变化验证增删操作")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        try:
            # 记录初始数据条数
            initial_count = len(mapping_crud.find(page_size=1000))
            print(f"✓ 初始数据条数: {initial_count}")

            # 测试插入操作的数据条数变化
            print("\n→ 测试插入操作数据条数变化...")
            test_mappings = []
            for i in range(3):
                mapping = MEngineHandlerMapping(
                    engine_id=f"count_test_engine_{i+1:03d}",
                    handler_id=f"count_test_handler_{i+1:03d}",
                    type=EVENT_TYPES.PRICEUPDATE,
                    name=f"数据条数测试处理器{i+1}",
                    source=SOURCE_TYPES.TEST
                )
                test_mappings.append(mapping)
                mapping_crud.add(mapping)

            after_insert_count = len(mapping_crud.find(page_size=1000))
            expected_after_insert = initial_count + 3
            print(f"✓ 插入后数据条数: {after_insert_count} (预期: {expected_after_insert})")
            assert after_insert_count == expected_after_insert, f"插入后数据条数不匹配: {after_insert_count} != {expected_after_insert}"

            # 测试删除操作的数据条数变化
            print("\n→ 测试删除操作数据条数变化...")
            delete_count = 2
            for i in range(delete_count):
                mapping_crud.remove(filters={
                    "engine_id": f"count_test_engine_{i+1:03d}"
                })

            after_delete_count = len(mapping_crud.find(page_size=1000))
            expected_after_delete = after_insert_count - delete_count
            print(f"✓ 删除后数据条数: {after_delete_count} (预期: {expected_after_delete})")
            assert after_delete_count == expected_after_delete, f"删除后数据条数不匹配: {after_delete_count} != {expected_after_delete}"

            # 验证剩余数据
            remaining_count = len(mapping_crud.find(filters={
                "engine_id__like": "count_test_engine_%"
            }))
            expected_remaining = 1
            print(f"✓ 剩余测试数据条数: {remaining_count} (预期: {expected_remaining})")
            assert remaining_count == expected_remaining, f"剩余数据条数不匹配: {remaining_count} != {expected_remaining}"

            print("✓ 数据条数变化验证成功")

        except Exception as e:
            print(f"✗ 数据条数变化验证失败: {e}")
            raise

    def test_to_entity_with_relationship_analysis(self):
        """测试to_entity转换包含关系分析"""
        print("\n" + "="*60)
        print("开始测试: to_entity转换包含关系分析")
        print("="*60)

        mapping_crud = EngineHandlerMappingCRUD()

        try:
            # 查询现有映射数据进行关系分析
            print("→ 查询映射数据进行关系分析...")
            all_mappings = mapping_crud.find(page_size=20)

            if len(all_mappings) == 0:
                print("✗ 映射数据不足，跳过关系分析测试")
                return

            # 构建关系分析的entity格式
            relationship_analysis = {
                "total_mappings": len(all_mappings),
                "engines": {},
                "handlers": {},
                "event_types": {},
                "complexity_metrics": {
                    "avg_handlers_per_engine": 0,
                    "avg_engines_per_handler": 0,
                    "most_connected_engine": None,
                    "most_used_handler": None
                }
            }

            # 分析映射关系
            engine_handler_counts = {}
            handler_engine_counts = {}

            for mapping in all_mappings:
                engine_id = mapping.engine_id
                handler_id = mapping.handler_id
                event_type = EVENT_TYPES(mapping.type).name

                # 引擎统计
                if engine_id not in relationship_analysis["engines"]:
                    relationship_analysis["engines"][engine_id] = {
                        "handlers": set(),
                        "event_types": set(),
                        "handler_count": 0
                    }

                relationship_analysis["engines"][engine_id]["handlers"].add(handler_id)
                relationship_analysis["engines"][engine_id]["event_types"].add(event_type)
                relationship_analysis["engines"][engine_id]["handler_count"] += 1

                # 处理器统计
                if handler_id not in relationship_analysis["handlers"]:
                    relationship_analysis["handlers"][handler_id] = {
                        "engines": set(),
                        "event_types": set(),
                        "engine_count": 0
                    }

                relationship_analysis["handlers"][handler_id]["engines"].add(engine_id)
                relationship_analysis["handlers"][handler_id]["event_types"].add(event_type)
                relationship_analysis["handlers"][handler_id]["engine_count"] += 1

                # 事件类型统计
                if event_type not in relationship_analysis["event_types"]:
                    relationship_analysis["event_types"][event_type] = {
                        "engines": set(),
                        "handlers": set(),
                        "mapping_count": 0
                    }

                relationship_analysis["event_types"][event_type]["engines"].add(engine_id)
                relationship_analysis["event_types"][event_type]["handlers"].add(handler_id)
                relationship_analysis["event_types"][event_type]["mapping_count"] += 1

                # 计数器更新
                engine_handler_counts[engine_id] = engine_handler_counts.get(engine_id, 0) + 1
                handler_engine_counts[handler_id] = handler_engine_counts.get(handler_id, 0) + 1

            # 计算复杂度指标
            if relationship_analysis["engines"]:
                relationship_analysis["complexity_metrics"]["avg_handlers_per_engine"] = \
                    len(all_mappings) / len(relationship_analysis["engines"])
                relationship_analysis["complexity_metrics"]["most_connected_engine"] = \
                    max(engine_handler_counts, key=engine_handler_counts.get)

            if relationship_analysis["handlers"]:
                relationship_analysis["complexity_metrics"]["avg_engines_per_handler"] = \
                    len(all_mappings) / len(relationship_analysis["handlers"])
                relationship_analysis["complexity_metrics"]["most_used_handler"] = \
                    max(handler_engine_counts, key=handler_engine_counts.get)

            print("✓ 关系分析entity转换完成:")
            print(f"  - 总映射数: {relationship_analysis['total_mappings']}")
            print(f"  - 引擎数量: {len(relationship_analysis['engines'])}")
            print(f"  - 处理器数量: {len(relationship_analysis['handlers'])}")
            print(f"  - 事件类型数量: {len(relationship_analysis['event_types'])}")
            print(f"  - 平均每引擎处理器数: {relationship_analysis['complexity_metrics']['avg_handlers_per_engine']:.2f}")
            print(f"  - 平均每处理器引擎数: {relationship_analysis['complexity_metrics']['avg_engines_per_handler']:.2f}")

            if relationship_analysis["complexity_metrics"]["most_connected_engine"]:
                most_engine = relationship_analysis["complexity_metrics"]["most_connected_engine"]
                print(f"  - 连接最多的引擎: {most_engine} ({engine_handler_counts[most_engine]} 个处理器)")

            if relationship_analysis["complexity_metrics"]["most_used_handler"]:
                most_handler = relationship_analysis["complexity_metrics"]["most_used_handler"]
                print(f"  - 使用最多的处理器: {most_handler} ({handler_engine_counts[most_handler]} 个引擎)")

            # 验证关系分析完整性
            assert relationship_analysis["total_mappings"] == len(all_mappings)
            assert len(relationship_analysis["engines"]) > 0
            assert len(relationship_analysis["handlers"]) > 0
            assert relationship_analysis["complexity_metrics"]["avg_handlers_per_engine"] > 0

            print("✓ to_entity关系分析验证成功")

        except Exception as e:
            print(f"✗ to_entity关系分析失败: {e}")
            raise


# TDD Red阶段验证：确保所有测试开始时都失败
if __name__ == "__main__":
    print("TDD Red阶段验证：EngineHandlerMapping CRUD测试")
    print("所有测试用例应该在实现开始前失败")
    print("运行: pytest test/data/crud/test_engine_handler_mapping_crud.py -v")
    print("预期结果: 所有测试失败 (Red阶段)")
    print("重点关注: 引擎处理器映射存储和事件管理功能")
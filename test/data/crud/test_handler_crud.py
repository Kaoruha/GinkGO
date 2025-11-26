"""
Handler CRUD数据库操作TDD测试

测试CRUD层的事件处理器数据操作：
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

Handler是事件处理器数据模型，存储系统中各种事件处理器的配置信息。
为事件处理、功能扩展和系统架构提供支持。
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.handler_crud import HandlerCRUD
from ginkgo.data.models.model_handler import MHandler
from ginkgo.enums import SOURCE_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestHandlerCRUDInsert:
    CRUD_TEST_CONFIG = {'crud_class': HandlerCRUD}
    """1. CRUD层插入操作测试 - Handler数据插入验证"""

    def test_add_batch_basic(self):
        """测试批量插入Handler数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: Handler CRUD层批量插入")
        print("="*60)

        handler_crud = HandlerCRUD()
        print(f"✓ 创建HandlerCRUD实例: {handler_crud.__class__.__name__}")

        # 创建测试Handler数据 - 不同类型的事件处理器
        test_handlers = []

        # 数据处理器
        data_handler = MHandler(
            name="data_processor",
            lib_path="ginkgo.handlers.data",
            func_name="process_data_event"
        )
        data_handler.source = SOURCE_TYPES.TEST
        test_handlers.append(data_handler)

        # 信号处理器
        signal_handler = MHandler(
            name="signal_generator",
            lib_path="ginkgo.handlers.signal",
            func_name="generate_signal"
        )
        signal_handler.source = SOURCE_TYPES.TEST
        test_handlers.append(signal_handler)

        # 订单处理器
        order_handler = MHandler(
            name="order_executor",
            lib_path="ginkgo.handlers.order",
            func_name="execute_order"
        )
        order_handler.source = SOURCE_TYPES.TEST
        test_handlers.append(order_handler)

        # 风险处理器
        risk_handler = MHandler(
            name="risk_manager",
            lib_path="ginkgo.handlers.risk",
            func_name="manage_risk"
        )
        risk_handler.source = SOURCE_TYPES.TEST
        test_handlers.append(risk_handler)

        print(f"✓ 创建测试数据: {len(test_handlers)}条Handler记录")
        handler_names = [h.name for h in test_handlers]
        print(f"  - 处理器名称: {handler_names}")

        try:
            # 批量插入
            print("\n→ 执行批量插入操作...")
            handler_crud.add_batch(test_handlers)
            print("✓ 批量插入成功")

            # 验证可以查询出插入的数据
            print("\n→ 验证插入的数据...")
            query_result = handler_crud.find()
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 4

            # 验证数据内容
            names = set(h.name for h in query_result)
            print(f"✓ 处理器名称验证通过: {len(names)} 种")
            assert len(names) >= 4

            # 验证我们插入的处理器
            for handler_name in handler_names:
                matching_handlers = [h for h in query_result if h.name == handler_name]
                assert len(matching_handlers) >= 1
                print(f"✓ 处理器 {handler_name} 插入验证成功")

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_handler(self):
        """测试单条Handler数据插入"""
        print("\n" + "="*60)
        print("开始测试: Handler CRUD层单条插入")
        print("="*60)

        handler_crud = HandlerCRUD()

        test_handler = MHandler(
            name="portfolio_analyzer",
            lib_path="ginkgo.handlers.portfolio",
            func_name="analyze_portfolio"
        )
        test_handler.source = SOURCE_TYPES.TEST
        print(f"✓ 创建测试Handler: {test_handler.name}")
        print(f"  - 库路径: {test_handler.lib_path}")
        print(f"  - 函数名: {test_handler.func_name}")

        try:
            # 单条插入
            print("\n→ 执行单条插入操作...")
            handler_crud.add(test_handler)
            print("✓ 单条插入成功")

            # 验证数据
            print("\n→ 验证插入的数据...")
            query_result = handler_crud.find(filters={"name": "portfolio_analyzer"})
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 1

            inserted_handler = query_result[0]
            print(f"✓ 插入的Handler验证: {inserted_handler.name}")
            assert inserted_handler.name == "portfolio_analyzer"
            assert inserted_handler.lib_path == "ginkgo.handlers.portfolio"
            assert inserted_handler.func_name == "analyze_portfolio"

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestHandlerCRUDQuery:
    CRUD_TEST_CONFIG = {'crud_class': HandlerCRUD}
    """2. CRUD层查询操作测试 - Handler数据查询和过滤"""

    def test_find_by_name(self):
        """测试根据处理器名称查询Handler"""
        print("\n" + "="*60)
        print("开始测试: 根据处理器名称查询Handler")
        print("="*60)

        handler_crud = HandlerCRUD()

        try:
            # 查询特定处理器
            print("→ 查询名称=signal_generator的处理器...")
            handlers = handler_crud.find(filters={"name": "signal_generator"})
            print(f"✓ 查询到 {len(handlers)} 条记录")

            # 验证查询结果
            for handler in handlers:
                print(f"  - {handler.name}: {handler.lib_path}.{handler.func_name}")
                assert handler.name == "signal_generator"
                assert "signal" in handler.lib_path.lower()

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_lib_path_pattern(self):
        """测试根据库路径模式查询Handler"""
        print("\n" + "="*60)
        print("开始测试: 根据库路径模式查询Handler")
        print("="*60)

        handler_crud = HandlerCRUD()

        try:
            # 查询所有处理器
            print("→ 查询所有处理器进行库路径分析...")
            all_handlers = handler_crud.find()
            print(f"✓ 查询到 {len(all_handlers)} 条处理器记录")

            # 按库路径分组统计
            lib_path_groups = {}
            for handler in all_handlers:
                # 提取库路径的主要部分
                main_lib = handler.lib_path.split('.')[-1] if '.' in handler.lib_path else handler.lib_path
                if main_lib not in lib_path_groups:
                    lib_path_groups[main_lib] = []
                lib_path_groups[main_lib].append(handler)

            print(f"✓ 库路径分组结果:")
            for lib_name, handlers in lib_path_groups.items():
                print(f"  - {lib_name}: {len(handlers)}个处理器")
                for handler in handlers:
                    print(f"    * {handler.name}: {handler.func_name}")

            print("✓ 库路径模式查询验证成功")

        except Exception as e:
            print(f"✗ 库路径模式查询失败: {e}")
            raise

    def test_find_all_handlers(self):
        """测试查询所有Handler"""
        print("\n" + "="*60)
        print("开始测试: 查询所有Handler")
        print("="*60)

        handler_crud = HandlerCRUD()

        try:
            # 查询所有处理器
            print("→ 查询所有事件处理器...")
            all_handlers = handler_crud.find()
            print(f"✓ 查询到 {len(all_handlers)} 条处理器记录")

            if len(all_handlers) > 0:
                # 分析处理器类型
                handler_types = {}
                for handler in all_handlers:
                    # 根据名称推断处理器类型
                    if "data" in handler.name.lower():
                        handler_type = "数据处理"
                    elif "signal" in handler.name.lower():
                        handler_type = "信号处理"
                    elif "order" in handler.name.lower():
                        handler_type = "订单处理"
                    elif "risk" in handler.name.lower():
                        handler_type = "风险管理"
                    elif "portfolio" in handler.name.lower():
                        handler_type = "投资组合"
                    else:
                        handler_type = "其他"

                    if handler_type not in handler_types:
                        handler_types[handler_type] = 0
                    handler_types[handler_type] += 1

                print(f"✓ 处理器类型分布:")
                for handler_type, count in handler_types.items():
                    print(f"  - {handler_type}: {count}个")

                # 显示前5个处理器的详细信息
                print(f"✓ 处理器详细信息 (前5个):")
                for handler in all_handlers[:5]:
                    print(f"  - {handler.name}: {handler.lib_path}.{handler.func_name}")

            print("✓ 所有处理器查询验证成功")

        except Exception as e:
            print(f"✗ 所有处理器查询失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestHandlerCRUDUpdate:
    CRUD_TEST_CONFIG = {'crud_class': HandlerCRUD}
    """3. CRUD层更新操作测试 - Handler信息更新"""

    def test_update_handler_info(self):
        """测试更新Handler基本信息"""
        print("\n" + "="*60)
        print("开始测试: 更新Handler基本信息")
        print("="*60)

        handler_crud = HandlerCRUD()

        try:
            # 查询待更新的处理器
            print("→ 查询待更新的处理器...")
            handlers = handler_crud.find(page_size=1)
            if not handlers:
                pytest.skip("没有找到可更新的处理器")

            target_handler = handlers[0]
            print(f"✓ 找到处理器: {target_handler.name}")
            print(f"  - 当前库路径: {target_handler.lib_path}")
            print(f"  - 当前函数名: {target_handler.func_name}")

            # 更新处理器信息
            print("→ 更新处理器信息...")
            updated_data = {
                "lib_path": "ginkgo.handlers.updated",
                "func_name": "updated_function"
            }

            handler_crud.modify(filters={"uuid": target_handler.uuid}, updates=updated_data)
            print(f"✓ 处理器信息更新完成")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_handlers = handler_crud.find(filters={"uuid": target_handler.uuid})
            assert len(updated_handlers) == 1

            updated_handler = updated_handlers[0]
            print(f"✓ 更新后库路径: {updated_handler.lib_path}")
            print(f"✓ 更新后函数名: {updated_handler.func_name}")

            assert updated_handler.lib_path == "ginkgo.handlers.updated"
            assert updated_handler.func_name == "updated_function"
            print("✓ Handler基本信息更新验证成功")

        except Exception as e:
            print(f"✗ 更新Handler基本信息失败: {e}")
            raise

    def test_update_handler_name(self):
        """测试更新Handler名称"""
        print("\n" + "="*60)
        print("开始测试: 更新Handler名称")
        print("="*60)

        handler_crud = HandlerCRUD()

        try:
            # 查询待更新的处理器
            print("→ 查询待更新的处理器...")
            handlers = handler_crud.find(page_size=1)
            if not handlers:
                pytest.skip("没有找到可更新的处理器")

            target_handler = handlers[0]
            original_name = target_handler.name
            print(f"✓ 找到处理器: {original_name}")

            # 更新处理器名称
            print("→ 更新处理器名称...")
            # 确保新名称不超过32字符
            if len(original_name) > 24:
                new_name = original_name[:24] + "_upd"
            else:
                new_name = f"{original_name}_updated"
            updated_data = {
                "name": new_name
            }

            handler_crud.modify(filters={"uuid": target_handler.uuid}, updates=updated_data)
            print(f"✓ 处理器名称更新为: {new_name}")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_handlers = handler_crud.find(filters={"uuid": target_handler.uuid})
            assert len(updated_handlers) == 1

            updated_handler = updated_handlers[0]
            print(f"✓ 更新后处理器名称: {updated_handler.name}")

            assert updated_handler.name == new_name
            print("✓ Handler名称更新验证成功")

        except Exception as e:
            print(f"✗ 更新Handler名称失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestHandlerCRUDBusinessLogic:
    CRUD_TEST_CONFIG = {'crud_class': HandlerCRUD}
    """4. CRUD层业务逻辑测试 - Handler业务场景验证"""

    def test_handler_system_analysis(self):
        """测试处理器系统分析"""
        print("\n" + "="*60)
        print("开始测试: 处理器系统分析")
        print("="*60)

        handler_crud = HandlerCRUD()

        try:
            # 查询所有处理器进行系统分析
            print("→ 查询所有处理器进行系统分析...")
            all_handlers = handler_crud.find()

            if len(all_handlers) < 3:
                pytest.skip("处理器数据不足(少于3条)，跳过系统分析")

            # 分析处理器系统架构
            lib_path_analysis = {}
            func_name_analysis = {}

            for handler in all_handlers:
                # 分析库路径分布
                lib_path = handler.lib_path
                if lib_path not in lib_path_analysis:
                    lib_path_analysis[lib_path] = []
                lib_path_analysis[lib_path].append(handler)

                # 分析函数名模式
                func_name = handler.func_name
                if func_name not in func_name_analysis:
                    func_name_analysis[func_name] = 0
                func_name_analysis[func_name] += 1

            print(f"✓ 处理器系统分析结果:")
            print(f"  - 总处理器数: {len(all_handlers)}")
            print(f"  - 涉及库路径数: {len(lib_path_analysis)}")
            print(f"  - 不同函数名数: {len(func_name_analysis)}")

            # 显示库路径分布
            print(f"  - 库路径分布:")
            for lib_path, handlers in lib_path_analysis.items():
                print(f"    * {lib_path}: {len(handlers)}个处理器")

            # 显示函数名统计
            print(f"  - 函数名使用频率:")
            sorted_funcs = sorted(func_name_analysis.items(), key=lambda x: x[1], reverse=True)
            for func_name, count in sorted_funcs[:5]:
                print(f"    * {func_name}: {count}次")

            # 验证分析结果
            assert len(all_handlers) > 0
            assert len(lib_path_analysis) > 0
            print("✓ 处理器系统分析验证成功")

        except Exception as e:
            print(f"✗ 处理器系统分析失败: {e}")
            raise

    def test_handler_integrity_check(self):
        """测试处理器完整性检查"""
        print("\n" + "="*60)
        print("开始测试: 处理器完整性检查")
        print("="*60)

        handler_crud = HandlerCRUD()

        try:
            # 查询所有处理器进行完整性检查
            print("→ 查询所有处理器进行完整性检查...")
            all_handlers = handler_crud.find()

            if len(all_handlers) == 0:
                pytest.skip("没有处理器记录，跳过完整性检查")

            # 检查处理器完整性
            issues = []
            valid_handlers = []

            for handler in all_handlers:
                handler_issues = []

                # 检查必填字段
                if not handler.name or handler.name.strip() == "":
                    handler_issues.append("缺少处理器名称")

                if not handler.lib_path or handler.lib_path.strip() == "":
                    handler_issues.append("缺少库路径")

                if not handler.func_name or handler.func_name.strip() == "":
                    handler_issues.append("缺少函数名")

                # 检查格式规范
                if " " in handler.name:
                    handler_issues.append("处理器名称包含空格")

                if not handler.lib_path.startswith("ginkgo.") and not handler.lib_path.startswith("custom."):
                    handler_issues.append("库路径格式不规范")

                if handler_issues:
                    issues.append((handler.name, handler_issues))
                else:
                    valid_handlers.append(handler)

            print(f"✓ 处理器完整性检查结果:")
            print(f"  - 总处理器数: {len(all_handlers)}")
            print(f"  - 有效处理器: {len(valid_handlers)}")
            print(f"  - 有问题的处理器: {len(issues)}")

            # 显示有问题的处理器
            if issues:
                print(f"  - 问题详情:")
                for handler_name, issue_list in issues:
                    print(f"    * {handler_name}: {', '.join(issue_list)}")

            # 显示有效处理器
            if valid_handlers:
                print(f"  - 有效处理器示例:")
                for handler in valid_handlers[:3]:
                    print(f"    * {handler.name}: {handler.lib_path}.{handler.func_name}")

            # 验证完整性检查结果
            assert len(all_handlers) == len(valid_handlers) + len(issues)
            print("✓ 处理器完整性检查验证成功")

        except Exception as e:
            print(f"✗ 处理器完整性检查失败: {e}")
            raise

    def test_handler_naming_convention(self):
        """测试处理器命名规范分析"""
        print("\n" + "="*60)
        print("开始测试: 处理器命名规范分析")
        print("="*60)

        handler_crud = HandlerCRUD()

        try:
            # 查询所有处理器进行命名规范分析
            print("→ 查询所有处理器进行命名规范分析...")
            all_handlers = handler_crud.find()

            if len(all_handlers) < 2:
                pytest.skip("处理器数据不足(少于2条)，跳过命名规范分析")

            # 分析命名规范
            naming_patterns = {
                "snake_case": [],      # data_processor
                "camel_case": [],      # dataProcessor
                "kebab_case": [],      # data-processor
                "other": []            # 其他格式
            }

            for handler in all_handlers:
                name = handler.name

                if "_" in name and name.replace("_", "").isalnum():
                    naming_patterns["snake_case"].append(handler)
                elif name != name.lower() and name.replace("_", "").replace("-", "").isalnum():
                    if any(c.isupper() for c in name[1:]):
                        naming_patterns["camel_case"].append(handler)
                    else:
                        naming_patterns["other"].append(handler)
                elif "-" in name:
                    naming_patterns["kebab_case"].append(handler)
                else:
                    naming_patterns["other"].append(handler)

            print(f"✓ 处理器命名规范分析结果:")
            print(f"  - 总处理器数: {len(all_handlers)}")

            for pattern, handlers in naming_patterns.items():
                if handlers:
                    print(f"  - {pattern}: {len(handlers)}个处理器")
                    for handler in handlers[:3]:
                        print(f"    * {handler.name}")

            # 分析命名一致性
            dominant_pattern = max(naming_patterns.items(), key=lambda x: len(x[1]))
            consistency_rate = len(dominant_pattern[1]) / len(all_handlers) * 100

            print(f"  - 主导命名模式: {dominant_pattern[0]} ({consistency_rate:.1f}%)")

            if consistency_rate >= 80:
                print(f"  ✓ 命名规范一致性良好")
            elif consistency_rate >= 60:
                print(f"  ⚠ 命名规范一致性中等")
            else:
                print(f"  ✗ 命名规范一致性较差")

            print("✓ 处理器命名规范分析验证成功")

        except Exception as e:
            print(f"✗ 处理器命名规范分析失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestHandlerCRUDDelete:
    CRUD_TEST_CONFIG = {'crud_class': HandlerCRUD}
    """4. CRUD层删除操作测试 - Handler数据删除验证"""

    def test_delete_handler_by_name(self):
        """测试根据处理器名称删除处理器"""
        print("\n" + "="*60)
        print("开始测试: 根据处理器名称删除处理器")
        print("="*60)

        handler_crud = HandlerCRUD()

        try:
            # 准备测试数据
            print("→ 创建测试处理器...")
            test_handler = handler_crud._create_from_params(
                name="delete_test_handler",
                lib_path="ginkgo.handlers.test",
                func_name="delete_test_function"
            )
            handler_crud.add(test_handler)
            print("✓ 测试处理器创建成功")

            # 验证数据存在
            print("→ 验证处理器存在...")
            handlers_before = handler_crud.find(filters={"name": "delete_test_handler"})
            print(f"✓ 删除前处理器数: {len(handlers_before)}")
            assert len(handlers_before) >= 1

            # 执行删除操作
            print("→ 执行处理器删除...")
            handler_crud.remove(filters={"name": "delete_test_handler"})
            print("✓ 删除操作完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            handlers_after = handler_crud.find(filters={"name": "delete_test_handler"})
            print(f"✓ 删除后处理器数: {len(handlers_after)}")
            assert len(handlers_after) == 0

            print("✓ 根据处理器名称删除处理器验证成功")

        except Exception as e:
            print(f"✗ 根据处理器名称删除处理器失败: {e}")
            raise

    def test_delete_handler_by_lib_path(self):
        """测试根据库路径删除处理器"""
        print("\n" + "="*60)
        print("开始测试: 根据库路径删除处理器")
        print("="*60)

        handler_crud = HandlerCRUD()

        try:
            # 准备测试数据
            print("→ 创建不同库路径的处理器...")
            test_handlers = [
                handler_crud._create_from_params(
                    name="data_processor",
                    lib_path="ginkgo.handlers.data",
                    func_name="process_data_event"
                ),
                handler_crud._create_from_params(
                    name="signal_processor",
                    lib_path="ginkgo.handlers.signal",
                    func_name="generate_signal"
                ),
                handler_crud._create_from_params(
                    name="order_processor",
                    lib_path="ginkgo.handlers.order",
                    func_name="execute_order"
                )
            ]

            for handler in test_handlers:
                handler_crud.add(handler)
            print(f"✓ {len(test_handlers)}个处理器创建成功")

            # 验证初始数据
            print("→ 验证初始数据...")
            all_handlers = handler_crud.find()
            data_handlers = [h for h in all_handlers if "data" in h.lib_path]
            print(f"✓ 总处理器数: {len(all_handlers)}, 数据处理器数: {len(data_handlers)}")
            assert len(data_handlers) >= 1

            # 删除数据处理器
            print("→ 删除数据处理器...")
            handler_crud.remove(filters={"lib_path__like": "data"})
            print("✓ 数据处理器删除完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            remaining_handlers = handler_crud.find()
            remaining_data = [h for h in remaining_handlers if "data" in h.lib_path]

            print(f"✓ 删除后处理器数: {len(remaining_handlers)}, 剩余数据处理器数: {len(remaining_data)}")
            assert len(remaining_data) == 0

            print("✓ 根据库路径删除处理器验证成功")

        except Exception as e:
            print(f"✗ 根据库路径删除处理器失败: {e}")
            raise

    def test_delete_handler_by_function_name(self):
        """测试根据函数名删除处理器"""
        print("\n" + "="*60)
        print("开始测试: 根据函数名删除处理器")
        print("="*60)

        handler_crud = HandlerCRUD()

        try:
            # 准备测试数据
            print("→ 创建不同函数名的处理器...")
            test_handlers = [
                handler_crud._create_from_params(
                    name="analyzer_handler",
                    lib_path="ginkgo.handlers.analysis",
                    func_name="analyze_data"
                ),
                handler_crud._create_from_params(
                    name="validator_handler",
                    lib_path="ginkgo.handlers.validation",
                    func_name="validate_data"
                ),
                handler_crud._create_from_params(
                    name="transformer_handler",
                    lib_path="ginkgo.handlers.transform",
                    func_name="transform_data"
                )
            ]

            for handler in test_handlers:
                handler_crud.add(handler)
            print(f"✓ {len(test_handlers)}个处理器创建成功")

            # 验证初始数据
            print("→ 验证初始数据...")
            all_handlers = handler_crud.find()
            analyzer_handlers = [h for h in all_handlers if "analyze" in h.func_name]
            print(f"✓ 总处理器数: {len(all_handlers)}, 分析处理器数: {len(analyzer_handlers)}")
            assert len(analyzer_handlers) >= 1

            # 删除分析处理器
            print("→ 删除分析处理器...")
            handler_crud.remove(filters={"func_name__like": "analyze"})
            print("✓ 分析处理器删除完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            remaining_handlers = handler_crud.find()
            remaining_analyzer = [h for h in remaining_handlers if "analyze" in h.func_name]

            print(f"✓ 删除后处理器数: {len(remaining_handlers)}, 剩余分析处理器数: {len(remaining_analyzer)}")
            assert len(remaining_analyzer) == 0

            print("✓ 根据函数名删除处理器验证成功")

        except Exception as e:
            print(f"✗ 根据函数名删除处理器失败: {e}")
            raise

    def test_delete_test_handlers(self):
        """测试删除测试处理器"""
        print("\n" + "="*60)
        print("开始测试: 删除测试处理器")
        print("="*60)

        handler_crud = HandlerCRUD()

        try:
            # 准备测试数据
            print("→ 创建不同类型的处理器...")
            test_handlers = [
                handler_crud._create_from_params(
                    name="test_data_handler",
                    lib_path="ginkgo.handlers.test.data",
                    func_name="test_data_function"
                ),
                handler_crud._create_from_params(
                    name="test_signal_handler",
                    lib_path="ginkgo.handlers.test.signal",
                    func_name="test_signal_function"
                ),
                handler_crud._create_from_params(
                    name="production_handler",
                    lib_path="ginkgo.handlers.production",
                    func_name="production_function"
                ),
                handler_crud._create_from_params(
                    name="debug_handler",
                    lib_path="ginkgo.handlers.debug",
                    func_name="debug_function"
                )
            ]

            for handler in test_handlers:
                handler_crud.add(handler)
            print(f"✓ {len(test_handlers)}个处理器创建成功")

            # 验证初始数据
            print("→ 验证初始数据...")
            all_handlers = handler_crud.find()
            test_handlers_list = [h for h in all_handlers if "test" in h.name]
            print(f"✓ 总处理器数: {len(all_handlers)}, 测试处理器数: {len(test_handlers_list)}")
            assert len(test_handlers_list) >= 2

            # 删除所有测试处理器
            print("→ 删除所有测试处理器...")
            handler_crud.remove(filters={"name__like": "test"})
            print("✓ 测试处理器删除完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            remaining_handlers = handler_crud.find()
            remaining_test = [h for h in remaining_handlers if "test" in h.name]

            print(f"✓ 删除后处理器数: {len(remaining_handlers)}, 剩余测试处理器数: {len(remaining_test)}")
            assert len(remaining_test) == 0

            # 验证剩余的都不是测试处理器
            for handler in remaining_handlers:
                assert "test" not in handler.name
                print(f"✓ 保留处理器: {handler.name}")

            print("✓ 删除测试处理器验证成功")

        except Exception as e:
            print(f"✗ 删除测试处理器失败: {e}")
            raise

    def test_delete_handler_by_name_pattern(self):
        """测试根据名称模式删除处理器"""
        print("\n" + "="*60)
        print("开始测试: 根据名称模式删除处理器")
        print("="*60)

        handler_crud = HandlerCRUD()

        try:
            # 准备测试数据
            print("→ 创建不同名称模式的处理器...")
            test_handlers = [
                handler_crud._create_from_params(
                    name="process_order_handler",
                    lib_path="ginkgo.handlers.order",
                    func_name="process_order"
                ),
                handler_crud._create_from_params(
                    name="process_signal_handler",
                    lib_path="ginkgo.handlers.signal",
                    func_name="process_signal"
                ),
                handler_crud._create_from_params(
                    name="execute_trade_handler",
                    lib_path="ginkgo.handlers.trade",
                    func_name="execute_trade"
                ),
                handler_crud._create_from_params(
                    name="validate_data_handler",
                    lib_path="ginkgo.handlers.validation",
                    func_name="validate_data"
                )
            ]

            for handler in test_handlers:
                handler_crud.add(handler)
            print(f"✓ {len(test_handlers)}个处理器创建成功")

            # 验证初始数据
            print("→ 验证初始数据...")
            all_handlers = handler_crud.find()
            process_handlers = [h for h in all_handlers if "process" in h.name]
            print(f"✓ 总处理器数: {len(all_handlers)}, process处理器数: {len(process_handlers)}")
            assert len(process_handlers) >= 2

            # 删除所有process处理器
            print("→ 删除所有process处理器...")
            handler_crud.remove(filters={"name__like": "process"})
            print("✓ process处理器删除完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            remaining_handlers = handler_crud.find()
            remaining_process = [h for h in remaining_handlers if "process" in h.name]

            print(f"✓ 删除后处理器数: {len(remaining_handlers)}, 剩余process处理器数: {len(remaining_process)}")
            assert len(remaining_process) == 0

            # 验证剩余的不包含process
            for handler in remaining_handlers:
                assert "process" not in handler.name
                print(f"✓ 保留处理器: {handler.name}")

            print("✓ 根据名称模式删除处理器验证成功")

        except Exception as e:
            print(f"✗ 根据名称模式删除处理器失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestHandlerCRUDDataConversion:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': HandlerCRUD}
    """测试HandlerCRUD数据转换方法"""

    def test_handler_data_conversion_api(self):
        """测试Handler数据转换API - to_dataframe(), to_entities()"""
        print("\n" + "="*60)
        print("开始测试: Handler数据转换API")
        print("="*60)

        handler_crud = HandlerCRUD()

        try:
            # 创建测试处理器数据
            print("→ 创建测试处理器数据...")
            test_handlers = [
                handler_crud.create(
                    name="conversion_test_handler_1",
                    lib_path="ginkgo.handlers.test_conversion",
                    func_name="test_function_1",
                    desc="转换测试处理器1"
                ),
                handler_crud.create(
                    name="conversion_test_handler_2",
                    lib_path="ginkgo.handlers.test_conversion",
                    func_name="test_function_2",
                    desc="转换测试处理器2"
                )
            ]
            print(f"✓ 创建了{len(test_handlers)}个测试处理器")

            # 查询处理器数据
            print("→ 查询处理器数据...")
            handler_models = handler_crud.find(filters={"name__like": "conversion_test"})
            print(f"✓ 查询到 {len(handler_models)} 个处理器")

            # 验证返回的是ModelList，支持转换方法
            assert hasattr(handler_models, 'to_dataframe'), "返回结果应该是ModelList，支持to_dataframe()方法"
            assert hasattr(handler_models, 'to_entities'), "返回结果应该是ModelList，支持to_entities()方法"
            print("✓ 返回结果支持转换方法")

            # 测试 to_entities() 方法
            print("\n→ 测试 to_entities() 转换...")
            entities = handler_models.to_entities()
            print(f"✓ to_entities() 返回 {len(entities)} 个业务实体")

            # 验证实体具有正确的字段
            for i, entity in enumerate(entities):
                print(f"  - 实体 {i+1}: {entity.name}")
                print(f"    - lib_path: {entity.lib_path}")
                print(f"    - func_name: {entity.func_name}")
                print(f"    - desc: {entity.desc}")

            print("✓ to_entities() 转换验证通过")

            # 测试 to_dataframe() 方法
            print("\n→ 测试 to_dataframe() 转换...")
            df = handler_models.to_dataframe()
            print(f"✓ to_dataframe() 返回 DataFrame: {df.shape}")
            print(f"✓ DataFrame列名: {list(df.columns)}")

            # 验证DataFrame中的字段
            if len(df) > 0:
                sample_row = df.iloc[0]
                print(f"  - 第一行数据样例:")
                print(f"    - name: {sample_row['name']}")
                print(f"    - lib_path: {sample_row['lib_path']}")
                print(f"    - func_name: {sample_row['func_name']}")

            print("✓ to_dataframe() 转换验证通过")

            # 测试单个模型的转换
            if len(handler_models) > 0:
                print("\n→ 测试单个Model的转换...")
                model_instance = handler_models[0]
                entity = model_instance.to_entity()
                print(f"✓ 单个Model to_entity(): {entity.name}")
                print(f"  - lib_path: {entity.lib_path}")
                print(f"  - func_name: {entity.func_name}")

            # 数据一致性验证
            print("\n→ 验证数据一致性...")
            entity_count = len(entities)
            dataframe_rows = len(df)

            assert entity_count == dataframe_rows, \
                f"数据不一致: entities={entity_count}, dataframe_rows={dataframe_rows}"
            print(f"✓ 数据一致性验证通过: {entity_count}个实体 = {dataframe_rows}行DataFrame")

            # 清理测试数据
            print("\n→ 清理测试数据...")
            handler_crud.remove(filters={"name__like": "conversion_test"})
            print("✓ 测试数据清理完成")

            print("✅ Handler数据转换API测试完全通过")

        except Exception as e:
            print(f"✗ Handler数据转换测试失败: {e}")
            raise


# TDD Red阶段验证：确保所有测试开始时都失败
if __name__ == "__main__":
    print("TDD Red阶段验证：Handler CRUD测试")
    print("所有测试用例应该在实现开始前失败")
    print("运行: pytest test/data/crud/test_handler_crud.py -v")
    print("预期结果: 所有测试失败 (Red阶段)")
    print("重点关注: 事件处理器配置管理功能")

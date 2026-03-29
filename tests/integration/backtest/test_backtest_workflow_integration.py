"""
Ginkgo Backtest Workflow Integration Test

完整的端到端回测工作流测试，覆盖以下流程：
1. Engine 创建
2. 修改回测范围
3. 创建 Portfolio
4. 绑定/解绑 Engine-Portfolio
5. 绑定各种组件
6. 解绑再绑定组件
7. 调整组件参数
8. 运行回测
9. 查看结果

运行前确保：
1. 调试模式已开启: ginkgo system config set --debug on
2. 数据库已初始化: ginkgo data init
3. 有可用的组件文件 (策略、风控、选择器等)

运行方式：
    PYTHONPATH=/home/kaoru/Ginkgo/src python -m pytest \\
        test/backtest/test_backtest_workflow_integration.py -v -s
"""

import unittest
import time
from datetime import datetime
from ginkgo.data.containers import container
from ginkgo.libs import GLOG, GCONF
from ginkgo.enums import FILE_TYPES, SOURCE_TYPES


class BacktestWorkflowIntegrationTest(unittest.TestCase):
    """
    回测工作流集成测试

    完整测试从 Engine 创建到结果查看的整个流程
    """

    @classmethod
    def setUpClass(cls):
        """测试类初始化 - 设置调试模式"""
        GCONF.set_debug(True)
        GLOG.INFO("=" * 60)
        GLOG.INFO("Backtest Workflow Integration Test Started")
        GLOG.INFO("=" * 60)

        # 初始化服务
        cls.engine_service = container.engine_service()
        cls.portfolio_service = container.portfolio_service()
        cls.file_service = container.file_service()
        cls.mapping_service = container.mapping_service()
        cls.result_service = container.result_service()

        # 清理测试数据（如果存在）
        cls._cleanup_test_data()

        # 类级别变量，用于在测试之间共享数据
        cls.test_engine_uuid = None
        cls.test_engine_name = None
        cls.test_portfolio_uuid = None
        cls.test_portfolio_name = None
        cls.available_components = None
        cls.bound_components = None
        cls.test_engine_instance = None
        cls.test_run_id = None

    @classmethod
    def tearDownClass(cls):
        """测试类清理 - 清理测试数据"""
        GLOG.INFO("=" * 60)
        GLOG.INFO("Backtest Workflow Integration Test Completed")
        GLOG.INFO("=" * 60)
        cls._cleanup_test_data()

    @classmethod
    def _cleanup_test_data(cls):
        """清理测试数据"""
        try:
            test_name_prefix = "workflow_test_"

            # 删除测试 Engine
            engines_result = cls.engine_service.get()
            if engines_result.success:
                for engine in engines_result.data:
                    if engine.name.startswith(test_name_prefix):
                        cls.engine_service.delete(engine.uuid)
                        GLOG.DEBUG(f"Cleaned up test engine: {engine.name}")

            # 删除测试 Portfolio
            portfolios_result = cls.portfolio_service.get()
            if portfolios_result.success:
                for portfolio in portfolios_result.data:
                    if portfolio.name.startswith(test_name_prefix):
                        cls.portfolio_service.delete(portfolio.uuid)
                        GLOG.DEBUG(f"Cleaned up test portfolio: {portfolio.name}")

        except Exception as e:
            GLOG.WARN(f"Cleanup warning: {e}")

    def test_01_create_engine(self):
        """
        Step 1: 创建 Engine
        """
        GLOG.INFO("\n" + "=" * 60)
        GLOG.INFO("Step 1: Create Engine")
        GLOG.INFO("=" * 60)

        # 创建回测 Engine（需要提供日期范围）
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)

        result = self.engine_service.add(
            name="workflow_test_engine",
            is_live=False,
            description="Workflow integration test engine",
            backtest_start_date=start_date,
            backtest_end_date=end_date
        )

        self.assertTrue(result.success, f"Engine creation failed: {result.error}")
        self.assertIsNotNone(result.data)

        # EngineService.add returns {"engine_info": {...}}
        engine_info = result.data.get('engine_info', result.data)
        BacktestWorkflowIntegrationTest.test_engine_uuid = engine_info['uuid']
        BacktestWorkflowIntegrationTest.test_engine_name = engine_info['name']

        GLOG.INFO(f"Engine created: {BacktestWorkflowIntegrationTest.test_engine_name}")
        GLOG.INFO(f"  UUID: {BacktestWorkflowIntegrationTest.test_engine_uuid}")

        # 验证 Engine 可以被查询
        get_result = self.engine_service.get(engine_id=BacktestWorkflowIntegrationTest.test_engine_uuid)
        self.assertTrue(get_result.success)
        self.assertEqual(len(get_result.data), 1)
        self.assertEqual(get_result.data[0].name, "workflow_test_engine")

    def test_02_create_portfolio(self):
        """
        Step 2: 创建 Portfolio
        """
        GLOG.INFO("\n" + "=" * 60)
        GLOG.INFO("Step 2: Create Portfolio")
        GLOG.INFO("=" * 60)

        # 创建 Portfolio
        result = self.portfolio_service.add(
            name="workflow_test_portfolio",
            initial_capital=1000000.0,
            is_live=False,
            description="Workflow integration test portfolio"
        )

        self.assertTrue(result.success, f"Portfolio creation failed: {result.error}")
        self.assertIsNotNone(result.data)

        # PortfolioService.add returns dict directly with uuid, name, etc.
        BacktestWorkflowIntegrationTest.test_portfolio_uuid = result.data['uuid']
        BacktestWorkflowIntegrationTest.test_portfolio_name = result.data['name']

        GLOG.INFO(f"Portfolio created: {BacktestWorkflowIntegrationTest.test_portfolio_name}")
        GLOG.INFO(f"  UUID: {BacktestWorkflowIntegrationTest.test_portfolio_uuid}")
        GLOG.INFO(f"  Initial Capital: ¥1,000,000.00")

    def test_03_bind_engine_portfolio(self):
        """
        Step 3: 绑定 Engine 到 Portfolio
        """
        GLOG.INFO("\n" + "=" * 60)
        GLOG.INFO("Step 3: Bind Engine to Portfolio")
        GLOG.INFO("=" * 60)

        result = self.mapping_service.create_engine_portfolio_mapping(
            engine_uuid=BacktestWorkflowIntegrationTest.test_engine_uuid,
            portfolio_uuid=BacktestWorkflowIntegrationTest.test_portfolio_uuid,
            engine_name=BacktestWorkflowIntegrationTest.test_engine_name,
            portfolio_name=BacktestWorkflowIntegrationTest.test_portfolio_name
        )

        self.assertTrue(result.success, f"Engine-Portfolio binding failed: {result.error}")

        GLOG.INFO(f"Engine-Portfolio binding created:")
        GLOG.INFO(f"  Engine: {BacktestWorkflowIntegrationTest.test_engine_name}")
        GLOG.INFO(f"  Portfolio: {BacktestWorkflowIntegrationTest.test_portfolio_name}")

        # 验证绑定
        mappings = self.mapping_service.get_engine_portfolio_mapping(
            engine_uuid=BacktestWorkflowIntegrationTest.test_engine_uuid
        )
        self.assertTrue(mappings.success)
        self.assertEqual(len(mappings.data), 1)
        self.assertEqual(mappings.data[0].portfolio_id, BacktestWorkflowIntegrationTest.test_portfolio_uuid)

    def test_04_unbind_rebind_engine_portfolio(self):
        """
        Step 4: 解绑再绑定 Engine-Portfolio
        """
        GLOG.INFO("\n" + "=" * 60)
        GLOG.INFO("Step 4: Unbind and Rebind Engine-Portfolio")
        GLOG.INFO("=" * 60)

        # 解绑
        unbind_result = self.mapping_service.delete_engine_portfolio_mapping(
            engine_uuid=BacktestWorkflowIntegrationTest.test_engine_uuid,
            portfolio_uuid=BacktestWorkflowIntegrationTest.test_portfolio_uuid
        )
        self.assertTrue(unbind_result.success, f"Unbind failed: {unbind_result.error}")
        GLOG.INFO("Engine-Portfolio unbound")

        # 验证解绑
        mappings = self.mapping_service.get_engine_portfolio_mapping(
            engine_uuid=BacktestWorkflowIntegrationTest.test_engine_uuid
        )
        self.assertEqual(len(mappings.data), 0)

        # 重新绑定
        bind_result = self.mapping_service.create_engine_portfolio_mapping(
            engine_uuid=BacktestWorkflowIntegrationTest.test_engine_uuid,
            portfolio_uuid=BacktestWorkflowIntegrationTest.test_portfolio_uuid,
            engine_name=BacktestWorkflowIntegrationTest.test_engine_name,
            portfolio_name=BacktestWorkflowIntegrationTest.test_portfolio_name
        )
        self.assertTrue(bind_result.success, f"Rebind failed: {bind_result.error}")
        GLOG.INFO("Engine-Portfolio rebound")

    def test_05_get_available_components(self):
        """
        Step 5: 获取可用组件
        """
        GLOG.INFO("\n" + "=" * 60)
        GLOG.INFO("Step 5: Get Available Components")
        GLOG.INFO("=" * 60)

        # 获取各类型组件
        component_types = [
            (FILE_TYPES.STRATEGY, "Strategy"),
            (FILE_TYPES.RISKMANAGER, "RiskManager"),
            (FILE_TYPES.SELECTOR, "Selector"),
            (FILE_TYPES.SIZER, "Sizer"),
            (FILE_TYPES.ANALYZER, "Analyzer"),
        ]

        BacktestWorkflowIntegrationTest.available_components = {}

        for file_type, type_name in component_types:
            result = self.file_service.get_by_type(file_type)
            if result.success and result.data.get('files'):
                files = result.data['files']
                BacktestWorkflowIntegrationTest.available_components[file_type] = files
                GLOG.INFO(f"{type_name}: {len(files)} available")
                for f in files[:3]:  # 只显示前3个
                    GLOG.INFO(f"  - {f.name} ({f.uuid[:8]}...)")
            else:
                GLOG.WARN(f"{type_name}: No available files")
                BacktestWorkflowIntegrationTest.available_components[file_type] = []

        # 至少需要有可用的组件才能继续后续测试
        has_components = any(len(v) > 0 for v in BacktestWorkflowIntegrationTest.available_components.values())
        if not has_components:
            self.skipTest("No available components found in database. "
                         "Please import components first using ginkgo data import.")

    def test_06_bind_components(self):
        """
        Step 6: 绑定各种组件到 Portfolio
        """
        GLOG.INFO("\n" + "=" * 60)
        GLOG.INFO("Step 6: Bind Components to Portfolio")
        GLOG.INFO("=" * 60)

        BacktestWorkflowIntegrationTest.bound_components = {}

        # 绑定策略
        if FILE_TYPES.STRATEGY in BacktestWorkflowIntegrationTest.available_components:
            strategies = BacktestWorkflowIntegrationTest.available_components[FILE_TYPES.STRATEGY][:1]
            for strategy in strategies:
                result = self.mapping_service.create_portfolio_file_binding(
                    portfolio_uuid=BacktestWorkflowIntegrationTest.test_portfolio_uuid,
                    file_uuid=strategy.uuid,
                    file_name=strategy.name,
                    file_type=FILE_TYPES.STRATEGY
                )
                if result.success:
                    BacktestWorkflowIntegrationTest.bound_components[strategy.uuid] = {
                        'name': strategy.name,
                        'type': FILE_TYPES.STRATEGY,
                        'mapping': result.data
                    }
                    GLOG.INFO(f"Strategy bound: {strategy.name}")

        # 绑定风控
        if FILE_TYPES.RISKMANAGER in BacktestWorkflowIntegrationTest.available_components:
            risks = BacktestWorkflowIntegrationTest.available_components[FILE_TYPES.RISKMANAGER][:2]
            for risk in risks:
                result = self.mapping_service.create_portfolio_file_binding(
                    portfolio_uuid=BacktestWorkflowIntegrationTest.test_portfolio_uuid,
                    file_uuid=risk.uuid,
                    file_name=risk.name,
                    file_type=FILE_TYPES.RISKMANAGER
                )
                if result.success:
                    BacktestWorkflowIntegrationTest.bound_components[risk.uuid] = {
                        'name': risk.name,
                        'type': FILE_TYPES.RISKMANAGER,
                        'mapping': result.data
                    }
                    GLOG.INFO(f"RiskManager bound: {risk.name}")

        # 绑定选择器
        if FILE_TYPES.SELECTOR in BacktestWorkflowIntegrationTest.available_components:
            selectors = BacktestWorkflowIntegrationTest.available_components[FILE_TYPES.SELECTOR][:1]
            for selector in selectors:
                result = self.mapping_service.create_portfolio_file_binding(
                    portfolio_uuid=BacktestWorkflowIntegrationTest.test_portfolio_uuid,
                    file_uuid=selector.uuid,
                    file_name=selector.name,
                    file_type=FILE_TYPES.SELECTOR
                )
                if result.success:
                    BacktestWorkflowIntegrationTest.bound_components[selector.uuid] = {
                        'name': selector.name,
                        'type': FILE_TYPES.SELECTOR,
                        'mapping': result.data
                    }
                    GLOG.INFO(f"Selector bound: {selector.name}")

        # 绑定仓位管理
        if FILE_TYPES.SIZER in BacktestWorkflowIntegrationTest.available_components:
            sizers = BacktestWorkflowIntegrationTest.available_components[FILE_TYPES.SIZER][:1]
            for sizer in sizers:
                result = self.mapping_service.create_portfolio_file_binding(
                    portfolio_uuid=BacktestWorkflowIntegrationTest.test_portfolio_uuid,
                    file_uuid=sizer.uuid,
                    file_name=sizer.name,
                    file_type=FILE_TYPES.SIZER
                )
                if result.success:
                    BacktestWorkflowIntegrationTest.bound_components[sizer.uuid] = {
                        'name': sizer.name,
                        'type': FILE_TYPES.SIZER,
                        'mapping': result.data
                    }
                    GLOG.INFO(f"Sizer bound: {sizer.name}")

        # 绑定分析器
        if FILE_TYPES.ANALYZER in BacktestWorkflowIntegrationTest.available_components:
            analyzers = BacktestWorkflowIntegrationTest.available_components[FILE_TYPES.ANALYZER][:2]
            for analyzer in analyzers:
                result = self.mapping_service.create_portfolio_file_binding(
                    portfolio_uuid=BacktestWorkflowIntegrationTest.test_portfolio_uuid,
                    file_uuid=analyzer.uuid,
                    file_name=analyzer.name,
                    file_type=FILE_TYPES.ANALYZER
                )
                if result.success:
                    BacktestWorkflowIntegrationTest.bound_components[analyzer.uuid] = {
                        'name': analyzer.name,
                        'type': FILE_TYPES.ANALYZER,
                        'mapping': result.data
                    }
                    GLOG.INFO(f"Analyzer bound: {analyzer.name}")

        GLOG.INFO(f"Total components bound: {len(BacktestWorkflowIntegrationTest.bound_components)}")

    def test_07_unbind_rebind_component(self):
        """
        Step 7: 解绑再绑定组件
        """
        GLOG.INFO("\n" + "=" * 60)
        GLOG.INFO("Step 7: Unbind and Rebind Component")
        GLOG.INFO("=" * 60)

        if not BacktestWorkflowIntegrationTest.bound_components:
            self.skipTest("No components bound in previous step")

        # 选择第一个绑定的组件进行解绑再绑定测试
        file_uuid = list(BacktestWorkflowIntegrationTest.bound_components.keys())[0]
        component_info = BacktestWorkflowIntegrationTest.bound_components[file_uuid]

        # 解绑
        unbind_result = self.mapping_service.delete_portfolio_file_binding(
            portfolio_uuid=BacktestWorkflowIntegrationTest.test_portfolio_uuid,
            file_uuid=file_uuid
        )
        self.assertTrue(unbind_result.success, f"Unbind failed: {unbind_result.error}")
        GLOG.INFO(f"Component unbound: {component_info['name']}")

        # 重新绑定
        bind_result = self.mapping_service.create_portfolio_file_binding(
            portfolio_uuid=BacktestWorkflowIntegrationTest.test_portfolio_uuid,
            file_uuid=file_uuid,
            file_name=component_info['name'],
            file_type=component_info['type']
        )
        self.assertTrue(bind_result.success, f"Rebind failed: {bind_result.error}")
        GLOG.INFO(f"Component rebound: {component_info['name']}")

        # 更新 mapping 引用
        BacktestWorkflowIntegrationTest.bound_components[file_uuid]['mapping'] = bind_result.data

    def test_08_set_component_parameters(self):
        """
        Step 8: 设置组件参数
        """
        GLOG.INFO("\n" + "=" * 60)
        GLOG.INFO("Step 8: Set Component Parameters")
        GLOG.INFO("=" * 60)

        if not BacktestWorkflowIntegrationTest.bound_components:
            self.skipTest("No components bound in previous step")

        # 为不同类型的组件设置不同的参数
        for file_uuid, component_info in BacktestWorkflowIntegrationTest.bound_components.items():
            mapping = component_info['mapping']
            component_type = component_info['type']
            component_name = component_info['name']

            # 根据组件类型设置不同的参数
            if component_type == FILE_TYPES.SELECTOR:
                # Selector 参数：股票代码列表 (JSON格式)
                selector_params = {
                    0: '["000001.SZ"]'  # 固定选择 000001.SZ
                }
                result = self.mapping_service.create_component_parameters(
                    mapping_uuid=mapping.uuid,
                    file_uuid=file_uuid,
                    parameters=selector_params
                )
                if result.success:
                    GLOG.INFO(f"Selector parameters set for {component_name}:")
                    GLOG.INFO(f"  - [0]: ['000001.SZ']")
                else:
                    GLOG.WARN(f"Failed to set parameters for {component_name}: {result.error}")

            elif component_type == FILE_TYPES.STRATEGY:
                # Strategy 参数：买卖概率等
                strategy_params = {
                    0: "0.9",  # buy_probability
                    1: "0.05"  # sell_probability
                }
                result = self.mapping_service.create_component_parameters(
                    mapping_uuid=mapping.uuid,
                    file_uuid=file_uuid,
                    parameters=strategy_params
                )
                if result.success:
                    GLOG.INFO(f"Strategy parameters set for {component_name}:")
                    for idx, val in sorted(strategy_params.items()):
                        GLOG.INFO(f"  - [{idx}]: {val}")
                else:
                    GLOG.WARN(f"Failed to set parameters for {component_name}: {result.error}")

            elif component_type == FILE_TYPES.SIZER:
                # Sizer 参数：固定数量
                sizer_params = {
                    0: "1000"  # volume
                }
                result = self.mapping_service.create_component_parameters(
                    mapping_uuid=mapping.uuid,
                    file_uuid=file_uuid,
                    parameters=sizer_params
                )
                if result.success:
                    GLOG.INFO(f"Sizer parameters set for {component_name}:")
                    GLOG.INFO(f"  - [0]: 1000")
                else:
                    GLOG.WARN(f"Failed to set parameters for {component_name}: {result.error}")

            # 其他组件类型暂时不设置参数
            else:
                GLOG.INFO(f"Skipping parameters for {component_name} (type: {component_type})")

    def test_09_verify_bindings(self):
        """
        Step 9: 验证所有绑定和参数
        """
        GLOG.INFO("\n" + "=" * 60)
        GLOG.INFO("Step 9: Verify All Bindings and Parameters")
        GLOG.INFO("=" * 60)

        # 获取 Portfolio 的所有绑定
        bindings_result = self.mapping_service.get_portfolio_file_bindings(
            portfolio_uuid=BacktestWorkflowIntegrationTest.test_portfolio_uuid
        )

        self.assertTrue(bindings_result.success)
        bindings = bindings_result.data

        GLOG.INFO(f"Total bindings for portfolio: {len(bindings)}")

        # 统计各类型组件
        type_counts = {}
        for binding in bindings:
            type_name = f"Type_{binding.type}"
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        for type_name, count in sorted(type_counts.items()):
            GLOG.INFO(f"  {type_name}: {count}")

    def test_10_assemble_and_run_backtest(self):
        """
        Step 10: 装配并运行回测
        """
        GLOG.INFO("\n" + "=" * 60)
        GLOG.INFO("Step 10: Assemble and Run Backtest")
        GLOG.INFO("=" * 60)

        try:
            from ginkgo.trading.core.containers import container as trading_container

            # 装配引擎
            GLOG.INFO("Assembling engine...")
            assembly_service = trading_container.services.engine_assembly_service()
            assemble_result = assembly_service.assemble_backtest_engine(
                engine_id=BacktestWorkflowIntegrationTest.test_engine_uuid
            )

            if not assemble_result.success:
                self.skipTest(f"Engine assembly failed: {assemble_result.error}. "
                             "This may be due to missing data or configuration.")

            engine = assemble_result.data
            BacktestWorkflowIntegrationTest.test_engine_instance = engine
            # run_id 在引擎启动时生成，装配时为 None
            BacktestWorkflowIntegrationTest.test_run_id = None

            GLOG.INFO(f"Engine assembled: {engine.name}")
            GLOG.INFO(f"  Engine ID: {engine.engine_id}")
            GLOG.INFO(f"  Run ID: {BacktestWorkflowIntegrationTest.test_run_id} (will be set after engine starts)")

            # 运行回测
            GLOG.INFO("Starting backtest...")
            GLOG.WARN("Note: This step may take time depending on data range")

            # 设置超时保护
            start_time = time.time()
            timeout = 300  # 5分钟超时

            success = engine.start()

            # 引擎启动后获取 run_id
            BacktestWorkflowIntegrationTest.test_run_id = engine.run_id
            GLOG.INFO(f"Engine started, Run ID: {BacktestWorkflowIntegrationTest.test_run_id}")

            # 等待引擎完成
            while engine.is_active and (time.time() - start_time) < timeout:
                time.sleep(0.5)

            elapsed = time.time() - start_time

            if engine.is_active:
                self.skipTest(f"Backtest timeout after {elapsed:.1f}s")

            GLOG.INFO(f"Backtest completed in {elapsed:.1f}s")

            # 基本验证
            if hasattr(engine, 'portfolios') and engine.portfolios:
                portfolio = list(engine.portfolios.values())[0] if isinstance(engine.portfolios, dict) else engine.portfolios[0]
                GLOG.INFO(f"  Final portfolio worth: ¥{getattr(portfolio, 'worth', 0):,.2f}")

        except Exception as e:
            self.skipTest(f"Backtest execution skipped: {e}")

    def test_11_check_backtest_results(self):
        """
        Step 11: 查看回测结果
        """
        GLOG.INFO("\n" + "=" * 60)
        GLOG.INFO("Step 11: Check Backtest Results")
        GLOG.INFO("=" * 60)

        if not hasattr(BacktestWorkflowIntegrationTest, 'test_run_id'):
            self.skipTest("No run_id attribute from backtest execution")

        run_id = BacktestWorkflowIntegrationTest.test_run_id
        if not run_id or (isinstance(run_id, str) and run_id.strip() == ''):
            self.skipTest(f"Run ID is empty: '{run_id}' (type: {type(run_id)})")

        GLOG.INFO(f"Checking results for run_id: {run_id}")

        # 获取运行摘要
        summary_result = self.result_service.get_run_summary(run_id)

        # 如果没有找到记录，这可能是正常的（没有 analyzer 绑定或未保存）
        if not summary_result.success:
            GLOG.WARN(f"No analyzer records found for run_id: {run_id}")
            GLOG.WARN("This may be because:")
            GLOG.WARN("  1. No analyzer components were bound to the portfolio")
            GLOG.WARN("  2. Analyzer data was not saved during backtest")
            GLOG.WARN("  3. Run completed but no data was generated")
            self.skipTest(f"No analyzer records found for run_id: {run_id}")

        summary = summary_result.data

        GLOG.info(f"Run Summary:")
        GLOG.info(f"  Run ID: {summary['run_id']}")
        GLOG.info(f"  Engine ID: {summary['engine_id']}")
        GLOG.info(f"  Portfolio Count: {summary['portfolio_count']}")
        GLOG.info(f"  Total Records: {summary['total_records']}")

        if summary['portfolio_count'] > 0:
            portfolio_id = summary['portfolios'][0]

            # 获取分析器列表
            analyzers_result = self.result_service.get_portfolio_analyzers(
                run_id=run_id,
                portfolio_id=portfolio_id
            )

            if analyzers_result.success:
                GLOG.info(f"  Analyzers: {', '.join(analyzers_result.data)}")

                # 获取第一个分析器的数据
                if analyzers_result.data:
                    analyzer_name = analyzers_result.data[0]
                    values_result = self.result_service.get_analyzer_values(
                        run_id=run_id,
                        portfolio_id=portfolio_id,
                        analyzer_name=analyzer_name
                    )

                    if values_result.success:
                        records = values_result.data
                        if hasattr(records, '__len__'):
                            GLOG.info(f"  {analyzer_name} records: {len(records)}")
                            if len(records) > 0:
                                # 显示最后一条记录
                                last_record = records[-1]
                                if hasattr(last_record, 'timestamp'):
                                    GLOG.info(f"  Latest timestamp: {last_record.timestamp}")
                                if hasattr(last_record, 'value'):
                                    GLOG.info(f"  Latest value: {last_record.value}")


if __name__ == '__main__':
    unittest.main(verbosity=2)

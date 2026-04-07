# Upstream: CLI命令(ginkgo data seed初始化示例数据)
# Downstream: DataContainer(通过container访问各服务)、EngineService/PortfolioService/FileService/MappingService/ParamService(业务服务创建引擎/组合/文件/映射/参数)
# Role: 数据种子模块为回测/演示目的初始化数据库提供运行/分步/清理等方法






"""
Example Data Seeding - Refactored Version

This module is responsible for initializing the database with a set of
example data for backtesting and demonstration purposes.

Updated to use the new DI container architecture with service layer.
"""

import os
import time
import json
from typing import Dict, Any, Optional, List
from rich.console import Console

# Import the container instance to access services
from ginkgo.data.containers import container

from ginkgo.libs import GCONF, GLOG
from ginkgo.enums import FILE_TYPES
from ginkgo.data.models import MEngine, MPortfolio


class DataSeeder:
    """
    Data seeding orchestrator for initializing example data.

    Refactored to separate concerns and provide better testability.
    """

    def __init__(self):
        """Initialize the data seeder."""
        self.console = Console()
        self.results = {
            'engine': None,
            'files_created': 0,
            'portfolio': None,
            'engines_count': 0,
            'portfolios_count': 0,
            'mappings_count': 0,
            'parameters_count': 0,
            'errors': []
        }

    def run_all(self) -> Dict[str, Any]:
        """
        Runs the complete example data seeding process.

        Returns:
            Dict containing seeding results and statistics
        """
        self._log_header()

        try:
            # Step 0: Cleanup existing data to ensure idempotency
            self._cleanup_existing_data()

            # Step 1: Validate sample data
            self._validate_sample_data()

            # Step 2: Initialize core components
            self._init_engines()
            self._init_files()
            self._init_portfolios()

            # Step 3: Create mappings and parameters
            if self.results['files_created'] > 0:
                self._create_engine_portfolio_mapping()
                self._create_portfolio_component_mappings()
                # 参数创建已在create_preset_bindings中完成，不再需要单独创建
                # self._create_parameters()

            self._log_completion()
            return self.results

        except Exception as e:
            error_msg = f"Data seeding failed: {str(e)}"
            GLOG.ERROR(error_msg)
            self.console.print(f"❌ {error_msg}")
            self.results['errors'].append(error_msg)
            raise

    def run_step(self, step_name: str) -> Dict[str, Any]:
        """
        Run a specific seeding step.

        Args:
            step_name: Name of the step to run

        Returns:
            Dict containing step results
        """
        self._log_header()

        try:
            if step_name == "validate":
                self._validate_sample_data()
            elif step_name == "engines":
                self._init_engines()
            elif step_name == "files":
                self._init_files()
            elif step_name == "portfolios":
                self._init_portfolios()
            elif step_name == "mappings":
                self._create_engine_portfolio_mapping()
                self._create_portfolio_component_mappings()
            elif step_name == "parameters":
                self._create_parameters()
            else:
                raise ValueError(f"Unknown step: {step_name}")

            return self.results

        except Exception as e:
            error_msg = f"Step '{step_name}' failed: {str(e)}"
            GLOG.ERROR(error_msg)
            self.console.print(f"❌ {error_msg}")
            self.results['errors'].append(error_msg)
            raise

    def _cleanup_existing_data(self):
        """清理现有的present_和preset_数据，确保幂等性"""
        GLOG.INFO("步骤 0: 清理现有present_和preset_数据")
        try:
            # 使用MappingService和ParamService的清理功能
            mapping_service = container.mapping_service()
            engine_service = container.engine_service()

            # 清理 preset_ 相关的引擎
            preset_engines = engine_service.get()
            if preset_engines.success and preset_engines.data:
                for engine in preset_engines.data:
                    if engine.name.startswith('preset_'):
                        GLOG.INFO(f"删除旧的preset引擎: {engine.name}")
                        delete_result = engine_service.delete(engine.uuid)
                        if delete_result.success:
                            self.console.print(f"🧹 删除了旧的preset引擎: {engine.name}")

            # 清理映射关系
            mapping_result = mapping_service.cleanup_by_names("present_%")
            if mapping_result.success:
                mapping_data = mapping_result.data
                total_mappings = mapping_data.get('total_deleted', 0)
                if total_mappings > 0:
                    GLOG.INFO(f"清理了 {total_mappings} 个映射关系")
                    self.console.print(f"🧹 清理了 {total_mappings} 个旧的映射关系")

            # 清理参数（需要先获取ParamService实例）
            param_service = container.param_service()
            param_result = param_service.cleanup_by_names("present_%")
            if param_result.success:
                param_data = param_result.data
                total_params = param_data.get('deleted_count', 0)
                if total_params > 0:
                    GLOG.INFO(f"清理了 {total_params} 个参数")
                    self.console.print(f"🧹 清理了 {total_params} 个旧的参数配置")

            # 清理文件（在文件创建函数中已经处理了单个文件的删除）
            # 这里不需要额外处理，因为_create_example_files会先删除同名文件

            GLOG.INFO("数据清理完成，确保幂等性")
            self.console.print("✅ 现有数据清理完成")

        except Exception as e:
            GLOG.ERROR(f"数据清理失败: {e}")
            self.console.print(f"⚠️ 数据清理时出现问题: {e}")
            # 不抛出异常，继续执行

    def _validate_sample_data(self) -> bool:
        """Validate that sample data exists for backtesting."""
        GLOG.INFO("步骤 1: 验证示例数据")
        try:
            stockinfo_service = container.stockinfo_service()
            result = stockinfo_service.get(limit=5)

            if not result.success or not result.data or len(result.data) == 0:
                GLOG.WARN("未找到股票基础数据，建议运行 'ginkgo data update --stockinfo' 来获取示例数据")
                self.console.print(
                    ":warning: No stock information found. Run 'ginkgo data update --stockinfo' to populate sample data."
                )
                return False

            stock_count = len(result.data)
            GLOG.INFO(f"找到股票基础数据: {stock_count} 条记录")
            self.console.print(f":white_check_mark: Found sample stock data")
            return True
        except Exception as e:
            GLOG.ERROR(f"验证示例数据失败: {e}")
            self.console.print(f":x: Failed to validate sample data: {e}")
            return False

    def _init_engines(self):
        """Initialize example backtest engines."""
        GLOG.INFO("步骤 2: 初始化引擎")
        engine = self._create_example_engine()
        if engine.success:
            self.results['engines_count'] += 1
        self.results['engine'] = engine

    def _init_files(self):
        """Initialize example files using file service."""
        GLOG.INFO("步骤 3: 初始化组件文件")
        files_created = self._create_example_files()
        self.results['files_created'] = files_created

    def _init_portfolios(self):
        """Initialize example portfolios."""
        GLOG.INFO("步骤 4: 初始化投资组合")
        portfolio = self._create_example_portfolio()
        if portfolio.success:
            self.results['portfolios_count'] += 1
        self.results['portfolio'] = portfolio

    def _log_header(self):
        """Log seeding header."""
        GLOG.INFO("========================================")
        GLOG.INFO("=== 开始初始化示例数据 (SEEDING) ===")
        GLOG.INFO("========================================")
        self.console.print("--- Initializing Example Data ---")

    def _log_completion(self):
        """Log seeding completion."""
        GLOG.INFO("========================================")
        GLOG.INFO("=== 示例数据初始化完成 ===")
        GLOG.INFO(f"总共创建文件: {self.results['files_created']}")
        GLOG.INFO(f"引擎数量: {self.results['engines_count']}")
        GLOG.INFO(f"投资组合数量: {self.results['portfolios_count']}")
        GLOG.INFO(f"映射数量: {self.results['mappings_count']}")
        GLOG.INFO(f"参数数量: {self.results['parameters_count']}")
        GLOG.INFO("========================================")
        self.console.print("--- Example Data Initialization Complete ---")

        # Display summary
        self.console.print("\n📋 Summary:")
        self.console.print(f"  • Files Created: {self.results['files_created']}")
        self.console.print(f"  • Engines: {self.results['engines_count']}")
        self.console.print(f"  • Portfolios: {self.results['portfolios_count']}")
        self.console.print(f"  • Mappings: {self.results['mappings_count']}")
        self.console.print(f"  • Parameters: {self.results['parameters_count']}")

        if self.results['errors']:
            self.console.print(f"  ⚠️ Errors: {len(self.results['errors'])}")

    def _create_example_engine(self) -> Dict[str, Any]:
        """Initialize example backtest engine using engine service."""
        GLOG.INFO("=== 开始初始化示例引擎 ===")
        engine_service = container.engine_service()
        engine_name = "present_engine"

        # 1. Remove existing engines with same name using direct database deletion
        try:
            from ginkgo.data.crud.engine_crud import EngineCRUD
            from sqlalchemy import text

            engine_crud = EngineCRUD()

            with engine_crud.get_session() as session:
                # 直接使用SQL删除同名引擎
                stmt = text("DELETE FROM engine WHERE name = :name")
                result = session.execute(stmt, {"name": engine_name})
                deleted_count = result.rowcount
                session.commit()

                if deleted_count > 0:
                    GLOG.WARN(f"直接SQL删除 {deleted_count} 个现有引擎: {engine_name}")
                    self.console.print(f":broom: Direct SQL deleted {deleted_count} existing '{engine_name}' engines.")
                else:
                    GLOG.DEBUG(f"没有找到需要删除的引擎: {engine_name}")

        except Exception as e:
            GLOG.ERROR(f"引擎删除失败: {engine_name}, 错误: {e}")
            self.console.print(f":warning: Engine deletion had issues: {str(e)}")

        # 2. Create new engine with time range matching complete_backtest_example.py
        GLOG.DEBUG(f"创建新引擎: {engine_name} (is_live=False)")

        # 按照complete_backtest_example.py设置时间范围: 2023-01-03 到 2023-01-10
        import datetime
        backtest_start_date = datetime.datetime(2023, 1, 3)
        backtest_end_date = datetime.datetime(2023, 1, 10)

        # 按照complete_backtest_example.py设置时间范围和broker attitude: 2023-01-03 到 2023-01-10
        from ginkgo.enums import ATTITUDE_TYPES

        engine = engine_service.add(
            name=engine_name,
            is_live=False,
            backtest_start_date=backtest_start_date,
            backtest_end_date=backtest_end_date,
            broker_attitude=ATTITUDE_TYPES.OPTIMISTIC  # 与Example保持一致，确保随机数序列一致
        )
        if engine.success:
            # Extract UUID safely from engine result
            engine_uuid = None
            if hasattr(engine, 'data') and engine.data:
                if hasattr(engine.data, 'uuid'):
                    engine_uuid = engine.data.uuid
                elif isinstance(engine.data, dict) and 'uuid' in engine.data:
                    engine_uuid = engine.data['uuid']

            GLOG.INFO(f"引擎创建成功: {engine_name} (UUID: {engine_uuid})")
            GLOG.INFO(f"引擎时间范围: {backtest_start_date} 到 {backtest_end_date}")
            self.console.print(f":gear: Example engine '{engine_name}' created.")
            self.console.print(f"   :calendar: Time range: {backtest_start_date.date()} to {backtest_end_date.date()}")
        else:
            GLOG.ERROR(f"引擎创建失败: {engine_name}, 错误: {engine.error}")
            self.console.print(f":warning: Engine creation failed: {engine.error}")

        return engine

    def _create_example_files(self) -> int:
        """Initialize example files using file service."""
        GLOG.INFO("=== 开始初始化示例组件文件 ===")
        file_service = container.file_service()
        file_root = os.path.join(GCONF.WORKING_PATH, "src", "ginkgo", "trading")
        GLOG.DEBUG(f"组件文件根目录: {file_root}")

        file_type_map = {
            "analysis/analyzers": FILE_TYPES.ANALYZER,  # 修复路径：analyzers在analysis子目录下
            "risk_management": FILE_TYPES.RISKMANAGER,
            "selectors": FILE_TYPES.SELECTOR,
            "sizers": FILE_TYPES.SIZER,
            "strategies": FILE_TYPES.STRATEGY,
        }

        files_created = 0
        blacklist = ["__", "base"]

        GLOG.INFO(f"开始扫描文件夹: {list(file_type_map.keys())}")

        for folder, file_type in file_type_map.items():
            folder_path = os.path.join(file_root, folder)
            GLOG.DEBUG(f"处理文件夹: {folder_path} (类型: {file_type.name})")

            if not os.path.isdir(folder_path):
                GLOG.WARN(f"文件夹不存在: {folder_path}")
                self.console.print(f":warning: Folder not found: {folder_path}")
                continue

            python_files = [f for f in os.listdir(folder_path)
                           if not any(substring in f for substring in blacklist) and f.endswith(".py")]
            GLOG.DEBUG(f"在 {folder} 中找到 {len(python_files)} 个Python文件")

            for file_name in python_files:
                preset_name = file_name.split('.')[0]
                GLOG.DEBUG(f"处理文件: {file_name} -> {preset_name}")

                # Remove existing files with same name and type using direct database deletion
                # 包括有present_前缀的旧版本和无前缀的新版本
                try:
                    from ginkgo.data.crud.file_crud import FileCRUD
                    from sqlalchemy import text

                    file_crud = FileCRUD()

                    with file_crud.get_session() as session:
                        # 删除所有相关文件：原始名称、present_前缀版本、preset_前缀版本
                        stmt = text("""
                            DELETE FROM file WHERE
                            (name = :name OR name = :present_name OR name = :preset2_name)
                            AND type = :type
                        """)
                        result = session.execute(stmt, {
                            "name": preset_name,
                            "present_name": f"present_{preset_name}",
                            "preset2_name": f"preset_{preset_name}",
                            "type": file_type.value
                        })
                        deleted_count = result.rowcount
                        session.commit()

                        if deleted_count > 0:
                            GLOG.WARN(f"直接SQL删除 {deleted_count} 个现有文件: {preset_name} (包括所有前缀版本)")
                            self.console.print(f":broom: Direct SQL deleted {deleted_count} existing '{preset_name}' files (including prefixed versions).")
                        else:
                            GLOG.DEBUG(f"没有找到需要删除的文件: {preset_name}")

                except Exception as e:
                    GLOG.ERROR(f"文件删除失败: {preset_name}, 错误: {e}")
                    self.console.print(f":warning: File deletion had issues: {str(e)}")

                # Read and add new file
                file_path = os.path.join(folder_path, file_name)
                try:
                    with open(file_path, "rb") as f:
                        content = f.read()
                    file_size = len(content)
                    GLOG.DEBUG(f"读取文件 {file_name}: {file_size} 字节")

                    result = file_service.add(name=preset_name, file_type=file_type, data=content)
                    if result.success:
                        files_created += 1
                        # result.data 的格式是 {"file_info": {"uuid": ..., "name": ..., ...}}
                        file_info = result.data.get("file_info", {}) if isinstance(result.data, dict) else {}
                        file_uuid = file_info.get("uuid", "Unknown")
                        GLOG.INFO(f"组件文件创建成功: {preset_name} ({file_type.name}, UUID: {file_uuid}, 大小: {file_size}字节)")
                        self.console.print(f":white_check_mark: Created {file_type.name}: {preset_name}")
                    else:
                        GLOG.ERROR(f"组件文件创建失败: {preset_name}, 错误: {result.error}")
                        self.console.print(f":x: Failed to create {preset_name}: {result.error}")
                except Exception as e:
                    GLOG.ERROR(f"读取文件失败: {file_path}, 错误: {e}")
                    self.console.print(f":x: Failed to read {file_path}: {e}")

        GLOG.INFO(f"=== 组件文件初始化完成 ===")
        GLOG.INFO(f"总共创建 {files_created} 个组件文件，来源: {file_root}")
        self.console.print(f":file_folder: {files_created} example files initialized from {file_root}")
        return files_created

    def _create_example_portfolio(self) -> Dict[str, Any]:
        """Initialize example portfolio using portfolio service."""
        GLOG.INFO("=== 开始初始化示例投资组合 ===")
        portfolio_service = container.portfolio_service()

        # 1. 创建回测Portfolio (is_live=False)
        portfolio_name = "present_portfolio"
        portfolio = self._create_single_portfolio(portfolio_service, portfolio_name, is_live=False)

        # 2. 创建实盘Portfolio (is_live=True)
        live_portfolio_name = "present_portfolio_live"
        live_portfolio = self._create_single_portfolio(portfolio_service, live_portfolio_name, is_live=True)

        return portfolio  # 返回回测portfolio以保持向后兼容

    def _create_single_portfolio(self, portfolio_service, portfolio_name: str, is_live: bool) -> Dict[str, Any]:
        """创建单个Portfolio的辅助方法"""
        portfolio_type = "实盘" if is_live else "回测"
        GLOG.INFO(f"创建{portfolio_type}投资组合: {portfolio_name}")

        # 1. 删除已存在的同名portfolio
        try:
            from ginkgo.data.crud.portfolio_crud import PortfolioCRUD
            from sqlalchemy import text

            portfolio_crud = PortfolioCRUD()

            with portfolio_crud.get_session() as session:
                stmt = text("DELETE FROM portfolio WHERE name = :name")
                result = session.execute(stmt, {"name": portfolio_name})
                deleted_count = result.rowcount
                session.commit()

                if deleted_count > 0:
                    GLOG.WARN(f"删除 {deleted_count} 个现有投资组合: {portfolio_name}")
                    self.console.print(f":broom: Deleted {deleted_count} existing '{portfolio_name}' portfolios.")

        except Exception as e:
            GLOG.ERROR(f"投资组合删除失败: {portfolio_name}, 错误: {e}")
            self.console.print(f":warning: Portfolio deletion had issues: {str(e)}")

        # 2. 创建新portfolio
        portfolio = portfolio_service.add(name=portfolio_name, is_live=is_live)

        if portfolio.success:
            portfolio_uuid = None
            if hasattr(portfolio, 'data') and portfolio.data:
                if hasattr(portfolio.data, 'uuid'):
                    portfolio_uuid = portfolio.data.uuid
                elif isinstance(portfolio.data, dict) and 'uuid' in portfolio.data:
                    portfolio_uuid = portfolio.data['uuid']

            GLOG.INFO(f"{portfolio_type}投资组合创建成功: {portfolio_name} (UUID: {portfolio_uuid}, is_live={is_live})")
            self.console.print(f":briefcase: {portfolio_type} portfolio '{portfolio_name}' created.")
        else:
            GLOG.ERROR(f"{portfolio_type}投资组合创建失败: {portfolio_name}, 错误: {portfolio.error}")
            self.console.print(f":warning: Portfolio creation failed: {portfolio.error}")

        return portfolio

    def _create_engine_portfolio_mapping(self):
        """Create engine-portfolio mapping using MappingService."""
        GLOG.INFO("步骤 5: 创建引擎-投资组合映射")

        # 使用新的MappingService
        mapping_service = container.mapping_service()

        # Extract UUIDs from service results with safer handling
        engine_id = None
        portfolio_id = None

        # Extract engine UUID - handle nested engine_info structure
        if self.results['engine'] and hasattr(self.results['engine'], 'data') and self.results['engine'].data:
            if hasattr(self.results['engine'].data, 'uuid'):
                engine_id = self.results['engine'].data.uuid
            elif isinstance(self.results['engine'].data, dict):
                # Handle direct uuid or nested engine_info.uuid
                if 'uuid' in self.results['engine'].data:
                    engine_id = self.results['engine'].data['uuid']
                elif 'engine_info' in self.results['engine'].data and isinstance(self.results['engine'].data['engine_info'], dict):
                    engine_id = self.results['engine'].data['engine_info'].get('uuid')

        # Extract portfolio UUID - handle nested portfolio_info structure
        if self.results['portfolio'] and hasattr(self.results['portfolio'], 'data') and self.results['portfolio'].data:
            if hasattr(self.results['portfolio'].data, 'uuid'):
                portfolio_id = self.results['portfolio'].data.uuid
            elif isinstance(self.results['portfolio'].data, dict):
                # Handle direct uuid or nested portfolio_info.uuid
                if 'uuid' in self.results['portfolio'].data:
                    portfolio_id = self.results['portfolio'].data['uuid']
                elif 'portfolio_info' in self.results['portfolio'].data and isinstance(self.results['portfolio'].data['portfolio_info'], dict):
                    portfolio_id = self.results['portfolio'].data['portfolio_info'].get('uuid')

        GLOG.INFO(f"提取UUID - Engine: {engine_id}, Portfolio: {portfolio_id}")

        if not engine_id:
            GLOG.ERROR(f"无法从结果中获取引擎UUID: {self.results['engine']}")
            self.console.print(f":x: Failed to get engine UUID from result: {self.results['engine']}")
            return

        if not portfolio_id:
            GLOG.ERROR(f"无法从结果中获取投资组合UUID: {self.results['portfolio']}")
            self.console.print(f":x: Failed to get portfolio UUID from result: {self.results['portfolio']}")
            return

        # 使用MappingService创建映射
        result = mapping_service.create_engine_portfolio_mapping(
            engine_id, portfolio_id, "present_engine", "present_portfolio"
        )

        if result.success:
            GLOG.INFO(f"引擎-投资组合映射创建成功: Engine({engine_id}) -> Portfolio({portfolio_id})")
            self.console.print(f":link: Engine-portfolio mapping created")
            self.results['mappings_count'] += 1
        else:
            GLOG.ERROR(f"引擎-投资组合映射创建失败: {result.error}")

    def _create_portfolio_component_mappings(self):
        """Create portfolio-component mappings using MappingService."""
        GLOG.INFO("步骤 6: 创建Portfolio组件绑定关系")
        try:
            portfolio_crud = container.cruds.portfolio()
            mapping_service = container.mapping_service()

            # 定义绑定规则
            binding_rules = {
                "strategies": [{"name": "random_signal_strategy"}],
                "selectors": [{"name": "fixed_selector"}],
                "sizers": [{"name": "fixed_sizer"}],
                "analyzers": [{"name": "net_value"}]
            }

            # 1. 为回测Portfolio创建组件绑定
            backtest_portfolios = portfolio_crud.find(filters={"name": "present_portfolio"})
            if len(backtest_portfolios) > 0:
                backtest_portfolio = backtest_portfolios[0]
                GLOG.INFO(f"为回测Portfolio创建组件绑定: {backtest_portfolio.name}")

                # 获取Engine UUID
                engine_crud = container.cruds.engine()
                engines = engine_crud.find(filters={"name": "present_engine"})

                if len(engines) > 0:
                    engine = engines[0]
                    result = mapping_service.create_preset_bindings(
                        engine_uuid=engine.uuid,
                        portfolio_uuid=backtest_portfolio.uuid,
                        binding_rules=binding_rules
                    )

                    if result.success:
                        binding_data = result.data
                        bindings_created = binding_data.get('bindings_created', 0)
                        self.results['mappings_count'] += bindings_created
                        GLOG.INFO(f"回测Portfolio: 成功创建 {bindings_created} 个组件绑定")
                        self.console.print(f"✅ 回测Portfolio: 创建了 {bindings_created} 个组件绑定")

                        # 为绑定的组件创建参数
                        self._create_parameters_for_portfolio_bindings(backtest_portfolio.uuid)
                    else:
                        GLOG.ERROR(f"回测Portfolio: 组件绑定失败: {result.error}")

            # 2. 为实盘Portfolio创建组件绑定
            live_portfolios = portfolio_crud.find(filters={"name": "present_portfolio_live"})
            if len(live_portfolios) > 0:
                live_portfolio = live_portfolios[0]
                GLOG.INFO(f"为实盘Portfolio创建组件绑定: {live_portfolio.name}")

                # 实盘Portfolio直接创建Portfolio-File绑定（不需要Engine）
                bindings_created = self._create_portfolio_file_bindings_direct(
                    mapping_service, live_portfolio.uuid, binding_rules
                )

                if bindings_created > 0:
                    GLOG.INFO(f"实盘Portfolio: 成功创建 {bindings_created} 个组件绑定")
                    self.console.print(f"✅ 实盘Portfolio: 创建了 {bindings_created} 个组件绑定")

                    # 为绑定的组件创建参数
                    self._create_parameters_for_portfolio_bindings(live_portfolio.uuid)

        except Exception as e:
            error_msg = f"创建组件绑定失败: {str(e)}"
            GLOG.ERROR(error_msg)
            self.results['errors'].append(error_msg)
            raise

    def _create_portfolio_file_bindings_direct(
        self, mapping_service, portfolio_uuid: str, binding_rules: dict
    ) -> int:
        """直接创建Portfolio-File绑定（不通过create_preset_bindings）"""
        from ginkgo.data.containers import container
        from ginkgo.enums import FILE_TYPES

        file_service = container.file_service()
        bindings_created = 0

        for component_type, components in binding_rules.items():
            type_mapping = {
                "selectors": FILE_TYPES.SELECTOR,
                "sizers": FILE_TYPES.SIZER,
                "strategies": FILE_TYPES.STRATEGY,
                "analyzers": FILE_TYPES.ANALYZER,
                "risk_managers": FILE_TYPES.RISKMANAGER
            }

            file_type_enum = type_mapping.get(component_type)
            if not file_type_enum:
                continue

            files_result = file_service.get_by_type(file_type_enum)
            if not files_result.success:
                continue

            files_list = files_result.data.get('files', [])
            if not files_list:
                continue

            for component_rule in components:
                rule_name = component_rule.get("name")
                if not rule_name:
                    continue

                matching_files = [f for f in files_list if rule_name in f.name.lower()]
                if not matching_files:
                    continue

                file = matching_files[0]
                binding_result = mapping_service.create_portfolio_file_binding(
                    portfolio_uuid, file.uuid, file.name, file_type_enum
                )

                if binding_result.success:
                    bindings_created += 1

        return bindings_created

    def _create_parameters_for_portfolio_bindings(self, portfolio_uuid: str):
        """为指定Portfolio的所有组件绑定创建参数

        这个方法的核心逻辑是：
        1. 获取Portfolio的所有Portfolio-File映射（bindings）
        2. 根据每个binding的file_uuid和type确定参数配置
        3. 为每个binding创建对应的参数记录，使用binding.uuid作为mapping_id
        """
        try:
            import json

            GLOG.INFO("为Portfolio组件绑定创建参数...")

            # 获取Portfolio的文件绑定
            mapping_service = container.mapping_service()
            file_mapping_result = mapping_service.get_portfolio_file_bindings(portfolio_uuid)

            if not file_mapping_result.success:
                GLOG.WARN("未找到Portfolio的文件绑定，跳过参数创建")
                return

            parameters_created = 0

            # 为每个绑定的组件创建参数
            for mapping in file_mapping_result.data:
                file_name = mapping.name.lower()
                mapping_uuid = mapping.uuid
                file_id = mapping.file_id

                # 🔑 关键修复：根据文件名和组件类型动态创建参数
                params = self._get_component_parameters_for_mapping(file_name, mapping.type)

                if params:  # 只有有参数的组件才创建
                    # 创建参数
                    result = mapping_service.create_component_parameters(
                        mapping_uuid=mapping_uuid,
                        file_uuid=file_id,
                        parameters=params
                    )

                    if result.success:
                        param_data = result.data
                        params_count = param_data.get('params_created', 0)
                        parameters_created += params_count
                        GLOG.INFO(f"为 {mapping.name} (mapping: {mapping_uuid}) 创建了 {params_count} 个参数")
                        self.console.print(f"   📝 {mapping.name}: 创建了 {params_count} 个参数")
                    else:
                        GLOG.WARN(f"为 {mapping.name} 创建参数失败: {result.message}")

            GLOG.INFO(f"总共为Portfolio创建了 {parameters_created} 个参数")
            if parameters_created > 0:
                self.console.print(f"✅ 总共创建了 {parameters_created} 个组件参数")

            # 🔑 关键修复：更新results统计
            self.results['parameters_count'] = parameters_created

        except Exception as e:
            error_msg = f"创建组件参数失败: {str(e)}"
            GLOG.ERROR(error_msg)
            self.results['errors'].append(error_msg)
            # 不抛出异常，允许继续执行

    def _get_component_parameters_for_mapping(self, file_name: str, component_type: int) -> dict:
        """根据文件名和组件类型获取对应的参数配置"""
        try:
            import json
            from ginkgo.enums import FILE_TYPES

            file_name_lower = file_name.lower()

            # 根据组件类型和文件名匹配创建参数
            if component_type == FILE_TYPES.SELECTOR.value:
                if "fixed_selector" in file_name_lower:
                    return {0: "default_selector", 1: json.dumps(["000001.SZ", "000002.SZ"])}  # 🎯 两只股票测试，参数统一
                elif "cn_all_selector" in file_name_lower:
                    return {0: "cn_all_selector", 1: json.dumps(["000001.SZ", "000002.SZ", "600519.SH"])}
                elif "momentum_selector" in file_name_lower:
                    return {0: "momentum_selector", 1: json.dumps(["000001.SZ", "600519.SH"])}
                elif "popularity_selector" in file_name_lower:
                    return {0: "popularity_selector", 1: json.dumps(["000001.SZ", "000002.SZ"])}

            elif component_type == FILE_TYPES.STRATEGY.value:
                if "random_signal_strategy" in file_name_lower:
                    # 🎯 修复：完整的5个参数，顺序必须与构造函数完全匹配
                    # RandomSignalStrategy构造函数：__init__(name, buy_probability, sell_probability, signal_reason_template, max_signals)
                    import json
                    return {
                        0: "backtest_base",                          # name: 策略名称
                        1: str(0.9),                                 # buy_probability: 0.9 (90%)
                        2: str(0.05),                                # sell_probability: 0.05 (5%)
                        3: "随机信号-{direction}-{index}",           # signal_reason_template: 信号原因模板
                        4: str(4),                                    # max_signals: 4
                    }
                elif "trend_follow" in file_name_lower:
                    return {0: "trend_follow_strategy"}
                elif "mean_reversion" in file_name_lower:
                    return {0: "mean_reversion_strategy"}
                elif "dual_thrust" in file_name_lower:
                    return {0: "dual_thrust_strategy"}

            elif component_type == FILE_TYPES.SIZER.value:
                if "fixed_sizer" in file_name_lower:
                    return {0: "default_sizer", 1: "1000"}
                elif "ratio_sizer" in file_name_lower:
                    return {0: "ratio_sizer", 1: json.dumps(0.1)}
                elif "atr_sizer" in file_name_lower:
                    return {0: "atr_sizer", 1: "2.0"}

            elif component_type == FILE_TYPES.RISKMANAGER.value:
                if "position_ratio_risk" in file_name_lower:
                    return {0: "0.2"}  # max_position_ratio
                elif "loss_limit_risk" in file_name_lower:
                    return {0: "0.05"}  # loss_limit
                elif "profit_target_risk" in file_name_lower:
                    return {0: "0.15"}  # profit_limit
                elif "no_risk" in file_name_lower:
                    return {}  # 无参数

            # 默认情况：根据类型创建基础参数
            if component_type == FILE_TYPES.SELECTOR.value:
                return {0: "default_selector", 1: json.dumps(["000001.SZ"])}
            elif component_type == FILE_TYPES.STRATEGY.value:
                return {0: "default_strategy"}
            elif component_type == FILE_TYPES.SIZER.value:
                return {0: "default_sizer", 1: "1000"}
            elif component_type == FILE_TYPES.RISKMANAGER.value:
                return {0: "0.1"}

            return {}  # 未知组件类型，无参数

        except Exception as e:
            GLOG.WARN(f"获取组件参数配置失败: {str(e)}")
            return {}

    def _create_parameters(self):
        """Create parameters for component mappings using MappingService."""
        GLOG.INFO("步骤 7: 创建组件参数配置")
        try:
            # 获取名为present_portfolio的Portfolio
            portfolio_crud = container.cruds.portfolio()
            portfolios = portfolio_crud.find(filters={"name": "present_portfolio"})

            if len(portfolios) == 0:
                GLOG.WARN("未找到名为present_portfolio的Portfolio，跳过参数创建")
                return

            portfolio = portfolios[0]
            GLOG.INFO(f"为Portfolio {portfolio.name} 创建组件参数")

            # 使用MappingService创建参数
            mapping_service = container.mapping_service()

            # 定义组件参数配置 - 修复参数顺序和数量
            component_parameters = {
                "fixed_selector": {0: "default_selector", 1: json.dumps(["000001.SZ", "000002.SZ"])},  # selector参数：name, codes
                "fixed_sizer": {0: "1000"},         # sizer参数：volume (name使用默认值)
            }

            parameters_created = 0
            param_details = []

            # 获取Portfolio的文件绑定
            file_mapping_result = mapping_service.get_portfolio_file_bindings(portfolio.uuid)
            if not file_mapping_result.success:
                GLOG.WARN("未找到Portfolio的文件绑定，跳过参数创建")
                return

            # 为每个绑定的组件创建参数
            for mapping in file_mapping_result.data:
                file_name = mapping.name.lower()

                # 检查是否需要为该文件创建参数
                for component_name, params in component_parameters.items():
                    if component_name in file_name:
                        result = mapping_service.create_component_parameters(
                            mapping_uuid=mapping.uuid,
                            file_uuid=mapping.file_id,
                            parameters=params
                        )

                        if result.success:
                            param_data = result.data
                            parameters_created += param_data.get('params_created', 0)
                            param_details.extend(param_data.get('param_details', []))
                            GLOG.INFO(f"为 {mapping.name} 创建了 {param_data.get('params_created', 0)} 个参数")
                            self.console.print(f"✅ 为 {mapping.name} 创建了 {param_data.get('params_created', 0)} 个参数")
                        break

            self.results['parameters_count'] = parameters_created

            if parameters_created > 0:
                GLOG.INFO(f"成功创建 {parameters_created} 个组件参数")
                self.console.print(f"✅ 总共创建了 {parameters_created} 个组件参数")

                # 显示参数详情
                for detail in param_details:
                    GLOG.DEBUG(f"   参数: {detail}")
            else:
                GLOG.WARN("未创建任何参数")
                self.console.print("⚠️ 未创建任何参数")

        except Exception as e:
            error_msg = f"创建组件参数失败: {str(e)}"
            GLOG.ERROR(error_msg)
            self.results['errors'].append(error_msg)
            raise


# Global instance for backward compatibility
_seeder_instance = None


def run():
    """Legacy run function for backward compatibility."""
    global _seeder_instance
    if _seeder_instance is None:
        _seeder_instance = DataSeeder()

    return _seeder_instance.run_all()


def get_seeder() -> DataSeeder:
    """Get the data seeder instance."""
    global _seeder_instance
    if _seeder_instance is None:
        _seeder_instance = DataSeeder()
    return _seeder_instance

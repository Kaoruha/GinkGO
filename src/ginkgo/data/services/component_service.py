"""
Component Service

This service handles the business logic for dynamically instantiating
trading system components (strategies, analyzers, selectors, sizers, risk managers)
from file content and parameters.
"""

from typing import List, Any, Optional, Type, Dict
import inspect

from ginkgo.enums import FILE_TYPES
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.libs import time_logger, retry


class ComponentService(BaseService):
    def __init__(self, file_service, portfolio_service):
        """Initializes the service with its dependencies."""
        super().__init__(file_service=file_service, portfolio_service=portfolio_service)

    # 注意：add、update、delete方法已移除，ComponentService专注于组件实例化功能
# 组件的基础CRUD通过FileService管理

    def get(self, component_id: str = None, **filters) -> ServiceResult:
        """
        获取组件信息记录

        Args:
            component_id: 组件ID（可选）
            **filters: 过滤条件

        Returns:
            ServiceResult: 操作结果
        """
        self._log_operation_start("get", component_id=component_id, **filters)
        try:
            # 由于ComponentService不直接管理数据存储，返回空结果
            # 主要功能在get_component_info方法中
            components = []

            self._log_operation_end("get", True)
            return ServiceResult.success(data=components, message="组件信息获取成功")

        except Exception as e:
            error_msg = f"获取组件信息失败: {str(e)}"
            self._logger.ERROR(error_msg)
            self._log_operation_end("get", False)
            return ServiceResult.error(error_msg)

    def exists(self, **filters) -> ServiceResult:
        """
        检查组件是否存在

        Args:
            **filters: 过滤条件

        Returns:
            ServiceResult: 操作结果，包含exists字段
        """
        self._log_operation_start("exists", **filters)
        try:
            # 基本的文件存在性检查
            file_id = filters.get("file_id")
            if file_id:
                file_result = self._file_service.get_by_uuid(file_id)
                exists = file_result.success if file_result else False
            else:
                exists = False

            self._log_operation_end("exists", True)
            return ServiceResult.success(data={"exists": exists}, message="组件存在性检查完成")

        except Exception as e:
            error_msg = f"检查组件存在性失败: {str(e)}"
            self._logger.ERROR(error_msg)
            self._log_operation_end("exists", False)
            return ServiceResult.error(error_msg)

    def count(self, **filters) -> ServiceResult:
        """
        统计组件数量

        Args:
            **filters: 过滤条件

        Returns:
            ServiceResult: 操作结果，包含count字段
        """
        self._log_operation_start("count", **filters)
        try:
            # 这里返回0，因为ComponentService不直接管理数据存储
            count = 0

            self._log_operation_end("count", True)
            return ServiceResult.success(data={"count": count}, message="组件数量统计完成")

        except Exception as e:
            error_msg = f"统计组件数量失败: {str(e)}"
            self._logger.ERROR(error_msg)
            self._log_operation_end("count", False)
            return ServiceResult.error(error_msg)

    def health_check(self) -> ServiceResult:
        """
        健康检查

        Returns:
            ServiceResult: 健康状态
        """
        try:
            # 检查依赖服务
            file_service_healthy = self._file_service and hasattr(self._file_service, 'health_check')
            portfolio_service_healthy = self._portfolio_service and hasattr(self._portfolio_service, 'health_check')

            health_data = {
                "service_name": self._service_name,
                "status": "healthy" if file_service_healthy and portfolio_service_healthy else "unhealthy",
                "dependencies": {
                    "file_service": "healthy" if file_service_healthy else "unavailable",
                    "portfolio_service": "healthy" if portfolio_service_healthy else "unavailable"
                },
                "component_types": list(FILE_TYPES)
            }

            return ServiceResult.success(data=health_data, message="ComponentService健康检查完成")

        except Exception as e:
            error_msg = f"健康检查失败: {str(e)}"
            self._logger.ERROR(error_msg)
            return ServiceResult.error(error_msg)

    def validate(self, data: Dict) -> ServiceResult:
        """
        验证组件数据

        Args:
            data: 要验证的数据

        Returns:
            ServiceResult: 验证结果
        """
        try:
            if not isinstance(data, dict):
                return ServiceResult.error("数据必须是字典格式")

            # 检查必填字段
            required_fields = ["file_id", "file_type"]
            missing_fields = [field for field in required_fields if not data.get(field)]

            if missing_fields:
                return ServiceResult.error(f"缺少必填字段: {', '.join(missing_fields)}")

            # 验证文件类型
            file_type = data.get("file_type")
            if isinstance(file_type, str):
                try:
                    file_type = FILE_TYPES(file_type)
                except ValueError:
                    return ServiceResult.error(f"无效的文件类型: {file_type}")

            return ServiceResult.success(data={"valid": True}, message="组件数据验证通过")

        except Exception as e:
            error_msg = f"验证组件数据失败: {str(e)}"
            self._logger.ERROR(error_msg)
            return ServiceResult.error(error_msg)

    def check_integrity(self, component_id: str = None) -> ServiceResult:
        """
        检查组件数据完整性

        Args:
            component_id: 组件ID（可选）

        Returns:
            ServiceResult: 完整性检查结果
        """
        try:
            integrity_issues = []

            if component_id:
                # 检查特定组件的完整性
                file_id = component_id  # 假设component_id就是file_id
                file_result = self._file_service.get_by_uuid(file_id)

                if not file_result.success:
                    integrity_issues.append(f"文件不存在或无法访问: {file_id}")
            else:
                # 检查整体服务完整性
                if not self._file_service:
                    integrity_issues.append("FileService依赖不可用")
                if not self._portfolio_service:
                    integrity_issues.append("PortfolioService依赖不可用")

            is_valid = len(integrity_issues) == 0

            return ServiceResult.success(
                data={
                    "valid": is_valid,
                    "issues": integrity_issues,
                    "component_id": component_id
                },
                message="组件完整性检查完成" if is_valid else f"发现{len(integrity_issues)}个完整性问题"
            )

        except Exception as e:
            error_msg = f"检查组件完整性失败: {str(e)}"
            self._logger.ERROR(error_msg)
            return ServiceResult.error(error_msg)

    @time_logger
    @retry(max_try=3)
    def instantiate(self, file_id: str, mapping_id: str, file_type: FILE_TYPES) -> ServiceResult:
        """
        Creates an instance of a trading component from file content and parameters.

        Args:
            file_id: UUID of the file containing the component code
            mapping_id: UUID of the portfolio-file mapping
            file_type: Type of component to instantiate

        Returns:
            ServiceResult: 包含实例化组件对象的结果
        """
        self._log_operation_start("instantiate", file_id=file_id, mapping_id=mapping_id, file_type=file_type.value)

        try:
            # 输入验证
            if not file_id or not file_id.strip():
                return ServiceResult.error("文件ID不能为空")

            if not mapping_id or not mapping_id.strip():
                return ServiceResult.error("映射ID不能为空")

            if not isinstance(file_type, FILE_TYPES):
                return ServiceResult.error(f"无效的文件类型: {file_type}")

            # Get the component class mapping
            cls_base_mapping = self._get_component_base_classes()

            if file_type not in cls_base_mapping:
                error_msg = f"不支持的文件类型: {file_type}"
                self._logger.ERROR(error_msg)
                self._log_operation_end("instantiate", False)
                return ServiceResult.error(error_msg)

            base_class = cls_base_mapping[file_type]

            # Get file content
            content_result = self._file_service.get_content(file_id)
            if not content_result.success:
                error_msg = f"获取文件内容失败: {file_id}, 错误: {content_result.error}"
                self._logger.ERROR(error_msg)
                self._log_operation_end("instantiate", False)
                return ServiceResult.error(error_msg)

            content = content_result.data
            if not content:
                error_msg = f"文件内容为空: {file_id}"
                self._logger.ERROR(error_msg)
                self._log_operation_end("instantiate", False)
                return ServiceResult.error(error_msg)

            # Execute code in isolated namespace
            namespace = {}
            try:
                exec(content.decode("utf-8"), namespace)
            except Exception as e:
                error_msg = f"文件代码执行失败 {file_id}: {e}"
                self._logger.ERROR(error_msg)
                self._log_operation_end("instantiate", False)
                return ServiceResult.error(error_msg)

            # Find the component class
            component_class = self._find_component_class(namespace, base_class)
            if component_class is None:
                error_msg = f"未找到有效的{base_class.__name__}子类: {file_id}"
                self._logger.ERROR(error_msg)
                self._log_operation_end("instantiate", False)
                return ServiceResult.error(error_msg)

            # Get parameters for instantiation
            parameters = self._get_instantiation_parameters(mapping_id)

            # Instantiate the component
            try:
                instance = component_class(*parameters)

                # Special handling for analyzers
                if file_type == FILE_TYPES.ANALYZER:
                    if hasattr(instance, "set_analyzer_id"):
                        instance.set_analyzer_id(file_id)

                success_msg = f"成功实例化{component_class.__name__}: {file_id}"
                self._logger.DEBUG(success_msg)
                self._log_operation_end("instantiate", True)
                return ServiceResult.success(
                    data={
                        "instance": instance,
                        "class_name": component_class.__name__,
                        "file_id": file_id,
                        "file_type": file_type.value
                    },
                    message=success_msg
                )

            except Exception as e:
                error_msg = f"实例化失败{component_class.__name__}: {file_id}, 错误: {e}"
                self._logger.ERROR(error_msg)
                self._log_operation_end("instantiate", False)
                return ServiceResult.error(error_msg)

        except Exception as e:
            error_msg = f"创建实例时发生意外错误 {file_id}: {e}"
            self._logger.ERROR(error_msg)
            self._log_operation_end("instantiate", False)
            return ServiceResult.error(error_msg)

    @time_logger
    @retry(max_try=3)
    def get_components(self, portfolio_id: str, file_type: FILE_TYPES) -> ServiceResult:
        """
        Gets all instantiated components of a specific type for a portfolio.

        Args:
            portfolio_id: UUID of the portfolio
            file_type: Type of components to retrieve

        Returns:
            ServiceResult: 包含实例化组件列表的结果
        """
        self._log_operation_start("get_components", portfolio_id=portfolio_id, file_type=file_type.value)

        try:
            # 输入验证
            if not portfolio_id or not portfolio_id.strip():
                return ServiceResult.error("投资组合ID不能为空")

            if not isinstance(file_type, FILE_TYPES):
                error_msg = f"无效的文件类型: {file_type}"
                self._logger.ERROR(error_msg)
                self._log_operation_end("get_components", False)
                return ServiceResult.error(error_msg)

            # Get all file mappings for the portfolio and type
            components_result = self._portfolio_service.get_components(portfolio_id=portfolio_id)
            if not components_result.success:
                error_msg = f"获取投资组合组件失败: {components_result.error}"
                self._logger.ERROR(error_msg)
                self._log_operation_end("get_components", False)
                return ServiceResult.error(error_msg)

            # Filter by file type
            filtered_mappings = [
                comp for comp in components_result.data
                if comp.get("component_type") == file_type.value
            ]

            components = []
            failed_mappings = []

            for mapping in filtered_mappings:
                file_id = mapping.get("component_id")
                mapping_id = mapping.get("uuid")  # 这里可能需要调整

                if not file_id or not mapping_id:
                    failed_mappings.append(mapping.get("uuid", "unknown"))
                    continue

                instance_result = self.get_instance_by_file(file_id, mapping_id, file_type)
                if instance_result.success:
                    components.append(instance_result.data["instance"])
                else:
                    failed_mappings.append(mapping_id)
                    self._logger.WARN(f"组件实例化失败: {mapping_id}, 错误: {instance_result.error}")

            success_msg = f"为投资组合{portfolio_id}获取了{len(components)}个{file_type.value}组件"
            self._logger.INFO(success_msg)
            self._log_operation_end("get_components", True)

            return ServiceResult.success(
                data={
                    "components": components,
                    "portfolio_id": portfolio_id,
                    "file_type": file_type.value,
                    "count": len(components),
                    "failed_count": len(failed_mappings),
                    "failed_mappings": failed_mappings
                },
                message=success_msg
            )

        except Exception as e:
            error_msg = f"获取投资组合组件时发生错误: {str(e)}"
            self._logger.ERROR(error_msg)
            self._log_operation_end("get_components", False)
            return ServiceResult.error(error_msg)

    def get_strategies(self, portfolio_id: str) -> ServiceResult:
        """Gets all strategy instances for a portfolio."""
        return self.get_components(portfolio_id, FILE_TYPES.STRATEGY)

    def get_analyzers(self, portfolio_id: str) -> ServiceResult:
        """Gets all analyzer instances for a portfolio."""
        return self.get_components(portfolio_id, FILE_TYPES.ANALYZER)

    def get_selectors(self, portfolio_id: str) -> ServiceResult:
        """Gets all selector instances for a portfolio."""
        return self.get_components(portfolio_id, FILE_TYPES.SELECTOR)

    def get_sizers(self, portfolio_id: str) -> ServiceResult:
        """Gets all sizer instances for a portfolio."""
        return self.get_components(portfolio_id, FILE_TYPES.SIZER)

    def get_risk_managers(self, portfolio_id: str) -> ServiceResult:
        """Gets all risk manager instances for a portfolio."""
        return self.get_components(portfolio_id, FILE_TYPES.RISKMANAGER)

    @time_logger
    @retry(max_try=3)
    def validate_code(self, code: str, file_type: FILE_TYPES) -> ServiceResult:
        """
        Validates component code without instantiating it.

        Args:
            code: Python code as string
            file_type: Expected component type

        Returns:
            ServiceResult: 包含验证结果的结果
        """
        self._log_operation_start("validate_code", file_type=file_type.value)

        try:
            # 输入验证
            if not code or not code.strip():
                error_msg = "代码内容不能为空"
                self._log_operation_end("validate_code", False)
                return ServiceResult.error(error_msg)

            if not isinstance(file_type, FILE_TYPES):
                error_msg = f"无效的文件类型: {file_type}"
                self._logger.ERROR(error_msg)
                self._log_operation_end("validate_code", False)
                return ServiceResult.error(error_msg)

            result = {
                "valid": False,
                "error": None,
                "class_name": None,
                "base_class": None,
                "file_type": file_type.value
            }

            # Get expected base class
            cls_base_mapping = self._get_component_base_classes()
            if file_type not in cls_base_mapping:
                result["error"] = f"不支持的文件类型: {file_type}"
                self._log_operation_end("validate_code", False)
                return ServiceResult.success(data=result, message="组件代码验证完成")

            base_class = cls_base_mapping[file_type]
            result["base_class"] = base_class.__name__

            # Try to execute the code
            namespace = {}
            try:
                exec(code, namespace)
            except Exception as e:
                result["error"] = f"代码执行失败: {e}"
                self._log_operation_end("validate_code", False)
                return ServiceResult.success(data=result, message="组件代码验证完成")

            # Find component class
            component_class = self._find_component_class(namespace, base_class)
            if component_class is None:
                result["error"] = f"未找到有效的{base_class.__name__}子类"
                self._log_operation_end("validate_code", False)
                return ServiceResult.success(data=result, message="组件代码验证完成")

            result["valid"] = True
            result["class_name"] = component_class.__name__

            success_msg = f"组件代码验证通过: {component_class.__name__}"
            self._log_operation_end("validate_code", True)
            return ServiceResult.success(data=result, message=success_msg)

        except Exception as e:
            error_msg = f"验证过程发生错误: {e}"
            self._logger.ERROR(error_msg)
            self._log_operation_end("validate_code", False)
            return ServiceResult.error(error_msg)

    def _get_component_base_classes(self) -> dict:
        """
        Gets the mapping of file types to their base classes.

        Returns:
            Dictionary mapping FILE_TYPES to base classes
        """
        try:
            from ginkgo.trading.strategies.base_strategy import BaseStrategy
            from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
            from ginkgo.trading.sizers.base_sizer import BaseSizer
            from ginkgo.trading.selectors.base_selector import BaseSelector
            from ginkgo.trading.risk_managementss.base_risk import BaseRiskManagement

            return {
                FILE_TYPES.STRATEGY: BaseStrategy,
                FILE_TYPES.ANALYZER: BaseAnalyzer,
                FILE_TYPES.SIZER: BaseSizer,
                FILE_TYPES.SELECTOR: BaseSelector,
                FILE_TYPES.RISKMANAGER: BaseRiskManagement,
            }
        except ImportError as e:
            self._logger.ERROR(f"Failed to import component base classes: {e}")
            return {}

    def _find_component_class(self, namespace: dict, base_class: Type) -> Optional[Type]:
        """
        Finds a component class in the namespace that inherits from base_class.

        Args:
            namespace: Execution namespace containing classes
            base_class: Expected base class

        Returns:
            Component class or None if not found
        """
        for name, obj in namespace.items():
            if (
                isinstance(obj, type) and issubclass(obj, base_class) and obj != base_class
            ):  # Don't return the base class itself
                return obj
        return None

    def _get_instantiation_parameters(self, mapping_id: str) -> List[str]:
        """
        Gets parameters for component instantiation from the database.

        Args:
            mapping_id: UUID of the portfolio-file mapping

        Returns:
            List of parameter values in order
        """
        try:
            params_df = self.portfolio_service.get_parameters_for_mapping(mapping_id, as_dataframe=True)

            if params_df.empty:
                return []

            # Sort by order and return values
            params_df = params_df.sort_values("index")
            return params_df["value"].tolist()

        except Exception as e:
            self._logger.ERROR(f"Failed to get parameters for mapping {mapping_id}: {e}")
            return []

    @time_logger
    @retry(max_try=3)
    def get_info(self, file_id: str, file_type: FILE_TYPES) -> ServiceResult:
        """
        Gets information about a component without instantiating it.

        Args:
            file_id: UUID of the file
            file_type: Type of component

        Returns:
            ServiceResult: 包含组件信息的详细结果
        """
        self._log_operation_start("get_info", file_id=file_id, file_type=file_type.value)

        try:
            # 输入验证
            if not file_id or not file_id.strip():
                error_msg = "文件ID不能为空"
                self._log_operation_end("get_info", False)
                return ServiceResult.error(error_msg)

            if not isinstance(file_type, FILE_TYPES):
                error_msg = f"无效的文件类型: {file_type}"
                self._logger.ERROR(error_msg)
                self._log_operation_end("get_info", False)
                return ServiceResult.error(error_msg)

            result = {
                "success": False,
                "file_id": file_id,
                "file_type": file_type.value,
                "error": None,
                "warnings": [],
                "class_name": None,
                "methods": [],
                "init_params": [],
                "init_signature": None,
                "valid": False,
                "file_size_bytes": 0,
                "code_lines": 0,
                "base_class": None,
                "docstring": None,
            }

            try:
                content_result = self._file_service.get_content(file_id)
                if not content_result.success:
                    error_msg = f"获取文件内容失败: {content_result.error}"
                    self._log_operation_end("get_info", False)
                    return ServiceResult.error(error_msg)

                content = content_result.data
                if not content:
                    error_msg = "文件内容为空"
                    self._log_operation_end("get_info", False)
                    return ServiceResult.error(error_msg)

                result["file_size_bytes"] = len(content)

            except Exception as e:
                error_msg = f"获取文件内容失败: {str(e)}"
                self._log_operation_end("get_info", False)
                return ServiceResult.error(error_msg)

            try:
                code_str = content.decode("utf-8")
                result["code_lines"] = len(code_str.splitlines())
            except UnicodeDecodeError as e:
                error_msg = f"文件内容解码失败: {str(e)}"
                self._log_operation_end("get_info", False)
                return ServiceResult.error(error_msg)

            # Validate the code
            validation_result = self.validate_component_code(code_str, file_type)
            if not validation_result.success:
                error_msg = f"代码验证失败: {validation_result.error}"
                self._log_operation_end("get_info", False)
                return ServiceResult.error(error_msg)

            validation_data = validation_result.data
            result["valid"] = validation_data["valid"]
            result["error"] = validation_data["error"]
            result["class_name"] = validation_data["class_name"]
            result["base_class"] = validation_data["base_class"]

            if validation_data["valid"]:
                # Get more detailed information
                try:
                    namespace = {}
                    exec(code_str, namespace)

                    cls_base_mapping = self._get_component_base_classes()
                    base_class = cls_base_mapping[file_type]
                    component_class = self._find_component_class(namespace, base_class)

                    if component_class:
                        # Get method names
                        try:
                            methods = [
                                name
                                for name, method in inspect.getmembers(component_class, predicate=inspect.isfunction)
                            ]
                            result["methods"] = [m for m in methods if not m.startswith("_")]
                        except Exception as e:
                            result["warnings"].append(f"方法分析失败: {str(e)}")

                        # Get init parameters
                        try:
                            init_signature = inspect.signature(component_class.__init__)
                            result["init_params"] = [
                                param.name for param in init_signature.parameters.values() if param.name != "self"
                            ]
                            result["init_signature"] = str(init_signature)
                        except Exception as e:
                            result["warnings"].append(f"初始化签名分析失败: {str(e)}")

                        # Get class docstring
                        try:
                            if component_class.__doc__:
                                result["docstring"] = component_class.__doc__.strip()
                        except Exception as e:
                            result["warnings"].append(f"文档字符串获取失败: {str(e)}")

                        result["success"] = True
                        success_msg = f"组件信息获取成功: {component_class.__name__}"
                        self._log_operation_end("get_info", True)
                        return ServiceResult.success(data=result, message=success_msg)

                    else:
                        error_msg = "验证通过后未找到组件类"
                        self._log_operation_end("get_info", False)
                        return ServiceResult.error(error_msg)

                except Exception as e:
                    error_msg = f"组件详细信息分析失败: {str(e)}"
                    self._logger.ERROR(error_msg)
                    self._log_operation_end("get_info", False)
                    return ServiceResult.error(error_msg)

            else:
                error_msg = validation_data.get("error", "组件验证失败")
                self._log_operation_end("get_info", False)
                return ServiceResult.success(data=result, message="组件信息获取完成（验证失败）")

        except Exception as e:
            error_msg = f"组件信息分析发生错误: {str(e)}"
            self._logger.ERROR(error_msg)
            self._log_operation_end("get_info", False)
            return ServiceResult.error(error_msg)

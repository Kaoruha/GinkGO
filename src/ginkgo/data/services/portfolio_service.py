# Upstream: CLI Commands (ginkgo portfolio add/list/delete)、Engine (投资组合管理)
# Downstream: BaseService (继承提供服务基础能力)、PortfolioCRUD (投资组合CRUD操作)、PortfolioFileMappingCRUD (文件映射CRUD)
# Role: PortfolioService投资组合管理业务服务提供增删改查/存在检查/统计/绑定/解绑/按名称获取等方法






"""
Portfolio Management Service (Class-based)

This service handles the business logic for managing investment portfolios,
including portfolio creation, file associations, and parameter management.

Enhanced with comprehensive error handling, retry mechanisms, and structured returns.
"""

import time
import importlib.util
import tempfile
import os
from typing import List, Union, Any, Optional, Dict
import pandas as pd
from datetime import datetime

from ginkgo.libs import cache_with_expiration, retry, time_logger, GLOG
from ginkgo.enums import FILE_TYPES
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.crud.model_conversion import ModelList


class PortfolioService(BaseService):
    def __init__(self, crud_repo, portfolio_file_mapping_crud):
        """
        初始化PortfolioService，设置投资组合和文件映射仓储依赖

        Args:
            crud_repo: 投资组合数据CRUD仓储实例
            portfolio_file_mapping_crud: 投资组合文件映射CRUD仓储实例
        """
        super().__init__(
            crud_repo=crud_repo, portfolio_file_mapping_crud=portfolio_file_mapping_crud
        )

    @time_logger
    @retry(max_try=3)
    def add(
        self,
        name: str,
        is_live: bool = False,
        description: str = None,
        **kwargs
    ) -> ServiceResult:
        """
        创建新的投资组合

        Args:
            name: 投资组合名称
            is_live: 是否为实盘交易组合
            description: 可选描述

        Returns:
            ServiceResult: 操作结果
        """
        try:
            # 输入验证
            if not name or not name.strip():
                return ServiceResult.error("投资组合名称不能为空")

            if len(name) > 100:  # 合理的名称长度限制
                name = name[:100]

            # 检查投资组合名称是否已存在
            try:
                exists_result = self.exists(name=name)
                if exists_result.is_success() and exists_result.data.get("exists", False):
                    return ServiceResult.error(f"投资组合名称 '{name}' 已存在")
            except Exception as e:
                GLOG.WARN(f"无法检查投资组合存在性: {str(e)}")

            # 创建投资组合
            with self._crud_repo.get_session() as session:
                # 提取 initial_capital 参数
                initial_capital = kwargs.get('initial_capital', None)
                create_kwargs = {
                    "name": name,
                    "is_live": is_live,
                    "desc": description or f"{'Live' if is_live else 'Backtest'} portfolio: {name}",
                    "session": session,
                }
                if initial_capital is not None:
                    create_kwargs["initial_capital"] = initial_capital
                    create_kwargs["current_capital"] = initial_capital
                    create_kwargs["cash"] = initial_capital

                portfolio_record = self._crud_repo.create(**create_kwargs)

                portfolio_info = {
                    "uuid": portfolio_record.uuid,
                    "name": portfolio_record.name,
                    "is_live": portfolio_record.is_live,
                    "desc": portfolio_record.desc,
                }

                GLOG.INFO(f"成功创建投资组合 '{name}' (实盘: {is_live})")

                return ServiceResult.success(
                    data=portfolio_info,
                    message=f"投资组合创建成功: {name}"
                )

        except Exception as e:
            GLOG.ERROR(f"创建投资组合失败 '{name}': {str(e)}")
            return ServiceResult.error(f"创建投资组合失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def update(
        self,
        portfolio_id: str,
        name: str = None,
        is_live: bool = None,
        description: str = None,
        **kwargs
    ) -> ServiceResult:
        """
        更新现有投资组合的信息，支持部分字段更新

        Args:
            portfolio_id: 投资组合UUID标识符
            name: 新的投资组合名称（可选）
            is_live: 新的实盘状态（可选）
            description: 新的描述信息（可选）

        Returns:
            ServiceResult: 包含更新状态和操作结果的详细信息
        """
        warnings = []
        updates_applied = []

        # Input validation
        if not portfolio_id or not portfolio_id.strip():
            return ServiceResult.error("Portfolio ID cannot be empty")

        updates = {}
        if name is not None:
            if not name.strip():
                return ServiceResult.error("Portfolio name cannot be empty")
            if len(name) > 100:
                warnings.append("Portfolio name truncated to 100 characters")
                name = name[:100]
            updates["name"] = name
            updates_applied.append("name")

        
        if is_live is not None:
            updates["is_live"] = is_live
            updates_applied.append("is_live")

        if description is not None:
            updates["desc"] = description
            updates_applied.append("description")

        if not updates:
            return ServiceResult.success({}, "No updates provided for portfolio update", warnings)

        # Check if name conflicts with existing portfolio (if name is being updated)
        if "name" in updates:
            try:
                existing_portfolios = self.get_portfolios(name=name)
                if len(existing_portfolios) > 0:
                    # Check if the existing portfolio is not the one we're updating
                    df = existing_portfolios.to_dataframe()
                    existing_uuids = df["uuid"].tolist()
                    if portfolio_id not in existing_uuids:
                        return ServiceResult.error(f"Portfolio with name '{name}' already exists")
            except Exception as e:
                warnings.append(f"Could not check name conflict: {str(e)}")

        try:
            self._crud_repo.modify(filters={"uuid": portfolio_id}, updates=updates)

            GLOG.INFO(f"Successfully updated portfolio {portfolio_id} with {len(updates)} changes")

        except Exception as e:
            return ServiceResult.error(f"Database operation failed: {str(e)}")

        # 返回更新结果
        result_data = {
            "portfolio_id": portfolio_id,
            "updates_applied": updates_applied,
            "warnings": warnings
        }
        return ServiceResult.success(result_data, f"Portfolio updated successfully")

    @time_logger
    @retry(max_try=3)
    def delete(self, portfolio_id: str, **kwargs) -> ServiceResult:
        """
        删除投资组合（包括清理相关文件映射和参数）

        Args:
            portfolio_id: 投资组合UUID

        Returns:
            ServiceResult: 删除结果
        """
        try:
            # 输入验证
            if not portfolio_id or not portfolio_id.strip():
                return ServiceResult.error("投资组合ID不能为空")

            # 检查投资组合是否存在
            exists_result = self.exists(portfolio_id=portfolio_id)
            if not exists_result.is_success():
                return ServiceResult.error(f"检查投资组合存在性失败: {exists_result.error}")

            if not exists_result.data.get("exists", False):
                return ServiceResult.error(f"投资组合不存在: {portfolio_id}")

            deleted_count = 0
            mappings_deleted = 0
            parameters_deleted = 0
            warnings = []

            # 清理投资组合-文件映射和参数
            try:
                file_mappings = self._portfolio_file_mapping_crud.find(
                    filters={"portfolio_id": portfolio_id}
                )

                for mapping in file_mappings:
                    # 删除关联参数
                    try:
                        self._param_crud.remove(
                            filters={"mapping_id": mapping.uuid}
                        )
                    except Exception as e:
                        warnings.append(f"删除映射参数失败 {mapping.uuid}: {str(e)}")

                # 删除投资组合-文件映射
                self._portfolio_file_mapping_crud.remove(
                    filters={"portfolio_id": portfolio_id}
                )

            except Exception as e:
                warnings.append(f"清理映射关系时出错: {str(e)}")

            # 软删除投资组合
            self._crud_repo.soft_remove(
                filters={"uuid": portfolio_id}
            )

            GLOG.INFO(f"成功删除投资组合 {portfolio_id}")

            result_data = {
                "portfolio_id": portfolio_id,
                "mappings_deleted": mappings_deleted,
                "parameters_deleted": parameters_deleted,
                "warnings": warnings
            }

            message = f"投资组合删除成功: {portfolio_id}"
            if warnings:
                message += f" (附带{len(warnings)}个警告)"

            return ServiceResult.success(result_data, message)

        except Exception as e:
            GLOG.ERROR(f"删除投资组合失败 {portfolio_id}: {str(e)}")
            return ServiceResult.error(f"删除投资组合失败: {str(e)}")

    # ==================== 投资组合组件管理方法 ====================

    @time_logger
    @retry(max_try=3)
    def mount_component(
        self, portfolio_id: str, component_id: str, component_name: str, component_type: FILE_TYPES
    ) -> ServiceResult:
        """
        为投资组合挂载量化交易组件，建立组合与组件的关联关系

        Args:
            portfolio_id: 投资组合UUID标识符
            component_id: 组件文件的UUID标识符
            component_name: 组件在投资组合中的显示名称
            component_type: 组件类型枚举值，确定组件功能分类

        Returns:
            ServiceResult: 包含挂载状态和操作信息的详细结果

        """
        try:
            # 输入验证
            if not portfolio_id or not portfolio_id.strip():
                return ServiceResult.error("投资组合ID不能为空")

            if not component_id or not component_id.strip():
                return ServiceResult.error("组件ID不能为空")

            if not component_name or not component_name.strip():
                return ServiceResult.error("组件名称不能为空")

            # 检查投资组合是否存在
            exists_result = self.exists(portfolio_id=portfolio_id)
            if not exists_result.is_success():
                return ServiceResult.error(f"检查投资组合存在性失败: {exists_result.error}")

            if not exists_result.data.get("exists", False):
                return ServiceResult.error(f"投资组合不存在: {portfolio_id}")

            # 检查组件是否已经挂载
            try:
                existing_components = self.get_components(portfolio_id=portfolio_id)
                if existing_components.is_success():
                    for component in existing_components.data:
                        if component.get("file_id") == component_id:
                            return ServiceResult.error(f"组件已挂载到投资组合: {component_name}")
            except Exception as e:
                GLOG.WARN(f"检查组件挂载状态失败: {str(e)}")

            # 创建挂载关系
            with self._portfolio_file_mapping_crud.get_session() as session:
                mapping_record = self._portfolio_file_mapping_crud.create(
                    portfolio_id=portfolio_id,
                    file_id=component_id,
                    name=component_name,
                    type=component_type,
                    session=session
                )

                mount_info = {
                    "mount_id": mapping_record.uuid,
                    "portfolio_id": portfolio_id,
                    "component_id": component_id,
                    "component_name": component_name,
                    "component_type": component_type.name if hasattr(component_type, "name") else str(component_type),
                }

                GLOG.INFO(f"成功为投资组合 {portfolio_id} 挂载组件 {component_name}")

                return ServiceResult.success(mount_info, f"组件挂载成功: {component_name}")

        except Exception as e:
            GLOG.ERROR(f"挂载组件失败 {component_name}: {str(e)}")
            return ServiceResult.error(f"挂载组件失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def unmount_component(self, mount_id: str) -> ServiceResult:
        """
        卸载投资组合的组件

        Args:
            mount_id: 挂载关系UUID

        Returns:
            ServiceResult: 卸载结果
        """
        try:
            # 输入验证
            if not mount_id or not mount_id.strip():
                return ServiceResult.error("挂载ID不能为空")

            # 软删除挂载关系
            self._portfolio_file_mapping_crud.soft_remove(
                filters={"uuid": mount_id}
            )

            GLOG.INFO(f"成功卸载组件挂载 {mount_id}")

            return ServiceResult.success(
                {"mount_id": mount_id},
                f"组件卸载成功: {mount_id}"
            )

        except Exception as e:
            GLOG.ERROR(f"卸载组件失败 {mount_id}: {str(e)}")
            return ServiceResult.error(f"卸载组件失败: {str(e)}")

    @time_logger
    def get_components(self, portfolio_id: str = None, component_type: FILE_TYPES = None) -> ServiceResult:
        """
        获取投资组合的组件列表

        Args:
            portfolio_id: 投资组合UUID
            component_type: 组件类型过滤

        Returns:
            ServiceResult: 组件列表
        """
        try:
            filters = {"is_del": False}

            if portfolio_id:
                filters["portfolio_id"] = portfolio_id

            if component_type:
                filters["type"] = component_type

            mappings = self._portfolio_file_mapping_crud.find(filters=filters)

            # 转换为统一的组件信息格式
            components = []
            for mapping in mappings or []:
                # 从 File 表获取实际文件名
                actual_file_name = mapping.name  # 默认使用 mapping.name
                try:
                    from ginkgo import services
                    file_crud = services.data.cruds.file()
                    files = file_crud.find(filters={"uuid": mapping.file_id}, page_size=1)
                    if files and len(files) > 0:
                        actual_file_name = files[0].name  # 使用 File 表中的实际文件名
                except Exception as e:
                    GLOG.WARN(f"Failed to get file name for {mapping.file_id}: {e}")

                component_info = {
                    "mount_id": mapping.uuid,
                    "portfolio_id": mapping.portfolio_id,
                    "component_id": mapping.file_id,
                    "component_name": actual_file_name,  # 使用 File 表中的实际文件名
                    "component_type": mapping.type.name if hasattr(mapping.type, "name") else str(mapping.type),
                    "created_at": mapping.created_at.isoformat() if hasattr(mapping, 'created_at') else None,
                }
                components.append(component_info)

            return ServiceResult.success(components, f"获取到{len(components)}个组件")

        except Exception as e:
            GLOG.ERROR(f"获取组件列表失败: {str(e)}")
            return ServiceResult.error(f"获取组件列表失败: {str(e)}")

  
    # ==================== 标准接口方法 ====================

    @time_logger
    @retry(max_try=3)
    def get(self, portfolio_id: str = None, name: str = None, is_live: bool = None, as_dataframe: bool = False, **kwargs) -> ServiceResult:
        """
        获取投资组合数据

        Args:
            portfolio_id: 投资组合UUID
            name: 投资组合名称
            is_live: 是否实盘组合
            as_dataframe: 是否返回DataFrame
            **kwargs: 其他过滤条件

        Returns:
            ServiceResult: 查询结果
        """
        try:
            if portfolio_id:
                # 按UUID查询
                portfolios = self._crud_repo.find(filters={"uuid": portfolio_id, "is_del": False})
                if not portfolios:
                    return ServiceResult.error(f"投资组合不存在: {portfolio_id}")
                return ServiceResult.success(portfolios, "获取投资组合成功")

            else:
                # 按条件查询
                filters = kwargs.get('filters', {})
                filters['is_del'] = False

                if is_live is not None:
                    filters['is_live'] = is_live

                # 支持名称模糊搜索
                if name:
                    filters['name__like'] = f'%{name}%'

                # 支持分页参数
                page = kwargs.get('page', 0)
                page_size = kwargs.get('page_size', 20)

                portfolios = self._crud_repo.find(filters=filters, page=page, page_size=page_size)
                return ServiceResult.success(portfolios, f"获取到{len(portfolios)}个投资组合")

        except Exception as e:
            GLOG.ERROR(f"获取投资组合失败: {str(e)}")
            return ServiceResult.error(f"获取投资组合失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def count(self, name: str = None, is_live: bool = None, **kwargs) -> ServiceResult:
        """
        统计投资组合数量

        Args:
            name: 投资组合名称筛选
            is_live: 是否实盘组合筛选
            **kwargs: 其他过滤条件

        Returns:
            ServiceResult: 统计结果
        """
        try:
            filters = kwargs.get('filters', {})
            filters['is_del'] = False

            if name:
                filters['name__like'] = f'%{name}%'
            if is_live is not None:
                filters['is_live'] = is_live

            count = self._crud_repo.count(filters=filters)

            return ServiceResult.success(
                {"count": count},
                f"统计到{count}个投资组合"
            )

        except Exception as e:
            GLOG.ERROR(f"统计投资组合失败: {str(e)}")
            return ServiceResult.error(f"统计投资组合失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def exists(self, portfolio_id: str = None, name: str = None, **kwargs) -> ServiceResult:
        """
        检查投资组合是否存在

        Args:
            portfolio_id: 投资组合UUID
            name: 投资组合名称
            **kwargs: 其他检查条件

        Returns:
            ServiceResult: 检查结果
        """
        try:
            if not portfolio_id and not name:
                return ServiceResult.error("必须提供portfolio_id或name参数")

            if portfolio_id:
                exists = self._crud_repo.exists(filters={"uuid": portfolio_id, "is_del": False})
            else:
                exists = self._crud_repo.exists(filters={"name": name, "is_del": False})

            return ServiceResult.success(
                {"exists": exists},
                f"投资组合{'存在' if exists else '不存在'}"
            )

        except Exception as e:
            GLOG.ERROR(f"检查投资组合存在性失败: {str(e)}")
            return ServiceResult.error(f"检查投资组合存在性失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def health_check(self) -> ServiceResult:
        """
        服务健康检查

        Returns:
            ServiceResult: 健康检查结果
        """
        try:
            health_info = {
                "service_name": "PortfolioService",
                "status": "healthy",
                "checks": {}
            }

            # 检查CRUD依赖
            if self._crud_repo is None:
                return ServiceResult.error("PortfolioCRUD依赖未初始化")

            health_info["checks"]["crud_dependency"] = {"status": "passed", "message": "PortfolioCRUD依赖正常"}

            # 检查数据库连接
            try:
                self._crud_repo.find()
                health_info["checks"]["database_connection"] = {"status": "passed", "message": "数据库连接正常"}
            except Exception as db_error:
                return ServiceResult.error(f"数据库连接失败: {str(db_error)}")

            # 检查服务功能
            try:
                count_result = self.count()
                if count_result.is_success():
                    total_count = count_result.data.get("count", 0)
                    health_info["checks"]["service_functionality"] = {
                        "status": "passed",
                        "message": f"服务功能正常，共{total_count}个投资组合"
                    }
                    health_info["total_portfolios"] = total_count
                else:
                    return ServiceResult.error("服务功能检查失败")
            except Exception as func_error:
                return ServiceResult.error(f"服务功能检查失败: {str(func_error)}")

            message = f"PortfolioService运行正常，共{health_info.get('total_portfolios', 0)}个投资组合"
            return ServiceResult.success(health_info, message)

        except Exception as e:
            GLOG.ERROR(f"PortfolioService健康检查失败: {str(e)}")
            return ServiceResult.error(f"健康检查失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def validate(self, portfolio_data: Dict[str, Any]) -> ServiceResult:
        """
        验证投资组合数据有效性

        Args:
            portfolio_data: 待验证的投资组合数据

        Returns:
            ServiceResult: 验证结果
        """
        try:
            if not isinstance(portfolio_data, dict):
                return ServiceResult.error("数据必须是字典格式")

            # 必填字段验证
            required_fields = ['name']
            missing_fields = [field for field in required_fields if not portfolio_data.get(field)]

            if missing_fields:
                return ServiceResult.error(
                    data={
                        "valid": False,
                        "missing_fields": missing_fields
                    },
                    error=f"缺少必填字段: {', '.join(missing_fields)}"
                )

            # 名称长度验证
            name = portfolio_data['name']
            if not name or not name.strip():
                return ServiceResult.error("投资组合名称不能为空")

            if len(name) > 100:
                return ServiceResult.error("投资组合名称不能超过100个字符")

            # 布尔值验证
            if 'is_live' in portfolio_data and not isinstance(portfolio_data['is_live'], bool):
                return ServiceResult.error("is_live字段必须是布尔值")

            return ServiceResult.success(
                data={"valid": True},
                message="投资组合数据验证通过"
            )

        except Exception as e:
            GLOG.ERROR(f"投资组合数据验证失败: {str(e)}")
            return ServiceResult.error(f"数据验证失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def check_integrity(self, portfolio_id: str = None) -> ServiceResult:
        """
        检查投资组合数据完整性

        Args:
            portfolio_id: 投资组合UUID，为空则检查所有

        Returns:
            ServiceResult: 完整性检查结果
        """
        try:
            issues = []

            if portfolio_id:
                # 检查单个投资组合
                get_result = self.get(portfolio_id=portfolio_id)
                if not get_result.is_success():
                    return ServiceResult.error(f"获取投资组合失败: {get_result.error}")

                portfolios = get_result.data
            else:
                # 检查所有投资组合
                get_result = self.get()
                if not get_result.is_success():
                    return ServiceResult.error(f"获取投资组合列表失败: {get_result.error}")

                portfolios = get_result.data

            total_count = len(portfolios) if portfolios else 0

            for portfolio in portfolios or []:
                portfolio_issues = []

                if not portfolio.name:
                    portfolio_issues.append("缺少投资组合名称")

                if portfolio_issues:
                    issues.append({
                        "portfolio_id": portfolio.uuid,
                        "portfolio_name": portfolio.name,
                        "issues": portfolio_issues
                    })

            integrity_score = 1.0
            if total_count > 0:
                integrity_score = (total_count - len(issues)) / total_count

            result = {
                "total_portfolios": total_count,
                "portfolios_with_issues": len(issues),
                "integrity_score": integrity_score,
                "issues": issues
            }

            message = f"完整性检查完成，{total_count}个投资组合中{len(issues)}个存在问题"
            return ServiceResult.success(result, message)

        except Exception as e:
            GLOG.ERROR(f"投资组合完整性检查失败: {str(e)}")
            return ServiceResult.error(f"完整性检查失败: {str(e)}")

    # ==================== Portfolio完整加载方法 ====================

    @time_logger
    @retry(max_try=3)
    def load_portfolio_with_components(self, portfolio_id: str) -> ServiceResult:
        """
        加载完整的Portfolio实例（包含所有实例化的组件）

        这个方法会：
        1. 从数据库加载Portfolio信息
        2. 查询所有组件配置（Strategy/Selector/Sizer/RiskManagement）
        3. 动态实例化所有组件
        4. 将组件绑定到Portfolio
        5. 返回完整的Portfolio对象（可直接用于实盘交易）

        Args:
            portfolio_id: Portfolio UUID（数据库中的真实UUID）

        Returns:
            ServiceResult: 包含完整Portfolio实例的结果
                - success: Portfolio对象（所有组件已绑定）
                - error: 错误信息

        使用示例:
            >>> portfolio_service = services.data.portfolio_service()
            >>> result = portfolio_service.load_portfolio_with_components(portfolio_id="xxx")
            >>> if result.is_success():
            >>>     portfolio = result.data
            >>>     # portfolio已经包含了所有组件，可以直接使用
            >>>     portfolio.on_price_update(event)
        """
        try:
            # 1. 获取Portfolio基本信息
            portfolio_result = self.get(portfolio_id=portfolio_id)
            if not portfolio_result.is_success():
                return ServiceResult.error(f"Portfolio不存在: {portfolio_id}")

            portfolio_model = portfolio_result.data
            if isinstance(portfolio_model, pd.DataFrame):
                if portfolio_model.shape[0] == 0:
                    return ServiceResult.error(f"Portfolio不存在: {portfolio_id}")
                portfolio_model = portfolio_model.iloc[0]
            elif hasattr(portfolio_model, '__iter__') and not isinstance(portfolio_model, dict):
                # ModelList或类似的可迭代对象
                portfolio_model = list(portfolio_model)[0] if len(portfolio_model) > 0 else None
                if portfolio_model is None:
                    return ServiceResult.error(f"Portfolio不存在: {portfolio_id}")

            # 2. 创建PortfolioLive实例
            from ginkgo.trading.portfolios.portfolio_live import PortfolioLive
            from decimal import Decimal

            portfolio = PortfolioLive(
                uuid=portfolio_model.uuid,  # 使用数据库UUID
                name=portfolio_model.name
            )

            # 设置初始资金
            portfolio.add_cash(float(portfolio_model.initial_capital))
            portfolio.initial_capital = float(portfolio_model.initial_capital)
            if not hasattr(portfolio, 'frozen_cash'):
                portfolio.frozen_cash = 0.0

            # 3. 设置上下文（engine_id和run_id）
            from ginkgo.trading.context.engine_context import EngineContext
            from ginkgo.trading.context.portfolio_context import PortfolioContext

            engine_context = EngineContext(engine_id="livecore")
            engine_context.set_run_id(portfolio.uuid)
            portfolio_context = PortfolioContext(
                portfolio_id=portfolio.uuid,
                engine_context=engine_context
            )
            portfolio._context = portfolio_context

            # 4. 获取并加载组件
            components_result = self.get_components(portfolio_id=portfolio_id)
            if not components_result.is_success():
                GLOG.WARN(f"获取组件失败: {components_result.error}，使用默认组件")
                # 使用默认组件
                self._bind_default_components(portfolio)
            else:
                components = components_result.data
                if not components or len(components) == 0:
                    GLOG.WARN(f"没有找到组件，使用默认组件")
                    self._bind_default_components(portfolio)
                else:
                    # 分类并加载组件
                    self._bind_components_from_config(portfolio, components)

            GLOG.INFO(f"✓ Portfolio {portfolio_id[:8]}... 加载成功，包含所有组件")

            return ServiceResult.success(portfolio, f"Portfolio加载成功")

        except Exception as e:
            GLOG.ERROR(f"加载Portfolio失败: {str(e)}")
            import traceback
            GLOG.ERROR(f"Traceback: {traceback.format_exc()}")
            return ServiceResult.error(f"加载Portfolio失败: {str(e)}")

    def _bind_default_components(self, portfolio):
        """绑定默认组件到Portfolio"""
        # 默认策略
        from ginkgo.trading.strategies.random_signal_strategy import RandomSignalStrategy
        strategy = RandomSignalStrategy()
        portfolio.add_strategy(strategy)
        GLOG.INFO(f"✓ 添加默认策略: RandomSignalStrategy")

        # 默认选股器
        from ginkgo.trading.selectors.cn_all_selector import CNAllSelector
        selector = CNAllSelector()
        portfolio.bind_selector(selector)
        GLOG.INFO(f"✓ 绑定默认选股器: CNAllSelector")

        # 默认Sizer
        from ginkgo.trading.sizers.fixed_sizer import FixedSizer
        sizer = FixedSizer()
        portfolio.bind_sizer(sizer)
        GLOG.INFO(f"✓ 绑定默认Sizer: FixedSizer")

        # 默认风控
        from ginkgo.trading.risk_management.position_ratio_risk import PositionRatioRisk
        risk_manager = PositionRatioRisk()
        portfolio.add_risk_manager(risk_manager)
        GLOG.INFO(f"✓ 添加默认风控: PositionRatioRisk")

    def _bind_components_from_config(self, portfolio, components: list):
        """从组件配置实例化并绑定到Portfolio"""
        # 组件分类
        strategies_list = []
        selectors_list = []
        sizers_list = []
        risk_managers_list = []

        for component in components:
            comp_type = component.get('component_type')

            # 处理component_type - 可能是字符串或数字
            if isinstance(comp_type, str):
                if comp_type.isdigit():
                    comp_type_int = int(comp_type)
                else:
                    try:
                        comp_type_int = FILE_TYPES[comp_type].value
                    except:
                        continue
            else:
                comp_type_int = int(comp_type)

            # 根据类型分类
            if comp_type_int == FILE_TYPES.STRATEGY.value:
                strategies_list.append(component)
            elif comp_type_int == FILE_TYPES.SELECTOR.value:
                selectors_list.append(component)
            elif comp_type_int == FILE_TYPES.SIZER.value:
                sizers_list.append(component)
            elif comp_type_int == FILE_TYPES.RISKMANAGER.value:
                risk_managers_list.append(component)

        GLOG.INFO(f"组件分类: 策略={len(strategies_list)}, 选股器={len(selectors_list)}, "
                 f"Sizer={len(sizers_list)}, 风控={len(risk_managers_list)}")

        # 1. 加载策略
        if len(strategies_list) == 0:
            from ginkgo.trading.strategies.random_signal_strategy import RandomSignalStrategy
            portfolio.add_strategy(RandomSignalStrategy())
        else:
            for strategy_config in strategies_list:
                strategy = self._instantiate_component(strategy_config, 'strategy')
                if strategy:
                    portfolio.add_strategy(strategy)
                    GLOG.INFO(f"✓ 添加策略: {strategy.__class__.__name__}")

        # 2. 加载选股器
        if len(selectors_list) == 0:
            from ginkgo.trading.selectors.cn_all_selector import CNAllSelector
            portfolio.bind_selector(CNAllSelector())
        else:
            selector_config = selectors_list[0]
            selector = self._instantiate_component(selector_config, 'selector')
            if selector:
                portfolio.bind_selector(selector)
                GLOG.INFO(f"✓ 绑定选股器: {selector.__class__.__name__}")

        # 3. 加载Sizer
        if len(sizers_list) == 0:
            from ginkgo.trading.sizers.fixed_sizer import FixedSizer
            portfolio.bind_sizer(FixedSizer())
        else:
            sizer_config = sizers_list[0]
            sizer = self._instantiate_component(sizer_config, 'sizer')
            if sizer:
                portfolio.bind_sizer(sizer)
                GLOG.INFO(f"✓ 绑定Sizer: {sizer.__class__.__name__}")

        # 4. 加载风控
        if len(risk_managers_list) == 0:
            from ginkgo.trading.risk_management.position_ratio_risk import PositionRatioRisk
            portfolio.add_risk_manager(PositionRatioRisk())
        else:
            for risk_config in risk_managers_list:
                risk_manager = self._instantiate_component(risk_config, 'risk_management')
                if risk_manager:
                    portfolio.add_risk_manager(risk_manager)
                    GLOG.INFO(f"✓ 添加风控: {risk_manager.__class__.__name__}")

    def _instantiate_component(self, component_config: dict, component_type: str):
        """从组件配置实例化组件"""
        try:
            file_id = component_config.get('component_id')
            if not file_id:
                return self._get_default_component(component_type)

            # 获取参数
            mount_id = component_config.get('mount_id')
            component_params = []

            if mount_id:
                try:
                    from ginkgo.data.containers import container
                    param_crud = container.cruds.param()
                    param_records = param_crud.find(filters={"mapping_id": mount_id})

                    if param_records:
                        sorted_params = sorted(param_records, key=lambda p: p.index)
                        component_params = [param.value for param in sorted_params]
                except Exception as e:
                    GLOG.WARN(f"获取参数失败: {e}")

            # 获取文件内容
            from ginkgo import services
            file_service = services.data.file_service()
            file_result = file_service.get_by_uuid(file_id)

            if not file_result.success or not file_result.data:
                return self._get_default_component(component_type)

            file_info = file_result.data
            if isinstance(file_info, dict) and "file" in file_info:
                mfile = file_info["file"]
                if hasattr(mfile, "data") and mfile.data:
                    if isinstance(mfile.data, bytes):
                        code_content = mfile.data.decode("utf-8", errors="ignore")
                    else:
                        code_content = str(mfile.data)
                else:
                    return self._get_default_component(component_type)
            else:
                return self._get_default_component(component_type)

            # 动态执行代码
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
                temp_file.write(code_content)
                temp_file_path = temp_file.name

            try:
                spec = importlib.util.spec_from_file_location("dynamic_component", temp_file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # 查找组件类
                component_class = None
                for attr_name in dir(module):
                    if attr_name.startswith("_"):
                        continue
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and hasattr(attr, "__bases__"):
                        is_component = False

                        if hasattr(attr, "__abstract__") and not getattr(attr, "__abstract__", True):
                            is_component = True
                        else:
                            for base in attr.__bases__:
                                base_name = base.__name__
                                if base_name.endswith("Strategy") or base_name.endswith("Selector") or \
                                   base_name.endswith("Sizer") or base_name.endswith("RiskManagement") or \
                                   base_name == "BaseStrategy" or base_name == "BaseSelector" or \
                                   base_name == "BaseSizer" or base_name == "BaseRiskManagement":
                                    is_component = True
                                    break

                        if is_component:
                            component_class = attr
                            break

                if component_class is None:
                    return self._get_default_component(component_type)

                # 实例化组件
                if component_params:
                    component = component_class(*component_params)
                else:
                    component = component_class()

                return component

            finally:
                try:
                    os.unlink(temp_file_path)
                except:
                    pass

        except Exception as e:
            GLOG.ERROR(f"实例化组件失败: {e}")
            return self._get_default_component(component_type)

    def _get_default_component(self, component_type: str):
        """获取默认组件作为fallback"""
        if component_type == 'strategy':
            from ginkgo.trading.strategies.random_signal_strategy import RandomSignalStrategy
            return RandomSignalStrategy()

        elif component_type == 'selector':
            from ginkgo.trading.selectors.cn_all_selector import CNAllSelector
            return CNAllSelector()

        elif component_type == 'sizer':
            from ginkgo.trading.sizers.fixed_sizer import FixedSizer
            return FixedSizer()

        elif component_type == 'risk_management':
            from ginkgo.trading.risk_management.position_ratio_risk import PositionRatioRisk
            return PositionRatioRisk()

        else:
            return None

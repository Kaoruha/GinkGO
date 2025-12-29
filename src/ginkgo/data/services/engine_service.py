# Upstream: CLI Commands (ginkgo engine add/list/delete)、Backtest Engines (引擎配置管理)
# Downstream: BaseService (继承提供服务基础能力)、EngineCRUD (引擎配置CRUD)、EnginePortfolioMappingCRUD (引擎投资组合映射CRUD)、ParamCRUD (参数CRUD)
# Role: EngineService引擎配置管理服务提供引擎CRUD和组合绑定功能支持交易系统功能和组件集成提供完整业务支持






"""
Engine Management Service (Class-based)

This service handles the business logic for managing backtest engines,
including engine creation, status management, and portfolio associations.

Enhanced with comprehensive error handling, retry mechanisms, and structured returns.
"""

import time
from typing import List, Union, Any, Optional, Dict
import pandas as pd
from datetime import datetime

from ginkgo.libs import cache_with_expiration, retry, time_logger, GLOG
from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.enums import ENGINESTATUS_TYPES, SOURCE_TYPES
from ginkgo.data.services.base_service import BaseService, ServiceResult


class EngineService(BaseService):
    def __init__(self, crud_repo, engine_portfolio_mapping_crud, param_crud):
        """
        Initializes the service with its dependencies.

        Args:
            crud_repo: Engine CRUD repository
            engine_portfolio_mapping_crud: EnginePortfolioMapping CRUD repository
            param_crud: Param CRUD repository (for engine parameters)
        """
        super().__init__(
            crud_repo=crud_repo,
            engine_portfolio_mapping_crud=engine_portfolio_mapping_crud,
            param_crud=param_crud
        )
        # Store mapping repo for easier access
        self._mapping_repo = engine_portfolio_mapping_crud

    # Standard interface methods
    @time_logger
    @retry(max_try=3)
    def get(self, engine_id: str = None, name: str = None, is_live: bool = None,
            status: ENGINESTATUS_TYPES = None) -> ServiceResult:
        """
        Get engine data

        Args:
            engine_id: Engine UUID
            name: Engine name
            is_live: Whether live trading
            status: Engine status

        Returns:
            ServiceResult: Query result with ModelList data
        """
        try:
            # Build filter conditions
            filters = {}
            if engine_id:
                filters['uuid'] = engine_id
            if name:
                filters['name'] = name
            if is_live is not None:
                filters['is_live'] = is_live
            if status:
                filters['status'] = status

            # Exclude deleted records by default
            filters['is_del'] = False

            # Execute query - always return ModelList
            result = self._crud_repo.find(filters=filters, as_dataframe=False)

            return ServiceResult.success(result, f"Successfully retrieved engine data")

        except Exception as e:
            return ServiceResult.error(f"Failed to get engine data: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def count(self, name: str = None, is_live: bool = None, status: ENGINESTATUS_TYPES = None) -> ServiceResult:
        """
        Count engine quantity

        Args:
            name: Engine name
            is_live: Whether live trading
            status: Engine status

        Returns:
            ServiceResult: Statistics result
        """
        try:
            # Build filter conditions
            filters = {}
            if name:
                filters['name'] = name
            if is_live is not None:
                filters['is_live'] = is_live
            if status:
                filters['status'] = status

            # Exclude deleted records by default
            filters['is_del'] = False

            # Execute count
            count = self._crud_repo.count(filters=filters)

            return ServiceResult.success({'count': count}, f"Successfully counted engines: {count}")

        except Exception as e:
            return ServiceResult.error(f"Failed to count engines: {str(e)}")

    @time_logger
    def validate(self, engine_id: str = None, engine_data: dict = None) -> ServiceResult:
        """
        Validate engine data

        Args:
            engine_id: Engine UUID
            engine_data: Engine data dictionary

        Returns:
            ServiceResult: Validation result
        """
        try:
            validation_errors = []

            if engine_id:
                # Validate if engine exists
                engine = self._crud_repo.find(filters={'uuid': engine_id, 'is_del': False})
                if not engine:
                    validation_errors.append(f"Engine {engine_id} does not exist")

            if engine_data:
                # Validate engine data format
                if 'name' in engine_data:
                    if not engine_data['name'] or not str(engine_data['name']).strip():
                        validation_errors.append("Engine name cannot be empty")
                    if len(str(engine_data['name'])) > 50:
                        validation_errors.append("Engine name length cannot exceed 50 characters")

                if 'is_live' in engine_data and not isinstance(engine_data['is_live'], bool):
                    validation_errors.append("is_live must be boolean")

                if 'status' in engine_data:
                    try:
                        ENGINESTATUS_TYPES(engine_data['status'])
                    except (ValueError, TypeError):
                        validation_errors.append("Invalid engine status")

            if validation_errors:
                return ServiceResult.error("Data validation failed", data={'errors': validation_errors})

            return ServiceResult.success({}, "Data validation passed")

        except Exception as e:
            return ServiceResult.error(f"Error occurred while validating engine data: {str(e)}")

    @time_logger
    def check_integrity(self, engine_id: str = None) -> ServiceResult:
        """
        Check engine data integrity

        Args:
            engine_id: Engine UUID, None means check all engines

        Returns:
            ServiceResult: Integrity check result
        """
        try:
            integrity_issues = []

            if engine_id:
                # 检查单个引擎
                engines = self._crud_repo.find(filters={'uuid': engine_id, 'is_del': False})
                engine_list = engines if isinstance(engines, list) else [engines]
            else:
                # 检查所有引擎
                engine_list = self._crud_repo.find(filters={'is_del': False}, as_dataframe=False)

            for engine in engine_list:
                if not engine:
                    continue

                # 检查必填字段
                if not engine.name:
                    integrity_issues.append(f"引擎 {engine.uuid}: 缺少名称")

                if not hasattr(engine, 'status') or engine.status is None:
                    integrity_issues.append(f"引擎 {engine.uuid}: 缺少状态")

                # 检查关联的投资组合映射
                mappings = self._mapping_repo.find(filters={'engine_id': engine.uuid, 'is_del': False})
                if mappings:
                    mapping_count = len(mappings) if isinstance(mappings, list) else len(mappings.index) if hasattr(mappings, 'index') else 1
                    if mapping_count > 100:  # 假设一个引擎最多关联100个投资组合
                        integrity_issues.append(f"引擎 {engine.uuid}: 关联的投资组合数量过多 ({mapping_count})")

            if integrity_issues:
                return ServiceResult.error("发现数据完整性问题", data={'issues': integrity_issues})

            return ServiceResult.success({}, "数据完整性检查通过")

        except Exception as e:
            return ServiceResult.error(f"检查引擎数据完整性时发生错误: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def add(self, name: str, is_live: bool = False, description: str = None, **kwargs) -> ServiceResult:
        """
        创建新的回测引擎

        Args:
            name: 引擎名称
            is_live: 是否为实盘引擎
            description: 可选描述
            **kwargs: 其他参数

        Returns:
            ServiceResult: 创建结果
        """
        try:
            # 输入验证
            if not name or not name.strip():
                return ServiceResult.error("引擎名称不能为空")

            # 名称长度限制
            engine_name = name.strip()
            warnings = []
            if len(engine_name) > 50:
                original_name = engine_name
                engine_name = engine_name[:50]
                warnings.append(f"引擎名称过长，已从 {len(original_name)} 字符截断至 {len(engine_name)} 字符")

            # 检查引擎名称是否已存在
            if self._crud_repo.exists(filters={'name': engine_name, 'is_del': False}):
                return ServiceResult.error(f"引擎名称 '{engine_name}' 已存在")

            # 创建引擎记录，包含时间范围参数
            create_params = {
                'name': engine_name,
                'is_live': is_live,
                'status': ENGINESTATUS_TYPES.IDLE,
                'desc': description or f"{'实盘' if is_live else '回测'}引擎: {engine_name}",
                'source': SOURCE_TYPES.SIM,
            }

            # 添加时间范围参数（如果提供）
            if 'backtest_start_date' in kwargs:
                create_params['backtest_start_date'] = kwargs['backtest_start_date']
            if 'backtest_end_date' in kwargs:
                create_params['backtest_end_date'] = kwargs['backtest_end_date']

            # 添加broker_attitude参数（如果提供）
            if 'broker_attitude' in kwargs:
                create_params['broker_attitude'] = kwargs['broker_attitude']

            engine_record = self._crud_repo.create(**create_params)

            engine_info = {
                "uuid": engine_record.uuid,
                "name": engine_record.name,
                "is_live": engine_record.is_live,
                "status": (
                    engine_record.status.name
                    if hasattr(engine_record.status, "name")
                    else str(engine_record.status)
                ),
                "desc": engine_record.desc,
            }

            GLOG.INFO(f"成功创建引擎 '{engine_name}' (实盘: {is_live})")
            result = ServiceResult.success(
                data={"engine_info": engine_info},
                message=f"引擎创建成功"
            )
            # 添加警告信息
            if warnings:
                result.warnings.extend(warnings)
            return result

        except Exception as e:
            GLOG.ERROR(f"创建引擎失败 '{name}': {e}")
            return ServiceResult.error(f"创建引擎失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def update(self, engine_id: str, name: str = None, is_live: bool = None,
               description: str = None, status: ENGINESTATUS_TYPES = None, **kwargs) -> ServiceResult:
        """
        更新现有引擎信息 - 整合update_engine_status功能

        Args:
            engine_id: 引擎UUID
            name: 可选的新名称
            is_live: 可选的新实盘状态
            description: 可选的新描述
            status: 可选的新引擎状态
            **kwargs: 其他参数

        Returns:
            ServiceResult: 更新结果
        """
        try:
            # 输入验证
            if not engine_id or not engine_id.strip():
                return ServiceResult.error("引擎ID不能为空")

            updates = {}
            warnings = []

            # 处理名称更新
            if name is not None:
                if not name.strip():
                    return ServiceResult.error("引擎名称不能为空")
                if len(name) > 50:
                    warnings.append("引擎名称已截断至50个字符")
                    name = name[:50]

                # 检查名称冲突
                existing_engines = self._crud_repo.find(filters={'name': name.strip(), 'is_del': False})
                if existing_engines:
                    # 检查是否有其他引擎使用此名称
                    conflict_found = False
                    for engine in existing_engines:
                        if engine.uuid != engine_id:
                            conflict_found = True
                            break
                    if conflict_found:
                        return ServiceResult.error(f"引擎名称 '{name}' 已存在")

                updates["name"] = name.strip()

            # 处理其他更新字段
            if is_live is not None:
                updates["is_live"] = is_live
            if description is not None:
                updates["desc"] = description
            if status is not None:
                if not isinstance(status, ENGINESTATUS_TYPES):
                    return ServiceResult.error(f"无效的引擎状态类型: {type(status)}")
                updates["status"] = status

            if not updates:
                return ServiceResult.success(
                    data={"engine_id": engine_id, "updates_applied": []},
                    message="未提供任何更新参数"
                )

            # 执行更新
            self._crud_repo.modify(
                filters={"uuid": engine_id},
                updates=updates
            )

            # 获取更新后的引擎信息
            updated_engines = self._crud_repo.find(filters={"uuid": engine_id})
            if not updated_engines:
                return ServiceResult.error(f"更新后找不到引擎 {engine_id}")
            updated_engine = updated_engines[0]

            GLOG.INFO(f"成功更新引擎 {engine_id}，更新字段: {list(updates.keys())}")

            return ServiceResult.success(
                    data={
                        "engine_id": engine_id,
                        "engine_info": {
                            "uuid": updated_engine.uuid,
                            "name": updated_engine.name,
                            "is_live": updated_engine.is_live,
                            "status": updated_engine.status.name if hasattr(updated_engine.status, 'name') else str(updated_engine.status),
                            "description": updated_engine.desc
                        },
                        "updates_applied": list(updates.keys()),
                        "warnings": warnings
                    },
                    message=f"引擎更新成功: {engine_id}"
                )

        except Exception as e:
            GLOG.ERROR(f"更新引擎失败 {engine_id}: {str(e)}")
            return ServiceResult.error(f"更新引擎失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def set_status(self, engine_id: str, status) -> ServiceResult:
        """
        更新引擎状态

        Args:
            engine_id: 引擎UUID
            status: 新的引擎状态 (支持 ENGINESTATUS_TYPES 枚举或 int 值)

        Returns:
            ServiceResult: 操作结果
        """
        try:
            # 输入验证
            if not engine_id or not engine_id.strip():
                return ServiceResult.error("引擎ID不能为空")

            # 支持枚举和整数两种类型
            status_value = None
            if isinstance(status, ENGINESTATUS_TYPES):
                status_value = status.value
            elif isinstance(status, int):
                status_value = status
                # 验证整数是否为有效的枚举值
                try:
                    status = ENGINESTATUS_TYPES(status)
                except ValueError:
                    return ServiceResult.error(f"无效的引擎状态值: {status}")
            else:
                return ServiceResult.error(f"无效的引擎状态类型: {type(status)}")

            # 检查引擎是否存在
            exists_result = self.exists(engine_id=engine_id)
            if not exists_result.is_success():
                return ServiceResult.error(f"检查引擎存在性失败: {exists_result.error}")

            if not exists_result.data.get("exists", False):
                return ServiceResult.error(f"引擎不存在: {engine_id}")

            # 更新状态 - 使用数值而不是枚举对象
            with self._crud_repo.get_session() as session:
                updated_count = self._crud_repo.modify(
                    filters={"uuid": engine_id}, updates={"status": status_value}, session=session
                )

                if updated_count == 0:
                    return ServiceResult.error(f"更新失败，未找到引擎: {engine_id}")

                status_name = status.name if hasattr(status, "name") else str(status)
                GLOG.INFO(f"引擎 {engine_id} 状态已更新为: {status_name}")

                return ServiceResult.success(
                    data={
                        "engine_id": engine_id,
                        "new_status": status_name,
                        "updated_count": updated_count
                    },
                    message=f"引擎状态更新成功: {engine_id} -> {status_name}"
                )

        except Exception as e:
            GLOG.ERROR(f"更新引擎状态失败 {engine_id}: {str(e)}")
            return ServiceResult.error(f"更新引擎状态失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def delete(self, engine_id: str, **kwargs) -> ServiceResult:
        """
        删除引擎 - 包括清理相关的投资组合映射

        Args:
            engine_id: 引擎UUID
            **kwargs: 其他参数

        Returns:
            ServiceResult: 删除结果
        """
        try:
            # 输入验证
            if not engine_id or not engine_id.strip():
                return ServiceResult.error("引擎ID不能为空")

            warnings = []

            with self._crud_repo.get_session() as session:
                # 清理引擎-投资组合映射
                mappings_deleted = 0
                try:
                    mappings_deleted = self._mapping_repo.remove(
                        filters={"engine_id": engine_id}, session=session
                    )
                    if mappings_deleted and mappings_deleted > 0:
                        GLOG.INFO(f"删除引擎 {engine_id} 的 {mappings_deleted} 个投资组合映射")
                except Exception as e:
                    warnings.append(f"清理投资组合映射时出错: {str(e)}")

                # 软删除引擎记录 (设置is_del=True)
                self._crud_repo.soft_remove(filters={"uuid": engine_id})

                # 验证删除是否成功
                existing_engines = self._crud_repo.find(filters={"uuid": engine_id, "is_del": False})
                if existing_engines:
                    return ServiceResult.error(f"删除失败，引擎 {engine_id} 仍然存在")

                GLOG.INFO(f"成功删除引擎 {engine_id}")

                return ServiceResult.success(
                    data={
                        "engine_id": engine_id,
                        "deleted_count": 1,
                        "mappings_deleted": mappings_deleted if mappings_deleted else 0,
                        "warnings": warnings
                    },
                    message=f"引擎删除成功: {engine_id}"
                )

        except Exception as e:
            GLOG.ERROR(f"删除引擎失败 {engine_id}: {str(e)}")
            return ServiceResult.error(f"删除引擎失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def delete_batch(self, engine_ids: List[str], **kwargs) -> ServiceResult:
        """
        批量删除引擎 - 包括清理相关的投资组合映射

        Args:
            engine_ids: 引擎UUID列表
            **kwargs: 其他参数

        Returns:
            ServiceResult: 批量删除结果
        """
        try:
            # 输入验证
            if not engine_ids:
                return ServiceResult.success(
                    data={
                        "total_requested": 0,
                        "successful_deletions": 0,
                        "failed_deletions": 0,
                        "total_mappings_deleted": 0,
                        "warnings": ["空的引擎列表"]
                    },
                    message="未提供要删除的引擎列表"
                )

            successful_deletions = 0
            failed_deletions = 0
            total_mappings_deleted = 0
            warnings = []
            failures = []

            for engine_id in engine_ids:
                try:
                    # 调用标准delete方法
                    delete_result = self.delete(engine_id)
                    if delete_result.is_success():
                        successful_deletions += 1
                        total_mappings_deleted += delete_result.data.get("mappings_deleted", 0)

                        # 收集警告信息
                        if delete_result.data.get("warnings"):
                            warnings.extend(delete_result.data["warnings"])
                    else:
                        failed_deletions += 1
                        failures.append({
                            "engine_id": engine_id,
                            "error": delete_result.error
                        })
                except Exception as e:
                    failed_deletions += 1
                    failures.append({
                        "engine_id": engine_id,
                        "error": f"意外错误: {str(e)}"
                    })
                    GLOG.ERROR(f"删除引擎 {engine_id} 时发生异常: {e}")

            # 判断整体成功状态
            overall_success = failed_deletions == 0

            GLOG.INFO(
                f"批量删除引擎完成: 成功 {successful_deletions}, 失败 {failed_deletions}, "
                f"清理映射 {total_mappings_deleted} 个"
            )

            return ServiceResult.success(
                data={
                    "total_requested": len(engine_ids),
                    "successful_deletions": successful_deletions,
                    "failed_deletions": failed_deletions,
                    "total_mappings_deleted": total_mappings_deleted,
                    "warnings": warnings,
                    "failures": failures
                },
                message=f"批量删除完成: 成功 {successful_deletions}, 失败 {failed_deletions}"
            ) if overall_success else ServiceResult.error(
                f"批量删除部分失败: {failed_deletions} 个引擎删除失败",
                data={
                    "total_requested": len(engine_ids),
                    "successful_deletions": successful_deletions,
                    "failed_deletions": failed_deletions,
                    "total_mappings_deleted": total_mappings_deleted,
                    "warnings": warnings,
                    "failures": failures
                }
            )

        except Exception as e:
            GLOG.ERROR(f"批量删除引擎失败: {str(e)}")
            return ServiceResult.error(f"批量删除引擎失败: {str(e)}")

    # 注意：重复的查询方法已删除
# - get_engines: 使用标准 get 方法替代
# - get_engine: 使用标准 get 方法替代
# - get_engine_status: 使用 get 方法获取引擎后提取 status
# - count_engines: 使用标准 count 方法替代

    # engine_exists方法已删除，使用标准exists方法替代

    @time_logger
    @retry(max_try=3)
    def add_portfolio(
        self, engine_id: str, portfolio_id: str, engine_name: str = None, portfolio_name: str = None, **kwargs
    ) -> ServiceResult:
        """
        添加引擎-投资组合映射

        Args:
            engine_id: 引擎UUID
            portfolio_id: 投资组合UUID
            engine_name: 可选的引擎名称
            portfolio_name: 可选的投资组合名称
            **kwargs: 其他参数

        Returns:
            ServiceResult: 映射结果
        """
        try:
            # 输入验证
            if not engine_id or not engine_id.strip():
                return ServiceResult.error("引擎ID不能为空")

            if not portfolio_id or not portfolio_id.strip():
                return ServiceResult.error("投资组合ID不能为空")

            warnings = []

            # 检查映射是否已存在
            try:
                existing_mappings = self.get_engine_portfolio_mappings(
                    engine_id=engine_id, portfolio_id=portfolio_id, as_dataframe=True
                )
                if not existing_mappings.empty:
                    return ServiceResult.error(f"投资组合 {portfolio_id} 已映射到引擎 {engine_id}")
            except Exception as e:
                warnings.append(f"检查现有映射时出错: {str(e)}")

            with self._mapping_repo.get_session() as session:
                mapping_record = self._mapping_repo.create(
                    engine_id=engine_id,
                    portfolio_id=portfolio_id,
                    engine_name=engine_name or "",
                    portfolio_name=portfolio_name or "",
                    session=session,
                )

                GLOG.INFO(f"成功将投资组合 {portfolio_id} 映射到引擎 {engine_id}")

                return ServiceResult.success(
                    data={
                        "engine_id": engine_id,
                        "portfolio_id": portfolio_id,
                        "mapping_info": {
                            "uuid": mapping_record.uuid,
                            "engine_id": mapping_record.engine_id,
                            "portfolio_id": mapping_record.portfolio_id,
                            "engine_name": mapping_record.engine_name,
                            "portfolio_name": mapping_record.portfolio_name,
                        },
                        "warnings": warnings
                    },
                    message=f"成功添加映射: 引擎 {engine_id} - 投资组合 {portfolio_id}"
                )

        except Exception as e:
            GLOG.ERROR(f"添加映射失败 引擎 {engine_id} - 投资组合 {portfolio_id}: {str(e)}")
            return ServiceResult.error(f"添加映射失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def remove_portfolio(self, engine_id: str, portfolio_id: str) -> ServiceResult:
        """
        从引擎中移除投资组合关联

        Args:
            engine_id: 引擎UUID
            portfolio_id: 投资组合UUID

        Returns:
            ServiceResult: 操作结果
        """
        try:
            # 输入验证
            if not engine_id or not engine_id.strip():
                return ServiceResult.error("引擎ID不能为空")

            if not portfolio_id or not portfolio_id.strip():
                return ServiceResult.error("投资组合ID不能为空")

            # 检查映射是否存在
            mappings_result = self.get_portfolios(engine_id=engine_id)
            if not mappings_result.is_success():
                return ServiceResult.error(f"查询投资组合映射失败: {mappings_result.error}")

            # 执行移除操作
            with self._mapping_repo.get_session() as session:
                removed_count = self._mapping_repo.soft_remove(
                    filters={"engine_id": engine_id, "portfolio_id": portfolio_id}, session=session
                )

                if removed_count == 0:
                    return ServiceResult.error(
                        f"未找到引擎 {engine_id} 与投资组合 {portfolio_id} 的映射关系"
                    )

                GLOG.INFO(f"成功移除投资组合 {portfolio_id} 与引擎 {engine_id} 的关联")

                return ServiceResult.success(
                    data={
                        "engine_id": engine_id,
                        "portfolio_id": portfolio_id,
                        "removed_count": removed_count
                    },
                    message=f"成功移除投资组合关联: {engine_id} - {portfolio_id}"
                )

        except Exception as e:
            GLOG.ERROR(f"移除投资组合关联失败 {engine_id} - {portfolio_id}: {str(e)}")
            return ServiceResult.error(f"移除投资组合关联失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def get_portfolios(
        self, engine_id: str = None, **kwargs
    ) -> ServiceResult:
        """
        获取引擎的投资组合映射

        Args:
            engine_id: 引擎UUID筛选
            **kwargs: 其他筛选条件

        Returns:
            ServiceResult: 投资组合映射数据
        """
        try:
            # 构建过滤条件
            filters = kwargs.get('filters', {})

            if engine_id:
                filters['engine_id'] = engine_id

            # 执行查询
            mappings = self._mapping_repo.find(filters=filters)

            # 提取投资组合ID列表
            portfolio_ids = []
            if mappings:
                if isinstance(mappings, list):
                    portfolio_ids = list(set(m.portfolio_id for m in mappings if hasattr(m, 'portfolio_id')))
                else:
                    # DataFrame的情况
                    if 'portfolio_id' in mappings.columns:
                        portfolio_ids = mappings['portfolio_id'].unique().tolist()

            GLOG.DEBUG(f"获取到引擎 {engine_id} 的 {len(portfolio_ids)} 个投资组合")

            return ServiceResult.success(
                data={
                    "portfolio_ids": portfolio_ids,
                    "mappings": mappings,
                    "count": len(portfolio_ids)
                },
                message=f"获取到{len(portfolio_ids)}个投资组合"
            )

        except Exception as e:
            GLOG.ERROR(f"获取投资组合映射失败: {str(e)}")
            return ServiceResult.error(f"获取投资组合映射失败: {str(e)}")

    # get_portfolios_for_engine方法已删除，功能合并到get_portfolios中

    # get_engines_for_portfolio方法已删除，功能可以通过get_portfolios方法实现

    @time_logger
    def exists(self, engine_id: str = None, name: str = None, **kwargs) -> ServiceResult:
        """
        检查引擎是否存在（标准化存在性检查）

        Args:
            engine_id: 引擎UUID
            name: 引擎名称
            **kwargs: 其他过滤条件

        Returns:
            ServiceResult: 存在性检查结果
        """
        try:
            filters = kwargs.get('filters', {})

            if engine_id:
                filters['uuid'] = engine_id
            if name:
                filters['name'] = name

            filters['is_del'] = False

            count = self._crud_repo.count(filters=filters)

            return ServiceResult.success(
                data={'exists': count > 0, 'count': count},
                message=f"引擎存在性检查完成"
            )

        except Exception as e:
            return ServiceResult.error(f"检查引擎存在性失败: {str(e)}")

    @time_logger
    def health_check(self) -> ServiceResult:
        """
        服务健康检查

        Returns:
            ServiceResult: 健康状态
        """
        try:
            # 检查数据库连接
            engine_count = self._crud_repo.count()

            # 检查依赖服务
            mapping_count = self._engine_portfolio_mapping_crud.count()
            param_count = self._param_crud.count()

            health_data = {
                'database_connection': 'ok',
                'engine_count': engine_count,
                'mapping_count': mapping_count,
                'param_count': param_count,
                'dependencies': {
                    'engine_portfolio_mapping_crud': 'ok',
                    'param_crud': 'ok'
                }
            }

            return ServiceResult.success(
                data=health_data,
                message="EngineService健康检查通过"
            )

        except Exception as e:
            return ServiceResult.error(f"健康检查失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def assemble(self, engine_id: str, **kwargs) -> ServiceResult:
        """
        通过EngineID装配回测引擎实例 - 数据库直接装配模式

        装配流程：
        1. 从engine_id收集所有配置数据
        2. 直接调用EngineAssemblyService程序化装配
        3. 参数通过数据库直接注入

        Args:
            engine_id: 引擎UUID
            **kwargs: 其他装配参数

        Returns:
            ServiceResult: 装配结果
        """
        try:
            # 1. 验证引擎存在性
            engine_result = self.get(engine_id=engine_id)
            if not engine_result.is_success():
                return ServiceResult.error(f"引擎不存在: {engine_id}")

            # 2. 收集配置数据
            config_data = self._collect_engine_config(engine_id)

            # 3. 调用EngineAssemblyService进行程序化装配
            assembly_service = self._dependencies.get('engine_assembly_service')
            if not assembly_service:
                return ServiceResult.error("缺少引擎装配服务依赖")

            assemble_result = assembly_service.assemble_backtest_engine(
                engine_id=engine_id,
                engine_data=config_data["engine_data"],
                portfolio_mappings=config_data["portfolio_mappings"],
                engine_params=config_data["engine_params"]
            )

            return ServiceResult.success(
                data=assemble_result.data,
                message=f"引擎装配成功: {engine_id}"
            )

        except Exception as e:
            return ServiceResult.error(f"引擎装配失败: {str(e)}")

    def _collect_engine_config(self, engine_id: str) -> Dict[str, Any]:
        """
        从数据库收集引擎配置数据

        Args:
            engine_id: 引擎UUID

        Returns:
            Dict[str, Any]: 配置数据
        """
        # 从Engine CRUD获取基础信息
        engine_info = self._crud_repo.get_by_uuid(engine_id)

        # 从EnginePortfolioMapping CRUD获取投资组合映射
        mappings = self._engine_portfolio_mapping_crud.get_engine_portfolio_mappings(engine_id=engine_id)

        # 从Param CRUD获取引擎参数
        params = self._param_crud.find(filters={"mapping_id": engine_id})

        return {
            "engine_data": {
                "uuid": engine_info.uuid,
                "name": engine_info.name,
                "is_live": engine_info.is_live,
                "status": engine_info.status,
                "description": engine_info.desc
            },
            "portfolio_mappings": [
                {
                    "portfolio_id": mapping.portfolio_id,
                    "engine_id": mapping.engine_id
                } for mapping in mappings
            ],
            "engine_params": {
                param.index: param.value for param in params
            }
        }

    def fuzzy_search(
        self,
        query: str,
        fields: Optional[List[str]] = None
    ) -> ServiceResult:
        """
        Fuzzy search engines across multiple fields with OR logic.

        Args:
            query: Search string
            fields: Fields to search in. Default: ['uuid', 'name', 'is_live', 'status']

        Returns:
            ServiceResult with list of engines data
        """
        try:
            if not query or not query.strip():
                return ServiceResult.success(ModelList([], self._crud_repo))

            # Delegate to CRUD layer for database-level fuzzy search
            results = self._crud_repo.fuzzy_search(query, fields)

            return ServiceResult.success(results)

        except Exception as e:
            return ServiceResult.error(f"Engine fuzzy search failed: {str(e)}")

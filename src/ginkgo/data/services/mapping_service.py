# Upstream: Trading Strategies, Analysis Modules, Backtest Engines
# Downstream: ClickHouse, MySQL, MongoDB
# Role: MappingService映射服务提供组件映射关系管理功能支持映射配置和查询支持交易系统功能支持相关功能






"""
Mapping Service - 统一管理所有映射关系

这个服务统一管理：
- Engine-Portfolio映射
- Portfolio-File组件映射
- Engine-Handler映射
- 参数管理

提供统一的接口和业务逻辑，避免在各个地方直接操作CRUD。
"""

from typing import List, Dict, Any, Optional
from ginkgo.libs import GLOG, time_logger, retry
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.models.model_engine_portfolio_mapping import MEnginePortfolioMapping
from ginkgo.data.models.model_portfolio_file_mapping import MPortfolioFileMapping
from ginkgo.data.models.model_engine_handler_mapping import MEngineHandlerMapping
from ginkgo.data.models.model_param import MParam
from ginkgo.enums import FILE_TYPES


class MappingService(BaseService):
    """映射关系管理服务"""

    def __init__(self, engine_portfolio_mapping_crud, portfolio_file_mapping_crud,
                 engine_handler_mapping_crud, param_crud):
        super().__init__(
            engine_portfolio_mapping_crud=engine_portfolio_mapping_crud,
            portfolio_file_mapping_crud=portfolio_file_mapping_crud,
            engine_handler_mapping_crud=engine_handler_mapping_crud,
            param_crud=param_crud
        )
        # 存储CRUD实例的引用
        self._engine_portfolio_mapping_crud = engine_portfolio_mapping_crud
        self._portfolio_file_mapping_crud = portfolio_file_mapping_crud
        self._engine_handler_mapping_crud = engine_handler_mapping_crud
        self._param_crud = param_crud

    # 清理方法 - 当关联对象不存在时自动清理
    @time_logger
    def cleanup_orphaned_mappings(self) -> ServiceResult:
        """清理孤立的映射关系（关联对象不存在的映射）"""
        try:
            from sqlalchemy import text
            from ginkgo.data.crud.engine_crud import EngineCRUD
            from ginkgo.data.crud.portfolio_crud import PortfolioCRUD
            from ginkgo.data.crud.file_crud import FileCRUD

            cleaned_count = 0
            cleaning_details = []

            with self._engine_portfolio_mapping_crud.get_session() as session:
                # 1. 清理孤立的Engine-Portfolio映射（Engine不存在）
                stmt = text("""
                    DELETE FROM engine_portfolio_mapping
                    WHERE engine_id NOT IN (SELECT uuid FROM engine WHERE is_del = 0)
                """)
                result = session.execute(stmt)
                count = result.rowcount
                if count > 0:
                    cleaned_count += count
                    cleaning_details.append(f"清理孤立Engine映射: {count} 个")

                # 2. 清理孤立的Engine-Portfolio映射（Portfolio不存在）
                stmt = text("""
                    DELETE FROM engine_portfolio_mapping
                    WHERE portfolio_id NOT IN (SELECT uuid FROM portfolio WHERE is_del = 0)
                """)
                result = session.execute(stmt)
                count = result.rowcount
                if count > 0:
                    cleaned_count += count
                    cleaning_details.append(f"清理孤立Portfolio映射: {count} 个")

                # 3. 清理孤立的Portfolio-File映射（Portfolio不存在）
                stmt = text("""
                    DELETE FROM portfolio_file_mapping
                    WHERE portfolio_id NOT IN (SELECT uuid FROM portfolio WHERE is_del = 0)
                """)
                result = session.execute(stmt)
                count = result.rowcount
                if count > 0:
                    cleaned_count += count
                    cleaning_details.append(f"清理孤立Portfolio-File映射: {count} 个")

                # 4. 清理孤立的Portfolio-File映射（File不存在）
                stmt = text("""
                    DELETE FROM portfolio_file_mapping
                    WHERE file_id NOT IN (SELECT uuid FROM file WHERE is_del = 0)
                """)
                result = session.execute(stmt)
                count = result.rowcount
                if count > 0:
                    cleaned_count += count
                    cleaning_details.append(f"清理孤立File映射: {count} 个")

                # 5. 清理孤立的Engine-Handler映射（Engine不存在）
                stmt = text("""
                    DELETE FROM engine_handler_mapping
                    WHERE engine_id NOT IN (SELECT uuid FROM engine WHERE is_del = 0)
                """)
                result = session.execute(stmt)
                count = result.rowcount
                if count > 0:
                    cleaned_count += count
                    cleaning_details.append(f"清理孤立Engine-Handler映射(Engine): {count} 个")

                # 6. 清理孤立的Engine-Handler映射（Handler不存在）
                stmt = text("""
                    DELETE FROM engine_handler_mapping
                    WHERE handler_id NOT IN (SELECT uuid FROM handler WHERE is_del = 0)
                """)
                result = session.execute(stmt)
                count = result.rowcount
                if count > 0:
                    cleaned_count += count
                    cleaning_details.append(f"清理孤立Engine-Handler映射(Handler): {count} 个")

                session.commit()

            if cleaned_count > 0:
                GLOG.INFO(f"清理了 {cleaned_count} 个孤立映射关系")
                for detail in cleaning_details:
                    GLOG.DEBUG(f"  - {detail}")
            else:
                GLOG.DEBUG("未发现孤立的映射关系")

            return ServiceResult.success({
                "cleaned_count": cleaned_count,
                "cleaning_details": cleaning_details
            }, f"清理完成，处理了 {cleaned_count} 个孤立映射")

        except Exception as e:
            return ServiceResult.error(f"清理孤立映射失败: {str(e)}")

    @time_logger
    def cleanup_by_names(self, name_pattern: str = "present_%") -> ServiceResult:
        """根据名称模式清理相关的所有映射关系"""
        try:
            from sqlalchemy import text

            with self._engine_portfolio_mapping_crud.get_session() as session:
                # 清理present_开头的对象相关的所有映射
                stmt = text("""
                    DELETE FROM portfolio_file_mapping
                    WHERE portfolio_id IN (
                        SELECT uuid FROM portfolio WHERE name LIKE :pattern
                    )
                """)
                result = session.execute(stmt, {"pattern": name_pattern})
                portfolio_file_deleted = result.rowcount

                stmt = text("""
                    DELETE FROM engine_portfolio_mapping
                    WHERE engine_id IN (
                        SELECT uuid FROM engine WHERE name LIKE :pattern
                    ) OR portfolio_id IN (
                        SELECT uuid FROM portfolio WHERE name LIKE :pattern
                    )
                """)
                result = session.execute(stmt, {"pattern": name_pattern})
                engine_portfolio_deleted = result.rowcount

                # 清理 Engine-Handler 映射
                stmt = text("""
                    DELETE FROM engine_handler_mapping
                    WHERE engine_id IN (
                        SELECT uuid FROM engine WHERE name LIKE :pattern
                    ) OR handler_id IN (
                        SELECT uuid FROM handler WHERE name LIKE :pattern
                    )
                """)
                result = session.execute(stmt, {"pattern": name_pattern})
                engine_handler_deleted = result.rowcount

                session.commit()

                total_deleted = portfolio_file_deleted + engine_portfolio_deleted + engine_handler_deleted

                GLOG.INFO(f"根据名称模式 '{name_pattern}' 清理了 {total_deleted} 个映射关系")
                GLOG.DEBUG(f"  - Portfolio-File映射: {portfolio_file_deleted} 个")
                GLOG.DEBUG(f"  - Engine-Portfolio映射: {engine_portfolio_deleted} 个")
                GLOG.DEBUG(f"  - Engine-Handler映射: {engine_handler_deleted} 个")

                return ServiceResult.success({
                    "total_deleted": total_deleted,
                    "portfolio_file_deleted": portfolio_file_deleted,
                    "engine_portfolio_deleted": engine_portfolio_deleted,
                    "engine_handler_deleted": engine_handler_deleted
                }, f"根据名称模式清理了 {total_deleted} 个映射关系")

        except Exception as e:
            return ServiceResult.error(f"根据名称模式清理映射失败: {str(e)}")

    @time_logger
    def cleanup_orphaned_handler_mappings(self) -> ServiceResult:
        """清理孤立的Engine-Handler映射关系（关联对象不存在的映射）

        注意：此方法只清理映射关系，不会删除Handler实体本身
        """
        try:
            from sqlalchemy import text

            cleaned_count = 0
            cleaning_details = []

            with self._engine_handler_mapping_crud.get_session() as session:
                # 1. 清理孤立的Engine-Handler映射（Engine不存在）
                stmt = text("""
                    DELETE FROM engine_handler_mapping
                    WHERE engine_id NOT IN (SELECT uuid FROM engine WHERE is_del = 0)
                """)
                result = session.execute(stmt)
                count = result.rowcount
                if count > 0:
                    cleaned_count += count
                    cleaning_details.append(f"清理孤立Engine映射: {count} 个")

                # 2. 清理孤立的Engine-Handler映射（Handler不存在）
                stmt = text("""
                    DELETE FROM engine_handler_mapping
                    WHERE handler_id NOT IN (SELECT uuid FROM handler WHERE is_del = 0)
                """)
                result = session.execute(stmt)
                count = result.rowcount
                if count > 0:
                    cleaned_count += count
                    cleaning_details.append(f"清理孤立Handler映射: {count} 个")

                session.commit()

            if cleaned_count > 0:
                GLOG.INFO(f"清理了 {cleaned_count} 个孤立Engine-Handler映射关系")
                for detail in cleaning_details:
                    GLOG.DEBUG(f"  - {detail}")
            else:
                GLOG.DEBUG("未发现孤立的Engine-Handler映射关系")

            return ServiceResult.success({
                "cleaned_count": cleaned_count,
                "cleaning_details": cleaning_details
            }, f"清理完成，处理了 {cleaned_count} 个孤立映射")

        except Exception as e:
            return ServiceResult.error(f"清理孤立Engine-Handler映射失败: {str(e)}")

    @time_logger
    def cleanup_handler_mappings_by_names(self, name_pattern: str = "present_%") -> ServiceResult:
        """根据名称模式清理Engine-Handler映射关系

        注意：此方法只清理映射关系，不会删除Handler实体本身

        Args:
            name_pattern: 名称模式，默认清理 present_ 开头的对象相关映射
        """
        try:
            from sqlalchemy import text

            with self._engine_handler_mapping_crud.get_session() as session:
                # 清理 Engine-Handler 映射
                stmt = text("""
                    DELETE FROM engine_handler_mapping
                    WHERE engine_id IN (
                        SELECT uuid FROM engine WHERE name LIKE :pattern
                    ) OR handler_id IN (
                        SELECT uuid FROM handler WHERE name LIKE :pattern
                    )
                """)
                result = session.execute(stmt, {"pattern": name_pattern})
                deleted_count = result.rowcount

                session.commit()

            GLOG.INFO(f"根据名称模式 '{name_pattern}' 清理了 {deleted_count} 个Engine-Handler映射关系")

            return ServiceResult.success({
                "deleted_count": deleted_count
            }, f"根据名称模式清理了 {deleted_count} 个Engine-Handler映射关系")

        except Exception as e:
            return ServiceResult.error(f"根据名称模式清理Engine-Handler映射失败: {str(e)}")

    # Engine-Portfolio映射方法
    @time_logger
    @retry(max_try=3)
    def create_engine_portfolio_mapping(self, engine_uuid: str, portfolio_uuid: str,
                                       engine_name: str = None, portfolio_name: str = None) -> ServiceResult:
        """创建Engine-Portfolio映射关系"""
        try:
            # 检查是否已存在
            existing = self._engine_portfolio_mapping_crud.find(
                filters={"engine_id": engine_uuid, "portfolio_id": portfolio_uuid}
            )

            if len(existing) > 0:
                return ServiceResult.success(existing[0], "映射关系已存在")

            # 创建新映射
            mapping = MEnginePortfolioMapping(
                engine_id=engine_uuid,
                portfolio_id=portfolio_uuid,
                engine_name=engine_name or "unknown",
                portfolio_name=portfolio_name or "unknown"
            )

            try:
                result = self._engine_portfolio_mapping_crud.add_batch([mapping])
                # ModelList没有success属性，只要没有异常就认为成功
                if result and len(result) > 0:
                    GLOG.INFO(f"创建Engine-Portfolio映射: {engine_uuid} -> {portfolio_uuid}")
                    return ServiceResult.success(result[0], "映射创建成功")
                else:
                    return ServiceResult.error("映射创建失败: 返回结果为空")
            except Exception as e:
                return ServiceResult.error(f"映射创建失败: {str(e)}")

        except Exception as e:
            return ServiceResult.error(f"创建Engine-Portfolio映射失败: {str(e)}")

    @time_logger
    def get_engine_portfolio_mapping(self, engine_uuid: str = None, portfolio_uuid: str = None) -> ServiceResult:
        """获取Engine-Portfolio映射关系"""
        try:
            filters = {}
            if engine_uuid:
                filters["engine_id"] = engine_uuid
            if portfolio_uuid:
                filters["portfolio_id"] = portfolio_uuid

            mappings = self._engine_portfolio_mapping_crud.find(filters=filters)
            return ServiceResult.success(mappings, f"找到 {len(mappings)} 个映射")

        except Exception as e:
            return ServiceResult.error(f"获取Engine-Portfolio映射失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def delete_engine_portfolio_mapping(self, engine_uuid: str, portfolio_uuid: str) -> ServiceResult:
        """删除Engine-Portfolio映射关系"""
        try:
            filters = {"engine_id": engine_uuid, "portfolio_id": portfolio_uuid}
            deleted_count = self._engine_portfolio_mapping_crud.remove(filters=filters)

            if deleted_count == 0:
                return ServiceResult.error("未找到要删除的映射关系")

            GLOG.INFO(f"删除Engine-Portfolio映射: {engine_uuid} -> {portfolio_uuid}")
            return ServiceResult.success({
                "deleted_count": deleted_count
            }, f"成功删除映射关系")

        except Exception as e:
            return ServiceResult.error(f"删除Engine-Portfolio映射失败: {str(e)}")

    # Portfolio-File组件映射方法
    @time_logger
    @retry(max_try=3)
    def create_portfolio_file_binding(self, portfolio_uuid: str, file_uuid: str,
                                      file_name: str, file_type: FILE_TYPES) -> ServiceResult:
        """创建Portfolio-File组件绑定关系"""
        try:
            # 检查是否已存在
            existing = self._portfolio_file_mapping_crud.find(
                filters={"portfolio_id": portfolio_uuid, "file_id": file_uuid}
            )

            if len(existing) > 0:
                return ServiceResult.success(existing[0], "绑定关系已存在")

            # 创建新绑定
            mapping = MPortfolioFileMapping(
                portfolio_id=portfolio_uuid,
                file_id=file_uuid,
                name=file_name,
                type=file_type.value
            )

            try:
                result = self._portfolio_file_mapping_crud.add_batch([mapping])
                # ModelList没有success属性，只要没有异常就认为成功
                if result and len(result) > 0:
                    GLOG.INFO(f"创建Portfolio-File绑定: {file_name} ({file_type.name}) -> Portfolio {portfolio_uuid}")
                    return ServiceResult.success(result[0], "绑定创建成功")
                else:
                    return ServiceResult.error("绑定创建失败: 返回结果为空")
            except Exception as e:
                return ServiceResult.error(f"绑定创建失败: {str(e)}")

        except Exception as e:
            return ServiceResult.error(f"创建Portfolio-File绑定失败: {str(e)}")

    @time_logger
    def get_portfolio_file_bindings(self, portfolio_uuid: str, file_type: FILE_TYPES = None) -> ServiceResult:
        """获取Portfolio的File绑定关系"""
        try:
            filters = {"portfolio_id": portfolio_uuid}
            if file_type:
                filters["type"] = file_type.value

            bindings = self._portfolio_file_mapping_crud.find(filters=filters)
            return ServiceResult.success(bindings, f"找到 {len(bindings)} 个绑定")

        except Exception as e:
            return ServiceResult.error(f"获取Portfolio-File绑定失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def delete_portfolio_file_binding(self, portfolio_uuid: str, file_uuid: str) -> ServiceResult:
        """删除Portfolio-File组件绑定关系"""
        try:
            filters = {"portfolio_id": portfolio_uuid, "file_id": file_uuid}
            deleted_count = self._portfolio_file_mapping_crud.remove(filters=filters)

            if deleted_count == 0:
                return ServiceResult.error("未找到要删除的绑定关系")

            GLOG.INFO(f"删除Portfolio-File绑定: {file_uuid} -> Portfolio {portfolio_uuid}")
            return ServiceResult.success({
                "deleted_count": deleted_count
            }, f"成功删除绑定关系")

        except Exception as e:
            return ServiceResult.error(f"删除Portfolio-File绑定失败: {str(e)}")

    # 批量绑定方法
    @time_logger
    def create_preset_bindings(self, engine_uuid: str, portfolio_uuid: str,
                                binding_rules: Dict[str, List[Dict]]) -> ServiceResult:
        """根据规则创建预设绑定关系

        Args:
            engine_uuid: Engine UUID
            portfolio_uuid: Portfolio UUID
            binding_rules: 绑定规则字典，例如：
                {
                    "selectors": [{"name": "fixed_selector", "type": FILE_TYPES.SELECTOR}],
                    "strategies": [{"name": "random_strategy", "type": FILE_TYPES.STRATEGY}]
                }
        """
        try:
            from ginkgo.data.containers import container
            file_service = container.file_service()

            bindings_created = 0
            binding_details = []

            # 1. 创建Engine-Portfolio绑定
            engine_result = self.create_engine_portfolio_mapping(
                engine_uuid, portfolio_uuid, "preset_backtest_engine", "preset_portfolio_demo"
            )
            if engine_result.success:
                bindings_created += 1
                binding_details.append(f"Engine-Portfolio: {engine_uuid} -> {portfolio_uuid}")

            # 2. 创建Portfolio-File绑定
            for component_type, components in binding_rules.items():
                # 根据组件类型获取对应的文件类型枚举
                type_mapping = {
                    "selectors": FILE_TYPES.SELECTOR,
                    "sizers": FILE_TYPES.SIZER,
                    "strategies": FILE_TYPES.STRATEGY,
                    "analyzers": FILE_TYPES.ANALYZER,
                    "risk_managers": FILE_TYPES.RISKMANAGER
                }

                file_type_enum = type_mapping.get(component_type)
                if not file_type_enum:
                    GLOG.WARN(f"未知的组件类型: {component_type}")
                    continue

                # 获取对应类型的文件
                files_result = file_service.get_by_type(file_type_enum)
                if not files_result.success:
                    GLOG.WARN(f"未找到 {component_type} 类型的文件")
                    continue

                # 获取文件列表（FileService返回的是包含'files'键的字典）
                files_list = files_result.data.get('files', [])
                if not files_list:
                    GLOG.WARN(f"未找到 {component_type} 类型的文件")
                    continue

                # 为每个组件规则创建绑定
                for component_rule in components:
                    rule_name = component_rule.get("name")
                    if not rule_name:
                        continue

                    # 查找匹配的文件
                    matching_files = [
                        f for f in files_list
                        if rule_name in f.name.lower()
                    ]

                    if not matching_files:
                        GLOG.WARN(f"未找到匹配的文件: {rule_name} (类型: {component_type})")
                        continue

                    # 绑定第一个匹配的文件
                    file = matching_files[0]
                    binding_result = self.create_portfolio_file_binding(
                        portfolio_uuid, file.uuid, file.name, file_type_enum
                    )

                    if binding_result.success:
                        bindings_created += 1
                        binding_details.append(f"{component_type}: {file.name} -> Portfolio {portfolio_uuid}")

            return ServiceResult.success({
                "bindings_created": bindings_created,
                "binding_details": binding_details
            }, f"成功创建 {bindings_created} 个绑定关系")

        except Exception as e:
            return ServiceResult.error(f"创建预设绑定失败: {str(e)}")

    # 参数管理方法
    @time_logger
    @retry(max_try=3)
    def create_component_parameters(self, mapping_uuid: str, file_uuid: str,
                                      parameters: Dict[int, str]) -> ServiceResult:
        """为组件创建参数（先删除旧参数再创建新参数）"""
        try:
            # 先删除该 mapping 的所有旧参数，避免重复
            try:
                self._param_crud.remove(filters={"mapping_id": mapping_uuid})
            except Exception:
                pass  # 忽略删除失败（可能没有旧参数）

            # 批量创建所有参数
            param_list = []
            param_details = []

            for index, value in parameters.items():
                param = MParam(
                    mapping_id=mapping_uuid,
                    index=index,
                    value=value
                )
                param_list.append(param)
                param_details.append(f"[{index}]: {value}")

            # 使用add_batch批量创建
            try:
                result = self._param_crud.add_batch(param_list)
                # ModelList没有success属性，只要没有异常就认为成功
                if result and len(result) > 0:
                    GLOG.INFO(f"成功为组件创建 {len(param_list)} 个参数")
                    return ServiceResult.success({
                        "params_created": len(param_list),
                        "param_details": param_details
                    }, f"成功创建 {len(param_list)} 个参数")
                else:
                    return ServiceResult.error("参数创建失败: 返回结果为空")
            except Exception as e:
                return ServiceResult.error(f"参数创建失败: {str(e)}")

        except Exception as e:
            return ServiceResult.error(f"创建组件参数失败: {str(e)}")

    @time_logger
    def get_portfolio_parameters(self, portfolio_uuid: str) -> ServiceResult:
        """获取Portfolio的所有参数"""
        try:
            params = self._param_crud.find(filters={"mapping_id": portfolio_uuid})
            return ServiceResult.success(params, f"找到 {len(params)} 个参数")

        except Exception as e:
            return ServiceResult.error(f"获取Portfolio参数失败: {str(e)}")

    # 工具方法
    def get_component_types_for_portfolio(self, portfolio_uuid: str) -> Dict[str, int]:
        """获取Portfolio绑定的组件类型统计"""
        try:
            result = self.get_portfolio_file_bindings(portfolio_uuid)
            if not result.success:
                return {}

            type_counts = {}
            for binding in result.data:
                file_type_name = f"Type_{binding.type}"
                type_counts[file_type_name] = type_counts.get(file_type_name, 0) + 1

            return type_counts

        except Exception as e:
            GLOG.ERROR(f"统计组件类型失败: {e}")
            return {}
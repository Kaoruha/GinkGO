from typing import Dict, Any, List, Optional, Union
import pandas as pd

from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.crud.param_crud import ParamCRUD
from ginkgo.data.models.model_param import MParam
from ginkgo.libs import GLOG, time_logger, retry


class ParamService(BaseService):
    """
    参数管理服务

    提供统一的参数管理功能，包括参数的增删改查、批量操作、
    参数验证和类型转换等业务方法。
    """

    def __init__(self):
        super().__init__()
        self._crud_repo = ParamCRUD()

    def _initialize_dependencies(self) -> None:
        """初始化依赖注入"""
        # ParamService通常不需要额外依赖，如果有可以在这里添加
        pass

    @time_logger
    @retry(max_try=3)
    def add(self, mapping_id: str, index: int, value: str, **kwargs) -> ServiceResult:
        """
        添加参数

        Args:
            mapping_id: 映射ID
            index: 参数索引
            value: 参数值
            **kwargs: 其他参数

        Returns:
            ServiceResult: 添加结果
        """
        try:
            # 输入验证
            if not mapping_id or not mapping_id.strip():
                return ServiceResult.error("映射ID不能为空")

            if index is None or index < 0:
                return ServiceResult.error("参数索引必须是非负整数")

            if value is None:
                return ServiceResult.error("参数值不能为空")

            # 检查是否已存在相同的参数
            existing_param = self._crud_repo.find(
                filters={"mapping_id": mapping_id, "index": index, "is_del": False},
                limit=1
            )
            if existing_param:
                return ServiceResult.error(f"映射 {mapping_id} 的索引 {index} 处已存在参数")

            # 创建参数记录
            param_record = self._crud_repo.create(
                mapping_id=mapping_id.strip(),
                index=int(index),
                value=str(value)
            )

            GLOG.INFO(f"成功添加参数: mapping_id={mapping_id}, index={index}")

            return ServiceResult.success(
                data={
                    "param_info": {
                        "uuid": param_record.uuid,
                        "mapping_id": param_record.mapping_id,
                        "index": param_record.index,
                        "value": param_record.value
                    }
                },
                message=f"成功添加参数: {mapping_id}[{index}]"
            )

        except Exception as e:
            GLOG.ERROR(f"添加参数失败: {str(e)}")
            return ServiceResult.error(f"添加参数失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def update(self, param_id: str = None, mapping_id: str = None, index: int = None,
               value: str = None, **kwargs) -> ServiceResult:
        """
        更新参数

        Args:
            param_id: 参数UUID（优先级高）
            mapping_id: 映射ID（与index配合使用）
            index: 参数索引（与mapping_id配合使用）
            value: 新的参数值
            **kwargs: 其他参数

        Returns:
            ServiceResult: 更新结果
        """
        try:
            updates = {}

            # 构建更新条件
            if param_id:
                filters = {"uuid": param_id}
            elif mapping_id and index is not None:
                filters = {"mapping_id": mapping_id, "index": int(index)}
            else:
                return ServiceResult.error("必须提供param_id或(mapping_id + index)")

            if value is not None:
                updates["value"] = str(value)

            if not updates:
                return ServiceResult.error("未提供要更新的字段")

            # 执行更新
            updated_count = self._crud_repo.modify(filters=filters, updates=updates)

            if updated_count == 0:
                return ServiceResult.error("未找到要更新的参数")

            # 获取更新后的参数信息
            updated_param = self._crud_repo.find(filters=filters, limit=1)
            if updated_param:
                param = updated_param[0]
                GLOG.INFO(f"成功更新参数: uuid={param.uuid}")

                return ServiceResult.success(
                    data={
                        "param_info": {
                            "uuid": param.uuid,
                            "mapping_id": param.mapping_id,
                            "index": param.index,
                            "value": param.value
                        }
                    },
                    message=f"成功更新参数: {param.mapping_id}[{param.index}]"
                )
            else:
                return ServiceResult.error("更新后无法获取参数信息")

        except Exception as e:
            GLOG.ERROR(f"更新参数失败: {str(e)}")
            return ServiceResult.error(f"更新参数失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def delete(self, param_id: str = None, mapping_id: str = None, index: int = None, **kwargs) -> ServiceResult:
        """
        删除参数

        Args:
            param_id: 参数UUID（优先级高）
            mapping_id: 映射ID（与index配合使用）
            index: 参数索引（与mapping_id配合使用）
            **kwargs: 其他参数

        Returns:
            ServiceResult: 删除结果
        """
        try:
            # 构建删除条件
            if param_id:
                filters = {"uuid": param_id}
            elif mapping_id and index is not None:
                filters = {"mapping_id": mapping_id, "index": int(index)}
            else:
                return ServiceResult.error("必须提供param_id或(mapping_id + index)")

            # 执行删除
            deleted_count = self._crud_repo.remove(filters=filters)

            if deleted_count == 0:
                return ServiceResult.error("未找到要删除的参数")

            GLOG.INFO(f"成功删除参数: deleted_count={deleted_count}")

            return ServiceResult.success(
                data={"deleted_count": deleted_count},
                message=f"成功删除参数: 删除数量 {deleted_count}"
            )

        except Exception as e:
            GLOG.ERROR(f"删除参数失败: {str(e)}")
            return ServiceResult.error(f"删除参数失败: {str(e)}")

    @time_logger
    def get(self, param_id: str = None, mapping_id: str = None, index: int = None,
            as_dataframe: bool = True, **kwargs) -> ServiceResult:
        """
        获取参数

        Args:
            param_id: 参数UUID（优先级高）
            mapping_id: 映射ID
            index: 参数索引
            as_dataframe: 是否返回DataFrame格式
            **kwargs: 其他过滤条件

        Returns:
            ServiceResult: 查询结果
        """
        try:
            # 构建查询条件
            if param_id:
                filters = {"uuid": param_id}
            elif mapping_id and index is not None:
                filters = {"mapping_id": mapping_id, "index": int(index)}
            else:
                filters = {}

            # 添加额外过滤条件
            filters.update(kwargs.get('filters', {}))
            if mapping_id:
                filters['mapping_id'] = mapping_id

            # 默认排除已删除记录
            filters['is_del'] = False

            # 执行查询
            result = self._crud_repo.find(filters=filters, as_dataframe=as_dataframe)

            return ServiceResult.success(result, f"成功获取参数数据")

        except Exception as e:
            GLOG.ERROR(f"获取参数失败: {str(e)}")
            return ServiceResult.error(f"获取参数失败: {str(e)}")

    @time_logger
    def count(self, mapping_id: str = None, **kwargs) -> ServiceResult:
        """
        统计参数数量

        Args:
            mapping_id: 映射ID过滤
            **kwargs: 其他过滤条件

        Returns:
            ServiceResult: 统计结果
        """
        try:
            filters = kwargs.get('filters', {})

            if mapping_id:
                filters['mapping_id'] = mapping_id

            # 默认排除已删除记录
            filters['is_del'] = False

            count = self._crud_repo.count(filters=filters)

            return ServiceResult.success({"count": count}, f"参数统计完成: {count} 条")

        except Exception as e:
            GLOG.ERROR(f"统计参数失败: {str(e)}")
            return ServiceResult.error(f"统计参数失败: {str(e)}")

    @time_logger
    def exists(self, param_id: str = None, mapping_id: str = None, index: int = None, **kwargs) -> ServiceResult:
        """
        检查参数是否存在

        Args:
            param_id: 参数UUID（优先级高）
            mapping_id: 映射ID
            index: 参数索引
            **kwargs: 其他过滤条件

        Returns:
            ServiceResult: 检查结果
        """
        try:
            # 构建检查条件
            if param_id:
                filters = {"uuid": param_id}
            elif mapping_id and index is not None:
                filters = {"mapping_id": mapping_id, "index": int(index)}
            else:
                filters = kwargs.get('filters', {})

            # 默认排除已删除记录
            filters['is_del'] = False

            exists = self._crud_repo.exists(filters=filters)

            return ServiceResult.success(
                {"exists": exists},
                f"参数存在性检查: {'存在' if exists else '不存在'}"
            )

        except Exception as e:
            GLOG.ERROR(f"检查参数存在性失败: {str(e)}")
            return ServiceResult.error(f"检查参数存在性失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def health_check(self) -> ServiceResult:
        """
        健康检查

        Returns:
            ServiceResult: 健康检查结果
        """
        try:
            # 检查CRUD连接
            param_count = self._crud_repo.count(filters={"is_del": False})

            health_status = {
                "status": "healthy",
                "param_count": param_count,
                "crud_connection": "ok"
            }

            return ServiceResult.success(health_status, "ParamService健康检查通过")

        except Exception as e:
            GLOG.ERROR(f"ParamService健康检查失败: {str(e)}")
            return ServiceResult.error(f"健康检查失败: {str(e)}")

    # ==================== 业务方法 ====================

    @time_logger
    @retry(max_try=3)
    def get_params_by_mapping(self, mapping_id: str, as_dataframe: bool = True, **kwargs) -> ServiceResult:
        """
        根据映射ID获取所有参数

        Args:
            mapping_id: 映射ID
            as_dataframe: 是否返回DataFrame格式
            **kwargs: 其他过滤条件

        Returns:
            ServiceResult: 参数列表
        """
        try:
            if not mapping_id or not mapping_id.strip():
                return ServiceResult.error("映射ID不能为空")

            filters = {"mapping_id": mapping_id.strip(), "is_del": False}
            filters.update(kwargs.get('filters', {}))

            # 按索引排序返回
            params = self._crud_repo.find(
                filters=filters,
                as_dataframe=as_dataframe,
                order_by=[("index", "asc")]
            )

            return ServiceResult.success(
                params,
                f"成功获取映射 {mapping_id} 的参数列表"
            )

        except Exception as e:
            GLOG.ERROR(f"获取映射参数失败: {str(e)}")
            return ServiceResult.error(f"获取映射参数失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def update_params_batch(self, mapping_id: str, params: Dict[int, str], **kwargs) -> ServiceResult:
        """
        批量更新映射的参数

        Args:
            mapping_id: 映射ID
            params: 参数字典 {index: value}
            **kwargs: 其他参数

        Returns:
            ServiceResult: 批量更新结果
        """
        try:
            if not mapping_id or not mapping_id.strip():
                return ServiceResult.error("映射ID不能为空")

            if not params or not isinstance(params, dict):
                return ServiceResult.error("参数字典不能为空")

            success_count = 0
            failed_updates = []

            for index, value in params.items():
                try:
                    if not isinstance(index, int) or index < 0:
                        failed_updates.append({"index": index, "error": "索引必须是非负整数"})
                        continue

                    update_result = self.update(
                        mapping_id=mapping_id,
                        index=index,
                        value=str(value)
                    )

                    if update_result.is_success():
                        success_count += 1
                    else:
                        failed_updates.append({
                            "index": index,
                            "error": update_result.error
                        })

                except Exception as e:
                    failed_updates.append({"index": index, "error": str(e)})

            total_count = len(params)
            result_data = {
                "mapping_id": mapping_id,
                "total_count": total_count,
                "success_count": success_count,
                "failed_count": total_count - success_count,
                "failed_updates": failed_updates
            }

            if success_count == total_count:
                message = f"批量更新成功: {success_count}/{total_count}"
                return ServiceResult.success(result_data, message)
            elif success_count > 0:
                message = f"批量更新部分成功: {success_count}/{total_count}"
                return ServiceResult.error(message, data=result_data)
            else:
                message = f"批量更新失败: 0/{total_count}"
                return ServiceResult.error(message, data=result_data)

        except Exception as e:
            GLOG.ERROR(f"批量更新参数失败: {str(e)}")
            return ServiceResult.error(f"批量更新参数失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def copy_params(self, source_mapping: str, target_mapping: str, **kwargs) -> ServiceResult:
        """
        复制参数从源映射到目标映射

        Args:
            source_mapping: 源映射ID
            target_mapping: 目标映射ID
            **kwargs: 其他参数

        Returns:
            ServiceResult: 复制结果
        """
        try:
            if not source_mapping or not source_mapping.strip():
                return ServiceResult.error("源映射ID不能为空")

            if not target_mapping or not target_mapping.strip():
                return ServiceResult.error("目标映射ID不能为空")

            if source_mapping == target_mapping:
                return ServiceResult.error("源映射和目标映射不能相同")

            # 获取源映射的所有参数
            source_result = self.get_params_by_mapping(source_mapping, as_dataframe=False)
            if not source_result.is_success():
                return ServiceResult.error(f"获取源映射参数失败: {source_result.error}")

            source_params = source_result.data
            if not source_params:
                return ServiceResult.success(
                    {"copied_count": 0},
                    f"源映射 {source_mapping} 没有参数需要复制"
                )

            # 清空目标映射的现有参数（可选）
            if kwargs.get('clear_target', False):
                clear_result = self.delete_mapping_params(target_mapping)
                if not clear_result.is_success():
                    GLOG.WARN(f"清空目标映射参数失败: {clear_result.error}")

            copied_count = 0
            failed_copies = []

            # 复制每个参数
            for param in source_params:
                try:
                    add_result = self.add(
                        mapping_id=target_mapping,
                        index=param.index,
                        value=param.value
                    )

                    if add_result.is_success():
                        copied_count += 1
                    else:
                        failed_copies.append({
                            "index": param.index,
                            "error": add_result.error
                        })

                except Exception as e:
                    failed_copies.append({
                        "index": param.index,
                        "error": str(e)
                    })

            total_count = len(source_params)
            result_data = {
                "source_mapping": source_mapping,
                "target_mapping": target_mapping,
                "total_count": total_count,
                "copied_count": copied_count,
                "failed_count": total_count - copied_count,
                "failed_copies": failed_copies
            }

            if copied_count == total_count:
                message = f"参数复制成功: {copied_count}/{total_count}"
                return ServiceResult.success(result_data, message)
            elif copied_count > 0:
                message = f"参数复制部分成功: {copied_count}/{total_count}"
                return ServiceResult.error(message, data=result_data)
            else:
                message = f"参数复制失败: 0/{total_count}"
                return ServiceResult.error(message, data=result_data)

        except Exception as e:
            GLOG.ERROR(f"复制参数失败: {str(e)}")
            return ServiceResult.error(f"复制参数失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def delete_mapping_params(self, mapping_id: str, **kwargs) -> ServiceResult:
        """
        删除指定映射的所有参数

        Args:
            mapping_id: 映射ID
            **kwargs: 其他参数

        Returns:
            ServiceResult: 删除结果
        """
        try:
            if not mapping_id or not mapping_id.strip():
                return ServiceResult.error("映射ID不能为空")

            # 删除该映射的所有参数
            deleted_count = self._crud_repo.remove(filters={"mapping_id": mapping_id})

            GLOG.INFO(f"删除映射 {mapping_id} 的参数: {deleted_count} 条")

            return ServiceResult.success(
                {"mapping_id": mapping_id, "deleted_count": deleted_count},
                f"成功删除映射 {mapping_id} 的参数: {deleted_count} 条"
            )

        except Exception as e:
            GLOG.ERROR(f"删除映射参数失败: {str(e)}")
            return ServiceResult.error(f"删除映射参数失败: {str(e)}")

    @time_logger
    def get_params_summary(self, mapping_id: str = None, **kwargs) -> ServiceResult:
        """
        获取参数汇总信息

        Args:
            mapping_id: 可选的映射ID过滤
            **kwargs: 其他过滤条件

        Returns:
            ServiceResult: 汇总信息
        """
        try:
            filters = {"is_del": False}
            if mapping_id:
                filters["mapping_id"] = mapping_id

            # 获取基础统计
            count_result = self.count(mapping_id=mapping_id)
            if not count_result.is_success():
                return ServiceResult.error(f"获取参数统计失败: {count_result.error}")

            total_count = count_result.data.get("count", 0)

            # 获取参数分布信息
            summary_data = {
                "total_params": total_count,
                "mapping_id": mapping_id,
                "unique_mappings": 0
            }

            if mapping_id:
                # 获取特定映射的详细信息
                params_result = self.get_params_by_mapping(mapping_id, as_dataframe=False)
                if params_result.is_success():
                    params = params_result.data
                    if params:
                        indices = [p.index for p in params]
                        summary_data.update({
                            "param_count": len(params),
                            "min_index": min(indices),
                            "max_index": max(indices),
                            "index_range": max(indices) - min(indices) + 1
                        })
            else:
                # 获取所有映射的汇总信息
                try:
                    all_params = self._crud_repo.find(filters={"is_del": False}, as_dataframe=True)
                    if all_params is not None and not all_params.empty:
                        unique_mappings = all_params["mapping_id"].nunique()
                        summary_data["unique_mappings"] = unique_mappings
                except Exception:
                    pass

            return ServiceResult.success(summary_data, "参数汇总信息获取成功")

        except Exception as e:
            GLOG.ERROR(f"获取参数汇总失败: {str(e)}")
            return ServiceResult.error(f"获取参数汇总失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def validate_params(self, mapping_id: str, **kwargs) -> ServiceResult:
        """
        验证映射参数的完整性和有效性

        Args:
            mapping_id: 映射ID
            **kwargs: 验证选项

        Returns:
            ServiceResult: 验证结果
        """
        try:
            if not mapping_id or not mapping_id.strip():
                return ServiceResult.error("映射ID不能为空")

            # 获取该映射的所有参数
            params_result = self.get_params_by_mapping(mapping_id, as_dataframe=False)
            if not params_result.is_success():
                return ServiceResult.error(f"获取映射参数失败: {params_result.error}")

            params = params_result.data
            validation_result = {
                "mapping_id": mapping_id,
                "is_valid": True,
                "issues": [],
                "warnings": [],
                "param_count": len(params),
                "indices": []
            }

            if not params:
                validation_result["warnings"].append("映射没有参数")
                return ServiceResult.success(validation_result, "验证完成：映射为空")

            # 收集索引信息
            indices = [p.index for p in params]
            validation_result["indices"] = indices

            # 检查索引重复
            index_counts = {}
            for idx in indices:
                index_counts[idx] = index_counts.get(idx, 0) + 1

            duplicate_indices = [idx for idx, count in index_counts.items() if count > 1]
            if duplicate_indices:
                validation_result["is_valid"] = False
                validation_result["issues"].append(f"存在重复索引: {duplicate_indices}")

            # 检查索引连续性（可选）
            if kwargs.get('check_continuity', False):
                sorted_indices = sorted(indices)
                expected_range = range(min(sorted_indices), max(sorted_indices) + 1)
                missing_indices = [i for i in expected_range if i not in sorted_indices]
                if missing_indices:
                    validation_result["warnings"].append(f"索引不连续，缺失索引: {missing_indices}")

            # 检查空值参数
            empty_params = [p for p in params if not p.value or not p.value.strip()]
            if empty_params:
                validation_result["warnings"].append(f"存在空值参数: {len(empty_params)} 个")

            # 检查参数值长度（可选）
            max_length = kwargs.get('max_value_length', 255)
            long_params = [p for p in params if len(p.value) > max_length]
            if long_params:
                validation_result["warnings"].append(f"存在超长参数值: {len(long_params)} 个")

            status_message = "参数验证通过" if validation_result["is_valid"] else "参数验证失败"
            return ServiceResult.success(validation_result, status_message)

        except Exception as e:
            GLOG.ERROR(f"参数验证失败: {str(e)}")
            return ServiceResult.error(f"参数验证失败: {str(e)}")
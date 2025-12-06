"""
Adjustfactor Data Service (Class-based)

This service, implemented as a class, handles the business logic for
synchronizing adjustment factor data. It relies on dependency injection
for its data source and CRUD repository, and manages transactions.

Enhanced with comprehensive error handling, retry mechanisms, and structured returns.
"""

import time
from datetime import datetime, timedelta
from typing import List, Union, Any, Dict
import pandas as pd

from ginkgo.libs import GCONF, datetime_normalize, cache_with_expiration, retry, to_decimal, time_logger
from ginkgo.libs.data.results import DataValidationResult, DataIntegrityCheckResult, DataSyncResult
from ginkgo.data import mappers
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.crud.model_conversion import ModelList


class AdjustfactorService(BaseService):
    def __init__(self, crud_repo, data_source, stockinfo_service):
        """Initializes the service with its dependencies."""
        super().__init__(crud_repo=crud_repo, data_source=data_source, stockinfo_service=stockinfo_service)

    # 注意：add、update、delete方法已移除，复权因子通过sync方法批量更新

    def get(self, code: str = None, **filters) -> ServiceResult:
        """
        获取复权因子信息记录

        Args:
            code: 股票代码（可选）
            **filters: 过滤条件

        Returns:
            ServiceResult: 操作结果
        """
        self._log_operation_start("get", code=code, **filters)
        try:
            # 构建查询过滤器
            query_filters = filters.copy()
            if code:
                query_filters["code"] = code

            # 执行查询
            data = self._crud_repo.find(filters=query_filters)

            self._log_operation_end("get", True)
            return ServiceResult.success(data=data, message="复权因子信息获取成功")

        except Exception as e:
            error_msg = f"获取复权因子信息失败: {str(e)}"
            self._logger.ERROR(error_msg)
            self._log_operation_end("get", False)
            return ServiceResult.error(error_msg)

    def exists(self, **filters) -> ServiceResult:
        """
        检查复权因子是否存在

        Args:
            **filters: 过滤条件

        Returns:
            ServiceResult: 操作结果，包含exists字段
        """
        self._log_operation_start("exists", **filters)
        try:
            # 基本的存在性检查
            code = filters.get("code")
            if code:
                count_result = self.count(code=code)
                exists = count_result.success and count_result.data > 0
            else:
                exists = False

            self._log_operation_end("exists", True)
            return ServiceResult.success(data={"exists": exists}, message="复权因子存在性检查完成")

        except Exception as e:
            error_msg = f"检查复权因子存在性失败: {str(e)}"
            self._logger.ERROR(error_msg)
            self._log_operation_end("exists", False)
            return ServiceResult.error(error_msg)

    def count(self, code: str = None, **filters) -> ServiceResult:
        """
        统计复权因子数量

        Args:
            code: 股票代码（可选）
            **filters: 过滤条件

        Returns:
            ServiceResult: 操作结果，包含count字段
        """
        self._log_operation_start("count", code=code, **filters)
        try:
            # 构建查询过滤器
            query_filters = filters.copy()
            if code:
                query_filters["code"] = code

            count = self._crud_repo.count(filters=query_filters)

            self._log_operation_end("count", True)
            return ServiceResult.success(data={"count": count}, message="复权因子数量统计完成")

        except Exception as e:
            error_msg = f"统计复权因子数量失败: {str(e)}"
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
            data_source_healthy = self._data_source and hasattr(self._data_source, 'fetch_cn_stock_adjustfactor')
            stockinfo_service_healthy = self._stockinfo_service and hasattr(self._stockinfo_service, 'get')

            # 检查数据库连接
            total_count = 0
            try:
                total_count = self.count().data or 0
            except:
                total_count = 0

            health_data = {
                "service_name": self._service_name,
                "status": "healthy" if data_source_healthy and stockinfo_service_healthy else "unhealthy",
                "dependencies": {
                    "data_source": "healthy" if data_source_healthy else "unavailable",
                    "stockinfo_service": "healthy" if stockinfo_service_healthy else "unavailable"
                },
                "total_records": total_count
            }

            return ServiceResult.success(data=health_data, message="AdjustfactorService健康检查完成")

        except Exception as e:
            error_msg = f"健康检查失败: {str(e)}"
            self._logger.ERROR(error_msg)
            return ServiceResult.error(error_msg)

    def validate(self, data: Dict) -> ServiceResult:
        """
        验证复权因子数据

        Args:
            data: 要验证的数据

        Returns:
            ServiceResult: 验证结果
        """
        try:
            if not isinstance(data, dict):
                return ServiceResult.error("数据必须是字典格式")

            # 检查必填字段
            required_fields = ['code', 'timestamp', 'adjustfactor']
            missing_fields = [field for field in required_fields if field not in data]

            if missing_fields:
                return ServiceResult.error(f"缺少必填字段: {', '.join(missing_fields)}")

            # 验证股票代码格式
            code = data.get('code')
            if not code or not isinstance(code, str) or len(code.strip()) == 0:
                return ServiceResult.error("股票代码格式无效")

            # 验证复权因子
            adjustfactor = data.get('adjustfactor')
            if adjustfactor is None or (isinstance(adjustfactor, (int, float)) and adjustfactor <= 0):
                return ServiceResult.error("复权因子必须为正数")

            return ServiceResult.success(data={"valid": True}, message="复权因子数据验证通过")

        except Exception as e:
            error_msg = f"验证复权因子数据失败: {str(e)}"
            self._logger.ERROR(error_msg)
            return ServiceResult.error(error_msg)

    def check_integrity(self, code: str = None, **filters) -> ServiceResult:
        """
        检查复权因子数据完整性

        Args:
            code: 股票代码（可选）
            **filters: 过滤条件

        Returns:
            ServiceResult: 完整性检查结果
        """
        try:
            integrity_issues = []

            if code:
                # 检查特定股票代码的完整性
                get_result = self.get(code=code)
                if not get_result.success:
                    integrity_issues.append(f"获取股票{code}数据失败: {get_result.error}")
                else:
                    records = get_result.data
                    if not records or len(records) == 0:
                        integrity_issues.append(f"股票{code}没有复权因子数据")
            else:
                # 检查整体服务完整性
                if not self._data_source:
                    integrity_issues.append("DataSource依赖不可用")
                if not self._stockinfo_service:
                    integrity_issues.append("StockinfoService依赖不可用")

            is_valid = len(integrity_issues) == 0

            return ServiceResult.success(
                data={
                    "valid": is_valid,
                    "issues": integrity_issues,
                    "code": code
                },
                message="复权因子完整性检查完成" if is_valid else f"发现{len(integrity_issues)}个完整性问题"
            )

        except Exception as e:
            error_msg = f"检查复权因子完整性失败: {str(e)}"
            self._logger.ERROR(error_msg)
            return ServiceResult.error(error_msg)

    @retry(max_try=3)
    def sync(self, code: str, start_date: datetime = None, end_date: datetime = None, **kwargs) -> ServiceResult:
        """
        Synchronizes adjustment factors for a single stock code.
        This method is transactional and includes enhanced error handling.

        Args:
            code: Stock code to sync
            start_date: Start date for sync (optional)
            end_date: End date for sync (optional)
            **kwargs: Additional parameters (fast_mode, etc.)

        Returns:
            ServiceResult with DataSyncResult data
        """
        fast_mode = kwargs.get('fast_mode', True)
        start_time = time.time()
        self._log_operation_start("sync", code=code, start_date=start_date, end_date=end_date, fast_mode=fast_mode)

        try:
            # Validate stock code
            exists_result = self._stockinfo_service.exists(code)
            if not exists_result.success or not exists_result.data:
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="adjustfactors",
                    entity_identifier=code,
                    sync_strategy="single"
                )
                sync_result.add_error(0, f"Stock code {code} not in stock list")
                return ServiceResult.failure(
                    message=f"Stock code {code} not in stock list",
                    data=sync_result
                )

            # Set date range
            if start_date is None or end_date is None:
                start_date = self._get_fetch_start_date(code, fast_mode)
                end_date = datetime.now()
            else:
                start_date = datetime_normalize(start_date)
                end_date = datetime_normalize(end_date)

            self._logger.INFO(f"Syncing adjustfactors for {code} from {start_date.date()} to {end_date.date()}")

            # Fetch data with retry mechanism
            try:
                raw_data = self._fetch_adjustfactor_data(code, start_date, end_date)
            except Exception as e:
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="adjustfactors",
                    entity_identifier=code,
                    sync_range=(start_date, end_date),
                    sync_strategy="single"
                )
                sync_result.add_error(0, f"Failed to fetch data from source: {e}")
                return ServiceResult.failure(
                    message=f"Failed to fetch data from source: {e}",
                    data=sync_result
                )

            if raw_data is None or raw_data.empty:
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="adjustfactors",
                    entity_identifier=code,
                    sync_range=(start_date, end_date),
                    sync_strategy="single"
                )
                sync_result.set_metadata("fast_mode", fast_mode)
                sync_result.add_warning("No new data available from source")
                return ServiceResult.success(
                    data=sync_result,
                    message=f"No new adjustfactor data available for {code}"
                )

            records_processed = len(raw_data)

            # Convert data with error handling
            models_to_add, mapping_errors = self._convert_to_models(raw_data, code)
            warnings = mapping_errors if mapping_errors else []

            if not models_to_add:
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="adjustfactors",
                    entity_identifier=code,
                    sync_range=(start_date, end_date),
                    sync_strategy="single"
                )
                sync_result.add_error(0, "No valid records after data conversion")
                return ServiceResult.failure(
                    message="No valid records after data conversion",
                    data=sync_result
                )

            # Database operations using new atomic replace/add method
            try:
                # Use new BaseCRUD.replace method for atomic operation
                if not fast_mode:
                    # For non-fast_mode, replace data in the time range of new records
                    min_date = min(item.timestamp for item in models_to_add)
                    max_date = max(item.timestamp for item in models_to_add)
                    filters = {
                        "code": code,
                        "timestamp__gte": min_date,
                        "timestamp__lte": max_date
                    }
                else:
                    # For fast_mode, replace all records for this code
                    filters = {"code": code}

                replaced_models = self._crud_repo.replace(filters=filters, new_items=models_to_add)
                records_added = len(replaced_models)

                # If replace returned empty (no existing data), use add_batch instead
                if records_added == 0:
                    inserted_models = self._crud_repo.add_batch(models_to_add)
                    records_added = len(inserted_models)
                    self._logger.INFO(f"Successfully inserted {records_added} new adjustfactors for {code}")
                else:
                    self._logger.INFO(f"Successfully replaced {records_added} adjustfactors for {code}")

                # Create successful sync result
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="adjustfactors",
                    entity_identifier=code,
                    sync_range=(start_date, end_date),
                    sync_strategy="single"
                )
                sync_result.records_processed = records_processed
                sync_result.records_added = records_added
                sync_result.set_metadata("fast_mode", fast_mode)
                for warning in warnings:
                    sync_result.add_warning(warning)

                duration = time.time() - start_time
                self._log_operation_end("sync", True, duration)

                return ServiceResult.success(
                    data=sync_result,
                    message=f"Successfully synced {records_added} adjustfactors for {code}"
                )

            except Exception as e:
                self._logger.ERROR(f"Failed to sync adjustfactors for {code}: {e}")
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="adjustfactors",
                    entity_identifier=code,
                    sync_range=(start_date, end_date),
                    sync_strategy="single"
                )
                sync_result.add_error(0, f"Database sync operation failed: {str(e)}")
                return ServiceResult.failure(
                    message=f"Database sync operation failed: {str(e)}",
                    data=sync_result
                )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation_end("sync", False, duration)
            sync_result = DataSyncResult.create_for_entity(
                entity_type="adjustfactors",
                entity_identifier=code,
                sync_strategy="single"
            )
            sync_result.add_error(0, f"Unexpected error during sync: {str(e)}")
            return ServiceResult.failure(
                message=f"Unexpected error during sync: {str(e)}",
                data=sync_result
            )

    @retry(max_try=3)
    def _fetch_adjustfactor_data(self, code: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Fetches adjustment factor data with retry mechanism.

        Args:
            code: Stock code
            start_date: Start date for data fetch
            end_date: End date for data fetch

        Returns:
            DataFrame with adjustment factor data or None if failed
        """
        try:
            raw_data = self._data_source.fetch_cn_stock_adjustfactor(code, start_date, end_date)
            return raw_data
        except Exception as e:
            self._logger.ERROR(f"Failed to fetch adjustfactors for {code} from source: {e}")
            raise  # Let retry decorator handle this

    def _convert_to_models(self, raw_data: pd.DataFrame, code: str) -> tuple:
        """
        Converts DataFrame to model objects with error tolerance.

        Args:
            raw_data: Raw data from source
            code: Stock code

        Returns:
            Tuple of (valid_models, error_messages)
        """
        models_to_add = []
        errors = []

        try:
            # Try batch conversion first
            models_to_add = mappers.dataframe_to_adjustfactor_models(raw_data, code)
            return models_to_add, errors
        except Exception as batch_error:
            self._logger.WARN(f"Batch conversion failed for {code}, trying row-by-row: {batch_error}")
            errors.append(f"Batch conversion failed: {batch_error}")

            # Fallback to row-by-row conversion
            for idx, row in raw_data.iterrows():
                try:
                    single_row_df = pd.DataFrame([row])
                    single_model = mappers.dataframe_to_adjustfactor_models(single_row_df, code)
                    if single_model:
                        models_to_add.extend(single_model)
                except Exception as row_error:
                    error_msg = f"Failed to convert row {idx}: {row_error}"
                    errors.append(error_msg)
                    self._logger.DEBUG(error_msg)
                    continue

        return models_to_add, errors

    
    def sync_batch(self, codes: List[str], fast_mode: bool = True) -> Dict[str, Any]:
        """
        Synchronizes adjustment factors for multiple stock codes with error tolerance.

        Args:
            codes: List of stock codes to sync
            fast_mode: If True, only fetch data from last available date

        Returns:
            Dictionary with batch sync results and statistics
        """
        from ginkgo.libs import RichProgress

        batch_result = {
            "total_codes": len(codes),
            "successful_codes": 0,
            "failed_codes": 0,
            "total_records_processed": 0,
            "total_records_added": 0,
            "results": [],
            "failures": [],
        }

        with RichProgress() as progress:
            task = progress.add_task("[cyan]Syncing Adjustfactor Data", total=len(codes))

            for code in codes:
                try:
                    progress.update(task, description=f"Processing {code}")
                    result = self.sync(code, fast_mode=fast_mode)

                    batch_result["results"].append(result)
                    batch_result["total_records_processed"] += result.data.records_processed

                    if result.success:
                        batch_result["successful_codes"] += 1
                        batch_result["total_records_added"] += result.data.records_added
                        progress.update(task, advance=1, description=f":white_check_mark: {code}")
                    else:
                        batch_result["failed_codes"] += 1
                        batch_result["failures"].append(
                            {"code": code, "error": result.message, "warnings": result.data.warnings if result.data else []}
                        )
                        progress.update(task, advance=1, description=f":x: {code}")

                except Exception as e:
                    batch_result["failed_codes"] += 1
                    error_msg = f"Unexpected error processing {code}: {e}"
                    batch_result["failures"].append({"code": code, "error": error_msg, "warnings": []})
                    self._logger.ERROR(error_msg)
                    progress.update(task, advance=1, description=f":x: {code}")
                    continue

        # Log summary
        self._logger.INFO(
            f"Batch adjustfactor sync completed: {batch_result['successful_codes']}/{batch_result['total_codes']} successful"
        )
        if batch_result["failures"]:
            self._logger.WARN(f"Failed to sync {batch_result['failed_codes']} codes")
            for failure in batch_result["failures"][:5]:  # Show first 5 failures
                self._logger.WARN(f"  - {failure['code']}: {failure['error']}")

        return batch_result

    @time_logger
    @retry(max_try=3)
    def get(
        self,
        code: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        **kwargs,
    ) -> ServiceResult:
        """
        Retrieves adjustment factor data from the database with caching.

        Args:
            code: Stock code filter
            start_date: Start date filter
            end_date: End date filter
            as_dataframe: Return format
            **kwargs: Additional filters

        Returns:
            ServiceResult containing adjustment factor data
        """
        try:
            # 提取filters参数并从kwargs中移除，避免重复传递
            filters = kwargs.pop("filters", {})

            # 具体参数优先级高于filters中的对应字段
            if code:
                filters["code"] = code
            if start_date:
                filters["timestamp__gte"] = start_date
            if end_date:
                filters["timestamp__lte"] = end_date

            # 调用CRUD并包装结果
            data = self._crud_repo.find(filters=filters, **kwargs)
            return ServiceResult.success(data)

        except Exception as e:
            error_msg = f"Failed to get adjustfactors: {e}"
            self._logger.ERROR(error_msg)
            return ServiceResult.error(error_msg)

    def calculate(self, code: str) -> ServiceResult:
        """
        为单个股票代码计算预计算的复权系数（原子安全版本）

        使用DataFrame进行高效的向量计算，基于原始的复权因子，
        计算该股票每个时间点的前复权和后复权系数。
        采用数据备份 + 恢复机制保证操作原子性，避免数据丢失。

        Args:
            code: 要处理的股票代码

        Returns:
            ServiceResult: 处理结果统计，包含操作状态和恢复信息
        """
        start_time = time.time()
        self._log_operation_start("calculate", code=code)

        # 优化：预先导入需要的模块，避免循环内重复导入
        from ginkgo.data.models.model_adjustfactor import MAdjustfactor

        # 备份信息
        backup_info = None
        original_records = []

        try:
            # 第一步：验证股票代码
            if not code:
                return ServiceResult.error("股票代码不能为空")

            # 第二步：获取并备份原始数据
            original_records = self._crud_repo.find(filters={"code": code})

            if len(original_records) < 2:
                return ServiceResult.success(
                    data={"code": code, "processed_records": 0, "backup_used": False},
                    message=f"股票 {code} 复权因子记录少于2条，无需处理"
                )

            # 创建备份信息
            backup_info = {
                "original_records": original_records,
                "record_count": len(original_records),
                "time_range": (min(r.timestamp for r in original_records),
                               max(r.timestamp for r in original_records)),
                "backup_timestamp": datetime.now()
            }

            self._logger.INFO(f"股票 {code} 备份 {len(original_records)} 条复权因子记录")

            # 第三步：执行计算逻辑
            self._logger.INFO(f"开始计算股票 {code} 的复权系数")

            # 转换为DataFrame进行高效计算
            df_records = original_records.to_dataframe()
            df_records = df_records.sort_values('timestamp').reset_index(drop=True)

            # 检查必要的字段
            if 'adjustfactor' not in df_records.columns:
                return ServiceResult.error(f"股票 {code} 数据缺少adjustfactor字段")

            # 优化：一次性处理adjustfactor列：转换类型 + 处理0值 + 统计
            df_records['adjustfactor'] = pd.to_numeric(df_records['adjustfactor'], errors='coerce').fillna(1.0)
            zero_mask = df_records['adjustfactor'] == 0
            zero_count = zero_mask.sum()
            if zero_count > 0:
                self._logger.WARN(f"股票 {code} 发现 {zero_count} 条记录的adjustfactor为0，将替换为1.0")
                df_records.loc[zero_mask, 'adjustfactor'] = 1.0

            # 使用DataFrame向量化计算复权系数
            original_factors = df_records['adjustfactor'].values

            # 验证原始因子数据
            if len(original_factors) == 0 or all(f == 1.0 for f in original_factors):
                self._logger.WARN(f"股票 {code} 的adjustfactor值全为1.0，计算结果可能与原始数据相同")

            # 计算前复权系数：相对于最新时间的系数
            latest_factor = original_factors[-1]
            fore_factors = latest_factor / original_factors

            # 计算后复权系数：相对于最早时间的系数
            earliest_factor = original_factors[0]
            back_factors = original_factors / earliest_factor

            # 优化：一次性更新DataFrame中的复权因子列（避免重复赋值）
            df_records['foreadjustfactor'] = fore_factors
            df_records['backadjustfactor'] = back_factors

            # 优化：更详细的统计日志
            self._logger.INFO(
                f"股票 {code} 复权因子计算完成 | "
                f"记录数: {len(df_records)} | "
                f"前复权范围: {fore_factors.min():.6f}-{fore_factors.max():.6f} | "
                f"后复权范围: {back_factors.min():.6f}-{back_factors.max():.6f}"
            )

            # 第五步：将DataFrame转换为MAdjustfactor列表
            try:
                # 优化：将导入语句移到方法顶部，避免循环内重复导入
                updated_entities = []
                for _, row in df_records.iterrows():
                    # 使用MAdjustfactor的Series更新功能，代码更简洁
                    entity = MAdjustfactor()
                    entity.update(row)  # singledispatch自动匹配Series更新
                    updated_entities.append(entity)

                self._logger.DEBUG(f"将DataFrame转换为 {len(updated_entities)} 个MAdjustfactor实体")

            except Exception as conversion_error:
                self._logger.ERROR(f"DataFrame转换为MAdjustfactor失败: {conversion_error}")
                return ServiceResult.error(f"数据转换失败: {str(conversion_error)}")

            if len(updated_entities) == 0:
                return ServiceResult.error(f"股票 {code} 计算后没有有效记录需要更新")

            # 第六步：执行原子替换操作
            self._logger.INFO(f"股票 {code} 开始原子替换：删除 {len(original_records)} 条，插入 {len(updated_entities)} 条")

            try:
                # 使用BaseCRUD的原子replace方法
                replaced_models = self._crud_repo.replace(filters={"code": code}, new_items=updated_entities)
                processed_count = len(replaced_models)
                self._logger.DEBUG(f"成功替换股票 {code} 的 {processed_count} 条复权因子记录")

                # 原子操作成功
                duration = time.time() - start_time
                self._log_operation_end("calculate", True, duration)

                return ServiceResult.success(
                    data={
                        "code": code,
                        "original_records": len(original_records),
                        "processed_records": processed_count,
                        "backup_used": False,
                        "backup_restored": False,
                        "fore_factor_range": (float(fore_factors.min()), float(fore_factors.max())),
                        "back_factor_range": (float(back_factors.min()), float(back_factors.max())),
                        "original_factor_range": (float(original_factors.min()), float(original_factors.max())),
                        "processing_time_seconds": duration
                    },
                    message=f"股票 {code} 成功计算并原子替换 {processed_count} 条复权因子记录"
                )

            except Exception as operation_error:
                # replace操作失败，无需回滚（BaseCRUD已处理原子性）
                self._logger.ERROR(f"股票 {code} 复权因子替换失败: {str(operation_error)}")

                duration = time.time() - start_time
                self._log_operation_end("calculate", False, duration)

                return ServiceResult.error(
                    data={
                        "code": code,
                        "original_records": len(original_records),
                        "processed_records": 0,
                        "backup_used": True,
                        "backup_restored": False,
                        "error_details": str(operation_error),
                        "processing_time_seconds": duration
                    },
                    error=f"复权因子替换失败: {str(operation_error)}"
                )

        except Exception as e:
            # 第七步：全局异常处理
            duration = time.time() - start_time
            self._log_operation_end("calculate", False, duration)
            error_msg = f"计算股票 {code} 复权因子失败: {str(e)}"
            self._logger.ERROR(error_msg)

            # 如果有备份数据，尝试恢复
            if backup_info and len(backup_info["original_records"]) > 0:
                try:
                    self._logger.ERROR(f"尝试从备份恢复股票 {code} 数据")
                    self._crud_repo.add_batch(backup_info["original_records"])
                    error_msg += " (已从备份恢复原始数据)"
                except Exception as restore_error:
                    self._logger.CRITICAL(f"股票 {code} 备份恢复也失败: {str(restore_error)}")
                    error_msg += f" (备份恢复也失败: {str(restore_error)})"

            return ServiceResult.error(error_msg)

    def get_latest_adjustfactor_for_code(self, code: str) -> datetime:
        """
        Gets the latest adjustment factor timestamp for a specific code.

        Args:
            code: Stock code

        Returns:
            Latest timestamp or default start date if no data exists
        """
        latest_records = self._crud_repo.find(filters={"code": code}, page_size=1, order_by="timestamp", desc_order=True)

        if latest_records:
            return latest_records[0].timestamp
        else:
            return datetime_normalize(GCONF.DEFAULTSTART)

    def count(self, code: str = None, **kwargs) -> ServiceResult:
        """
        Counts the number of adjustment factor records matching the filters.

        Args:
            code: Stock code filter
            **kwargs: Additional filters

        Returns:
            ServiceResult with count data
        """
        try:
            # 提取filters参数并从kwargs中移除，避免重复传递
            filters = kwargs.pop("filters", {})

            # 具体参数优先级高于filters中的对应字段
            if code:
                filters["code"] = code

            count = self._crud_repo.count(filters=filters)
            return ServiceResult.success(count)

        except Exception as e:
            error_msg = f"Failed to count adjustfactors: {e}"
            self._logger.ERROR(error_msg)
            return ServiceResult.error(error_msg)

    def get_available_codes(self) -> List[str]:
        """
        Gets list of available stock codes that have adjustment factor data.

        Returns:
            List of unique stock codes
        """
        return self._crud_repo.find(distinct_field="code")

    def _get_fetch_start_date(self, code: str, fast_mode: bool) -> datetime:
        if not fast_mode:
            try:
                stockinfo_result = self._stockinfo_service.get(filters={"code": code}, page_size=1)
                stockinfo = stockinfo_result.data[0] if stockinfo_result.success and stockinfo_result.data else None
                date = stockinfo.list_date if stockinfo and hasattr(stockinfo, 'list_date') else datetime_normalize(GCONF.DEFAULTSTART)
            except Exception as e:
                date = datetime_normalize(GCONF.DEFAULTSTART)
            return date

        latest_timestamp = self.get_latest_adjustfactor_for_code(code)
        return latest_timestamp + timedelta(days=1)

    def validate(self, code: str, start_date: datetime = None, end_date: datetime = None, **kwargs) -> ServiceResult:
        """
        Validates adjustfactor data for business rules and data quality.

        Args:
            code: Stock code to validate
            start_date: Start date for validation (optional)
            end_date: End date for validation (optional)
            **kwargs: Additional parameters

        Returns:
            ServiceResult with DataValidationResult data
        """
        start_time = time.time()
        self._log_operation_start("validate", code=code, start_date=start_date, end_date=end_date)

        try:
            # Get validation data
            get_result = self.get(code=code, start_date=start_date, end_date=end_date)
            if not get_result.success:
                validation_result = DataValidationResult.create_for_entity(
                    entity_type="adjustfactors",
                    entity_identifier=code
                )
                validation_result.add_error("data_fetch_failed", f"Failed to fetch data for validation: {get_result.message}")
                return ServiceResult.failure(
                    message=f"Failed to fetch data for validation: {get_result.message}",
                    data=validation_result
                )

            records = get_result.data
            validation_result = DataValidationResult.create_for_entity(
                entity_type="adjustfactors",
                entity_identifier=code,
                validation_range=(start_date, end_date) if start_date and end_date else None
            )

            # Check if we have data
            if not records or len(records) == 0:
                validation_result.add_warning("no_data", "No adjustfactor records found for validation")
                duration = time.time() - start_time
                self._log_operation_end("validate", True, duration)
                return ServiceResult.success(
                    data=validation_result,
                    message="No data found for validation"
                )

            # Convert to DataFrame for analysis
            try:
                df = records.to_dataframe()
            except Exception as e:
                validation_result.add_error("data_conversion_failed", f"Failed to convert data to DataFrame: {e}")
                duration = time.time() - start_time
                self._log_operation_end("validate", False, duration)
                return ServiceResult.failure(
                    message=f"Data conversion failed: {e}",
                    data=validation_result
                )

            total_records = len(df)
            validation_result.records_validated = total_records

            # Validate adjustfactor column exists
            if 'adjustfactor' not in df.columns:
                validation_result.add_error("missing_column", "adjustfactor column is missing")
                validation_result.data_quality_score = 0.0
            else:
                # Check for null/NaN values
                null_mask = df['adjustfactor'].isnull()
                null_count = null_mask.sum()
                if null_count > 0:
                    validation_result.add_error("null_values", f"Found {null_count} null adjustfactor values")
                    validation_result.records_failed += null_count

                # Check for zero or negative values
                zero_mask = df['adjustfactor'] <= 0
                zero_count = zero_mask.sum()
                if zero_count > 0:
                    validation_result.add_error("invalid_values", f"Found {zero_count} zero or negative adjustfactor values")
                    validation_result.records_failed += zero_count

                # Check for extreme values (adjustment factors should be reasonable)
                extreme_mask = (df['adjustfactor'] > 100) | (df['adjustfactor'] < 0.01)
                extreme_count = extreme_mask.sum()
                if extreme_count > 0:
                    validation_result.add_warning("extreme_values", f"Found {extreme_count} extreme adjustfactor values (>100 or <0.01)")

                # Calculate data quality score
                if total_records > 0:
                    valid_records = total_records - validation_result.records_failed
                    validation_result.data_quality_score = valid_records / total_records
                else:
                    validation_result.data_quality_score = 0.0

            duration = time.time() - start_time
            self._log_operation_end("validate", validation_result.is_valid, duration)

            return ServiceResult.success(
                data=validation_result,
                message=f"Validation completed for {total_records} adjustfactor records"
            )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation_end("validate", False, duration)
            validation_result = DataValidationResult.create_for_entity(
                entity_type="adjustfactors",
                entity_identifier=code
            )
            validation_result.add_error("validation_failed", f"Validation process failed: {str(e)}")
            return ServiceResult.failure(
                message=f"Validation failed: {str(e)}",
                data=validation_result
            )

    def check_integrity(self, code: str, start_date: datetime = None, end_date: datetime = None, **kwargs) -> ServiceResult:
        """
        Checks data integrity for adjustfactor data including completeness and consistency.

        Args:
            code: Stock code to check
            start_date: Start date for integrity check (optional)
            end_date: End date for integrity check (optional)
            **kwargs: Additional parameters

        Returns:
            ServiceResult with DataIntegrityCheckResult data
        """
        start_time = time.time()
        self._log_operation_start("check_integrity", code=code, start_date=start_date, end_date=end_date)

        try:
            # Determine check range
            if start_date and end_date:
                check_range = (start_date, end_date)
            else:
                # Default to last 90 days
                end_date = datetime.now()
                start_date = end_date - timedelta(days=90)
                check_range = (start_date, end_date)

            # Create integrity check result
            result = DataIntegrityCheckResult.create_for_entity(
                entity_type="adjustfactors",
                entity_identifier=code,
                check_range=check_range
            )

            # Get data for integrity check
            get_result = self.get(code=code, start_date=check_range[0], end_date=check_range[1])
            if not get_result.success:
                result.add_issue("data_fetch_failed", f"Failed to fetch data for integrity check: {get_result.message}")
                result.integrity_score = 0.0
                duration = time.time() - start_time
                self._log_operation_end("check_integrity", False, duration)
                return ServiceResult.failure(
                    message=f"Failed to fetch data for integrity check: {get_result.message}",
                    data=result
                )

            records = get_result.data
            if not records or len(records) == 0:
                result.add_warning("no_data", "No adjustfactor records found for integrity check")
                result.integrity_score = 1.0  # No data is considered complete
                duration = time.time() - start_time
                self._log_operation_end("check_integrity", True, duration)
                return ServiceResult.success(
                    data=result,
                    message="No data found for integrity check"
                )

            # Convert to DataFrame for analysis
            try:
                df = records.to_dataframe()
            except Exception as e:
                result.add_issue("data_conversion_failed", f"Failed to convert data to DataFrame: {e}")
                result.integrity_score = 0.0
                duration = time.time() - start_time
                self._log_operation_end("check_integrity", False, duration)
                return ServiceResult.failure(
                    message=f"Data conversion failed: {e}",
                    data=result
                )

            total_records = len(df)
            result.records_checked = total_records

            # Check for duplicate timestamps
            duplicate_timestamps = df['timestamp'].duplicated().sum()
            if duplicate_timestamps > 0:
                result.add_issue("duplicate_timestamps", f"Found {duplicate_timestamps} duplicate timestamps")

            # Check for missing timestamps in sequence
            if 'timestamp' in df.columns:
                df_sorted = df.sort_values('timestamp')
                time_gaps = df_sorted['timestamp'].diff().dt.days
                # Look for gaps larger than 30 days (might indicate missing data)
                large_gaps = (time_gaps > 30).sum()
                if large_gaps > 0:
                    result.add_warning("large_time_gaps", f"Found {large_gaps} time gaps larger than 30 days")

            # Check for data consistency
            if 'adjustfactor' in df.columns:
                # Check for sudden large changes in adjustment factors
                df_sorted = df.sort_values('timestamp')
                adj_changes = df_sorted['adjustfactor'].pct_change().abs()
                large_changes = (adj_changes > 0.5).sum()  # Changes larger than 50%
                if large_changes > 0:
                    result.add_warning("large_adjustment_changes", f"Found {large_changes} large adjustment factor changes (>50%)")

            # Calculate overall integrity score
            issues_count = len(result.issues)
            warnings_count = len(result.warnings)

            # Deduct points for issues and warnings
            score_deduction = (issues_count * 0.3) + (warnings_count * 0.1)
            result.integrity_score = max(0.0, 1.0 - score_deduction)

            duration = time.time() - start_time
            self._log_operation_end("check_integrity", result.is_healthy(), duration)

            return ServiceResult.success(
                data=result,
                message=f"Integrity check completed for {total_records} adjustfactor records"
            )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation_end("check_integrity", False, duration)
            self._logger.ERROR(f"Failed to check adjustfactor integrity: {e}")

            result = DataIntegrityCheckResult.create_for_entity(
                entity_type="adjustfactors",
                entity_identifier=code
            )
            result.add_issue("integrity_check_failure", f"Integrity check process failed: {str(e)}")
            result.check_duration = duration
            result.integrity_score = 0.0

            return ServiceResult.failure(
                message=f"Integrity check failed: {str(e)}",
                data=result
            )


    
    
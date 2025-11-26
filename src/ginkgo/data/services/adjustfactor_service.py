"""
Adjustfactor Data Service (Class-based)

This service, implemented as a class, handles the business logic for
synchronizing adjustment factor data. It relies on dependency injection
for its data source and CRUD repository, and manages transactions.
"""

import time
from datetime import datetime, timedelta
from typing import List, Union, Any, Dict
import pandas as pd

from ginkgo.libs import GCONF, datetime_normalize, cache_with_expiration, retry, to_decimal, time_logger
from ginkgo.data import mappers
from ginkgo.data.services.base_service import DataService, ServiceResult
from ginkgo.data.crud.model_conversion import ModelList


class AdjustfactorService(DataService):
    def __init__(self, crud_repo, data_source, stockinfo_service):
        """Initializes the service with its dependencies."""
        super().__init__(crud_repo=crud_repo, data_source=data_source, stockinfo_service=stockinfo_service)

    def sync_for_code(self, code: str, fast_mode: bool = True) -> ServiceResult:
        """
        Synchronizes adjustment factors for a single stock code.
        This method is transactional and includes enhanced error handling.

        Args:
            code: Stock code to sync
            fast_mode: If True, only fetch data from last available date

        Returns:
            ServiceResult with sync results and statistics
        """

        # Validate stock code
        if not self.stockinfo_service.is_code_in_stocklist(code):
            self._logger.DEBUG(f"Skipping adjustfactor sync for {code} as it's not in the stock list.")
            return ServiceResult.error(f"Code {code} not in stock list")

        start_date = self._get_fetch_start_date(code, fast_mode)
        end_date = datetime.now()
        self._logger.INFO(f"Syncing adjustfactors for {code} from {start_date.date()} to {end_date.date()}")

        # Fetch data with retry mechanism
        try:
            raw_data = self._fetch_adjustfactor_data(code, start_date, end_date)
        except Exception as e:
            return ServiceResult.error(f"Failed to fetch data from source: {e}")

        if raw_data is None:
            return ServiceResult.error("Failed to fetch data from source")

        if raw_data.empty:
            self._logger.INFO(f"No new adjustfactor data for {code} from source.")
            return ServiceResult.success(
                data={
                    "code": code,
                    "records_processed": 0,
                    "records_added": 0,
                    "warnings": ["No new data available from source"]
                },
                message=f"No new adjustfactor data available for {code}"
            )

        records_processed = len(raw_data)

        # Convert data with error handling
        models_to_add, mapping_errors = self._convert_to_models(raw_data, code)
        warnings = mapping_errors if mapping_errors else []

        if not models_to_add:
            return ServiceResult.error("No valid records after data conversion")

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

            replaced_models = self.crud_repo.replace(filters=filters, new_items=models_to_add)
            records_added = len(replaced_models)

            # If replace returned empty (no existing data), use add_batch instead
            if records_added == 0:
                inserted_models = self.crud_repo.add_batch(models_to_add)
                records_added = len(inserted_models)
                self._logger.INFO(f"Successfully inserted {records_added} new adjustfactors for {code}")
            else:
                self._logger.INFO(f"Successfully replaced {records_added} adjustfactors for {code}")

            return ServiceResult.success(
                data={
                    "code": code,
                    "records_processed": records_processed,
                    "records_added": records_added,
                    "warnings": warnings
                },
                message=f"Successfully synced {records_added} adjustfactors for {code}"
            )

        except Exception as e:
            self._logger.ERROR(f"Failed to sync adjustfactors for {code}: {e}")
            return ServiceResult.error(f"Database sync operation failed: {str(e)}")

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
            raw_data = self.data_source.fetch_cn_stock_adjustfactor(code, start_date, end_date)
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

    
    def sync_batch_codes(self, codes: List[str], fast_mode: bool = True) -> Dict[str, Any]:
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
                    result = self.sync_for_code(code, fast_mode)

                    batch_result["results"].append(result)
                    batch_result["total_records_processed"] += result["records_processed"]

                    if result["success"]:
                        batch_result["successful_codes"] += 1
                        batch_result["total_records_added"] += result["records_added"]
                        progress.update(task, advance=1, description=f":white_check_mark: {code}")
                    else:
                        batch_result["failed_codes"] += 1
                        batch_result["failures"].append(
                            {"code": code, "error": result["error"], "warnings": result.get("warnings", [])}
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
    def get_adjustfactors(
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
            data = self.crud_repo.find(filters=filters, **kwargs)
            return ServiceResult.success(data)

        except Exception as e:
            error_msg = f"Failed to get adjustfactors: {e}"
            self._logger.ERROR(error_msg)
            return ServiceResult.error(error_msg)

    def calculate_precomputed_factors_for_code(self, code: str) -> ServiceResult:
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
        self._log_operation_start("calculate_precomputed_factors_for_code", code=code)

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
            original_records = self.crud_repo.find(filters={"code": code})

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
                replaced_models = self.crud_repo.replace(filters={"code": code}, new_items=updated_entities)
                processed_count = len(replaced_models)
                self._logger.DEBUG(f"成功替换股票 {code} 的 {processed_count} 条复权因子记录")

                # 原子操作成功
                duration = time.time() - start_time
                self._log_operation_end("calculate_precomputed_factors_for_code", True, duration)

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
                self._log_operation_end("calculate_precomputed_factors_for_code", False, duration)

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
            self._log_operation_end("calculate_precomputed_factors_for_code", False, duration)
            error_msg = f"计算股票 {code} 预计算复权因子失败: {str(e)}"
            self._logger.ERROR(error_msg)

            # 如果有备份数据，尝试恢复
            if backup_info and len(backup_info["original_records"]) > 0:
                try:
                    self._logger.ERROR(f"尝试从备份恢复股票 {code} 数据")
                    self.crud_repo.add_batch(backup_info["original_records"])
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
        latest_records = self.crud_repo.find(filters={"code": code}, page_size=1, order_by="timestamp", desc_order=True)

        if latest_records:
            return latest_records[0].timestamp
        else:
            return datetime_normalize(GCONF.DEFAULTSTART)

    def count_adjustfactors(self, code: str = None, **kwargs) -> int:
        """
        Counts the number of adjustment factor records matching the filters.

        Args:
            code: Stock code filter
            **kwargs: Additional filters

        Returns:
            Number of matching records
        """
        # 提取filters参数并从kwargs中移除，避免重复传递
        filters = kwargs.pop("filters", {})

        # 具体参数优先级高于filters中的对应字段
        if code:
            filters["code"] = code

        return self.crud_repo.count(filters=filters)

    def get_available_codes(self) -> List[str]:
        """
        Gets list of available stock codes that have adjustment factor data.

        Returns:
            List of unique stock codes
        """
        return self.crud_repo.find(distinct_field="code")

    def _get_fetch_start_date(self, code: str, fast_mode: bool) -> datetime:
        if not fast_mode:
            try:
                date = self.stockinfo_service.get_stockinfo_by_code(code).list_date
            except Exception as e:
                date = datetime_normalize(GCONF.DEFAULTSTART)
            return date

        latest_timestamp = self.get_latest_adjustfactor_for_code(code)
        return latest_timestamp + timedelta(days=1)


    
    
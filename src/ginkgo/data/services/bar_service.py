"""
Bar Data Service (Class-based)

This service handles the business logic for synchronizing daily bar data.
It coordinates between data sources (e.g., Tushare) and CRUD operations.

Enhanced with comprehensive error handling, retry mechanisms, and structured returns.
"""

import time
from datetime import datetime, timedelta
from typing import List, Union, Any, Dict
import pandas as pd

from ginkgo.libs import GCONF, datetime_normalize, to_decimal, RichProgress, cache_with_expiration, retry
from ginkgo.libs.data.results import DataValidationResult, DataIntegrityCheckResult, DataSyncResult
from ginkgo.data import mappers
from ginkgo.enums import FREQUENCY_TYPES, ADJUSTMENT_TYPES
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.crud.model_conversion import ModelList


class BarService(BaseService):
    def __init__(self, crud_repo, data_source, stockinfo_service, adjustfactor_service=None):
        """Initializes the service with its dependencies."""
        super().__init__(crud_repo=crud_repo, data_source=data_source, stockinfo_service=stockinfo_service)

        # Initialize AdjustfactorService for price adjustment support
        if adjustfactor_service is None:
            from ginkgo.data.services.adjustfactor_service import AdjustfactorService
            from ginkgo.data.crud.adjustfactor_crud import AdjustfactorCRUD

            adjustfactor_service = AdjustfactorService(
                crud_repo=AdjustfactorCRUD(), data_source=data_source, stockinfo_service=stockinfo_service
            )
        self._adjustfactor_service = adjustfactor_service

        # BaseService 已提供所有需要的通用方法：
        # - _log_operation_start, _log_operation_end
        # - create_result
        # 直接继承使用即可

    # ==================== BaseService标准接口实现 ====================

    
    def sync_range(
        self,
        code: str,
        start_date: datetime = None,
        end_date: datetime = None,
        frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY,
    ) -> ServiceResult:
        """
        按日期范围同步K线数据，支持智能增量同步和数据验证。

        Args:
            code (str): 股票代码
            start_date (datetime, optional): 开始日期
            end_date (datetime, optional): 结束日期
            frequency (FREQUENCY_TYPES): 数据频率

        Returns:
            ServiceResult: 同步结果，包含DataSyncResult统计信息
        """
        start_time = time.time()
        self._log_operation_start("sync_range", code=code, start_date=start_date,
                                end_date=end_date, frequency=frequency.value)

        try:
            # Validate stock code
            if not self._stockinfo_service.exists(code):
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="bars",
                    entity_identifier=code,
                    sync_strategy="range"
                )
                sync_result.add_error(0, f"Stock code {code} not in stock list")
                return ServiceResult.error(
                    message=f"Stock code {code} not in stock list",
                    data=sync_result
                )

            # Convert dates to datetime objects and validate
            start_date = datetime_normalize(start_date) if start_date else None
            end_date = datetime_normalize(end_date) if end_date else None
            validated_start, validated_end = self._validate_and_set_date_range(start_date, end_date)

            self._logger.INFO(
                f"Syncing {frequency.value} bars for {code} from {validated_start.date()} to {validated_end.date()}"
            )

            # Fetch data with retry mechanism
            try:
                raw_data = self._fetch_raw_data(code, validated_start, validated_end, frequency)
                if raw_data is None or raw_data.empty:
                    sync_result = DataSyncResult.create_for_entity(
                        entity_type="bars",
                        entity_identifier=code,
                        sync_range=(validated_start, validated_end),
                        sync_strategy="range"
                    )
                    sync_result.set_metadata("date_range", f"{validated_start.date()} to {validated_end.date()}")
                    sync_result.add_warning("No new data available from source")
                    return ServiceResult.success(
                        data=sync_result,
                        message="No new data available from source"
                    )
            except Exception as e:
                return ServiceResult.error(
                    error=f"Failed to fetch data from source: {str(e)}"
                )

            # Validate data quality
            if not self._validate_bar_data(raw_data):
                self._logger.WARN("Data quality issues detected")

            # Convert data to models with error handling
            try:
                bar_entities = mappers.dataframe_to_bar_entities(raw_data, code, frequency)
                if not bar_entities:
                    sync_result = DataSyncResult.create_for_entity(
                        entity_type="bars",
                        entity_identifier=code,
                        sync_range=(validated_start, validated_end),
                        sync_strategy="range"
                    )
                    sync_result.add_warning("No valid bar entities generated from data")
                    return ServiceResult.success(
                        data=sync_result,
                        message="No valid bar entities generated from data"
                    )
            except Exception as e:
                # Fallback: try row-by-row conversion
                self._logger.WARN(f"Batch conversion failed for {code}, attempting row-by-row: {e}")
                bar_entities = self._convert_rows_individually(raw_data, code, frequency)
                if not bar_entities:
                    sync_result = DataSyncResult.create_for_entity(
                        entity_type="bars",
                        entity_identifier=code,
                        sync_range=(validated_start, validated_end),
                        sync_strategy="range"
                    )
                    sync_result.add_error(0, f"Data mapping failed: {str(e)}")
                    return ServiceResult.error(
                        message=f"Data mapping failed: {str(e)}",
                        data=sync_result
                    )

            # Smart duplicate checking and database operations
            final_entities = self._filter_existing_data(bar_entities, code, frequency)

            if not final_entities:
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="bars",
                    entity_identifier=code,
                    sync_range=(validated_start, validated_end),
                    sync_strategy="range"
                )
                sync_result.records_processed = len(raw_data)
                sync_result.records_skipped = len(raw_data)  # 全部跳过
                sync_result.is_idempotent = True
                sync_result.add_warning("All data already exists in database")
                return ServiceResult.success(
                    data=sync_result,
                    message="All data already exists in database"
                )

            # Use BaseCRUD.replace method for atomic operation
            if start_date is not None or end_date is not None:
                # For limited date range, replace data in that range
                min_date = min(item.timestamp for item in final_entities)
                max_date = max(item.timestamp for item in final_entities)
                filters = {
                    "code": code,
                    "timestamp__gte": min_date,
                    "timestamp__lte": max_date,
                    "frequency": frequency,
                }
            else:
                # For full sync, replace all data for this code and frequency
                filters = {
                    "code": code,
                    "frequency": frequency,
                }

            # Use remove + add_batch for better business object handling
            self._crud_repo.remove(filters=filters)
            inserted_entities = self._crud_repo.add_batch(final_entities)
            records_added = len(inserted_entities)
            removed_count = len(final_entities)  # All existing records were removed
            self._logger.INFO(f"Successfully removed {removed_count} and inserted {records_added} bar records for {code}")

            duration = time.time() - start_time
            self._log_operation_end("sync_for_code_with_date_range", True, duration)

            # Create DataSyncResult to wrap sync statistics
            sync_result = DataSyncResult(
                entity_type="bars",
                entity_identifier=code,
                sync_range=(validated_start, validated_end),
                records_processed=len(raw_data),
                records_added=records_added,
                records_updated=0,  # Current implementation only adds new records
                records_skipped=0,   # No skipping in current implementation
                records_failed=0,
                sync_duration=duration,
                is_idempotent=True,
                sync_strategy="incremental"
            )

            # Set additional metadata
            sync_result.set_metadata("frequency", frequency.value)
            sync_result.set_metadata("removed_count", removed_count)
            sync_result.set_metadata("data_source", type(self._data_source).__name__)

            return ServiceResult.success(
                data=sync_result,
                message=f"Bar data for {code} saved successfully: {records_added} records"
            )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation_end("sync_for_code_with_date_range", False, duration)
            self._logger.ERROR(f"Unexpected error syncing {code}: {e}")
            return ServiceResult.error(
                error=f"Unexpected error during sync: {str(e)}"
            )

    @retry(max_try=3)
    def sync_full(
        self, code: str, frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY
    ) -> ServiceResult:
        """
        全量同步单个股票的K线数据，从历史开始到当前日期。

        Args:
            code (str): 股票代码
            frequency (FREQUENCY_TYPES): 数据频率

        Returns:
            ServiceResult: 全量同步结果，包含DataSyncResult统计信息
        """

    @retry(max_try=3)
    def sync_incremental(
        self, code: str, frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY
    ) -> ServiceResult:
        """
        增量同步单个股票的K线数据，从最新数据之后开始到当前日期。

        Args:
            code (str): 股票代码
            frequency (FREQUENCY_TYPES): 数据频率

        Returns:
            ServiceResult: 增量同步结果，包含DataSyncResult统计信息
        """

    @retry(max_try=3)
    def sync_smart(
        self, code: str, fast_mode: bool = True, frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY
    ) -> ServiceResult:
        """
        智能同步K线数据，根据现有数据状态和fast_mode自动选择最优同步策略。

        Args:
            code (str): 股票代码
            fast_mode (bool): True为增量模式，False为全量模式
            frequency (FREQUENCY_TYPES): 数据频率

        Returns:
            ServiceResult: 智能同步结果，包含DataSyncResult统计信息
        """
        start_time = time.time()
        self._log_operation_start("sync_smart", code=code, fast_mode=fast_mode, frequency=frequency.value)

        try:
            # Determine date range based on fast_mode
            start_date, end_date = self._get_fetch_date_range(code, fast_mode, frequency)

            # Call the new date range method
            sync_result = self.sync_range(code, start_date, end_date, frequency)

            # Convert dict result to ServiceResult
            duration = time.time() - start_time
            self._log_operation_end("sync_smart", sync_result.success, duration)

            if sync_result.success:
                # Extract DataSyncResult from the nested ServiceResult
                data_sync_result = sync_result.data
                records_added = data_sync_result.records_added if hasattr(data_sync_result, 'records_added') else 0

                return ServiceResult.success(
                    data=data_sync_result,
                    message=f"Successfully synced {records_added} bar records for {code}"
                )
            else:
                return ServiceResult.error(
                    message=sync_result.error,
                    data=sync_result.data
                )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation_end("sync_smart", False, duration)
            self._logger.ERROR(f"Failed to sync bar data for {code}: {e}")
            return ServiceResult.error(
                error=f"Sync operation failed: {str(e)}"
            )

    def sync_range_batch(
        self,
        codes: List[str],
        start_date: datetime = None,
        end_date: datetime = None,
        frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY,
    ) -> ServiceResult:
        """
        Range batch sync of Bar data for multiple stocks with error isolation and parallel processing.

        Args:
            codes: List of stock codes
            start_date: Start date
            end_date: End date
            frequency: Data frequency

        Returns:
            ServiceResult: Batch sync result and statistics
        """
        batch_result = {
            "total_codes": len(codes),
            "successful_codes": 0,
            "failed_codes": 0,
            "total_records_processed": 0,
            "total_records_added": 0,
            "results": [],
            "failures": [],
            "date_range": None,
        }

        # Validate date range first
        try:
            start_date = datetime_normalize(start_date) if start_date else None
            end_date = datetime_normalize(end_date) if end_date else None
            validated_start, validated_end = self._validate_and_set_date_range(start_date, end_date)
            batch_result["date_range"] = f"{validated_start.date()} to {validated_end.date()}"
        except ValueError as e:
            batch_result["failures"].append({"error": f"Invalid date range: {str(e)}"})
            return ServiceResult.error(
                error=f"Invalid date range: {str(e)}",
                data=batch_result
            )

        valid_codes = [code for code in codes if self._stockinfo_service.exists(code)]
        invalid_codes = [code for code in codes if code not in valid_codes]

        # Track invalid codes
        for invalid_code in invalid_codes:
            batch_result["failures"].append({"code": invalid_code, "error": "Stock code not in stock list"})
            batch_result["failed_codes"] += 1

        self._logger.INFO(
            f"Starting batch sync for {len(valid_codes)} valid codes out of {len(codes)} provided from {validated_start.date()} to {validated_end.date()}"
        )

        with RichProgress() as progress:
            task = progress.add_task("[cyan]Syncing Bar Data", total=len(valid_codes))

            for code in valid_codes:
                try:
                    progress.update(task, description=f"Processing {code}")
                    result = self.sync_range(code, validated_start, validated_end, frequency)

                    batch_result["results"].append(result)
                    batch_result["total_records_processed"] += result.data.records_processed
                    batch_result["total_records_added"] += result.data.records_added

                    if result.success:
                        batch_result["successful_codes"] += 1
                    else:
                        batch_result["failed_codes"] += 1
                        batch_result["failures"].append({"code": code, "error": result.error})

                    progress.update(task, advance=1)

                except Exception as e:
                    self._logger.ERROR(f"Unexpected error syncing {code}: {e}")
                    batch_result["failed_codes"] += 1
                    batch_result["failures"].append({"code": code, "error": f"Unexpected error: {str(e)}"})
                    progress.update(task, advance=1)
                    continue

        self._logger.INFO(
            f"Batch sync completed: {batch_result['successful_codes']} successful, {batch_result['failed_codes']} failed"
        )

        # 创建DataSyncResult来包装批量同步结果
        sync_result = DataSyncResult.create_for_entity(
            entity_type="bars",
            entity_identifier=f"batch_{len(codes)}_codes",
            sync_strategy="batch_range"
        )

        # 设置统计数据
        sync_result.records_processed = batch_result["total_records_processed"]
        sync_result.records_added = batch_result["total_records_added"]
        sync_result.records_updated = 0  # 批量同步暂时不跟踪更新

        # 设置成功率
        success_rate = batch_result["successful_codes"] / batch_result["total_codes"] if batch_result["total_codes"] > 0 else 0
        sync_result.success_rate = success_rate

        # 将批量详细信息存储在附加数据中
        sync_result.batch_details = batch_result

        return ServiceResult.success(
            data=sync_result,
            message=f"Batch sync completed: {batch_result['successful_codes']}/{batch_result['total_codes']} successful"
        )

    @retry(max_try=3)
    def sync_full_batch(
        self, codes: List[str], frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY
    ) -> ServiceResult:
        """
        Full batch sync of K-line data for multiple stocks from history to today.

        Args:
            codes: List of stock codes
            frequency: Data frequency

        Returns:
            ServiceResult: Batch sync result
        """
        from datetime import datetime
        return self.sync_range_batch(codes, None, datetime.now(), frequency)

    @retry(max_try=3)
    def sync_incremental_batch(
        self, codes: List[str], frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY
    ) -> ServiceResult:
        """
        Incremental batch sync of K-line data for multiple stocks from last available date to today.

        Args:
            codes: List of stock codes
            frequency: Data frequency

        Returns:
            ServiceResult: Batch sync result
        """
        from datetime import datetime, timedelta

        # 为每个股票代码获取最后的日期
        batch_result = {
            "total_codes": len(codes),
            "successful_codes": 0,
            "failed_codes": 0,
            "total_records_processed": 0,
            "total_records_added": 0,
            "results": [],
            "failures": [],
            "date_ranges": {}
        }

        try:
            # 获取每个代码的最后可用日期
            date_ranges = {}
            for code in codes:
                try:
                    last_date_result = self.get_latest_timestamp(code, frequency)
                    if last_date_result.success and last_date_result.data:
                        last_date = last_date_result.data
                        start_date = last_date + timedelta(days=1)
                    else:
                        start_date = None
                    date_ranges[code] = start_date
                    batch_result["date_ranges"][code] = start_date.isoformat() if start_date else None
                except Exception as e:
                    batch_result["failures"].append({"code": code, "error": f"Failed to get last date: {str(e)}"})
                    batch_result["failed_codes"] += 1

            # 执行同步
            end_date = datetime.now()
            for code in codes:
                try:
                    start_date = date_ranges.get(code)
                    result = self.sync_range(code, start_date, end_date, frequency)

                    if result.success:
                        batch_result["successful_codes"] += 1
                        if result.data:
                            batch_result["total_records_processed"] += result.data.records_processed
                            batch_result["total_records_added"] += result.data.records_added
                        batch_result["results"].append({"code": code, "success": True, "result": result.data})
                    else:
                        batch_result["failed_codes"] += 1
                        batch_result["failures"].append({"code": code, "error": result.error})
                        batch_result["results"].append({"code": code, "success": False, "error": result.error})

                except Exception as e:
                    batch_result["failed_codes"] += 1
                    batch_result["failures"].append({"code": code, "error": str(e)})
                    batch_result["results"].append({"code": code, "success": False, "error": str(e)})

            return ServiceResult.success(
                data=batch_result,
                message=f"Batch incremental sync completed: {batch_result['successful_codes']}/{batch_result['total_codes']} successful"
            )

        except Exception as e:
            return ServiceResult.error(
                error=f"Batch incremental sync failed: {str(e)}"
            )

    def sync_smart_batch(
        self, codes: List[str], fast_mode: bool = True, frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY
    ) -> ServiceResult:
        """
        Smart batch sync of K-line data for multiple stock codes with comprehensive error tracking.

        Args:
            codes: List of stock codes
            fast_mode: True for latest data only, False for full sync
            frequency: Data frequency

        Returns:
            ServiceResult: Batch sync result and statistics
        """
        # For backward compatibility, we need to determine date ranges for each code individually
        # since fast_mode behavior is per-code
        if fast_mode:
            # In fast mode, each code has its own start date, so we can't use batch date range method
            # Fall back to individual sync_smart calls
            batch_result = {
                "total_codes": len(codes),
                "successful_codes": 0,
                "failed_codes": 0,
                "total_records_processed": 0,
                "total_records_added": 0,
                "results": [],
                "failures": [],
            }

            try:
                valid_codes = [code for code in codes if self._stockinfo_service.exists(code)]
                invalid_codes = [code for code in codes if code not in valid_codes]

                # Track invalid codes
                for invalid_code in invalid_codes:
                    batch_result["failures"].append({"code": invalid_code, "error": "Stock code not in stock list"})
                    batch_result["failed_codes"] += 1

                self._logger.INFO(
                    f"Starting batch sync for {len(valid_codes)} valid codes out of {len(codes)} provided (fast mode)."
                )

                with RichProgress() as progress:
                    task = progress.add_task("[cyan]Syncing Bar Data", total=len(valid_codes))

                    for code in valid_codes:
                        try:
                            progress.update(task, description=f"Processing {code}")
                            result = self.sync_smart(code, fast_mode, frequency)

                            batch_result["results"].append(result)

                            # Extract data from DataSyncResult if available
                            if result.success and hasattr(result.data, 'records_processed'):
                                data_sync_result = result.data
                                batch_result["total_records_processed"] += data_sync_result.records_processed
                                batch_result["total_records_added"] += data_sync_result.records_added
                            else:
                                # Fallback for backward compatibility
                                data_dict = result.data if isinstance(result.data, dict) else {}
                                batch_result["total_records_processed"] += data_dict.get("records_processed", 0)
                                batch_result["total_records_added"] += data_dict.get("records_added", 0)

                            if result.success:
                                batch_result["successful_codes"] += 1
                            else:
                                batch_result["failed_codes"] += 1
                                batch_result["failures"].append({"code": code, "error": result.error})

                            progress.update(task, advance=1)

                        except Exception as e:
                            self._logger.ERROR(f"Unexpected error syncing {code}: {e}")
                            batch_result["failed_codes"] += 1
                            batch_result["failures"].append({"code": code, "error": f"Unexpected error: {str(e)}"})
                            progress.update(task, advance=1)
                            continue

                self._logger.INFO(
                    f"Batch sync completed: {batch_result['successful_codes']} successful, {batch_result['failed_codes']} failed"
                )

                # Create DataSyncResult to wrap batch sync statistics
                from datetime import datetime
                start_time_dt = start_date or datetime(2020, 1, 1)
                end_time_dt = end_date or datetime.now()

                batch_sync_result = DataSyncResult(
                    entity_type="bars",
                    entity_identifier=f"batch_{len(codes)}_stocks",
                    sync_range=(start_time_dt, end_time_dt),
                    records_processed=batch_result["total_records_processed"],
                    records_added=batch_result["total_records_added"],
                    records_updated=0,  # Current implementation only tracks added records
                    records_skipped=0,   # No skipping in current implementation
                    records_failed=batch_result["failed_codes"],
                    sync_duration=0.0,  # Would need to track actual duration
                    is_idempotent=True,
                    sync_strategy="batch"
                )

                # Set batch-specific metadata
                batch_sync_result.set_metadata("frequency", frequency.value)
                batch_sync_result.set_metadata("total_codes", batch_result["total_codes"])
                batch_sync_result.set_metadata("successful_codes", batch_result["successful_codes"])
                batch_sync_result.set_metadata("failed_codes", batch_result["failed_codes"])
                batch_sync_result.set_metadata("success_rate", batch_result["successful_codes"] / batch_result["total_codes"] if batch_result["total_codes"] > 0 else 0)
                batch_sync_result.set_metadata("data_source", type(self._data_source).__name__)
                batch_sync_result.set_metadata("batch_results", batch_result["results"])

                if batch_result["failures"]:
                    batch_sync_result.set_metadata("failure_details", batch_result["failures"])

                return ServiceResult.success(
                    data=batch_sync_result,
                    message=f"Batch sync completed: {batch_result['successful_codes']}/{batch_result['total_codes']} successful"
                )

            except Exception as e:
                self._logger.ERROR(f"Batch sync failed: {str(e)}")
                return ServiceResult.error(f"Batch sync operation failed: {str(e)}")
        else:
            # In non-fast mode, all codes use the same date range, so we can use the batch date range method
            start_date = datetime_normalize(GCONF.DEFAULTSTART)
            end_date = datetime.now()
            return self.sync_range_batch(codes, start_date, end_date, frequency)

    def get(
        self,
        code: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY,
        adjustment_type: ADJUSTMENT_TYPES = ADJUSTMENT_TYPES.FORE,
        page: int = None,
        page_size: int = None,
        order_by: str = "timestamp",
        desc_order: bool = False,
    ) -> ServiceResult:
        """
        获取K线数据，支持多种过滤条件、复权类型和分页查询

        Args:
            code (str, optional): 股票代码，支持多代码查询
            start_date (datetime, optional): 开始时间，支持datetime和字符串格式
            end_date (datetime, optional): 结束时间，支持datetime和字符串格式
            frequency (FREQUENCY_TYPES): 数据频率（日线/周线/月线等）
            adjustment_type (ADJUSTMENT_TYPES): 复权类型（前复权/后复权/原始）
            page (int, optional): 分页页码，支持大数据量分页查询
            page_size (int, optional): 每页记录数，默认1000条
            order_by (str): 排序字段，支持timestamp, open, high, low, close, volume
            desc_order (bool): 是否降序排列

        Returns:
            ServiceResult: 查询结果，data中包含ModelList，支持转换为entities和dataframe

        Note:
            - to_entities: 可通过result.data.to_entities()转换为实体对象列表
            - to_dataframe: 可通过result.data.to_dataframe()转换为pandas DataFrame
        """
        start_time = time.time()
        self._log_operation_start("get_bars", code=code, start_date=start_date,
                                end_date=end_date, frequency=frequency.value,
                                adjustment_type=adjustment_type.value)

        try:
            # 基本参数验证 - 至少需要一个查询条件
            if not code and not start_date and not end_date:
                return ServiceResult.error(
                    "查询参数不能为空，至少需要提供code、start_date或end_date中的一个"
                )

            # 构建filters字典
            filters = {}

            if code:
                filters["code"] = code
            if start_date:
                # 使用datetime_normalize处理时间
                normalized_start = datetime_normalize(start_date)
                filters["timestamp__gte"] = normalized_start
            if end_date:
                # 使用datetime_normalize处理时间
                normalized_end = datetime_normalize(end_date)
                filters["timestamp__lte"] = normalized_end
            if frequency:
                filters["frequency"] = frequency

            # Get original bar data - 返回ModelList
            model_list = self._crud_repo.find(
                filters=filters,
                page=page,
                page_size=page_size,
                order_by=order_by,
                desc_order=desc_order
            )

            # Return original data if no adjustment needed
            if adjustment_type == ADJUSTMENT_TYPES.NONE:
                duration = time.time() - start_time
                self._log_operation_end("get_bars", True, duration)
                return ServiceResult.success(
                    data=model_list,
                    message=f"Retrieved {len(model_list)} bar records without adjustment"
                )

            # Apply price adjustment if requested
            if code is None:
                # Multi-stock adjustment when no specific code provided
                adjusted_data = self._apply_price_adjustment_multi_stock(model_list, adjustment_type)
            else:
                # Single-stock adjustment when code is provided - 使用高性能矩阵化计算
                adjusted_data = self._apply_price_adjustment_to_modellist(model_list, code, adjustment_type)

            duration = time.time() - start_time
            self._log_operation_end("get_bars", True, duration)

            return ServiceResult.success(
                data=adjusted_data,
                message=f"Retrieved and adjusted {len(adjusted_data)} bar records [adjustment_type: {adjustment_type.value}]"
            )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation_end("get_bars", False, duration)
            self._logger.ERROR(f"Failed to get bar data: {e}")
            return ServiceResult.error(
                error=f"Database operation failed: {str(e)}"
            )

    
    # TODO: 复权方法性能优化
    # 当前复权实现存在性能问题，在大数据量处理时效率较低
    # 需要优化的方向：
    # 1. 批量计算优化，减少循环操作
    # 2. 内存使用优化，避免大DataFrame复制
    # 3. 复权因子缓存机制
    # 4. 并行计算支持
    # 未来版本需要重构以提升性能
    def _apply_price_adjustment(
        self,
        bars_data: ModelList,
        code: str,
        adjustment_type: ADJUSTMENT_TYPES,
    ) -> ModelList:
        """
        Applies price adjustment factors to bar data.

        Args:
            bars_data: Original bar data as ModelList
            code: Stock code for getting adjustment factors
            adjustment_type: Type of adjustment (FORE/BACK)

        Returns:
            Price-adjusted bar data as ModelList
        """
        if not code:
            self._logger.ERROR("Stock code required for price adjustment")
            return bars_data

        # Handle empty data
        if (isinstance(bars_data, pd.DataFrame) and bars_data.empty) or (
            isinstance(bars_data, list) and len(bars_data) == 0
        ):
            return bars_data

        try:
            # Convert to DataFrame if needed for processing
            if isinstance(bars_data, pd.DataFrame):
                bars_df = bars_data.copy()
            else:
                # Convert list of models to DataFrame
                bars_df = pd.DataFrame(
                    [
                        {
                            "code": bar.code,
                            "timestamp": bar.timestamp,
                            "open": float(bar.open),
                            "high": float(bar.high),
                            "low": float(bar.low),
                            "close": float(bar.close),
                            "volume": bar.volume,
                            "amount": float(bar.amount),
                        }
                        for bar in bars_data
                    ]
                )

            if bars_df.empty:
                return bars_data

            # Get adjustment factors for the same date range
            start_date = bars_df["timestamp"].min()
            end_date = bars_df["timestamp"].max()

            # Get adjustment factors for the same date range
            adjustfactors_result = self._adjustfactor_service.get(
                code=code, start_date=start_date, end_date=end_date
            )

            if not adjustfactors_result.success or not adjustfactors_result.data:
                self._logger.DEBUG(f"No adjustment factors found for {code}, returning original data")
                return bars_data

            # Convert ModelList to DataFrame
            adjustfactors_df = adjustfactors_result.data.to_dataframe()

            if adjustfactors_df.empty:
                self._logger.DEBUG(f"No adjustment factors found for {code}, returning original data")
                return bars_data

            # Apply adjustment factors
            adjusted_df = self._calculate_adjusted_prices(bars_df, adjustfactors_df, adjustment_type)

            # Return in original format
            if isinstance(bars_data, pd.DataFrame):
                return adjusted_df
            else:
                # Convert back to list of models
                from ginkgo.data.models.model_bar import MBar

                adjusted_bars = []
                for _, row in adjusted_df.iterrows():
                    bar = MBar()
                    bar.code = row["code"]
                    bar.timestamp = row["timestamp"]
                    bar.open = to_decimal(row["open"])
                    bar.high = to_decimal(row["high"])
                    bar.low = to_decimal(row["low"])
                    bar.close = to_decimal(row["close"])
                    bar.volume = int(row["volume"])
                    bar.amount = to_decimal(row["amount"])
                    adjusted_bars.append(bar)
                return adjusted_bars

        except Exception as e:
            self._logger.ERROR(f"Failed to apply price adjustment for {code}: {e}")
            return bars_data

    def _calculate_adjusted_prices(
        self, bars_df: pd.DataFrame, adjustfactors_df: pd.DataFrame, adjustment_type: ADJUSTMENT_TYPES
    ) -> pd.DataFrame:
        """
        Calculates price-adjusted bar data using adjustment factors.

        Args:
            bars_df: Bar data DataFrame
            adjustfactors_df: Adjustment factors DataFrame
            adjustment_type: Type of adjustment (FORE/BACK)

        Returns:
            DataFrame with adjusted prices
        """
        adjusted_df = bars_df.copy()

        # Select appropriate adjustment factor column
        if adjustment_type == ADJUSTMENT_TYPES.FORE:
            factor_column = "foreadjustfactor"
        elif adjustment_type == ADJUSTMENT_TYPES.BACK:
            factor_column = "backadjustfactor"
        else:
            return adjusted_df  # No adjustment

        # Merge bar data with adjustment factors on timestamp
        merged_df = pd.merge(adjusted_df, adjustfactors_df[["timestamp", factor_column]], on="timestamp", how="left")

        # Fill missing adjustment factors with 1.0 (no adjustment)
        merged_df[factor_column] = merged_df[factor_column].fillna(1.0)

        # Apply adjustment to price fields (OHLC)
        price_columns = ["open", "high", "low", "close"]
        for col in price_columns:
            if col in merged_df.columns:
                merged_df[col] = merged_df[col] * merged_df[factor_column]

        # Amount should also be adjusted as it's price * volume
        if "amount" in merged_df.columns:
            merged_df["amount"] = merged_df["amount"] * merged_df[factor_column]

        # Volume remains unchanged
        # Drop the temporary adjustment factor column
        result_df = merged_df.drop(columns=[factor_column])

        return result_df

    def _apply_price_adjustment_to_modellist(
        self,
        bars_data: ModelList,
        code: str,
        adjustment_type: ADJUSTMENT_TYPES,
    ) -> ModelList:
        """
        对ModelList应用复权计算，返回ModelList格式

        内部使用DataFrame进行高性能矩阵化计算，但最终转换为ModelList保持接口一致性

        Args:
            bars_data: 原始K线数据ModelList
            code: 股票代码
            adjustment_type: 复权类型

        Returns:
            复权后的K线数据ModelList
        """
        if not code:
            self._logger.ERROR("Stock code required for price adjustment")
            return bars_data

        # Handle empty data
        if not bars_data:
            return bars_data

        try:
            # Step 1: 转换为DataFrame进行高性能计算
            df_bars = self._convert_modellist_to_dataframe(bars_data)

            if df_bars.empty:
                return bars_data

            # Step 2: 获取预计算的复权系数
            factors_df = self._get_precomputed_adjustment_factors(
                code=code,
                dates=df_bars['timestamp'].unique(),
                adjustment_type=adjustment_type
            )

            if factors_df.empty:
                self._logger.DEBUG(f"No precomputed adjustment factors found for {code}, returning original data")
                return bars_data

            # Step 3: 矩阵化复权计算
            adjusted_df = self._apply_matrix_adjustment(df_bars, factors_df, adjustment_type)

            # Step 4: 转换回ModelList格式
            adjusted_modellist = self._convert_dataframe_to_modellist(adjusted_df)

            return adjusted_modellist

        except Exception as e:
            self._logger.ERROR(f"Failed to apply price adjustment for {code}: {e}")
            return bars_data

    def _get_precomputed_adjustment_factors(
        self,
        code: str,
        dates,
        adjustment_type: ADJUSTMENT_TYPES,
    ) -> pd.DataFrame:
        """
        获取预计算的复权系数

        Args:
            code: 股票代码
            dates: 需要查询的日期数组
            adjustment_type: 复权类型

        Returns:
            DataFrame包含timestamp和复权系数列
        """
        try:
            # 确定复权因子列名
            if adjustment_type == ADJUSTMENT_TYPES.FORE:
                factor_column = 'foreadjustfactor'
            else:  # ADJUSTMENT_TYPES.BACK
                factor_column = 'backadjustfactor'

            # 调用AdjustfactorService获取预计算复权因子
            # TODO: 实现get_precomputed_factors方法
            # 目前使用原始adjustfactor数据作为fallback
            start_date = min(dates)
            end_date = max(dates)

            # 获取原始adjustfactor数据
            result = self._adjustfactor_service.get(
                code=code, start_date=start_date, end_date=end_date
            )

            if not result.success or len(result.data) == 0:
                return pd.DataFrame(columns=['timestamp', factor_column])

            # 使用ServiceResult.data中的ModelList转换为DataFrame
            df_factors = result.data.to_dataframe()

            if df_factors.empty:
                return pd.DataFrame(columns=['timestamp', factor_column])

            # 简化处理：目前假设fore/back因子需要基于adjustfactor计算
            # TODO: 替换为真正的预计算因子查询
            if factor_column in df_factors.columns:
                # 如果已经有预计算的因子，直接返回
                return df_factors[['timestamp', factor_column]].copy()
            else:
                # 基于adjustfactor计算临时因子（仅用于测试）
                if 'adjustfactor' in df_factors.columns and not df_factors.empty():
                    latest_factor = df_factors['adjustfactor'].iloc[-1]
                    if adjustment_type == ADJUSTMENT_TYPES.FORE:
                        # 前复权系数 = 最新因子 / 历史因子
                        df_factors[factor_column] = latest_factor / df_factors['adjustfactor']
                    else:
                        # 后复权系数 = 历史因子 / 最早因子
                        earliest_factor = df_factors['adjustfactor'].iloc[0]
                        df_factors[factor_column] = df_factors['adjustfactor'] / earliest_factor

                    return df_factors[['timestamp', factor_column]].copy()

            return pd.DataFrame(columns=['timestamp', factor_column])

        except Exception as e:
            self._logger.ERROR(f"Failed to get precomputed adjustment factors for {code}: {e}")
            return pd.DataFrame(columns=['timestamp', 'foreadjustfactor', 'backadjustfactor'])

    def _apply_matrix_adjustment(
        self,
        bars_df: pd.DataFrame,
        factors_df: pd.DataFrame,
        adjustment_type: ADJUSTMENT_TYPES,
    ) -> pd.DataFrame:
        """
        高性能矩阵化复权计算

        利用pandas向量化操作，批量应用复权因子到所有价格数据

        Args:
            bars_df: K线数据DataFrame
            factors_df: 复权因子DataFrame
            adjustment_type: 复权类型

        Returns:
            复权后的DataFrame
        """
        if bars_df.empty or factors_df.empty:
            return bars_df

        try:
            # 确定复权因子列名
            factor_column = 'foreadjustfactor' if adjustment_type == ADJUSTMENT_TYPES.FORE else 'backadjustfactor'

            # 合并K线数据和复权系数
            merged_df = bars_df.merge(
                factors_df[['timestamp', factor_column]],
                on='timestamp',
                how='left'
            )

            # 填充缺失复权系数为1.0（无复权）
            merged_df[factor_column] = merged_df[factor_column].fillna(1.0)

            # 向量化复权计算 - 一次性应用到所有价格字段
            price_columns = ['open', 'high', 'low', 'close']
            for col in price_columns:
                if col in merged_df.columns:
                    merged_df[col] = merged_df[col] * merged_df[factor_column]

            # 成交额也需要复权调整
            if 'amount' in merged_df.columns:
                merged_df['amount'] = merged_df['amount'] * merged_df[factor_column]

            # 删除临时复权系数列，返回干净的DataFrame
            result_df = merged_df.drop(columns=[factor_column])

            return result_df

        except Exception as e:
            self._logger.ERROR(f"Failed to apply matrix adjustment: {e}")
            return bars_df

    def _convert_modellist_to_dataframe(self, bars_data) -> pd.DataFrame:
        """
        将ModelList转换为DataFrame

        Args:
            bars_data: ModelList数据

        Returns:
            DataFrame格式数据
        """
        if isinstance(bars_data, pd.DataFrame):
            return bars_data.copy()

        if hasattr(bars_data, 'to_dataframe'):
            return bars_data.to_dataframe()

        # 手动转换
        return pd.DataFrame([{
            'code': bar.code,
            'timestamp': bar.timestamp,
            'open': float(bar.open),
            'high': float(bar.high),
            'low': float(bar.low),
            'close': float(bar.close),
            'volume': bar.volume,
            'amount': float(bar.amount) if bar.amount else 0,
            'frequency': getattr(bar, 'frequency', None),
            'adjustflag': getattr(bar, 'adjustflag', None)
        } for bar in bars_data])

    def _convert_dataframe_to_modellist(self, df: pd.DataFrame):
        """
        将DataFrame转换为ModelList

        Args:
            df: DataFrame数据

        Returns:
            ModelList格式数据
        """
        if df.empty:
            from ginkgo.data.crud.model_conversion import ModelList
            return ModelList([], self._crud_repo)

        try:
            from ginkgo.data.models.model_bar import MBar
            from ginkgo.libs.data.number import to_decimal
            from ginkgo.data.crud.model_conversion import ModelList

            bars = []
            for _, row in df.iterrows():
                bar = MBar()
                bar.code = row['code']
                bar.timestamp = row['timestamp']
                bar.open = to_decimal(row['open'])
                bar.high = to_decimal(row['high'])
                bar.low = to_decimal(row['low'])
                bar.close = to_decimal(row['close'])
                bar.volume = int(row['volume'])
                bar.amount = to_decimal(row['amount']) if pd.notna(row.get('amount')) else None

                # 保持其他字段（如果存在）
                if 'frequency' in row and pd.notna(row['frequency']):
                    bar.frequency = row['frequency']
                if 'adjustflag' in row and pd.notna(row['adjustflag']):
                    bar.adjustflag = row['adjustflag']

                bars.append(bar)

            return ModelList(bars, self._crud_repo)

        except Exception as e:
            self._logger.ERROR(f"Failed to convert DataFrame to ModelList: {e}")
            # 返回空ModelList
            from ginkgo.data.crud.model_conversion import ModelList
            return ModelList([], self._crud_repo)

    # TODO: 多股票复权方法性能优化
    # 当前多股票批量复权实现存在性能问题，在大数据量处理时效率较低
    # 需要优化的方向：
    # 1. 批量复权因子获取，避免逐股票查询
    # 2. 向量化计算替代逐行处理
    # 3. 内存使用优化，减少数据复制
    # 4. 并行处理多股票复权
    # 未来版本需要重构以提升批量处理性能
    def _apply_price_adjustment_multi_stock(
        self,
        bars_data: ModelList,
        adjustment_type: ADJUSTMENT_TYPES,
    ) -> ModelList:
        """
        Applies price adjustment factors to bar data for multiple stocks.

        This method handles the case where bars_data contains data from multiple stocks
        by grouping by stock code and applying adjustment factors individually.

        Args:
            bars_data: Bar data containing multiple stocks (DataFrame or list of models)
            adjustment_type: Type of adjustment (FORE/BACK)
            as_dataframe: Whether bars_data is DataFrame format

        Returns:
            Price-adjusted bar data in the same format as input
        """
        # Handle empty data
        if (isinstance(bars_data, pd.DataFrame) and bars_data.empty) or (
            isinstance(bars_data, list) and len(bars_data) == 0
        ):
            return bars_data

        try:
            if isinstance(bars_data, pd.DataFrame):
                # DataFrame processing - group by stock code
                if "code" not in bars_data.columns:
                    self._logger.ERROR("Cannot apply multi-stock adjustment: 'code' column missing")
                    return bars_data

                # Group by stock code and apply adjustment individually
                adjusted_dfs = []
                unique_codes = bars_data["code"].unique()

                self._logger.INFO(f"Applying {adjustment_type.value} adjustment to {len(unique_codes)} stocks")

                for code in unique_codes:
                    stock_data = bars_data[bars_data["code"] == code].copy()
                    adjusted_stock_data = self._apply_price_adjustment(stock_data, code, adjustment_type)
                    adjusted_dfs.append(adjusted_stock_data)

                # Combine all adjusted data
                result_df = pd.concat(adjusted_dfs, ignore_index=True)

                # Sort by original order (timestamp and code)
                if "timestamp" in result_df.columns:
                    result_df = result_df.sort_values(["timestamp", "code"])

                return result_df

            else:
                # List of models processing - group by stock code
                if not hasattr(bars_data[0], "code"):
                    self._logger.ERROR("Cannot apply multi-stock adjustment: models missing 'code' attribute")
                    return bars_data

                # Group by stock code
                code_to_models = {}
                for bar in bars_data:
                    code = bar.code
                    if code not in code_to_models:
                        code_to_models[code] = []
                    code_to_models[code].append(bar)

                # Apply adjustment to each stock's data
                adjusted_models = []
                unique_codes = list(code_to_models.keys())

                self._logger.INFO(f"Applying {adjustment_type.value} adjustment to {len(unique_codes)} stocks")

                for code in unique_codes:
                    stock_models = code_to_models[code]
                    adjusted_stock_models = self._apply_price_adjustment(stock_models, code, adjustment_type, False)
                    adjusted_models.extend(adjusted_stock_models)

                # Maintain original order
                return adjusted_models

        except Exception as e:
            self._logger.ERROR(f"Failed to apply multi-stock price adjustment: {e}")
            return bars_data

    def get_latest_timestamp(self, code: str, frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY) -> ServiceResult:
        """
        Gets the latest timestamp for a specific code and frequency.

        Args:
            code: Stock code
            frequency: Data frequency

        Returns:
            ServiceResult - 包装latest timestamp数据，使用result.data获取时间戳
        """
        start_time = time.time()
        self._log_operation_start("get_latest_timestamp_for_code", code=code, frequency=frequency.value)

        try:
            latest_records = self._crud_repo.find(
                filters={"code": code, "frequency": frequency}, page_size=1, order_by="timestamp", desc_order=True
            )

            if latest_records:
                timestamp = latest_records[0].timestamp
                duration = time.time() - start_time
                self._log_operation_end("get_latest_timestamp_for_code", True, duration)
                return ServiceResult.success(
                    data=timestamp,
                    message=f"Found latest timestamp {timestamp} for {code}"
                )
            else:
                # 返回默认开始日期
                default_timestamp = datetime_normalize(GCONF.DEFAULTSTART)
                duration = time.time() - start_time
                self._log_operation_end("get_latest_timestamp_for_code", True, duration)
                return ServiceResult.success(
                    data=default_timestamp,
                    message=f"No data found for {code}, returning default start date {default_timestamp}"
                )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation_end("get_latest_timestamp_for_code", False, duration)
            self._logger.ERROR(f"Failed to get latest timestamp for {code}: {e}")
            return ServiceResult.error(
                error=f"Database query failed: {str(e)}"
            )

    def _get_fetch_date_range(self, code: str, fast_mode: bool, frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY) -> tuple:
        """Determines the date range for fetching data."""
        end_date = datetime.now()

        if not fast_mode:
            start_date = self._get_intelligent_start_date(code)
        else:
            latest_timestamp_result = self.get_latest_timestamp(code, frequency)
            if latest_timestamp_result.success and latest_timestamp_result.data:
                start_date = latest_timestamp_result.data + timedelta(days=1)
            else:
                # 如果获取最新时间戳失败，使用默认的开始日期
                start_date = datetime.now() - timedelta(days=365)  # 默认一年前

        return start_date, end_date

    def _get_intelligent_start_date(self, code: str) -> datetime:
        """
        Gets intelligent start date for data sync, prioritizing stock listing date.

        Args:
            code: Stock code

        Returns:
            Intelligent start date based on stock listing date or reasonable default
        """
        try:
            # 1. Try to get stock listing date
            stockinfo_result = self._stockinfo_service.get(filters={"code": code}, page_size=1)
            stockinfo = stockinfo_result.data[0] if stockinfo_result.success and stockinfo_result.data else None
            if stockinfo and hasattr(stockinfo, "list_date") and stockinfo.list_date:
                # Ensure not earlier than reasonable range (1990-01-01)
                reasonable_earliest = datetime(1990, 1, 1)
                intelligent_start = max(stockinfo.list_date, reasonable_earliest)
                self._logger.DEBUG(
                    f"Using intelligent start date for {code}: {intelligent_start.date()} (listing: {stockinfo.list_date.date()})"
                )
                return intelligent_start
        except Exception as e:
            self._logger.WARN(f"Failed to get listing date for {code}: {e}")

        # 2. Fallback to configuration default
        default_start = datetime_normalize(GCONF.DEFAULTSTART)
        self._logger.DEBUG(f"Using default start date for {code}: {default_start.date()}")
        return default_start

    @retry(max_try=3)
    def _fetch_raw_data(
        self, code: str, start_date: datetime, end_date: datetime, frequency: FREQUENCY_TYPES
    ) -> pd.DataFrame:
        """Fetches raw data from data source based on frequency with retry mechanism."""
        if frequency == FREQUENCY_TYPES.DAY:
            return self._data_source.fetch_cn_stock_daybar(code=code, start_date=start_date, end_date=end_date)
        else:
            raise NotImplementedError(f"Frequency {frequency} not yet supported")

    def _validate_bar_data(self, df: pd.DataFrame) -> bool:
        """
        Validates bar data for basic OHLC logic.

        Args:
            df: DataFrame containing bar data

        Returns:
            True if data passes basic validation, False otherwise
        """
        if df.empty:
            return True

        try:
            # Check for required columns
            required_cols = ["open", "high", "low", "close"]
            if not all(col in df.columns for col in required_cols):
                self._logger.WARN("Missing required OHLC columns")
                return False

            # Basic OHLC validation: high >= max(open, close), low <= min(open, close)
            invalid_high = (df["high"] < df[["open", "close"]].max(axis=1)).sum()
            invalid_low = (df["low"] > df[["open", "close"]].min(axis=1)).sum()

            if invalid_high > 0:
                self._logger.WARN(f"Found {invalid_high} records with high < max(open, close)")
            if invalid_low > 0:
                self._logger.WARN(f"Found {invalid_low} records with low > min(open, close)")

            # Check for negative prices
            negative_prices = (df[required_cols] <= 0).any(axis=1).sum()
            if negative_prices > 0:
                self._logger.WARN(f"Found {negative_prices} records with non-positive prices")

            return invalid_high == 0 and invalid_low == 0 and negative_prices == 0

        except Exception as e:
            self._logger.ERROR(f"Error validating bar data: {e}")
            return False

    def _convert_rows_individually(self, df: pd.DataFrame, code: str, frequency: FREQUENCY_TYPES) -> List[Any]:
        """
        Fallback method: convert DataFrame rows individually when batch conversion fails.

        Args:
            df: DataFrame to convert
            code: Stock code
            frequency: Data frequency

        Returns:
            List of successfully converted models
        """
        models = []
        for idx, row in df.iterrows():
            try:
                # Create single-row DataFrame for mapper
                single_row_df = pd.DataFrame([row])
                row_entities = mappers.dataframe_to_bar_entities(single_row_df, code, frequency)
                models.extend(row_entities)
            except Exception as e:
                self._logger.WARN(f"Failed to convert row {idx} for {code}: {e}")
                continue

        return models

    def _validate_and_set_date_range(self, start_date: datetime = None, end_date: datetime = None) -> tuple:
        """
        Validates and sets the date range for data synchronization.

        Args:
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Tuple of (validated_start_date, validated_end_date)
        """
        # Set default end date to today if not provided
        if end_date is None:
            end_date = datetime.now()

        # Set default start date to config default if not provided
        if start_date is None:
            start_date = datetime_normalize(GCONF.DEFAULTSTART)

        # Validate date range
        if start_date > end_date:
            raise ValueError(f"Start date {start_date.date()} cannot be later than end date {end_date.date()}")

        return start_date, end_date

    def _filter_existing_data(self, bar_entities: List[Any], code: str, frequency: FREQUENCY_TYPES) -> List[Any]:
        """
        Filters out existing data to avoid duplicates.

        Args:
            bar_entities: List of models to potentially add
            code: Stock code
            frequency: Data frequency

        Returns:
            List of models that don't already exist in database
        """
        if not bar_entities:
            return []

        try:
            # Get timestamps of models to add
            timestamps_to_add = [model.timestamp for model in bar_entities]

            # Check which timestamps already exist in database
            existing_records = self._crud_repo.find(
                filters={"code": code, "timestamp__in": timestamps_to_add, "frequency": frequency}
            )

            existing_timestamps = {record.timestamp for record in existing_records}

            # Filter out existing records
            new_models = [model for model in bar_entities if model.timestamp not in existing_timestamps]

            if len(existing_timestamps) > 0:
                self._logger.DEBUG(f"Filtered out {len(existing_timestamps)} existing records for {code}")

            return new_models

        except Exception as e:
            self._logger.WARN(f"Error filtering existing data for {code}: {e}, proceeding with all models")
            return bar_entities

    def count(self, code: str = None, frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY,
              start_date: datetime = None, end_date: datetime = None) -> ServiceResult:
        """
        统计K线记录数量，支持按股票代码和频率过滤

        Args:
            code (str, optional): 股票代码过滤条件
            frequency (FREQUENCY_TYPES): 数据频率过滤条件
            start_date (datetime, optional): 统计此日期之后的记录
            end_date (datetime, optional): 统计此日期之前的记录

        Returns:
            ServiceResult: 统计结果，data中包含总记录数量
        """
        start_time = time.time()
        self._log_operation_start("count_bars", code=code, frequency=frequency.value)

        try:
            filters = {}
            if code:
                filters["code"] = code
            if frequency:
                filters["frequency"] = frequency
            if start_date:
                filters["timestamp__gte"] = datetime_normalize(start_date)
            if end_date:
                filters["timestamp__lte"] = datetime_normalize(end_date)

            count = self._crud_repo.count(filters=filters)
            duration = time.time() - start_time
            self._log_operation_end("count_bars", True, duration)

            return ServiceResult.success(
                data=count,
                message=f"Found {count} bar records matching criteria"
            )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation_end("count_bars", False, duration)
            self._logger.ERROR(f"Failed to count bar records: {e}")
            return ServiceResult.error(
                error=f"Database query failed: {str(e)}"
            )

    def get_available_codes(self, frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY) -> ServiceResult:
        """
        Gets list of available stock codes for a given frequency.

        Args:
            frequency: Data frequency

        Returns:
            ServiceResult - 包装股票代码列表，使用result.data获取列表
        """
        start_time = time.time()
        self._log_operation_start("get_available_codes", frequency=frequency.value)

        try:
            codes = self._crud_repo.find(filters={"frequency": frequency}, distinct_field="code")

            # Ensure we return a list
            if not isinstance(codes, list):
                codes = list(codes) if codes else []

            codes = sorted(codes)
            duration = time.time() - start_time
            self._log_operation_end("get_available_codes", True, duration)

            return ServiceResult.success(
                data=codes,
                message=f"Found {len(codes)} available stock codes for {frequency.value} frequency"
            )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation_end("get_available_codes", False, duration)
            self._logger.ERROR(f"Failed to get available codes: {e}")
            return ServiceResult.error(
                error=f"Database query failed: {str(e)}"
            )

    def validate(
        self,
        code: str,
        start_date: str = None,
        end_date: str = None,
        frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY,
        **kwargs
    ) -> ServiceResult:
        """
        验证Bar数据质量（标准validate方法）

        Args:
            code: Stock code
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            frequency: Data frequency
            **kwargs: Additional validation parameters

        Returns:
            ServiceResult - 包装DataValidationResult，使用result.data获取验证结果
        """
        from datetime import datetime
        from dateutil.parser import parse

        start_time = time.time()
        self._log_operation_start("validate_bars", code=code, start_date=start_date, end_date=end_date)

        # Create validation result
        result = DataValidationResult.create_for_entity(
            entity_type="bars",
            entity_identifier=code,
            validation_type="business_rules"
        )

        try:
            # Get bars data for validation
            bars_result = self.get(code=code, start_date=start_date, end_date=end_date, frequency=frequency, page_size=10000)

            if not bars_result.success or not bars_result.data:
                result.add_error(f"No bar data found for validation: {bars_result.message}")
                duration = time.time() - start_time
                result.validation_timestamp = datetime.now()
                result.set_metadata("validation_duration", duration)
                return ServiceResult.error(
                    message=f"Bar data validation failed: {bars_result.message}",
                    data=result
                )

            bars = bars_result.data
            result.set_metadata("total_records", len(bars))
            result.set_metadata("frequency", frequency.value if frequency else None)

            # OHLC relationship validation
            ohlc_violations = []
            for i, bar in enumerate(bars):
                if bar.high < max(bar.open, bar.close):
                    result.add_error(f"OHLC violation: High({bar.high}) < max(Open({bar.open}), Close({bar.close})) at {bar.timestamp}")
                    ohlc_violations.append(f"High < max(Open, Close) at {bar.timestamp}")

                if bar.low > min(bar.open, bar.close):
                    result.add_error(f"OHLC violation: Low({bar.low}) > min(Open({bar.open}), Close({bar.close})) at {bar.timestamp}")
                    ohlc_violations.append(f"Low > min(Open, Close) at {bar.timestamp}")

                # Price validation
                if any(price <= 0 for price in [bar.open, bar.high, bar.low, bar.close]):
                    result.add_error(f"Non-positive price detected at {bar.timestamp}: O={bar.open}, H={bar.high}, L={bar.low}, C={bar.close}")

                # Volume validation
                if bar.volume < 0:
                    result.add_error(f"Negative volume detected at {bar.timestamp}: {bar.volume}")

            result.set_metadata("ohlc_violations", ohlc_violations)

            # Duplicate timestamp validation
            timestamps = [bar.timestamp for bar in bars]
            unique_timestamps = set(timestamps)
            if len(timestamps) != len(unique_timestamps):
                duplicate_count = len(timestamps) - len(unique_timestamps)
                result.add_error(f"Found {duplicate_count} duplicate timestamps")

                # Find specific duplicates
                from collections import Counter
                timestamp_counts = Counter(timestamps)
                duplicates = [ts for ts, count in timestamp_counts.items() if count > 1]
                result.set_metadata("duplicate_timestamps", [dt.isoformat() for dt in duplicates])

            # Time sequence validation (for daily data)
            if frequency == FREQUENCY_TYPES.DAY and len(bars) > 1:
                sorted_bars = sorted(bars, key=lambda x: x.timestamp)
                for i in range(1, len(sorted_bars)):
                    if sorted_bars[i].timestamp <= sorted_bars[i-1].timestamp:
                        result.add_error(f"Timestamp sequence violation: {sorted_bars[i].timestamp} <= {sorted_bars[i-1].timestamp}")

            # Price continuity validation (check for extreme jumps)
            if len(bars) > 1:
                sorted_bars = sorted(bars, key=lambda x: x.timestamp)
                for i in range(1, len(sorted_bars)):
                    prev_close = sorted_bars[i-1].close
                    curr_open = sorted_bars[i].open

                    if prev_close > 0:
                        jump_ratio = abs(curr_open - prev_close) / prev_close
                        if jump_ratio > 0.2:  # 20% jump threshold
                            result.add_warning(f"Large price jump detected: {jump_ratio*100:.1f}% from {prev_close} to {curr_open} at {sorted_bars[i].timestamp}")

            # Date range validation
            if start_date and end_date:
                try:
                    start_dt = parse(start_date)
                    end_dt = parse(end_date)
                    result.set_metadata("expected_range", (start_dt.date().isoformat(), end_dt.date().isoformat()))

                    # Check if we have data within expected range
                    actual_dates = [bar.timestamp.date() for bar in bars]
                    if actual_dates:
                        result.set_metadata("actual_range", (min(actual_dates).isoformat(), max(actual_dates).isoformat()))

                except Exception as e:
                    result.add_warning(f"Date range parsing issue: {e}")

            duration = time.time() - start_time
            self._log_operation_end("validate", result.error_count == 0, duration)

            result.validation_timestamp = datetime.now()
            result.set_metadata("validation_duration", duration)
            result.set_metadata("validation_summary", {
                "total_records": len(bars),
                "error_count": result.error_count,
                "warning_count": result.warning_count,
                "quality_score": result.data_quality_score
            })

            return ServiceResult.success(
                data=result,
                message=f"Bar data validation completed: {len(bars)} records processed"
            )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation_end("validate", False, duration)
            self._logger.ERROR(f"Failed to validate bars: {e}")

            result.add_error(f"Validation process failed: {str(e)}")
            result.validation_timestamp = datetime.now()
            result.set_metadata("validation_duration", duration)
            result.is_valid = False

            return ServiceResult.error(
                message=f"Bar data validation failed: {str(e)}",
                data=result
            )

    def check_integrity(
        self,
        code: str,
        start_date: str = None,
        end_date: str = None,
        frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY,
        **kwargs
    ) -> ServiceResult:
        """
        检查Bar数据完整性（标准check_integrity方法）

        Args:
            code: Stock code
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            frequency: Data frequency
            **kwargs: Additional integrity check parameters

        Returns:
            ServiceResult - 包装DataIntegrityCheckResult，使用result.data获取完整性检查结果
        """
        from datetime import datetime, timedelta
        from dateutil.parser import parse
        import pandas as pd

        start_time = time.time()
        self._log_operation_start("check_bars_integrity", code=code, start_date=start_date, end_date=end_date)

        # Determine check range
        if start_date and end_date:
            try:
                start_dt = parse(start_date)
                end_dt = parse(end_date)
                check_range = (start_dt, end_dt)
            except Exception:
                # Default to recent data if date parsing fails
                end_dt = datetime.now()
                start_dt = end_dt - timedelta(days=30)
                check_range = (start_dt, end_dt)
        else:
            # Default to last 30 days
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=30)
            check_range = (start_dt, end_dt)

        # Create integrity check result
        result = DataIntegrityCheckResult.create_for_entity(
            entity_type="bars",
            entity_identifier=code,
            check_range=check_range,
            check_duration=0.0
        )

        try:
            # Get actual data
            bars_result = self.get(code=code, start_date=start_date, end_date=end_date, frequency=frequency, page_size=10000)

            if not bars_result.success:
                result.add_issue("data_retrieval_failure", f"Failed to retrieve data: {bars_result.message}")
                result.check_duration = time.time() - start_time
                return ServiceResult.error(
                    message=f"Bar data integrity check failed: {bars_result.message}",
                    data=result
                )

            bars = bars_result.data if bars_result.data else []
            result.total_records = len(bars)

            # Set basic metadata
            result.set_metadata("frequency", frequency.value if frequency else None)
            result.set_metadata("code", code)

            if not bars:
                # No data found - this could be expected or an issue
                result.missing_records = 0  # We don't know expected count yet
                result.add_issue("no_data_found", f"No bar data found for {code} in specified range")
                result.add_recommendation("Check if stock exists and data source covers this period")
                result.check_duration = time.time() - start_time
                return ServiceResult.success(
                    data=result,
                    message=f"Bar data integrity check completed: no data found for {code}"
                )

            # Analyze data completeness for daily frequency
            if frequency and frequency == FREQUENCY_TYPES.DAY:
                expected_trading_days = self._calculate_expected_trading_days(check_range[0], check_range[1])
                result.set_metadata("expected_trading_days", len(expected_trading_days))

                actual_trading_days = set(bar.timestamp.date() for bar in bars)
                result.set_metadata("actual_trading_days", len(actual_trading_days))

                missing_days = expected_trading_days - actual_trading_days
                result.missing_records = len(missing_days)

                if missing_days:
                    missing_dates = sorted([day.isoformat() for day in missing_days])
                    result.set_metadata("missing_dates", missing_dates)
                    result.add_issue("missing_trading_days", f"Missing {len(missing_days)} trading days")
                    result.add_recommendation("Check market holidays and data source coverage")

                # Check for weekends in data (shouldn't exist for daily data)
                weekend_records = [bar for bar in bars if bar.timestamp.weekday() >= 5]
                if weekend_records:
                    result.add_issue("weekend_data_found", f"Found {len(weekend_records)} weekend records")
                    result.set_metadata("weekend_records", len(weekend_records))

            # Check for duplicate timestamps
            timestamps = [bar.timestamp for bar in bars]
            unique_timestamps = set(timestamps)
            duplicate_count = len(timestamps) - len(unique_timestamps)

            if duplicate_count > 0:
                result.duplicate_records = duplicate_count
                result.add_issue("duplicate_timestamps", f"Found {duplicate_count} duplicate timestamps")

                # Find specific duplicates
                from collections import Counter
                timestamp_counts = Counter(timestamps)
                duplicates = [ts for ts, count in timestamp_counts.items() if count > 1]
                result.set_metadata("duplicate_timestamps", [dt.isoformat() for dt in duplicates])
                result.add_recommendation("Remove duplicate records and investigate data source")

            # Check for data gaps (more than expected interval)
            if len(bars) > 1:
                sorted_bars = sorted(bars, key=lambda x: x.timestamp)
                gaps = []

                for i in range(1, len(sorted_bars)):
                    prev_ts = sorted_bars[i-1].timestamp
                    curr_ts = sorted_bars[i].timestamp

                    # For daily data, gap > 2 days might indicate missing data
                    if frequency == FREQUENCY_TYPES.DAY:
                        gap_days = (curr_ts.date() - prev_ts.date()).days
                        if gap_days > 2:  # Allow for weekends
                            gaps.append({
                                "start": prev_ts.isoformat(),
                                "end": curr_ts.isoformat(),
                                "gap_days": gap_days
                            })

                if gaps:
                    result.add_issue("data_gaps", f"Found {len(gaps)} significant data gaps")
                    result.set_metadata("data_gaps", gaps)

            # Check price consistency
            price_anomalies = []
            for i, bar in enumerate(bars):
                # Check for zero or negative prices
                if bar.close <= 0:
                    price_anomalies.append(f"Zero/negative close price at {bar.timestamp}: {bar.close}")

                # Check for extreme price changes
                if i > 0:
                    prev_close = bars[i-1].close
                    if prev_close > 0:
                        change_pct = abs(bar.close - prev_close) / prev_close
                        if change_pct > 0.5:  # 50% change threshold
                            price_anomalies.append(f"Extreme price change: {change_pct*100:.1f}% at {bar.timestamp}")

            if price_anomalies:
                result.add_issue("price_anomalies", f"Found {len(price_anomalies)} price anomalies")
                result.set_metadata("price_anomalies", price_anomalies[:10])  # Store first 10

            # Calculate final integrity score
            result._recalculate_integrity_score()

            # Set final metadata
            result.check_duration = time.time() - start_time
            result.set_metadata("check_summary", {
                "total_records": result.total_records,
                "missing_records": result.missing_records,
                "duplicate_records": result.duplicate_records,
                "integrity_score": result.integrity_score,
                "is_healthy": result.is_healthy()
            })

            # Add recommendations based on findings
            if result.missing_records > 0:
                result.add_recommendation("Investigate missing trading days and update data source")

            if result.duplicate_records > 0:
                result.add_recommendation("Clean up duplicate timestamps to ensure data consistency")

            if result.integrity_score < 90:
                result.add_recommendation("Review data quality and consider data source improvements")

            self._log_operation_end("check_integrity", result.is_healthy(), result.check_duration)
            return ServiceResult.success(
                data=result,
                message=f"Bar data integrity check completed: {result.total_records} records processed"
            )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation_end("check_integrity", False, duration)
            self._logger.ERROR(f"Failed to check bars integrity: {e}")

            result.add_issue("integrity_check_failure", f"Integrity check process failed: {str(e)}")
            result.check_duration = duration
            result.integrity_score = 0.0

            return ServiceResult.error(
                message=f"Bar data integrity check failed: {str(e)}",
                data=result
            )

    def _calculate_expected_trading_days(self, start_date: datetime, end_date: datetime) -> set:
        """
        Calculate expected trading days (excluding weekends) for a date range.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            set of datetime.date objects representing expected trading days
        """
        from datetime import timedelta

        trading_days = set()
        current_date = start_date.date()
        end_date_only = end_date.date()

        while current_date <= end_date_only:
            # Exclude weekends (Saturday=5, Sunday=6)
            if current_date.weekday() < 5:
                trading_days.add(current_date)
            current_date += timedelta(days=1)

        return trading_days

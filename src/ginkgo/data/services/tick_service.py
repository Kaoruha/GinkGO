"""
Tick Data Service (Class-based)

This service handles the business logic for synchronizing tick data.
It coordinates between data sources (e.g., TDX) and CRUD operations.

Enhanced with comprehensive error handling, retry mechanisms, and structured returns.
"""

import time
from datetime import datetime, timedelta
from typing import List, Union, Any, Optional, Dict
import pandas as pd

from ginkgo.libs import datetime_normalize, RichProgress, cache_with_expiration, retry, to_decimal, ensure_tick_table
from ginkgo.data import mappers
from ginkgo.enums import TICKDIRECTION_TYPES, ADJUSTMENT_TYPES
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.libs.data.results import DataSyncResult, DataValidationResult, DataIntegrityCheckResult


class TickService(BaseService):
    def __init__(self, data_source, stockinfo_service, crud_repo=None, redis_service=None, adjustfactor_service=None):
        """Initializes the service with its dependencies."""
        # TickService handles CRUD creation dynamically, so crud_repo is optional
        super().__init__(crud_repo=crud_repo, data_source=data_source, stockinfo_service=stockinfo_service)

        # 集成RedisService
        if redis_service is None:
            from ginkgo.data.services.redis_service import RedisService

            redis_service = RedisService()
        self._redis_service = redis_service

        # Initialize AdjustfactorService for price adjustment support
        if adjustfactor_service is None:
            from ginkgo.data.services.adjustfactor_service import AdjustfactorService
            from ginkgo.data.crud.adjustfactor_crud import AdjustfactorCRUD

            adjustfactor_service = AdjustfactorService(
                crud_repo=AdjustfactorCRUD(), data_source=data_source, stockinfo_service=stockinfo_service
            )
        self._adjustfactor_service = adjustfactor_service

  
    @retry(max_try=3)
    def sync_date(self, code: str, date: datetime, fast_mode: bool = False) -> ServiceResult:
        """
        同步指定股票代码在指定日期的tick数据。

        Args:
            code: Stock code (e.g., '000001.SZ')
            date: Target date
            fast_mode: If True, skip if data already exists

        Returns:
            ServiceResult - 包装同步结果数据，使用result.data获取DataSyncResult详细信息
        """
        start_time = time.time()
        self._log_operation_start("sync_date", code=code, date=date, fast_mode=fast_mode)

        try:
            # Validate stock code
            if not self._stockinfo_service.exists(code):
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="tick",
                    entity_identifier=code,
                    sync_range=(date, date),
                    sync_strategy="single_date"
                )
                sync_result.records_failed = 1
                sync_result.add_error(0, f"Stock code {code} not in stock list")
                return ServiceResult.failure(
                    message=f"Stock code {code} not in stock list",
                    data=sync_result
                )

            # Normalize date and create time range
            normalized_date = datetime_normalize(date).replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = normalized_date + timedelta(minutes=1)
            end_date = normalized_date + timedelta(days=1) - timedelta(minutes=1)

            self._logger.INFO(f"Syncing tick data for {code} on {normalized_date.date()}")

            # Check if data exists and fast_mode is enabled
            if fast_mode:
                try:
                    existing_result = self.get(code=code, start_date=start_date, end_date=end_date)
                    if existing_result.success and existing_result.data and len(existing_result.data) > 0:
                        sync_result = DataSyncResult.create_for_entity(
                            entity_type="tick",
                            entity_identifier=code,
                            sync_range=(normalized_date, normalized_date),
                            sync_strategy="single_date"
                        )
                        sync_result.records_skipped = len(existing_result.data)
                        sync_result.is_idempotent = True
                        sync_result.add_warning(f"Data already exists in DB ({len(existing_result.data)} records), skipped")
                        duration = time.time() - start_time
                        self._log_operation_end("sync_date", True, duration)
                        return ServiceResult.success(
                            data=sync_result,
                            message=f"Data already exists for {code} on {normalized_date.date()}, skipped"
                        )
                except Exception as e:
                    self._logger.WARN(f"Failed to check existing data: {str(e)}")

            # Fetch data from source with retry mechanism
            try:
                raw_data = self._fetch_tick_data_with_validation(code, normalized_date)
                if raw_data is None or raw_data.empty:
                    sync_result = DataSyncResult.create_for_entity(
                        entity_type="tick",
                        entity_identifier=code,
                        sync_range=(normalized_date, normalized_date),
                        sync_strategy="single_date"
                    )
                    sync_result.add_warning("No data available from source")
                    duration = time.time() - start_time
                    self._log_operation_end("sync_date", True, duration)
                    return ServiceResult.success(
                        data=sync_result,
                        message=f"No tick data available for {code} on {normalized_date.date()}"
                    )
            except Exception as e:
                return ServiceResult.error(
                    error=f"Failed to fetch data from source: {str(e)}"
                )

            # Validate tick data quality
            if not self._validate_tick_data(raw_data):
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="tick",
                    entity_identifier=code,
                    sync_range=(normalized_date, normalized_date),
                    sync_strategy="single_date"
                )
                sync_result.records_failed = len(raw_data)
                sync_result.add_error(0, "Data quality validation failed")
                return ServiceResult.failure(
                    message="Data quality validation failed",
                    data=sync_result
                )

            # Convert to tick models with error handling
            try:
                tick_models = mappers.dataframe_to_tick_models(raw_data, code)
                if not tick_models:
                    sync_result = DataSyncResult.create_for_entity(
                        entity_type="tick",
                        entity_identifier=code,
                        sync_range=(normalized_date, normalized_date),
                        sync_strategy="single_date"
                    )
                    sync_result.add_warning("No valid models generated from data")
                    return ServiceResult.success(
                        data=sync_result,
                        message="No valid models generated from data"
                    )
            except Exception as e:
                # Fallback: try row-by-row conversion
                self._logger.WARN(f"Batch conversion failed for {code} on {normalized_date.date()}, attempting row-by-row: {e}")
                tick_models = self._convert_ticks_individually(raw_data, code)
                if not tick_models:
                    sync_result = DataSyncResult.create_for_entity(
                        entity_type="tick",
                        entity_identifier=code,
                        sync_range=(normalized_date, normalized_date),
                        sync_strategy="single_date"
                    )
                    sync_result.records_failed = len(raw_data)
                    sync_result.add_error(0, f"Data mapping failed: {str(e)}")
                    return ServiceResult.failure(
                        message=f"Data mapping failed: {str(e)}",
                        data=sync_result
                    )

            # Enhanced database operations with error handling
            try:
                # Use dynamic CRUD repo based on stock code
                from ginkgo.data.crud.tick_crud import TickCRUD
                # Use TickCRUD instance from dependency injection

                # Remove existing data for the date range (non-transactional for ClickHouse)
                removed_count = self._crud_repo.remove(
                    filters={"code": code, "timestamp__gte": start_date, "timestamp__lte": end_date}
                )

                # Insert new data in optimized batches for large tick datasets
                batch_size = 1000  # Smaller batches for tick data
                total_added = 0

                for i in range(0, len(tick_models), batch_size):
                    batch = tick_models[i : i + batch_size]
                    self._crud_repo.add_batch(batch)
                    total_added += len(batch)

                    # Progress feedback for large datasets
                    if len(tick_models) > 5000 and i % (batch_size * 5) == 0:
                        self._logger.DEBUG(f"Processed {i + len(batch)}/{len(tick_models)} ticks for {code}")

                duration = time.time() - start_time
                self._log_operation_end("sync_date", True, duration)

                # Create DataSyncResult
                sync_result = DataSyncResult(
                    entity_type="tick",
                    entity_identifier=code,
                    sync_range=(normalized_date, normalized_date),
                    records_processed=len(raw_data),
                    records_added=total_added,
                    records_updated=0,
                    records_skipped=0,
                    records_failed=0,
                    sync_duration=duration,
                    is_idempotent=True,
                    sync_strategy="single_date"
                )

                # Set additional metadata
                sync_result.set_metadata("date", normalized_date.date())
                sync_result.set_metadata("removed_count", removed_count or 0)
                sync_result.set_metadata("data_source", type(self._data_source).__name__)
                sync_result.set_metadata("batch_size", batch_size)

                if removed_count and removed_count > 0:
                    sync_result.add_warning(f"Removed {removed_count} existing records")

                self._logger.INFO(f"Successfully synced {total_added} ticks for {code} on {normalized_date.date()}")

                return ServiceResult.success(
                    data=sync_result,
                    message=f"Tick data for {code} on {normalized_date.date()} saved successfully: {total_added} records"
                )

            except Exception as e:
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="tick",
                    entity_identifier=code,
                    sync_range=(normalized_date, normalized_date),
                    sync_strategy="single_date"
                )
                sync_result.records_failed = len(tick_models) if tick_models else len(raw_data)
                sync_result.add_error(0, f"Database operation failed: {str(e)}")
                duration = time.time() - start_time
                self._log_operation_end("sync_date", False, duration)
                return ServiceResult.failure(
                    message=f"Database operation failed: {str(e)}",
                    data=sync_result
                )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation_end("sync_date", False, duration)
            self._logger.ERROR(f"Unexpected error syncing tick data for {code} on {date}: {e}")
            return ServiceResult.error(
                error=f"Unexpected error during sync: {str(e)}"
            )

    def sync_smart(self, code: str, fast_mode: bool = False, max_backtrack_days: int = 0) -> ServiceResult:
        """
        智能同步指定股票代码的tick数据。

        Args:
            code: Stock code
            fast_mode: If True, skip dates that already have data
            max_backtrack_days: Maximum number of days to go back (0 = unlimited)

        Returns:
            ServiceResult - 包装同步结果数据，使用result.data获取DataSyncResult详细信息
        """
        start_time = time.time()
        self._log_operation_start("sync_smart", code=code, fast_mode=fast_mode, max_backtrack_days=max_backtrack_days)

        try:
            # Validate stock code
            if not self._stockinfo_service.exists(code):
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="tick",
                    entity_identifier=code,
                    sync_strategy="smart"
                )
                sync_result.records_failed = 1
                sync_result.add_error(0, f"Stock code {code} not in stock list")
                return ServiceResult.failure(
                    message=f"Stock code {code} not in stock list",
                    data=sync_result
                )

            # Get stock info to determine valid date range
            try:
                result = self._stockinfo_service.get(filters={"code": code})
                stock_info = result.data if result.success else []
                if len(stock_info) == 0:
                    sync_result = DataSyncResult.create_for_entity(
                        entity_type="tick",
                        entity_identifier=code,
                        sync_strategy="smart"
                    )
                    sync_result.records_failed = 1
                    sync_result.add_error(0, f"No stock info found for {code}")
                    return ServiceResult.failure(
                        message=f"No stock info found for {code}",
                        data=sync_result
                    )
            except Exception as e:
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="tick",
                    entity_identifier=code,
                    sync_strategy="smart"
                )
                sync_result.records_failed = 1
                sync_result.add_error(0, f"Failed to get stock info: {str(e)}")
                return ServiceResult.failure(
                    message=f"Failed to get stock info: {str(e)}",
                    data=sync_result
                )

            list_date = datetime_normalize(stock_info.to_dataframe().iloc[0]["list_date"])
            current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            # Initialize Redis cache for tracking processed dates using RedisService
            processed_dates = set()
            try:
                # 使用RedisService获取已处理的日期
                cached_progress = self._redis_service.get_sync_progress(code, "tick")
                processed_dates = cached_progress
            except Exception as e:
                self._logger.WARN(f"Redis connection failed, proceeding without cache: {e}")

            # Calculate actual total dates to process
            actual_days = (current_date - list_date).days + 1
            total_days = actual_days
            # Determine total days based on max_backtrack_days setting
            if max_backtrack_days > 0:
                total_days = min(actual_days, max_backtrack_days)

            update_count = 0
            total_dates_processed = 0
            successful_dates = 0
            failed_dates = 0
            skipped_dates = 0
            total_records_processed = 0
            total_records_added = 0
            results = []

            self._logger.INFO(f"Starting smart tick sync for {code} ({total_days} days)")

            with RichProgress() as progress:
                task = progress.add_task(f"[cyan]Syncing Tick Data for {code}", total=total_days)

                while current_date >= list_date and update_count < total_days:
                    update_count += 1
                    total_dates_processed += 1
                    date_str = current_date.strftime("%Y-%m-%d")

                    progress.update(task, description=f"Processing {code} on {date_str}")

                    # Check cache
                    if date_str in processed_dates:
                        self._logger.DEBUG(f"Skipping {code} on {date_str} - already processed (cached)")
                        skipped_dates += 1
                        current_date -= timedelta(days=1)
                        progress.update(task, advance=1)
                        continue

                    # Process the date
                    try:
                        day_result = self.sync_date(code, current_date, fast_mode)
                        results.append(day_result)

                        if day_result.success:
                            data_sync_result = day_result.data
                            if data_sync_result and hasattr(data_sync_result, 'records_processed'):
                                total_records_processed += data_sync_result.records_processed
                                total_records_added += data_sync_result.records_added

                            # Check if skipped
                            if "skipped" in day_result.message or (data_sync_result and data_sync_result.records_skipped > 0):
                                skipped_dates += 1
                            else:
                                successful_dates += 1

                            self._logger.INFO(
                                f"Updated tick data for {code} on {date_str}: {data_sync_result.records_added if data_sync_result else 0} records"
                            )

                            # Cache if it's more than 2 days old (likely no data available) or if successful
                            should_cache = (datetime.now() - current_date).days > 2 or day_result.success
                        else:
                            failed_dates += 1

                        # Update Redis cache using RedisService
                        if should_cache:
                            try:
                                self._redis_service.save_sync_progress(code, current_date, "tick")
                                processed_dates.add(date_str)
                            except Exception as e:
                                self._logger.WARN(f"Failed to update Redis cache: {e}")

                    except Exception as e:
                        failed_dates += 1
                        self._logger.ERROR(f"Unexpected error processing {code} on {date_str}: {e}")

                    current_date -= timedelta(days=1)
                    progress.update(task, advance=1)

            duration = time.time() - start_time
            self._log_operation_end("sync_smart", failed_dates == 0, duration)

            # Create DataSyncResult to wrap smart sync results
            sync_result = DataSyncResult(
                entity_type="tick",
                entity_identifier=code,
                sync_range=(list_date, datetime.now()),
                records_processed=total_records_processed,
                records_added=total_records_added,
                records_updated=0,
                records_skipped=skipped_dates,
                records_failed=failed_dates,
                sync_duration=duration,
                is_idempotent=True,
                sync_strategy="smart"
            )

            # Set success rate
            sync_result.success_rate = (successful_dates + skipped_dates) / total_dates_processed if total_dates_processed > 0 else 0

            # Set additional metadata
            sync_result.set_metadata("total_dates_processed", total_dates_processed)
            sync_result.set_metadata("successful_dates", successful_dates)
            sync_result.set_metadata("failed_dates", failed_dates)
            sync_result.set_metadata("skipped_dates", skipped_dates)
            sync_result.set_metadata("max_backtrack_days", max_backtrack_days)
            sync_result.set_metadata("data_source", type(self._data_source).__name__)
            sync_result.set_metadata("daily_results", results)

            self._logger.INFO(
                f"Completed tick sync for {code}: {successful_dates} successful, {failed_dates} failed, {skipped_dates} skipped"
            )

            if failed_dates == 0:
                return ServiceResult.success(
                    data=sync_result,
                    message=f"Smart sync completed successfully: {successful_dates} successful, {skipped_dates} skipped"
                )
            else:
                return ServiceResult.failure(
                    message=f"Smart sync completed with failures: {successful_dates} successful, {failed_dates} failed, {skipped_dates} skipped",
                    data=sync_result
                )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation_end("sync_smart", False, duration)
            self._logger.ERROR(f"Unexpected error in smart sync for {code}: {e}")
            return ServiceResult.error(
                error=f"Unexpected error during smart sync: {str(e)}"
            )

    def sync_range(
        self, code: str, start_date: datetime, end_date: datetime, fast_mode: bool = True, use_cache: bool = True
    ) -> ServiceResult:
        """
        为指定股票代码同步指定日期范围的tick数据（支持中断恢复）

        Args:
            code: 股票代码 (e.g., '000001.SZ')
            start_date: 开始日期
            end_date: 结束日期
            fast_mode: 快速模式，跳过已存在的数据
            use_cache: 是否使用Redis缓存记录进度（支持中断恢复）

        Returns:
            ServiceResult - 包装同步结果数据，使用result.data获取DataSyncResult详细信息
        """
        start_time = time.time()
        self._log_operation_start("sync_range", code=code, start_date=start_date,
                                  end_date=end_date, fast_mode=fast_mode, use_cache=use_cache)

        try:
            # 验证股票代码
            if not self._stockinfo_service.exists(code):
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="tick",
                    entity_identifier=code,
                    sync_range=(start_date, end_date),
                    sync_strategy="range"
                )
                sync_result.records_failed = 1
                sync_result.add_error(0, f"Stock code {code} not in stock list")
                return ServiceResult.failure(
                    message=f"Stock code {code} not in stock list",
                    data=sync_result
                )

            # 标准化日期
            start_date = datetime_normalize(start_date)
            end_date = datetime_normalize(end_date)

            if start_date > end_date:
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="tick",
                    entity_identifier=code,
                    sync_range=(start_date, end_date),
                    sync_strategy="range"
                )
                sync_result.records_failed = 1
                sync_result.add_error(0, f"Start date {start_date.date()} cannot be later than end date {end_date.date()}")
                return ServiceResult.failure(
                    message=f"Start date {start_date.date()} cannot be later than end date {end_date.date()}",
                    data=sync_result
                )

            # 获取缓存进度摘要
            cache_completion_rate = 0.0
            if use_cache:
                try:
                    progress = self._redis_service.get_progress_summary(code, start_date, end_date, "tick")
                    cache_completion_rate = progress["completion_rate"]
                    self._logger.INFO(
                        f"Cache info for {code}: {cache_completion_rate:.2%} complete, {progress['missing_count']} dates missing"
                    )
                except Exception as e:
                    self._logger.WARN(f"Failed to get cache info: {str(e)}")

            total_dates = (end_date - start_date).days + 1
            successful_dates = 0
            failed_dates = 0
            skipped_dates = 0
            resumed_from_cache = 0
            total_records_added = 0
            results = []

            self._logger.INFO(f"Starting tick sync for {code} from {start_date.date()} to {end_date.date()} ({total_dates} days)")

            with RichProgress() as progress:
                task = progress.add_task(f"[cyan]Syncing Tick Data for {code}", total=total_dates)

                current_date = start_date
                while current_date <= end_date:
                    # 检查是否已在缓存中（中断恢复点检测）
                    if use_cache:
                        try:
                            if self._redis_service.check_date_synced(code, current_date, "tick"):
                                resumed_from_cache += 1
                                self._logger.DEBUG(f"Skipping {code} on {current_date.date()} - found in cache (resuming)")
                                current_date += timedelta(days=1)
                                progress.update(task, advance=1)
                                continue
                        except Exception as e:
                            self._logger.WARN(f"Failed to check cache for {current_date.date()}: {str(e)}")

                    progress.update(task, description=f"Processing {code} on {current_date.date()}")

                    # 调用单日同步方法
                    day_result = self.sync_date(code, current_date, fast_mode)
                    results.append(day_result)

                    if day_result.success:
                        data_sync_result = day_result.data
                        if data_sync_result and hasattr(data_sync_result, 'records_added'):
                            total_records_added += data_sync_result.records_added

                            # 判断是否为跳过的情况（有warning标记）
                            if len(data_sync_result.warnings) > 0 and "skipped" in day_result.message:
                                skipped_dates += 1
                            else:
                                successful_dates += 1

                        # 更新Redis缓存（记录成功处理的日期）
                        if use_cache:
                            try:
                                self._redis_service.save_sync_progress(code, current_date, "tick")
                            except Exception as e:
                                self._logger.WARN(f"Failed to update cache for {current_date.date()}: {str(e)}")
                    else:
                        failed_dates += 1

                    current_date += timedelta(days=1)
                    progress.update(task, advance=1)

            duration = time.time() - start_time
            self._log_operation_end("sync_range", failed_dates == 0, duration)

            # 创建DataSyncResult来包装范围同步结果
            sync_result = DataSyncResult(
                entity_type="tick",
                entity_identifier=code,
                sync_range=(start_date, end_date),
                records_processed=sum(r.data.records_processed if r.data and hasattr(r.data, 'records_processed') else 0 for r in results),
                records_added=total_records_added,
                records_updated=0,
                records_skipped=skipped_dates,
                records_failed=failed_dates,
                sync_duration=duration,
                is_idempotent=True,
                sync_strategy="range"
            )

            # 设置成功率
            sync_result.success_rate = (successful_dates + skipped_dates) / total_dates if total_dates > 0 else 0

            # 设置附加元数据
            sync_result.set_metadata("total_dates", total_dates)
            sync_result.set_metadata("successful_dates", successful_dates)
            sync_result.set_metadata("failed_dates", failed_dates)
            sync_result.set_metadata("skipped_dates", skipped_dates)
            sync_result.set_metadata("resumed_from_cache", resumed_from_cache)
            sync_result.set_metadata("cache_completion_rate", cache_completion_rate)
            sync_result.set_metadata("data_source", type(self._data_source).__name__)
            sync_result.set_metadata("daily_results", results)

            # 添加失败详情
            if failed_dates > 0:
                failed_results = [r for r in results if not r.success]
                for failed_result in failed_results:
                    sync_result.add_error(0, f"Failed on date: {failed_result.message}")

            message = f"Tick range sync for {code}: {successful_dates} successful, {failed_dates} failed, {skipped_dates} skipped, {resumed_from_cache} resumed from cache"
            if failed_dates == 0:
                return ServiceResult.success(
                    data=sync_result,
                    message=message
                )
            else:
                return ServiceResult.failure(
                    message=message,
                    data=sync_result
                )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation_end("sync_range", False, duration)
            self._logger.ERROR(f"Unexpected error syncing range for {code}: {e}")
            return ServiceResult.error(
                error=f"Unexpected error during range sync: {str(e)}"
            )

    def sync_batch(
        self, codes: List[str], start_date: datetime, end_date: datetime, fast_mode: bool = True, use_cache: bool = True
    ) -> ServiceResult:
        """
        批量同步多个股票代码的指定日期范围数据

        Args:
            codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            fast_mode: 快速模式
            use_cache: 是否使用缓存

        Returns:
            ServiceResult - 包装批量同步结果数据，使用result.data获取DataSyncResult详细信息
        """
        start_time = time.time()
        self._log_operation_start("sync_batch", codes=codes, start_date=start_date,
                                  end_date=end_date, fast_mode=fast_mode, use_cache=use_cache)

        try:
            # 验证日期范围
            start_date = datetime_normalize(start_date)
            end_date = datetime_normalize(end_date)

            if start_date > end_date:
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="tick",
                    entity_identifier=f"batch_{len(codes)}_codes",
                    sync_range=(start_date, end_date),
                    sync_strategy="batch_range"
                )
                sync_result.records_failed = len(codes)
                sync_result.add_error(0, f"Start date {start_date.date()} cannot be later than end date {end_date.date()}")
                return ServiceResult.failure(
                    message=f"Start date {start_date.date()} cannot be later than end date {end_date.date()}",
                    data=sync_result
                )

            # 过滤有效股票代码
            valid_codes = [code for code in codes if self._stockinfo_service.exists(code)]
            invalid_codes = [code for code in codes if code not in valid_codes]

            total_codes = len(codes)
            successful_codes = 0
            failed_codes = len(invalid_codes)
            total_records_added = 0
            total_records_processed = 0
            total_resumed_from_cache = 0
            results = []
            failures = []

            # 记录无效代码
            for invalid_code in invalid_codes:
                failures.append({"code": invalid_code, "error": "Stock code not in stock list"})

            self._logger.INFO(
                f"Starting batch tick sync for {len(valid_codes)} valid codes out of {total_codes} provided from {start_date.date()} to {end_date.date()}"
            )

            # 批量处理有效代码
            with RichProgress() as progress:
                task = progress.add_task(f"[cyan]Syncing Batch Tick Data", total=len(valid_codes))

                for code in valid_codes:
                    try:
                        progress.update(task, description=f"Processing {code}")
                        code_result = self.sync_range(code, start_date, end_date, fast_mode, use_cache)
                        results.append(code_result)

                        if code_result.success:
                            successful_codes += 1
                            data_sync_result = code_result.data
                            if data_sync_result:
                                total_records_added += data_sync_result.records_added
                                total_records_processed += data_sync_result.records_processed
                                total_resumed_from_cache += data_sync_result.metadata.get("resumed_from_cache", 0)
                        else:
                            failed_codes += 1
                            failures.append({"code": code, "error": code_result.message})

                        progress.update(task, advance=1)

                    except Exception as e:
                        failed_codes += 1
                        failures.append({"code": code, "error": f"Unexpected error: {str(e)}"})
                        self._logger.ERROR(f"Unexpected error syncing {code}: {e}")
                        progress.update(task, advance=1)
                        continue

            duration = time.time() - start_time
            self._log_operation_end("sync_batch", failed_codes == 0, duration)

            # 创建DataSyncResult来包装批量同步结果
            sync_result = DataSyncResult(
                entity_type="tick",
                entity_identifier=f"batch_{total_codes}_codes",
                sync_range=(start_date, end_date),
                records_processed=total_records_processed,
                records_added=total_records_added,
                records_updated=0,
                records_skipped=0,
                records_failed=failed_codes,
                sync_duration=duration,
                is_idempotent=True,
                sync_strategy="batch_range"
            )

            # 设置成功率
            sync_result.success_rate = successful_codes / total_codes if total_codes > 0 else 0

            # 设置批量特定元数据
            sync_result.set_metadata("total_codes", total_codes)
            sync_result.set_metadata("valid_codes", len(valid_codes))
            sync_result.set_metadata("successful_codes", successful_codes)
            sync_result.set_metadata("failed_codes", failed_codes)
            sync_result.set_metadata("invalid_codes", len(invalid_codes))
            sync_result.set_metadata("total_resumed_from_cache", total_resumed_from_cache)
            sync_result.set_metadata("data_source", type(self._data_source).__name__)
            sync_result.set_metadata("batch_results", results)

            # 添加失败详情
            if failures:
                sync_result.set_metadata("failure_details", failures)
                for failure in failures:
                    sync_result.add_error(0, f"Code {failure['code']}: {failure['error']}")

            message = f"Batch tick sync completed: {successful_codes}/{total_codes} codes successful"

            if failed_codes == 0:
                return ServiceResult.success(
                    data=sync_result,
                    message=message
                )
            else:
                return ServiceResult.failure(
                    message=message,
                    data=sync_result
                )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation_end("sync_batch", False, duration)
            self._logger.ERROR(f"Unexpected error in batch sync: {e}")
            return ServiceResult.error(
                error=f"Unexpected error during batch sync: {str(e)}"
            )

    @ensure_tick_table
    def get(
        self,
        code: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        adjustment_type: ADJUSTMENT_TYPES = ADJUSTMENT_TYPES.FORE,
        **kwargs,
    ) -> ServiceResult:
        """
        Retrieves tick data from the database with optional price adjustment.

        Args:
            code: Stock code filter (required)
            start_date: Start datetime filter
            end_date: End datetime filter
            adjustment_type: Price adjustment type (NONE/FORE/BACK)
            **kwargs: Additional filters

        Returns:
            ServiceResult - 包装ModelList数据，使用result.data获取数据
                           data支持to_dataframe()和to_entities()方法
        """
        start_time = time.time()
        self._log_operation_start("get", code=code, start_date=start_date,
                                  end_date=end_date, adjustment_type=adjustment_type.value)

        try:
            # Validate required parameter
            if not code:
                return ServiceResult.failure(
                    message="Code parameter is required for tick data operations",
                    data=None
                )

            # 提取filters参数并从kwargs中移除，避免重复传递
            filters = kwargs.pop("filters", {})

            # 具体参数优先级高于filters中的对应字段
            if code:
                filters["code"] = code
            if start_date:
                filters["timestamp__gte"] = start_date
            if end_date:
                filters["timestamp__lte"] = end_date

            # Get original tick data using TickCRUD
            model_list = self._crud_repo.find(filters=filters, **kwargs)

            # Return original data if no adjustment needed
            if adjustment_type == ADJUSTMENT_TYPES.NONE:
                duration = time.time() - start_time
                self._log_operation_end("get", True, duration)
                return ServiceResult.success(
                    data=model_list,
                    message=f"Retrieved {len(model_list)} tick records without adjustment"
                )

            # Apply price adjustment if requested
            adjusted_data = self._apply_price_adjustment_to_modellist(model_list, code, adjustment_type)

            duration = time.time() - start_time
            self._log_operation_end("get", True, duration)

            return ServiceResult.success(
                data=adjusted_data,
                message=f"Retrieved and adjusted {len(adjusted_data)} tick records [adjustment_type: {adjustment_type.value}]"
            )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation_end("get", False, duration)
            self._logger.ERROR(f"Failed to get tick data: {e}")
            return ServiceResult.error(
                error=f"Database operation failed: {str(e)}"
            )

    
    # TODO: Tick数据复权方法性能优化
    # 当前Tick数据复权实现存在性能问题，在大数据量处理时效率较低
    # 需要优化的方向：
    # 1. 高频数据批量计算优化
    # 2. Tick级别复权因子插值算法优化
    def _apply_price_adjustment_to_modellist(
        self,
        ticks_data: ModelList,
        code: str,
        adjustment_type: ADJUSTMENT_TYPES,
    ) -> ModelList:
        """
        对ModelList应用复权计算，返回ModelList格式

        内部使用DataFrame进行高性能矩阵化计算，但最终转换为ModelList保持接口一致性

        Args:
            ticks_data: 原始Tick数据ModelList
            code: 股票代码
            adjustment_type: 复权类型

        Returns:
            复权后的Tick数据ModelList
        """
        if not code:
            self._logger.ERROR("Stock code required for price adjustment")
            return ticks_data

        # Handle empty data
        if not ticks_data:
            return ticks_data

        try:
            # Step 1: 转换为DataFrame进行高性能计算
            df_ticks = self._convert_modellist_to_dataframe(ticks_data)

            # Step 2: 获取复权因子
            factors_df = self._get_precomputed_adjustment_factors(code, df_ticks['timestamp'].unique(), adjustment_type)

            if factors_df.empty:
                self._logger.DEBUG(f"No precomputed adjustment factors found for {code}, returning original data")
                return ticks_data

            # Step 3: 矩阵化复权计算
            adjusted_df = self._apply_matrix_adjustment(df_ticks, factors_df, adjustment_type)

            # Step 4: 转换回ModelList格式
            adjusted_modellist = self._convert_dataframe_to_modellist(adjusted_df)

            return adjusted_modellist

        except Exception as e:
            self._logger.ERROR(f"Failed to apply price adjustment for {code}: {e}")
            return ticks_data

    def _convert_modellist_to_dataframe(self, ticks_data) -> pd.DataFrame:
        """
        将ModelList转换为DataFrame

        Args:
            ticks_data: ModelList数据

        Returns:
            DataFrame数据
        """
        return pd.DataFrame([
            {
                "code": tick.code,
                "timestamp": tick.timestamp,
                "price": float(tick.price),
                "volume": tick.volume,
                "direction": tick.direction,
            }
            for tick in ticks_data
        ])

    def _convert_dataframe_to_modellist(self, df_ticks: pd.DataFrame) -> ModelList:
        """
        将DataFrame转换为ModelList

        Args:
            df_ticks: DataFrame数据

        Returns:
            ModelList数据
        """
        from ginkgo.data.models.model_tick import MTick

        ticks = []
        for _, row in df_ticks.iterrows():
            tick = MTick()
            tick.code = row["code"]
            tick.timestamp = row["timestamp"]
            tick.price = to_decimal(row["price"])
            tick.volume = row["volume"]
            tick.direction = row["direction"]
            ticks.append(tick)

        return ModelList(ticks)

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
            dates: 日期列表
            adjustment_type: 复权类型

        Returns:
            复权因子DataFrame
        """
        try:
            start_date = min(dates)
            end_date = max(dates)

            # Get adjustment factors from the database
            from ginkgo import services
            adjustfactor_crud = services.data.cruds.adjustfactor()

            result = adjustfactor_crud.get_adjustfactors_page_filtered(
                code=code,
                start_date=start_date,
                end_date=end_date,
                page_size=10000  # Large enough for tick data
            )

            if not result.success or not result.data:
                return pd.DataFrame(columns=['timestamp', 'foreadjustfactor', 'backadjustfactor'])

            # Convert to DataFrame
            factors_data = []
            for factor in result.data:
                factors_data.append({
                    'timestamp': factor.timestamp,
                    'foreadjustfactor': float(factor.foreadjustfactor),
                    'backadjustfactor': float(factor.backadjustfactor)
                })

            return pd.DataFrame(factors_data)

        except Exception as e:
            self._logger.ERROR(f"Failed to get precomputed adjustment factors for {code}: {e}")
            return pd.DataFrame(columns=['timestamp', 'foreadjustfactor', 'backadjustfactor'])

    def _apply_matrix_adjustment(
        self,
        ticks_df: pd.DataFrame,
        factors_df: pd.DataFrame,
        adjustment_type: ADJUSTMENT_TYPES,
    ) -> pd.DataFrame:
        """
        高性能矩阵化复权计算

        利用pandas向量化操作，批量应用复权因子到所有价格数据

        Args:
            ticks_df: Tick数据DataFrame
            factors_df: 复权因子DataFrame
            adjustment_type: 复权类型

        Returns:
            复权后的DataFrame
        """
        # Determine which factor column to use
        factor_column = "foreadjustfactor" if adjustment_type == ADJUSTMENT_TYPES.FORE else "backadjustfactor"

        # Merge tick data with adjustment factors
        merged_df = pd.merge(
            ticks_df,
            factors_df[["timestamp", factor_column]],
            on="timestamp",
            how="left"
        )

        # Forward fill missing factors (use previous known factor)
        merged_df[factor_column] = merged_df[factor_column].fillna(method='ffill').fillna(1.0)

        # Apply adjustment to price column
        merged_df["price"] = merged_df["price"] * merged_df[factor_column]

        # Drop the temporary adjustment factor column
        result_df = merged_df.drop(columns=[factor_column])

        return result_df

    # 1. 批量计算优化，减少循环操作
    # 2. 内存使用优化，避免大DataFrame复制
    # 3. 复权因子缓存机制
    # 4. 并行计算支持
    # 未来版本需要重构以提升性能
    def _apply_price_adjustment(
        self,
        ticks_data: ModelList,
        code: str,
        adjustment_type: ADJUSTMENT_TYPES,
    ) -> ModelList:
        """
        Applies price adjustment factors to tick data.

        Args:
            ticks_data: Original tick data (DataFrame or list of models)
            code: Stock code for getting adjustment factors
            adjustment_type: Type of adjustment (FORE/BACK)
            as_dataframe: Whether ticks_data is DataFrame format

        Returns:
            Price-adjusted tick data in the same format as input
        """
        if not code:
            self._logger.ERROR("Stock code required for price adjustment")
            return ticks_data

        # Handle empty data
        if (isinstance(ticks_data, pd.DataFrame) and ticks_data.empty) or (
            isinstance(ticks_data, list) and len(ticks_data) == 0
        ):
            return ticks_data

        try:
            # Convert to DataFrame if needed for processing
            if as_dataframe:
                ticks_df = ticks_data.copy()
            else:
                # Convert list of models to DataFrame
                ticks_df = pd.DataFrame(
                    [
                        {
                            "code": tick.code,
                            "timestamp": tick.timestamp,
                            "price": float(tick.price),
                            "volume": tick.volume,
                            "direction": tick.direction,
                        }
                        for tick in ticks_data
                    ]
                )

            if ticks_df.empty:
                return ticks_data

            # Get adjustment factors for the same date range
            start_date = ticks_df["timestamp"].min().date()
            end_date = ticks_df["timestamp"].max().date()

            adjustfactors_result = self._adjustfactor_service.get(
                code=code, start_date=start_date, end_date=end_date
            )

            if not adjustfactors_result.success or not adjustfactors_result.data:
                self._logger.DEBUG(f"No adjustment factors found for {code}, returning original data")
                return ticks_data

            # Convert ModelList to DataFrame
            adjustfactors_df = adjustfactors_result.data.to_dataframe()

            if adjustfactors_df.empty:
                self._logger.DEBUG(f"No adjustment factors found for {code}, returning original data")
                return ticks_data

            # Apply adjustment factors
            adjusted_df = self._calculate_adjusted_tick_prices(ticks_df, adjustfactors_df, adjustment_type)

            # Return in original format
            if as_dataframe:
                return adjusted_df
            else:
                # Convert back to list of models
                from ginkgo.data.models.model_tick import MTick

                adjusted_ticks = []
                for _, row in adjusted_df.iterrows():
                    tick = MTick()
                    tick.code = row["code"]
                    tick.timestamp = row["timestamp"]
                    tick.price = to_decimal(row["price"])
                    tick.volume = int(row["volume"])
                    tick.direction = row["direction"]
                    adjusted_ticks.append(tick)
                return adjusted_ticks

        except Exception as e:
            self._logger.ERROR(f"Failed to apply price adjustment for {code}: {e}")
            return ticks_data

    def _calculate_adjusted_tick_prices(
        self, ticks_df: pd.DataFrame, adjustfactors_df: pd.DataFrame, adjustment_type: ADJUSTMENT_TYPES
    ) -> pd.DataFrame:
        """
        Calculates price-adjusted tick data using adjustment factors.

        Args:
            ticks_df: Tick data DataFrame
            adjustfactors_df: Adjustment factors DataFrame
            adjustment_type: Type of adjustment (FORE/BACK)

        Returns:
            DataFrame with adjusted prices
        """
        adjusted_df = ticks_df.copy()

        # Select appropriate adjustment factor column
        if adjustment_type == ADJUSTMENT_TYPES.FORE:
            factor_column = "foreadjustfactor"
        elif adjustment_type == ADJUSTMENT_TYPES.BACK:
            factor_column = "backadjustfactor"
        else:
            return adjusted_df  # No adjustment

        # Convert timestamp to date for matching with daily adjustment factors
        adjusted_df["date"] = pd.to_datetime(adjusted_df["timestamp"]).dt.date
        adjustfactors_df["date"] = pd.to_datetime(adjustfactors_df["timestamp"]).dt.date

        # Merge tick data with adjustment factors on date
        merged_df = pd.merge(adjusted_df, adjustfactors_df[["date", factor_column]], on="date", how="left")

        # Fill missing adjustment factors with 1.0 (no adjustment)
        merged_df[factor_column] = merged_df[factor_column].fillna(1.0)

        # Apply adjustment to price field
        if "price" in merged_df.columns:
            merged_df["price"] = merged_df["price"] * merged_df[factor_column]

        # Volume and direction remain unchanged
        # Drop the temporary columns
        result_df = merged_df.drop(columns=["date", factor_column])

        return result_df

    @ensure_tick_table
    def count(self, code: str = None, date: datetime = None, **kwargs) -> ServiceResult:
        """
        Counts the number of tick records matching the filters.

        Args:
            code: Stock code filter (required)
            date: Specific date filter (will be converted to date range)
            **kwargs: Additional filters

        Returns:
            ServiceResult - 包装计数结果，使用result.data获取数量
        """
        start_time = time.time()
        self._log_operation_start("count", code=code, date=date)

        try:
            # Validate required parameter
            if not code:
                return ServiceResult.failure(
                    message="Code parameter is required for tick count operations",
                    data=0
                )

            # 提取filters参数并从kwargs中移除，避免重复传递
            filters = kwargs.pop("filters", {})

            # 具体参数优先级高于filters中的对应字段
            if code:
                filters["code"] = code
            if date:
                date = datetime_normalize(date).replace(hour=0, minute=0, second=0, microsecond=0)
                filters["timestamp__gte"] = date
                filters["timestamp__lte"] = date + timedelta(days=1) - timedelta(microseconds=1)

            # Use TickCRUD for counting
            count = self._crud_repo.count(filters=filters)

            duration = time.time() - start_time
            self._log_operation_end("count", True, duration)

            return ServiceResult.success(
                data=count,
                message=f"Found {count} tick records matching criteria"
            )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation_end("count", False, duration)
            self._logger.ERROR(f"Failed to count tick records: {e}")
            return ServiceResult.error(
                error=f"Database query failed: {str(e)}"
            )

    def is_tick_data_available(self, code: str, date: datetime) -> bool:
        """
        Checks if tick data is available for a specific code and date.

        Args:
            code: Stock code
            date: Target date

        Returns:
            True if tick data exists for the date
        """
        count_result = self.count(code=code, date=date)
        if count_result.success:
            return count_result.data > 0
        return False

    def get_available_codes(self) -> List[str]:
        """
        Gets list of available stock codes that have tick data.

        Note: With partitioned tick tables, this method queries table names
        to find available stock codes rather than data records.

        Returns:
            List of unique stock codes
        """
        try:
            # With partitioned tables, we need to query table metadata to find available codes
            # This is a simplified implementation - in practice, you might want to use
            # the stockinfo service to get all valid codes and check if tables exist

            # For now, return an empty list and log a warning
            # TODO: Implement proper table metadata querying for partitioned tick tables
            self._logger.WARN("get_available_codes not fully implemented for partitioned tick tables")
            return []
        except Exception as e:
            self._logger.ERROR(f"Failed to get available codes: {e}")
            return []

    def check_sync_progress(self, code: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        检查指定股票和日期范围的同步进度（使用RedisService）

        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            Dict containing progress information
        """
        return self._redis_service.get_progress_summary(code, start_date, end_date, "tick")

    def clear_sync_cache(self, code: str) -> bool:
        """
        清除同步缓存（使用RedisService）

        Args:
            code: 股票代码

        Returns:
            成功返回True
        """
        return self._redis_service.clear_sync_progress(code, "tick")

    def clear_cache_for_code(self, code: str):
        """
        Clears Redis cache for a specific stock code.
        (Deprecated: Use clear_sync_cache instead)

        Args:
            code: Stock code
        """
        self._logger.WARN("clear_cache_for_code is deprecated, use clear_sync_cache instead")
        self.clear_sync_cache(code)

    @retry(max_try=3)
    def _fetch_tick_data_with_validation(self, code: str, date: datetime) -> pd.DataFrame:
        """
        Fetches tick data from source with validation and retry mechanism.

        Args:
            code: Stock code
            date: Target date

        Returns:
            DataFrame containing tick data
        """
        return self._data_source.fetch_history_transaction_detail(code, date)

    def _validate_tick_data(self, df: pd.DataFrame) -> bool:
        """
        Validates tick data for basic quality checks.

        Args:
            df: DataFrame containing tick data

        Returns:
            True if data passes basic validation, False otherwise
        """
        if df.empty:
            self._logger.ERROR("There is no dataframe.")
            return True

        try:
            # Track if we find any critical data quality issues
            has_critical_issues = False

            # Check for required columns based on TDX API format
            required_cols = ["price", "volume", "timestamp"]
            if not all(col in df.columns for col in required_cols):
                self._logger.ERROR("Missing required tick data columns")
                return False

            # Check for negative prices (critical issue)
            if "price" in df.columns:
                negative_prices = (df["price"] <= 0).sum()
                if negative_prices > 0:
                    self._logger.ERROR(f"Found {negative_prices} records with non-positive prices")
                    has_critical_issues = True

            # Check for negative volumes (critical issue)
            if "volume" in df.columns:
                negative_volumes = (df["volume"] < 0).sum()
                if negative_volumes > 0:
                    self._logger.ERROR(f"Found {negative_volumes} records with negative volumes")
                    has_critical_issues = True

            # Check for valid buy/sell direction values (critical issue)
            if "buyorsell" in df.columns:
                # Valid values: 0=CANCEL, 1=BUY, 2=SELL, 8=CALL_AUCTION (集合竞价)
                # Note: 8 is not in TICKDIRECTION_TYPES enum but is used by TDX API for call auction
                valid_directions = [0, 1, 2, 4, 5, 6, 7, 8]
                invalid_directions = df[~df["buyorsell"].isin(valid_directions)].shape[0]
                if invalid_directions > 0:
                    self._logger.ERROR(f"Found {invalid_directions} records with invalid buy/sell directions")
                    has_critical_issues = True

            # Check timestamp continuity (warning but not critical)
            if "timestamp" in df.columns:
                timestamps = pd.to_datetime(df["timestamp"])
                # Basic check: all timestamps should be on the same day
                unique_dates = timestamps.dt.date.nunique()
                if unique_dates > 1:
                    self._logger.ERROR(f"Tick data spans multiple dates: {unique_dates} unique dates")
                    # Note: Multiple dates is a warning but not critical enough to stop processing

            # Return False if critical issues found, True otherwise
            return not has_critical_issues

        except Exception as e:
            self._logger.ERROR(f"Error validating tick data: {e}")
            return False

    def _convert_ticks_individually(self, df: pd.DataFrame, code: str) -> List[Any]:
        """
        Fallback method: convert DataFrame rows individually when batch conversion fails.

        Args:
            df: DataFrame to convert
            code: Stock code

        Returns:
            List of successfully converted tick models
        """
        models = []
        for idx, row in df.iterrows():
            try:
                # Create single-row DataFrame for mapper
                single_row_df = pd.DataFrame([row])
                row_models = mappers.dataframe_to_tick_models(single_row_df, code)
                models.extend(row_models)
            except Exception as e:
                self._logger.WARN(f"Failed to convert tick row {idx} for {code}: {e}")
                continue

        return models

    def validate(
        self,
        code: str,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> ServiceResult:
        """
        Validates tick data for business rules and data quality.

        Args:
            code: Stock code
            start_date: Start date for validation range
            end_date: End date for validation range

        Returns:
            ServiceResult - 包装DataValidationResult，使用result.data获取验证结果
        """
        start_time = time.time()
        self._log_operation_start("validate", code=code, start_date=start_date, end_date=end_date)

        try:
            # Validate stock code
            if not self._stockinfo_service.exists(code):
                duration = time.time() - start_time
                self._log_operation_end("validate", False, duration)
                validation_result = DataValidationResult.create_for_entity(
                    entity_type="tick",
                    entity_identifier=code
                )
                validation_result.add_error(f"Stock code {code} not in stock list")
                return ServiceResult.failure(
                    message=f"Stock code {code} not in stock list",
                    data=validation_result
                )

            # Set default date range if not provided
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=30)  # Default to last 30 days

            # Get tick data for validation
            get_result = self.get(code=code, start_date=start_date, end_date=end_date)

            if not get_result.success:
                duration = time.time() - start_time
                self._log_operation_end("validate", False, duration)
                validation_result = DataValidationResult.create_for_entity(
                    entity_type="tick",
                    entity_identifier=code
                )
                validation_result.add_error(f"Failed to retrieve tick data: {get_result.message}")
                return ServiceResult.failure(
                    message=f"Failed to retrieve tick data: {get_result.message}",
                    data=validation_result
                )

            tick_models = get_result.data
            validation_result = DataValidationResult.create_for_entity(
                entity_type="tick",
                entity_identifier=code,
                            )

            if not tick_models or len(tick_models) == 0:
                validation_result.add_warning("No tick data found for validation")
                validation_result.records_validated = 0
                duration = time.time() - start_time
                self._log_operation_end("validate", True, duration)
                return ServiceResult.success(
                    data=validation_result,
                    message=f"No tick data found for validation for {code}"
                )

            # Convert to DataFrame for analysis
            df = tick_models.to_dataframe() if hasattr(tick_models, 'to_dataframe') else pd.DataFrame([
                {
                    'timestamp': tick.timestamp,
                    'price': float(tick.price),
                    'volume': tick.volume,
                    'direction': tick.direction,
                    'code': tick.code
                }
                for tick in tick_models
            ])

            validation_result.records_validated = len(df)

            # Business Rule 1: Price validation
            invalid_prices = (df['price'] <= 0).sum()
            if invalid_prices > 0:
                validation_result.add_business_error(
                    f"Found {invalid_prices} records with non-positive prices"
                )
                validation_result.records_failed += invalid_prices

            # Business Rule 2: Volume validation
            invalid_volumes = (df['volume'] < 0).sum()
            if invalid_volumes > 0:
                validation_result.add_business_error(
                    f"Found {invalid_volumes} records with negative volumes"
                )
                validation_result.records_failed += invalid_volumes

            # Business Rule 3: Direction validation
            valid_directions = [0, 1, 2, 4, 5, 6, 7, 8]  # Include call auction (8)
            if 'direction' in df.columns:
                invalid_directions = df[~df['direction'].isin(valid_directions)].shape[0]
                if invalid_directions > 0:
                    validation_result.add_business_error(
                        f"Found {invalid_directions} records with invalid direction values"
                    )
                    validation_result.records_failed += invalid_directions

            # Business Rule 4: Timestamp continuity and ordering
            df_sorted = df.sort_values('timestamp')
            duplicate_timestamps = df_sorted.duplicated('timestamp').sum()
            if duplicate_timestamps > 0:
                validation_result.add_warning(
                    f"Found {duplicate_timestamps} duplicate timestamps (normal for tick data)"
                )

            # Business Rule 5: Price spike detection (basic outlier detection)
            if len(df) > 1:
                price_changes = df['price'].pct_change().abs()
                extreme_spikes = (price_changes > 0.2).sum()  # >20% price change
                if extreme_spikes > 0:
                    validation_result.add_warning(
                        f"Found {extreme_spikes} extreme price spikes (>20% change)"
                    )

            # Calculate data quality score
            if validation_result.records_validated > 0:
                success_rate = (validation_result.records_validated - validation_result.records_failed) / validation_result.records_validated
                validation_result.quality_score = success_rate * 100

                # Deduct points for warnings
                warning_penalty = len(validation_result.warnings) * 2
                validation_result.quality_score = max(0, validation_result.quality_score - warning_penalty)
            else:
                validation_result.quality_score = 0

            validation_result.is_valid = validation_result.records_failed == 0
            validation_result.validation_summary = (
                f"Validated {validation_result.records_validated} tick records: "
                f"{validation_result.records_failed} failed, {len(validation_result.warnings)} warnings"
            )

            duration = time.time() - start_time
            self._log_operation_end("validate", validation_result.is_valid, duration)

            return ServiceResult.success(
                data=validation_result,
                message=f"Validation completed for {code}: {validation_result.records_validated} records"
            )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation_end("validate", False, duration)
            self._logger.ERROR(f"Error during tick data validation: {e}")
            validation_result = DataValidationResult.create_for_entity(
                entity_type="tick",
                entity_identifier=code
            )
            validation_result.add_error(f"Validation process failed: {str(e)}")
            return ServiceResult.failure(
                message=f"Validation process failed: {str(e)}",
                data=validation_result
            )

    def check_integrity(
        self,
        code: str,
        start_date: datetime,
        end_date: datetime
    ) -> ServiceResult:
        """
        Checks tick data integrity for the specified date range.

        Args:
            code: Stock code
            start_date: Start date of the range to check
            end_date: End date of the range to check

        Returns:
            ServiceResult - 包装DataIntegrityCheckResult，使用result.data获取完整性检查结果
        """
        start_time = time.time()
        self._log_operation_start("check_integrity", code=code, start_date=start_date, end_date=end_date)

        try:
            # Validate stock code
            if not self._stockinfo_service.exists(code):
                duration = time.time() - start_time
                self._log_operation_end("check_integrity", False, duration)
                integrity_result = DataIntegrityCheckResult.create_for_entity(
                    entity_type="tick",
                    entity_identifier=code,
                    check_range=(start_date, end_date)
                )
                integrity_result.add_issue("validation_error", f"Stock code {code} not in stock list")
                return ServiceResult.failure(
                    message=f"Stock code {code} not in stock list",
                    data=integrity_result
                )

            # Normalize dates
            start_date = datetime_normalize(start_date)
            end_date = datetime_normalize(end_date)

            if start_date > end_date:
                duration = time.time() - start_time
                self._log_operation_end("check_integrity", False, duration)
                integrity_result = DataIntegrityCheckResult.create_for_entity(
                    entity_type="tick",
                    entity_identifier=code,
                    check_range=(start_date, end_date)
                )
                integrity_result.add_issue("validation_error", f"Start date {start_date.date()} cannot be later than end date {end_date.date()}")
                return ServiceResult.failure(
                    message=f"Start date {start_date.date()} cannot be later than end date {end_date.date()}",
                    data=integrity_result
                )

            # Create integrity check result
            integrity_result = DataIntegrityCheckResult.create_for_entity(
                entity_type="tick",
                entity_identifier=code,
                check_range=(start_date, end_date)
            )

            # Check 1: Date coverage completeness
            total_days = (end_date - start_date).days + 1
            days_with_data = 0

            current_date = start_date
            while current_date <= end_date:
                if self.is_tick_data_available(code, current_date):
                    days_with_data += 1
                current_date += timedelta(days=1)

            coverage_rate = days_with_data / total_days if total_days > 0 else 0
            integrity_result.set_metadata("total_days", total_days)
            integrity_result.set_metadata("days_with_data", days_with_data)
            integrity_result.set_metadata("coverage_rate", coverage_rate)

            if coverage_rate < 0.5:
                integrity_result.add_issue(
                    "coverage_error",
                    f"Low data coverage: {coverage_rate:.1%} ({days_with_data}/{total_days} days)"
                )

            # Check 2: Total record count
            count_result = self.count(code=code, start_date=start_date, end_date=end_date)
            if count_result.success:
                total_records = count_result.data
                integrity_result.set_metadata("total_records", total_records)

                # Basic check: should have some records for covered days
                if days_with_data > 0 and total_records == 0:
                    integrity_result.add_issue("data_error", "Days with data but no records found")
            else:
                integrity_result.add_issue("count_error", f"Failed to count records: {count_result.message}")

            # Check 3: Recent data availability
            recent_cutoff = datetime.now() - timedelta(days=7)
            if end_date >= recent_cutoff:
                recent_days = 0
                recent_date = max(start_date, recent_cutoff)
                while recent_date <= end_date:
                    if self.is_tick_data_available(code, recent_date):
                        recent_days += 1
                    recent_date += timedelta(days=1)

                integrity_result.set_metadata("recent_days_with_data", recent_days)

                # Warning if no recent data
                if recent_days == 0:
                    integrity_result.add_warning("No recent tick data available (last 7 days)")

            # Check 4: Data consistency (sample validation)
            sample_dates = []
            if total_days >= 5:
                # Sample up to 5 dates across the range
                step = max(1, total_days // 5)
                for i in range(0, total_days, step):
                    sample_dates.append(start_date + timedelta(days=i))
            else:
                # Check all dates if less than 5
                current_date = start_date
                while current_date <= end_date:
                    sample_dates.append(current_date)
                    current_date += timedelta(days=1)

            validation_errors = 0
            for sample_date in sample_dates:
                if self.is_tick_data_available(code, sample_date):
                    validation_result = self.validate(code=code, start_date=sample_date, end_date=sample_date)
                    if not validation_result.success:
                        validation_errors += 1

            if validation_errors > 0:
                integrity_result.add_issue(
                    "validation_error",
                    f"Data quality issues found in {validation_errors} sampled dates"
                )

            # Calculate overall integrity score
            base_score = coverage_rate * 70  # Coverage worth 70 points

            # Deduct for integrity issues
            issue_penalty = len(integrity_result.integrity_issues) * 15
            final_score = max(0, base_score - issue_penalty)

            # Calculate duration first
            duration = time.time() - start_time

            # Set required fields for DataIntegrityCheckResult
            integrity_result.integrity_score = final_score
            integrity_result.total_records = integrity_result.metadata.get("total_records", 0)
            integrity_result.missing_records = 0  # Will be calculated based on coverage
            integrity_result.duplicate_records = 0  # Will be calculated based on future checks
            integrity_result.check_duration = duration

            # Set summary in metadata
            integrity_result.set_metadata("is_integrity_passed", final_score >= 70 and len(integrity_result.integrity_issues) == 0)
            integrity_result.set_metadata("coverage_rate", coverage_rate)
            integrity_result.set_metadata("check_summary",
                f"Integrity check for {code}: {coverage_rate:.1%} coverage, "
                f"{final_score:.1f} score, {len(integrity_result.integrity_issues)} issues"
            )

            passed = integrity_result.metadata.get("is_integrity_passed", False)
            self._log_operation_end("check_integrity", passed, duration)

            return ServiceResult.success(
                data=integrity_result,
                message=f"Integrity check completed for {code}: {final_score:.1f} score"
            )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation_end("check_integrity", False, duration)
            self._logger.ERROR(f"Error during integrity check: {e}")
            integrity_result = DataIntegrityCheckResult.create_for_entity(
                entity_type="tick",
                entity_identifier=code,
                check_range=(start_date, end_date)
            )
            integrity_result.add_issue("system_error", f"Integrity check failed: {str(e)}")
            integrity_result.total_records = 0
            integrity_result.missing_records = 0
            integrity_result.duplicate_records = 0
            integrity_result.integrity_score = 0.0
            integrity_result.check_duration = duration

            return ServiceResult.failure(
                message=f"Integrity check failed: {str(e)}",
                data=integrity_result
            )

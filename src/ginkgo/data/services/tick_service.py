"""
Tick Data Service (扁平化架构)

This service handles the business logic for synchronizing tick data.
It coordinates between data sources (e.g., TDX) and CRUD operations.

Enhanced with comprehensive error handling, retry mechanisms, and structured returns.
"""

import time
from datetime import datetime, timedelta
from typing import List, Union, Any, Optional, Dict
import pandas as pd

from ginkgo.libs import datetime_normalize, RichProgress, cache_with_expiration, retry, to_decimal, ensure_tick_table, time_logger, GLOG
from ginkgo.data import mappers
from ginkgo.enums import TICKDIRECTION_TYPES, ADJUSTMENT_TYPES, SOURCE_TYPES
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

    @time_logger
    @retry(max_try=3)
    def sync_date(self, code: str, date: Union[datetime, str, Any], fast_mode: bool = False) -> ServiceResult:
        """
        Sync tick data for a single trading day with incremental updates and fast mode.

        Args:
            code: Stock code
            date: Sync date, supports multiple formats
            fast_mode: Skip if data exists; force refresh when disabled

        Returns:
            ServiceResult: Sync statistics result
        """
        start_time = time.time()

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
                return ServiceResult(success=False,
                                   message=f"Stock code {code} not in stock list",
                                   data=sync_result)

            # Normalize date and create time range (accepts datetime, str, or any type)
            normalized_date = datetime_normalize(date).replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = normalized_date + timedelta(minutes=1)
            end_date = normalized_date + timedelta(days=1) - timedelta(minutes=1)

            GLOG.INFO(f"Syncing tick data for {code} on {normalized_date.date()}")

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
                        sync_result.sync_duration = duration
                        return ServiceResult(success=True,
                                           message=f"Tick data already exists for {code} on {normalized_date.date()}, skipped",
                                           data=sync_result)
                except Exception as e:
                    GLOG.WARN(f"Failed to check existing data for {code}: {e}")

            # Fetch data from source with retry mechanism
            try:
                print(f"[DEBUG] Fetching data for {code} on {normalized_date}")
                raw_data = self._fetch_data_with_validation(code, normalized_date)
                print(f"[DEBUG] Fetched data: {len(raw_data) if raw_data is not None else 0} records")
            except Exception as e:
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="tick",
                    entity_identifier=code,
                    sync_range=(normalized_date, normalized_date),
                    sync_strategy="single_date"
                )
                sync_result.records_failed = 1
                sync_result.add_error(0, f"Failed to fetch tick data: {e}")
                return ServiceResult(success=False,
                                   message=f"Failed to fetch tick data: {e}",
                                   data=sync_result)

            if raw_data is None or raw_data.empty:
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="tick",
                    entity_identifier=code,
                    sync_range=(normalized_date, normalized_date),
                    sync_strategy="single_date"
                )
                sync_result.add_warning("No tick data available from source")
                duration = time.time() - start_time
                sync_result.sync_duration = duration
                return ServiceResult(success=True,
                                   message=f"No tick data available for {code} on {normalized_date.date()}",
                                   data=sync_result)

            # Validate tick data quality
            print(f"[DEBUG] Validating data quality for {len(raw_data)} records")
            validation_result = self._validate_data_quality(raw_data)
            print(f"[DEBUG] Validation result: {validation_result}")
            if not validation_result:
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="tick",
                    entity_identifier=code,
                    sync_range=(normalized_date, normalized_date),
                    sync_strategy="single_date"
                )
                sync_result.records_failed = len(raw_data)
                sync_result.add_error(0, "Data quality validation failed")
                return ServiceResult(success=False,
                                   message="Data quality validation failed",
                                   data=sync_result)

            print(f"[DEBUG] Validation passed, proceeding to database operations")
            # Enhanced database operations with remove-and-replace strategy
            records_added = 0
            records_failed = 0
            records_removed = 0
            errors = []
            batch_size = 1000  # Smaller batches for tick data

            try:
                print(f"[DEBUG] Starting database operations try block")
                # TickCRUD will handle table creation internally
                print(f"[DEBUG] TickCRUD will handle table creation")

                # Remove existing data for the date range (non-transactional for ClickHouse)
                GLOG.INFO(f"Removing existing tick data for {code} on {normalized_date.date()}")
                removed_count = self._crud_repo.remove(
                    filters={"code": code, "timestamp__gte": start_date, "timestamp__lte": end_date}
                )
                if removed_count:
                    records_removed = removed_count
                    GLOG.INFO(f"Removed {removed_count} existing tick records for {code}")

                # Convert to raw data format for TickCRUD (dict or Tick objects)
                print(f"[DEBUG] Converting {len(raw_data)} raw records to dicts")
                tick_dicts = self._convert_to_dicts(raw_data, code)
                print(f"[DEBUG] Converted to {len(tick_dicts)} dict records")

                # Insert new data in optimized batches for large tick datasets
                total_added = 0

                # Batch processing for better performance
                for i in range(0, len(tick_dicts), batch_size):
                    batch = tick_dicts[i : i + batch_size]
                    try:
                        print(f"[DEBUG] Attempting to insert batch of {len(batch)} items for {code}")
                        print(f"[DEBUG] First item in batch: {batch[0] if batch else 'N/A'}")
                        result = self._crud_repo.add_batch(batch)
                        batch_added = len(result) if result else 0
                        total_added += batch_added
                        print(f"[DEBUG] Batch insert successful: {batch_added} items added")

                        # Progress feedback for large datasets
                        if len(tick_dicts) > 5000 and i % (batch_size * 5) == 0:
                            GLOG.DEBUG(f"Processed {i + batch_added}/{len(tick_dicts)} ticks for {code}")

                    except Exception as e:
                        records_failed += len(batch)
                        error_msg = f"Batch insert failed at index {i}: {str(e)}"
                        errors.append((i, error_msg))
                        print(f"[ERROR] {error_msg}")
                        import traceback
                        print(f"[ERROR] Traceback: {traceback.format_exc()}")
                        GLOG.ERROR(error_msg)

                records_added = total_added

            except Exception as e:
                records_failed = len(raw_data)
                errors.append((0, f"Database operation failed: {str(e)}"))

            # Create sync result with detailed statistics
            sync_result = DataSyncResult.create_for_entity(
                entity_type="tick",
                entity_identifier=code,
                sync_range=(normalized_date, normalized_date),
                sync_strategy="single_date"
            )
            sync_result.records_processed = len(raw_data)
            sync_result.records_added = records_added
            sync_result.records_updated = 0  # Using remove-and-replace strategy
            sync_result.records_failed = records_failed
            sync_result.sync_duration = time.time() - start_time
            sync_result.is_idempotent = True

            # Set additional metadata
            sync_result.set_metadata("date", normalized_date.date())
            sync_result.set_metadata("removed_count", records_removed)
            sync_result.set_metadata("data_source", type(self._data_source).__name__)
            sync_result.set_metadata("batch_size", batch_size)

            # Add warnings for removed data
            if records_removed and records_removed > 0:
                sync_result.add_warning(f"Removed {records_removed} existing records")

            for error in errors:
                sync_result.add_error(error[0], error[1])

            # Determine success
            success = records_failed == 0 and records_added > 0
            message = f"Tick data sync for {code} on {normalized_date.date()}: {records_removed} removed, {records_added} added, {records_failed} failed"

            GLOG.INFO(f"Successfully synced {records_added} ticks for {code} on {normalized_date.date()}")

            return ServiceResult(success=success, message=message, data=sync_result)

        except Exception as e:
            sync_result = DataSyncResult.create_for_entity(
                entity_type="tick",
                entity_identifier=code,
                sync_range=(date, date),
                sync_strategy="single_date"
            )
            sync_result.records_failed = 1
            sync_result.sync_duration = time.time() - start_time
            sync_result.add_error(0, f"Unexpected error: {e}")
            return ServiceResult(success=False,
                               message=f"Unexpected error during tick sync: {e}",
                               data=sync_result)

    def _convert_to_dicts(self, raw_data: pd.DataFrame, code: str) -> List[Dict]:
        """Convert raw tick data to dictionary format for TickCRUD."""
        tick_dicts = []
        for _, row in raw_data.iterrows():
            try:
                # 转换方向值
                direction_value = row.get('buyorsell', 0)
                direction_enum = None
                if direction_value is not None:
                    try:
                        # 如果是数字，使用from_int
                        direction_int = int(direction_value)
                        direction_enum = TICKDIRECTION_TYPES.from_int(direction_int)
                        if direction_enum is None:
                            direction_enum = TICKDIRECTION_TYPES.NEUTRAL
                    except (ValueError, TypeError):
                        # 如果不是数字，使用enum_convert
                        direction_enum = TICKDIRECTION_TYPES.enum_convert(str(direction_value))
                        if direction_enum is None:
                            direction_enum = TICKDIRECTION_TYPES.NEUTRAL

                # 创建字典格式数据，TickCRUD内部会进行模型转换
                tick_dict = {
                    'code': code,
                    'timestamp': datetime_normalize(row['timestamp']),
                    'price': float(row['price']),
                    'volume': int(row.get('volume', 0)),
                    'direction': direction_enum,  # 传递枚举对象，可读性更强
                    'source': SOURCE_TYPES.TDX  # 传递枚举对象
                }
                tick_dicts.append(tick_dict)
            except Exception as e:
                GLOG.WARN(f"Failed to convert tick row to dict: {e}, row data: {dict(row)}")
                continue

        return tick_dicts

    @retry(max_try=3)
    def _fetch_data_with_validation(self, code: str, date: datetime) -> pd.DataFrame:
        """
        Fetches tick data from source with validation and retry mechanism.

        Args:
            code: Stock code
            date: Target date

        Returns:
            DataFrame containing tick data
        """
        return self._data_source.fetch_history_transaction_detail(code, date)

    def _validate_data_quality(self, df: pd.DataFrame) -> bool:
        """
        Validates tick data for basic quality checks.

        Args:
            df: DataFrame containing tick data

        Returns:
            True if data passes basic validation, False otherwise
        """
        if df.empty:
            GLOG.ERROR("There is no dataframe.")
            return True

        try:
            # Track if we find any critical data quality issues
            has_critical_issues = False

            # Check for required columns based on TDX API format
            required_cols = ["price", "volume", "timestamp"]
            if not all(col in df.columns for col in required_cols):
                GLOG.ERROR("Missing required tick data columns")
                return False

            # Check for negative prices (critical issue)
            if "price" in df.columns:
                negative_prices = (df["price"] <= 0).sum()
                if negative_prices > 0:
                    GLOG.ERROR(f"Found {negative_prices} records with non-positive prices")
                    has_critical_issues = True

            # Check for negative volumes (critical issue)
            if "volume" in df.columns:
                negative_volumes = (df["volume"] < 0).sum()
                if negative_volumes > 0:
                    GLOG.ERROR(f"Found {negative_volumes} records with negative volumes")
                    has_critical_issues = True

            # Check for valid buy/sell direction values (critical issue)
            if "buyorsell" in df.columns:
                # Valid values: 0=CANCEL, 1=BUY, 2=SELL, 8=CALL_AUCTION (集合竞价)
                # Note: 8 is not in TICKDIRECTION_TYPES enum but is used by TDX API for call auction
                valid_directions = [0, 1, 2, 4, 5, 6, 7, 8]
                invalid_directions = df[~df["buyorsell"].isin(valid_directions)].shape[0]
                if invalid_directions > 0:
                    GLOG.ERROR(f"Found {invalid_directions} records with invalid buy/sell directions")
                    has_critical_issues = True

            # Check timestamp continuity (warning but not critical)
            if "timestamp" in df.columns:
                timestamps = pd.to_datetime(df["timestamp"])
                # Basic check: all timestamps should be on the same day
                unique_dates = timestamps.dt.date.nunique()
                if unique_dates > 1:
                    GLOG.ERROR(f"Tick data spans multiple dates: {unique_dates} unique dates")
                    # Note: Multiple dates is a warning but not critical enough to stop processing

            # Return False if critical issues found, True otherwise
            return not has_critical_issues

        except Exception as e:
            GLOG.ERROR(f"Error validating tick data: {e}")
            return False

    def get(self, code: str = None, start_date: Union[datetime, str, Any] = None, end_date: Union[datetime, str, Any] = None,
            adjustment_type: ADJUSTMENT_TYPES = ADJUSTMENT_TYPES.FORE) -> ServiceResult:
        """
        Query tick data with multiple filter conditions and price adjustment support.

        Args:
            code: Stock code, empty for all stocks
            start_date: Start time, supports multiple date formats
            end_date: End time, supports multiple date formats
            adjustment_type: Price adjustment type (NONE/FORE/BACK)

        Returns:
            ServiceResult: Query result with data and statistics
        """
        start_time = time.time()
        self._log_operation_start("get", code=code, start_date=start_date, end_date=end_date, adjustment_type=adjustment_type.value)

        try:
            # Validate required parameter
            if not code:
                return ServiceResult.failure(
                    message="Code parameter is required for tick data operations",
                    data=None
                )

            # 构建filters字典
            filters = {}

            # 具体参数优先级高于filters中的对应字段
            if code:
                filters["code"] = code
            if start_date:
                filters["timestamp__gte"] = datetime_normalize(start_date)
            if end_date:
                filters["timestamp__lte"] = datetime_normalize(end_date)

            # Get original tick data using TickCRUD
            if not self._crud_repo:
                return ServiceResult.error("CRUD repository not available")

            model_list = self._crud_repo.find(filters=filters)

            # Return original data if no adjustment needed
            if adjustment_type == ADJUSTMENT_TYPES.NONE:
                duration = time.time() - start_time
                self._log_operation_end("get", True, duration)
                return ServiceResult.success(
                    data=model_list,
                    message=f"Retrieved {len(model_list) if model_list else 0} tick records"
                )

            # Apply price adjustment if needed
            # TODO: 实现复权调整逻辑，目前返回原始数据
            duration = time.time() - start_time
            self._log_operation_end("get", True, duration)

            return ServiceResult.success(
                data=model_list,
                message=f"Retrieved {len(model_list) if model_list else 0} tick records (adjustment not yet implemented)"
            )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation_end("get", False, duration)
            GLOG.ERROR(f"Failed to get tick data: {e}")
            return ServiceResult.error(
                error=f"Database query failed: {str(e)}"
            )

    def count(self, code: str = None, date: datetime = None) -> ServiceResult:
        """
        Count tick records with filter conditions.

        Args:
            code: Stock code, empty for all stocks
            date: Specific date filter (will be converted to date range)

        Returns:
            ServiceResult: Count result with matching records
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

            # 构建filters字典
            filters = {}

            # 具体参数优先级高于filters中的对应字段
            if code:
                filters["code"] = code
            if date:
                date = datetime_normalize(date).replace(hour=0, minute=0, second=0, microsecond=0)
                filters["timestamp__gte"] = date
                filters["timestamp__lt"] = date + timedelta(days=1)

            # Get count using CRUD
            if not self._crud_repo:
                return ServiceResult.error("CRUD repository not available")

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
            GLOG.ERROR(f"Failed to count tick records: {e}")
            return ServiceResult.error(
                error=f"Database query failed: {str(e)}"
            )

    def validate(self, tick_data: Union[List[Any], pd.DataFrame, ModelList]) -> ServiceResult:
        """
        Validate tick data integrity and quality.

        Args:
            tick_data: Tick data to validate, supports model lists, DataFrames, etc.

        Returns:
            ServiceResult: Validation result with data quality score and detailed report
        """
        try:
            validation_result = DataValidationResult(
                is_valid=True,
                error_count=0,
                warning_count=0,
                data_quality_score=100.0,  # 默认满分，后续会根据实际情况调整
                validation_timestamp=datetime.now(),
                validation_type="tick_data",
                entity_type="tick",
                entity_identifier="batch"
            )

            # Convert to DataFrame if needed
            if isinstance(tick_data, list):
                df = pd.DataFrame([{
                    'code': t.code,
                    'timestamp': t.timestamp,
                    'price': float(t.price),
                    'volume': t.volume,
                    'direction': t.direction
                } for t in tick_data])
            elif hasattr(tick_data, 'to_dataframe'):
                df = tick_data.to_dataframe()
            else:
                df = tick_data

            # Basic validations
            if df.empty:
                validation_result.is_valid = False
                validation_result.add_error("No tick data provided")
                validation_result.error_count = 1
                return ServiceResult(success=False, data=validation_result)

            # Check required fields
            required_fields = ['code', 'timestamp', 'price', 'volume']
            missing_fields = [field for field in required_fields if field not in df.columns]
            if missing_fields:
                validation_result.is_valid = False
                validation_result.add_error(f"Missing required fields: {missing_fields}")
                validation_result.error_count += 1

            # Check data quality
            invalid_prices = df[df['price'] <= 0]
            if not invalid_prices.empty:
                validation_result.add_warning(f"Found {len(invalid_prices)} records with non-positive prices")
                validation_result.warning_count += len(invalid_prices)

            invalid_volumes = df[df['volume'] < 0]
            if not invalid_volumes.empty:
                validation_result.add_warning(f"Found {len(invalid_volumes)} records with negative volumes")
                validation_result.warning_count += len(invalid_volumes)

            validation_result.data_quality_score = 100.0 - (validation_result.warning_count * 5.0)

            return ServiceResult(success=True, data=validation_result)

        except Exception as e:
            return ServiceResult(success=False,
                               message=f"Failed to validate tick data: {e}",
                               data=None)

    def check_integrity(self, code: str, start_date: datetime, end_date: datetime) -> ServiceResult:
        """
        Check tick data integrity for a stock within specified time range.

        Args:
            code: Stock code, format like '000001.SZ'
            start_date: Check start time
            end_date: Check end time

        Returns:
            ServiceResult: Integrity check result with integrity score and issue report
        """
        try:
            # Get tick data for the range
            result = self.get(code=code, start_date=start_date, end_date=end_date)

            if not result.success:
                return ServiceResult(success=False,
                                   message=f"Failed to retrieve data for integrity check: {result.error}",
                                   data=None)

            tick_data = result.data

            # Calculate expected trading hours
            trading_days = self._calculate_trading_days(start_date, end_date)
            expected_hours = len(trading_days) * 4  # Assuming 4 hours per trading day

            integrity_result = DataIntegrityCheckResult(
                entity_type="tick",
                entity_identifier=code,
                check_range=(start_date, end_date),
                total_records=len(tick_data),
                missing_records=0,
                duplicate_records=0,
                integrity_score=100.0,
                check_duration=0.0
            )

            # Check for data gaps
            if len(tick_data) == 0:
                integrity_result.integrity_score = 0.0
                integrity_result.add_issue("no_data", "No tick data found in the specified range")
                integrity_result.missing_records = expected_hours * 60  # Rough estimate

            # Check for duplicates based on timestamp
            if hasattr(tick_data, '__len__') and len(tick_data) > 0:
                timestamps = [t.timestamp for t in tick_data if hasattr(t, 'timestamp')]
                unique_timestamps = len(set(timestamps))
                if unique_timestamps < len(timestamps):
                    duplicate_count = len(timestamps) - unique_timestamps
                    integrity_result.duplicate_records = duplicate_count
                    integrity_result.integrity_score -= duplicate_count * 10
                    integrity_result.add_issue("duplicate_timestamps", f"Found {duplicate_count} duplicate timestamps")

            return ServiceResult(success=True, data=integrity_result)

        except Exception as e:
            return ServiceResult(success=False,
                               message=f"Failed to check tick data integrity: {e}",
                               data=None)

    @time_logger
    @retry(max_try=3)
    def sync_range(self, code: str, start_date: datetime, end_date: datetime, **kwargs) -> ServiceResult:
        """
        Batch sync tick data for date range with automatic trading day detection.

        Args:
            code: Stock code
            start_date: Sync start time
            end_date: Sync end time
            **kwargs: Configuration parameters, includes fast_mode option

        Returns:
            ServiceResult: Range sync statistics result
        """
        fast_mode = kwargs.get('fast_mode', True)
        start_time = time.time()

        try:
            # Validate inputs
            if not code:
                return ServiceResult(success=False, message="Stock code cannot be empty")

            if not start_date or not end_date:
                return ServiceResult(success=False, message="Start date and end date are required")

            if start_date >= end_date:
                return ServiceResult(success=False, message="Start date must be before end date")

            # Validate stock code
            if not self._stockinfo_service.exists(code):
                return ServiceResult(success=False, message=f"Stock code {code} not found")

            # Normalize dates
            start_date = datetime_normalize(start_date)
            end_date = datetime_normalize(end_date)

            GLOG.INFO(f"Syncing tick data for {code} from {start_date.date()} to {end_date.date()}")

            # Calculate trading days in range
            trading_days = self._calculate_trading_days(start_date, end_date)
            if not trading_days:
                return ServiceResult(success=True, message="No trading days in the specified range", data={})

            # Check existing data if fast_mode
            if fast_mode:
                try:
                    existing_result = self.get(code=code, start_date=start_date, end_date=end_date)
                    if existing_result.success and existing_result.data and len(existing_result.data) > 0:
                        sync_result = DataSyncResult.create_for_entity(
                            entity_type="tick",
                            entity_identifier=code,
                            sync_range=(start_date, end_date),
                            sync_strategy="range"
                        )
                        sync_result.records_skipped = len(existing_result.data)
                        sync_result.is_idempotent = True
                        sync_result.add_warning(f"Data already exists: {len(existing_result.data)} records skipped")
                        duration = time.time() - start_time
                        sync_result.sync_duration = duration
                        return ServiceResult(success=True, message="Tick data already exists, skipped", data=sync_result)
                except Exception as e:
                    GLOG.WARN(f"Failed to check existing data: {e}")

            # Sync each trading day
            total_records_processed = 0
            total_records_added = 0
            total_records_failed = 0
            all_errors = []

            for trading_day in trading_days:
                try:
                    # Use sync_date for each day
                    day_result = self.sync_date(code=code, date=trading_day, fast_mode=False)

                    if day_result.success and day_result.data:
                        sync_data = day_result.data
                        total_records_processed += sync_data.records_processed
                        total_records_added += sync_data.records_added
                        total_records_failed += sync_data.records_failed

                        if sync_data.errors:
                            all_errors.extend(sync_data.errors)
                    else:
                        total_records_failed += 1
                        all_errors.append((str(trading_day.date()), day_result.message or "Unknown error"))

                except Exception as e:
                    total_records_failed += 1
                    all_errors.append((str(trading_day.date()), str(e)))
                    GLOG.ERROR(f"Failed to sync tick data for {code} on {trading_day.date()}: {e}")

            # Create final result
            sync_result = DataSyncResult.create_for_entity(
                entity_type="tick",
                entity_identifier=code,
                sync_range=(start_date, end_date),
                sync_strategy="range"
            )
            sync_result.records_processed = total_records_processed
            sync_result.records_added = total_records_added
            sync_result.records_failed = total_records_failed
            sync_result.sync_duration = time.time() - start_time
            sync_result.is_idempotent = True
            sync_result.set_metadata("trading_days_count", len(trading_days))
            sync_result.set_metadata("fast_mode", fast_mode)

            for error in all_errors:
                sync_result.add_error(error[0], error[1])

            success = total_records_failed == 0 and total_records_added > 0
            message = f"Tick data range sync for {code}: {len(trading_days)} days, {total_records_added} added, {total_records_failed} failed"

            return ServiceResult(success=success, message=message, data=sync_result)

        except Exception as e:
            sync_result = DataSyncResult.create_for_entity(
                entity_type="tick",
                entity_identifier=code,
                sync_range=(start_date, end_date),
                sync_strategy="range"
            )
            sync_result.records_failed = 1
            sync_result.sync_duration = time.time() - start_time
            sync_result.add_error(0, f"Unexpected error: {e}")
            return ServiceResult(success=False, message=f"Unexpected error during tick range sync: {e}", data=sync_result)

    @time_logger
    @retry(max_try=3)
    def sync_smart(self, code: str, max_backtrack_days: int = 7, **kwargs) -> ServiceResult:
        """
        Smart sync tick data - automatically detect and sync missing data.

        Args:
            code: Stock code, format like '000001.SZ'
            max_backtrack_days: Maximum backtrack days, default 7 days
            **kwargs: Additional configuration parameters, includes fast_mode option

        Returns:
            ServiceResult: Smart sync result with sync statistics and metadata
        """
        fast_mode = kwargs.get('fast_mode', True)
        start_time = time.time()

        try:
            # Validate inputs
            if not code:
                return ServiceResult(success=False, message="Stock code cannot be empty")

            # Validate stock code
            if not self._stockinfo_service.exists(code):
                return ServiceResult(success=False, message=f"Stock code {code} not found")

            GLOG.INFO(f"Smart sync tick data for {code}, max_backtrack_days: {max_backtrack_days}")

            # Find latest existing data
            latest_date = None
            if fast_mode and self._crud_repo:
                try:
                    latest_records = self._crud_repo.find(
                        filters={"code": code},
                        order_by='timestamp',
                        desc_order=True
                    )
                    if latest_records:
                        latest_date = latest_records[0].timestamp
                except Exception as e:
                    GLOG.WARN(f"Failed to find latest data: {e}")

            # Calculate sync range
            if latest_date:
                # Start from the day after latest data
                start_date = latest_date + timedelta(days=1)
            else:
                # No existing data, look back max_backtrack_days
                end_date = datetime.now()
                start_date = end_date - timedelta(days=max_backtrack_days)
                latest_date = None

            end_date = datetime.now()

            # If we're already up to date
            if latest_date and start_date >= end_date:
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="tick",
                    entity_identifier=code,
                    sync_range=(start_date, end_date),
                    sync_strategy="smart"
                )
                sync_result.records_skipped = 0
                sync_result.is_idempotent = True
                sync_result.add_warning("Tick data is already up to date")
                sync_result.sync_duration = time.time() - start_time
                return ServiceResult(success=True, message="Tick data is already up to date", data=sync_result)

            # Use sync_range to sync the determined range
            return self.sync_range(code=code, start_date=start_date, end_date=end_date, fast_mode=fast_mode)

        except Exception as e:
            sync_result = DataSyncResult.create_for_entity(
                entity_type="tick",
                entity_identifier=code,
                sync_range=(None, None),
                sync_strategy="smart"
            )
            sync_result.records_failed = 1
            sync_result.sync_duration = time.time() - start_time
            sync_result.add_error(0, f"Smart sync error: {e}")
            return ServiceResult(success=False, message=f"Unexpected error during smart tick sync: {e}", data=sync_result)

    def _calculate_trading_days(self, start_date: datetime, end_date: datetime) -> List[datetime]:
        """Calculate trading days in the date range (excluding weekends)."""
        trading_days = []
        current_date = start_date.date()
        end_date_only = end_date.date()

        while current_date <= end_date_only:
            # Exclude weekends (Saturday=5, Sunday=6)
            if current_date.weekday() < 5:
                trading_days.append(datetime.combine(current_date, datetime.min.time()))
            current_date += timedelta(days=1)

        return trading_days

    @time_logger
    def sync_batch(self, codes: List[str], start_date: Union[datetime, str], end_date: Union[datetime, str], **kwargs) -> ServiceResult:
        """
        批量同步多个股票的tick数据

        Args:
            codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            **kwargs: 其他参数

        Returns:
            ServiceResult: 批量同步结果
        """
        if not codes:
            return ServiceResult.error("股票代码列表不能为空")

        batch_results = []
        total_success = 0
        total_failed = 0
        errors = []

        for code in codes:
            try:
                result = self.sync_range(code=code, start_date=start_date, end_date=end_date, **kwargs)
                batch_results.append({
                    'code': code,
                    'success': result.is_success(),
                    'message': result.message,
                    'data': result.data
                })

                if result.is_success():
                    total_success += 1
                else:
                    total_failed += 1
                    errors.append(f"{code}: {result.message}")

            except Exception as e:
                batch_results.append({
                    'code': code,
                    'success': False,
                    'message': str(e),
                    'data': None
                })
                total_failed += 1
                errors.append(f"{code}: {str(e)}")

        success_rate = total_success / len(codes) if codes else 0

        return ServiceResult.success(
            data={
                'batch_results': batch_results,
                'total_codes': len(codes),
                'total_success': total_success,
                'total_failed': total_failed,
                'success_rate': success_rate,
                'errors': errors
            },
            message=f"批量同步完成: {total_success}/{len(codes)} 成功，成功率 {success_rate:.1%}"
        )
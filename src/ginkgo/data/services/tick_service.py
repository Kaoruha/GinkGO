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

from ...libs import datetime_normalize, RichProgress, cache_with_expiration, retry, to_decimal, ensure_tick_table
from .. import mappers
from ...enums import TICKDIRECTION_TYPES, ADJUSTMENT_TYPES
from .base_service import DataService


class TickService(DataService):
    def __init__(self, data_source, stockinfo_service, crud_repo=None, redis_service=None, adjustfactor_service=None):
        """Initializes the service with its dependencies."""
        # TickService handles CRUD creation dynamically, so crud_repo is optional
        super().__init__(crud_repo=crud_repo, data_source=data_source, stockinfo_service=stockinfo_service)

        # 集成RedisService
        if redis_service is None:
            from .redis_service import RedisService

            redis_service = RedisService()
        self.redis_service = redis_service

        # Initialize AdjustfactorService for price adjustment support
        if adjustfactor_service is None:
            from .adjustfactor_service import AdjustfactorService
            from ..crud.adjustfactor_crud import AdjustfactorCRUD

            adjustfactor_service = AdjustfactorService(
                crud_repo=AdjustfactorCRUD(), data_source=data_source, stockinfo_service=stockinfo_service
            )
        self.adjustfactor_service = adjustfactor_service

    def get_crud(self, code: str):
        """
        Get TickCRUD instance for a specific stock code.
        TickCRUD requires a code parameter, so we create instances dynamically.

        Args:
            code: Stock code (e.g., '000001.SZ')

        Returns:
            TickCRUD: CRUD instance for the specified stock code
        """
        from ..crud.tick_crud import TickCRUD

        return TickCRUD(code)

    @retry(max_try=3)
    def sync_for_code_on_date(self, code: str, date: datetime, fast_mode: bool = False) -> Dict[str, Any]:
        """
        Synchronizes tick data for a single stock code on a specific date with enhanced error handling.

        Args:
            code: Stock code (e.g., '000001.SZ')
            date: Target date
            fast_mode: If True, skip if data already exists

        Returns:
            Dict containing sync results with success status, statistics, and error info
        """
        result = {
            "code": code,
            "date": date.date() if isinstance(date, datetime) else date,
            "success": False,
            "records_processed": 0,
            "records_added": 0,
            "error": None,
            "warnings": [],
            "skipped": False,
        }
        # Validate stock code
        if not self.stockinfo_service.is_code_in_stocklist(code):
            result["error"] = f"Stock code {code} not in stock list"
            self._logger.DEBUG(f"Exit fetch and update tick {code} on {date}.")
            return result

        # Normalize date and create time range
        date = datetime_normalize(date).replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = date + timedelta(minutes=1)
        end_date = date + timedelta(days=1) - timedelta(minutes=1)

        # Check if data exists and fast_mode is enabled
        if fast_mode:
            try:
                existing_data = self.get_ticks(code=code, start_date=start_date, end_date=end_date, as_dataframe=True)
                if not existing_data.empty:
                    result["success"] = True
                    result["skipped"] = True
                    result["warnings"].append(f"Data already exists in DB ({len(existing_data)} records), skipped")
                    self._logger.DEBUG(f"{code} on {date.date()} has {len(existing_data)} ticks in db, skip.")
                    return result
            except Exception as e:
                result["warnings"].append(f"Failed to check existing data: {str(e)}")

        # Fetch data from source with retry mechanism
        try:
            raw_data = self._fetch_tick_data_with_validation(code, date)
            if raw_data is None or raw_data.empty:
                result["success"] = True  # No data is not an error
                result["skipped"] = True  # 标记为跳过
                result["warnings"].append("No data available from source")
                self._logger.DEBUG(f"No tick data available for {code} on {date.date()}")
                return result
        except Exception as e:
            result["error"] = f"Failed to fetch data from source: {str(e)}"
            self._logger.ERROR(f"Failed to fetch tick data for {code} on {date.date()}: {e}")
            return result

        result["records_processed"] = len(raw_data)

        # Validate tick data quality
        if not self._validate_tick_data(raw_data):
            result["error"] = "Data quality validation failed"
            self._logger.ERROR(f"Data quality validation failed for {code} on {date.date()}")
            self._logger.ERROR(raw_data)
            return result

        # Convert to tick models with error handling
        try:
            tick_models = mappers.dataframe_to_tick_models(raw_data, code)
            if not tick_models:
                result["success"] = True
                result["warnings"].append("No valid models generated from data")
                return result
        except Exception as e:
            # Fallback: try row-by-row conversion
            self._logger.WARN(f"Batch conversion failed for {code} on {date.date()}, attempting row-by-row: {e}")
            tick_models = self._convert_ticks_individually(raw_data, code)
            if not tick_models:
                result["error"] = f"Data mapping failed: {str(e)}"
                return result
            result["warnings"].append("Used row-by-row conversion due to batch failure")

        # Enhanced database operations with error handling
        try:
            # Use dynamic CRUD repo based on stock code
            from ..crud.tick_crud import TickCRUD

            tick_crud = TickCRUD(code)

            # Remove existing data for the date range (non-transactional for ClickHouse)
            removed_count = tick_crud.remove(
                filters={"code": code, "timestamp__gte": start_date, "timestamp__lte": end_date}
            )

            if removed_count is not None and removed_count > 0:
                result["warnings"].append(f"Removed {removed_count} existing records")

            # Insert new data in optimized batches for large tick datasets
            batch_size = 1000  # Smaller batches for tick data
            total_added = 0

            for i in range(0, len(tick_models), batch_size):
                batch = tick_models[i : i + batch_size]
                tick_crud.add_batch(batch)
                total_added += len(batch)

                # Progress feedback for large datasets
                if len(tick_models) > 5000 and i % (batch_size * 5) == 0:
                    self._logger.DEBUG(f"Processed {i + len(batch)}/{len(tick_models)} ticks for {code}")

            result["records_added"] = total_added
            result["success"] = True
            self._logger.INFO(f"Successfully synced {total_added} ticks for {code} on {date.date()}")

        except Exception as e:
            result["error"] = f"Database operation failed: {str(e)}"
            self._logger.ERROR(f"Transaction for {code} ticks on {date.date()} failed: {e}")
            return result

        return result

    def sync_for_code(self, code: str, fast_mode: bool = False, max_backtrack_days: int = 0) -> Dict[str, Any]:
        """
        Synchronizes tick data for a stock code across multiple dates with comprehensive tracking.

        Args:
            code: Stock code
            fast_mode: If True, skip dates that already have data
            max_backtrack_days: Maximum number of days to go back (0 = unlimited)

        Returns:
            Dict containing comprehensive sync results and statistics
        """
        batch_result = {
            "code": code,
            "total_dates_processed": 0,
            "successful_dates": 0,
            "failed_dates": 0,
            "skipped_dates": 0,
            "total_records_processed": 0,
            "total_records_added": 0,
            "results": [],
            "failures": [],
        }
        # Validate stock code
        if not self.stockinfo_service.is_code_in_stocklist(code):
            batch_result["failures"].append({"error": f"Stock code {code} not in stock list"})
            self._logger.DEBUG(f"Exit fetch and update tick {code} - not in stock list.")
            return batch_result

        # Get stock info to determine valid date range
        try:
            stock_info = self.stockinfo_service.get_stockinfos(filters={"code": code}, as_dataframe=True)
            if stock_info.empty:
                batch_result["failures"].append({"error": f"No stock info found for {code}"})
                self._logger.ERROR(f"No stock info found for {code}")
                return batch_result
        except Exception as e:
            batch_result["failures"].append({"error": f"Failed to get stock info: {str(e)}"})
            self._logger.ERROR(f"Failed to get stock info for {code}: {e}")
            return batch_result

        list_date = datetime_normalize(stock_info.iloc[0]["list_date"])
        current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Initialize Redis cache for tracking processed dates using RedisService
        cache_key = f"tick_update_{code}"
        processed_dates = set()

        try:
            # 使用RedisService获取已处理的日期
            cached_progress = self.redis_service.get_sync_progress(code, "tick")
            processed_dates = cached_progress
        except Exception as e:
            self._logger.WARN(f"Redis connection failed, proceeding without cache: {e}")

        update_count = 0

        with RichProgress() as progress:
            # Calculate actual total dates to process
            actual_days = (current_date - list_date).days + 1

            total_days = actual_days
            # Determine total days based on max_backtrack_days setting
            if max_backtrack_days > 0:
                total_days = min(actual_days, max_backtrack_days)

            task = progress.add_task(f"[cyan]Syncing Tick Data for {code}", total=total_days)

            while current_date >= list_date and update_count < total_days:
                update_count += 1
                batch_result["total_dates_processed"] += 1
                date_str = current_date.strftime("%Y-%m-%d")

                progress.update(task, description=f"Processing {code} on {date_str}")

                # Check cache
                if date_str in processed_dates:
                    self._logger.DEBUG(f"Skipping {code} on {date_str} - already processed (cached)")
                    batch_result["skipped_dates"] += 1
                    current_date -= timedelta(days=1)
                    progress.update(task, advance=1)
                    continue

                # Process the date
                try:
                    result = self.sync_for_code_on_date(code, current_date, fast_mode)

                    batch_result["results"].append(result)
                    batch_result["total_records_processed"] += result["records_processed"]
                    batch_result["total_records_added"] += result["records_added"]

                    if result["success"]:
                        if result["skipped"]:
                            batch_result["skipped_dates"] += 1
                        else:
                            batch_result["successful_dates"] += 1
                            self._logger.INFO(
                                f"Updated tick data for {code} on {date_str}: {result['records_added']} records"
                            )
                        should_cache = True
                    else:
                        batch_result["failed_dates"] += 1
                        batch_result["failures"].append({"date": date_str, "error": result["error"]})
                        # Cache if it's more than 2 days old (likely no data available)
                        should_cache = (datetime.now() - current_date).days > 2

                    # Update Redis cache using RedisService
                    if should_cache:
                        try:
                            self.redis_service.save_sync_progress(code, current_date, "tick")
                            processed_dates.add(date_str)
                        except Exception as e:
                            self._logger.WARN(f"Failed to update Redis cache: {e}")

                except Exception as e:
                    batch_result["failed_dates"] += 1
                    batch_result["failures"].append({"date": date_str, "error": f"Unexpected error: {str(e)}"})
                    self._logger.ERROR(f"Unexpected error processing {code} on {date_str}: {e}")

                current_date -= timedelta(days=1)
                progress.update(task, advance=1)

        self._logger.INFO(
            f"Completed tick sync for {code}: {batch_result['successful_dates']} successful, {batch_result['failed_dates']} failed, {batch_result['skipped_dates']} skipped"
        )
        return batch_result

    def sync_for_code_with_date_range(
        self, code: str, start_date: datetime, end_date: datetime, fast_mode: bool = True, use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        为指定股票代码同步指定日期范围的tick数据（支持中断恢复）

        Args:
            code: 股票代码 (e.g., '000001.SZ')
            start_date: 开始日期
            end_date: 结束日期
            fast_mode: 快速模式，跳过已存在的数据
            use_cache: 是否使用Redis缓存记录进度（支持中断恢复）

        Returns:
            Dict containing sync results with statistics
        """
        result = {
            "code": code,
            "start_date": start_date.date(),
            "end_date": end_date.date(),
            "total_dates": 0,
            "successful_dates": 0,
            "failed_dates": 0,
            "skipped_dates": 0,
            "resumed_from_cache": 0,  # 从缓存恢复跳过的日期数
            "total_records_added": 0,
            "results": [],
            "failures": [],
        }

        # 验证股票代码
        if not self.stockinfo_service.is_code_in_stocklist(code):
            result["failures"].append({"error": f"Stock code {code} not in stock list"})
            return result

        # 获取缓存进度摘要
        if use_cache:
            progress = self.redis_service.get_progress_summary(code, start_date, end_date, "tick")
            result["cache_info"] = {
                "completion_rate": progress["completion_rate"],
                "missing_count": progress["missing_count"],
            }
            self._logger.INFO(
                f"Cache info for {code}: {progress['completion_rate']:.2%} complete, {progress['missing_count']} dates missing"
            )

        # 按日期范围逐日处理
        current_date = start_date
        while current_date <= end_date:
            result["total_dates"] += 1

            # 检查是否已在缓存中（中断恢复点检测）
            if use_cache and self.redis_service.check_date_synced(code, current_date, "tick"):
                result["resumed_from_cache"] += 1
                self._logger.DEBUG(f"Skipping {code} on {current_date.date()} - found in cache (resuming)")
                current_date += timedelta(days=1)
                continue

            # 调用现有的单日同步方法
            day_result = self.sync_for_code_on_date(code, current_date, fast_mode)
            result["results"].append(day_result)

            if day_result["success"]:
                if day_result.get("skipped", False):
                    result["skipped_dates"] += 1
                else:
                    result["successful_dates"] += 1
                result["total_records_added"] += day_result["records_added"]

                # 更新Redis缓存（记录成功处理的日期）
                if use_cache:
                    self.redis_service.save_sync_progress(code, current_date, "tick")
            else:
                result["failed_dates"] += 1
                result["failures"].append({"date": current_date.date(), "error": day_result["error"]})

            current_date += timedelta(days=1)

        self._logger.INFO(
            f"Completed date range sync for {code}: {result['successful_dates']} successful, {result['failed_dates']} failed, {result['skipped_dates']} skipped, {result['resumed_from_cache']} resumed from cache"
        )
        return result

    def sync_batch_codes_with_date_range(
        self, codes: List[str], start_date: datetime, end_date: datetime, fast_mode: bool = True, use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        批量同步多个股票代码的指定日期范围数据

        Args:
            codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            fast_mode: 快速模式
            use_cache: 是否使用缓存

        Returns:
            Dict containing batch sync results
        """
        batch_result = {
            "total_codes": len(codes),
            "successful_codes": 0,
            "failed_codes": 0,
            "total_records_added": 0,
            "total_resumed_from_cache": 0,
            "results": [],
            "failures": [],
        }

        for code in codes:
            code_result = self.sync_for_code_with_date_range(code, start_date, end_date, fast_mode, use_cache)
            batch_result["results"].append(code_result)

            if code_result["successful_dates"] > 0 or code_result["skipped_dates"] > 0:
                batch_result["successful_codes"] += 1
            else:
                batch_result["failed_codes"] += 1
                batch_result["failures"].extend(code_result["failures"])

            batch_result["total_records_added"] += code_result["total_records_added"]
            batch_result["total_resumed_from_cache"] += code_result["resumed_from_cache"]

        self._logger.INFO(
            f"Completed batch sync: {batch_result['successful_codes']}/{batch_result['total_codes']} codes successful"
        )
        return batch_result

    @ensure_tick_table
    def get_ticks(
        self,
        code: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        as_dataframe: bool = True,
        adjustment_type: ADJUSTMENT_TYPES = ADJUSTMENT_TYPES.NONE,
        **kwargs,
    ) -> Union[pd.DataFrame, List[Any]]:
        """
        Retrieves tick data from the database with optional price adjustment.

        Args:
            code: Stock code filter
            start_date: Start datetime filter
            end_date: End datetime filter
            as_dataframe: Return format
            adjustment_type: Price adjustment type (NONE/FORE/BACK)
            **kwargs: Additional filters

        Returns:
            Tick data as DataFrame or list of models, optionally price-adjusted
        """
        # 提取filters参数并从kwargs中移除，避免重复传递
        filters = kwargs.pop("filters", {})

        # 具体参数优先级高于filters中的对应字段
        if code:
            filters["code"] = code
        if start_date:
            filters["timestamp__gte"] = start_date
        if end_date:
            filters["timestamp__lte"] = end_date

        # Get original tick data using dynamic CRUD based on code
        if not code:
            raise ValueError("Code parameter is required for tick data operations")
        tick_crud = self.get_crud(code)
        original_data = tick_crud.find(filters=filters, as_dataframe=as_dataframe, **kwargs)

        # Return original data if no adjustment needed
        if adjustment_type == ADJUSTMENT_TYPES.NONE:
            return original_data

        # Apply price adjustment if requested
        return self._apply_price_adjustment(original_data, code, adjustment_type, as_dataframe)

    def get_ticks_adjusted(
        self,
        code: str,
        adjustment_type: ADJUSTMENT_TYPES = ADJUSTMENT_TYPES.FORE,
        start_date: datetime = None,
        end_date: datetime = None,
        as_dataframe: bool = True,
        **kwargs,
    ) -> Union[pd.DataFrame, List[Any]]:
        """
        Convenience method to get price-adjusted tick data.

        Args:
            code: Stock code (required for adjustment)
            adjustment_type: Price adjustment type (FORE/BACK)
            start_date: Start datetime filter
            end_date: End datetime filter
            as_dataframe: Return format
            **kwargs: Additional filters

        Returns:
            Price-adjusted tick data as DataFrame or list of models
        """
        if adjustment_type == ADJUSTMENT_TYPES.NONE:
            self._logger.WARN("Use get_ticks() for unadjusted data")

        return self.get_ticks(
            code=code,
            start_date=start_date,
            end_date=end_date,
            as_dataframe=as_dataframe,
            adjustment_type=adjustment_type,
            **kwargs,
        )

    def _apply_price_adjustment(
        self,
        ticks_data: Union[pd.DataFrame, List[Any]],
        code: str,
        adjustment_type: ADJUSTMENT_TYPES,
        as_dataframe: bool,
    ) -> Union[pd.DataFrame, List[Any]]:
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

            adjustfactors_df = self.adjustfactor_service.get_adjustfactors(
                code=code, start_date=start_date, end_date=end_date, as_dataframe=True
            )

            if adjustfactors_df.empty:
                self._logger.WARN(f"No adjustment factors found for {code}, returning original data")
                return ticks_data

            # Apply adjustment factors
            adjusted_df = self._calculate_adjusted_tick_prices(ticks_df, adjustfactors_df, adjustment_type)

            # Return in original format
            if as_dataframe:
                return adjusted_df
            else:
                # Convert back to list of models
                from ..models.model_tick import MTick

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
    def count_ticks(self, code: str = None, date: datetime = None, **kwargs) -> int:
        """
        Counts the number of tick records matching the filters.

        Args:
            code: Stock code filter
            date: Specific date filter (will be converted to date range)
            **kwargs: Additional filters

        Returns:
            Number of matching records
        """
        # 提取filters参数并从kwargs中移除，避免重复传递
        filters = kwargs.pop("filters", {})

        # 具体参数优先级高于filters中的对应字段
        if code:
            filters["code"] = code
        if date:
            date = datetime_normalize(date).replace(hour=0, minute=0, second=0, microsecond=0)
            filters["timestamp__gte"] = date
            filters["timestamp__lte"] = date + timedelta(days=1) - timedelta(microseconds=1)

        # Use dynamic CRUD based on code parameter
        if not code:
            raise ValueError("Code parameter is required for tick count operations")
        tick_crud = self.get_crud(code)
        return tick_crud.count(filters=filters)

    def is_tick_data_available(self, code: str, date: datetime) -> bool:
        """
        Checks if tick data is available for a specific code and date.

        Args:
            code: Stock code
            date: Target date

        Returns:
            True if tick data exists for the date
        """
        count = self.count_ticks(code=code, date=date)
        return count > 0

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
        return self.redis_service.get_progress_summary(code, start_date, end_date, "tick")

    def clear_sync_cache(self, code: str) -> bool:
        """
        清除同步缓存（使用RedisService）

        Args:
            code: 股票代码

        Returns:
            成功返回True
        """
        return self.redis_service.clear_sync_progress(code, "tick")

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
        return self.data_source.fetch_history_transaction_detail(code, date)

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

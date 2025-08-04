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

from ...libs import GCONF, datetime_normalize, to_decimal, RichProgress, cache_with_expiration, retry
from .. import mappers
from ...enums import FREQUENCY_TYPES, ADJUSTMENT_TYPES
from .base_service import DataService


class BarService(DataService):
    def __init__(self, crud_repo, data_source, stockinfo_service, adjustfactor_service=None):
        """Initializes the service with its dependencies."""
        super().__init__(crud_repo=crud_repo, data_source=data_source, stockinfo_service=stockinfo_service)

        # Initialize AdjustfactorService for price adjustment support
        if adjustfactor_service is None:
            from .adjustfactor_service import AdjustfactorService
            from ..crud.adjustfactor_crud import AdjustfactorCRUD

            adjustfactor_service = AdjustfactorService(
                crud_repo=AdjustfactorCRUD(), data_source=data_source, stockinfo_service=stockinfo_service
            )
        self.adjustfactor_service = adjustfactor_service

    @retry(max_try=3)
    def sync_for_code_with_date_range(
        self,
        code: str,
        start_date: datetime = None,
        end_date: datetime = None,
        frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY,
    ) -> Dict[str, Any]:
        """
        Synchronizes bar data for a single stock code within specified date range.

        Args:
            code: Stock code (e.g., '000001.SZ')
            start_date: Start date for data sync (if None, determined by existing logic)
            end_date: End date for data sync (if None, defaults to today)
            frequency: Data frequency (currently only DAY supported)

        Returns:
            Dict containing sync results with success status, statistics, and error info
        """
        result = {
            "code": code,
            "success": False,
            "records_processed": 0,
            "records_added": 0,
            "error": None,
            "warnings": [],
            "date_range": None,
        }

        # Validate stock code
        if not self.stockinfo_service.is_code_in_stocklist(code):
            result["error"] = f"Stock code {code} not in stock list"
            self._logger.DEBUG(f"Skipping bar sync for {code} as it's not in the stock list.")
            return result

        try:
            # Validate and set date range
            validated_start, validated_end = self._validate_and_set_date_range(start_date, end_date)
            result["date_range"] = f"{validated_start.date()} to {validated_end.date()}"

            self._logger.INFO(
                f"Syncing {frequency.value} bars for {code} from {validated_start.date()} to {validated_end.date()}"
            )

            # Fetch data with retry mechanism
            try:
                raw_data = self._fetch_raw_data(code, validated_start, validated_end, frequency)
                if raw_data is None or raw_data.empty:
                    result["success"] = True
                    result["warnings"].append("No new data available from source")
                    self._logger.INFO(f"No new bar data for {code} from source.")
                    return result
            except Exception as e:
                result["error"] = f"Failed to fetch data from source: {str(e)}"
                self._logger.ERROR(f"Failed to fetch bars for {code} from source: {e}")
                return result

            result["records_processed"] = len(raw_data)

            # Validate data quality
            if not self._validate_bar_data(raw_data):
                result["warnings"].append("Data quality issues detected")

            # Convert data to models with error handling
            try:
                models_to_add = mappers.dataframe_to_bar_models(raw_data, code, frequency)
                if not models_to_add:
                    result["success"] = True
                    result["warnings"].append("No valid models generated from data")
                    return result
            except Exception as e:
                # Fallback: try row-by-row conversion
                self._logger.WARN(f"Batch conversion failed for {code}, attempting row-by-row: {e}")
                models_to_add = self._convert_rows_individually(raw_data, code, frequency)
                if not models_to_add:
                    result["error"] = f"Data mapping failed: {str(e)}"
                    return result
                result["warnings"].append("Used row-by-row conversion due to batch failure")

            # Smart duplicate checking and database operations
            try:
                final_models = self._filter_existing_data(models_to_add, code, frequency)

                if not final_models:
                    result["success"] = True
                    result["warnings"].append("All data already exists in database")
                    return result

                # Only remove existing data if we have a limited date range (for data consistency)
                if start_date is not None or end_date is not None:
                    min_date = min(item.timestamp for item in final_models)
                    max_date = max(item.timestamp for item in final_models)
                    removed_count = self.crud_repo.remove(
                        filters={
                            "code": code,
                            "timestamp__gte": min_date,
                            "timestamp__lte": max_date,
                            "frequency": frequency,
                        }
                    )
                    if removed_count is not None and removed_count > 0:
                        result["warnings"].append(f"Removed {removed_count} existing records for consistency")
                    time.sleep(0.2)  # Brief pause for database consistency

                self.crud_repo.add_batch(final_models)
                result["records_added"] = len(final_models)
                result["success"] = True
                self._logger.INFO(f"Bar data for {code} saved successfully: {len(final_models)} records")

            except Exception as e:
                result["error"] = f"Database operation failed: {str(e)}"
                self._logger.ERROR(f"Failed to save bar data for {code}: {e}")
                return result

        except Exception as e:
            result["error"] = f"Unexpected error during sync: {str(e)}"
            self._logger.ERROR(f"Unexpected error syncing {code}: {e}")

        return result

    @retry(max_try=3)
    def sync_for_code(
        self, code: str, fast_mode: bool = True, frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY
    ) -> Dict[str, Any]:
        """
        Synchronizes bar data for a single stock code with enhanced error handling.

        Args:
            code: Stock code (e.g., '000001.SZ')
            fast_mode: If True, only fetch data from last available date
            frequency: Data frequency (currently only DAY supported)

        Returns:
            Dict containing sync results with success status, statistics, and error info
        """
        # Determine date range based on fast_mode
        start_date, end_date = self._get_fetch_date_range(code, fast_mode)

        # Call the new date range method
        result = self.sync_for_code_with_date_range(code, start_date, end_date, frequency)

        # For backward compatibility with existing deletion logic in non-fast mode
        if not fast_mode and result["success"] and result["records_added"] > 0:
            # Ensure we handle the old delete-and-replace behavior for non-fast mode
            # The new method already handles this, but we add this check for clarity
            pass

        return result

    def sync_batch_codes_with_date_range(
        self,
        codes: List[str],
        start_date: datetime = None,
        end_date: datetime = None,
        frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY,
    ) -> Dict[str, Any]:
        """
        Synchronizes bar data for multiple stock codes within specified date range.

        Args:
            codes: List of stock codes
            start_date: Start date for data sync (if None, determined by existing logic)
            end_date: End date for data sync (if None, defaults to today)
            frequency: Data frequency

        Returns:
            Dict containing batch sync results and statistics
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
            validated_start, validated_end = self._validate_and_set_date_range(start_date, end_date)
            batch_result["date_range"] = f"{validated_start.date()} to {validated_end.date()}"
        except ValueError as e:
            batch_result["failures"].append({"error": f"Invalid date range: {str(e)}"})
            return batch_result

        valid_codes = [code for code in codes if self.stockinfo_service.is_code_in_stocklist(code)]
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
                    result = self.sync_for_code_with_date_range(code, validated_start, validated_end, frequency)

                    batch_result["results"].append(result)
                    batch_result["total_records_processed"] += result["records_processed"]
                    batch_result["total_records_added"] += result["records_added"]

                    if result["success"]:
                        batch_result["successful_codes"] += 1
                    else:
                        batch_result["failed_codes"] += 1
                        batch_result["failures"].append({"code": code, "error": result["error"]})

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
        return batch_result

    def sync_batch_codes(
        self, codes: List[str], fast_mode: bool = True, frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY
    ) -> Dict[str, Any]:
        """
        Synchronizes bar data for multiple stock codes with comprehensive error tracking.

        Args:
            codes: List of stock codes
            fast_mode: If True, only fetch data from last available date
            frequency: Data frequency

        Returns:
            Dict containing batch sync results and statistics
        """
        # For backward compatibility, we need to determine date ranges for each code individually
        # since fast_mode behavior is per-code
        if fast_mode:
            # In fast mode, each code has its own start date, so we can't use batch date range method
            # Fall back to individual sync_for_code calls
            batch_result = {
                "total_codes": len(codes),
                "successful_codes": 0,
                "failed_codes": 0,
                "total_records_processed": 0,
                "total_records_added": 0,
                "results": [],
                "failures": [],
            }

            valid_codes = [code for code in codes if self.stockinfo_service.is_code_in_stocklist(code)]
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
                        result = self.sync_for_code(code, fast_mode, frequency)

                        batch_result["results"].append(result)
                        batch_result["total_records_processed"] += result["records_processed"]
                        batch_result["total_records_added"] += result["records_added"]

                        if result["success"]:
                            batch_result["successful_codes"] += 1
                        else:
                            batch_result["failed_codes"] += 1
                            batch_result["failures"].append({"code": code, "error": result["error"]})

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
            return batch_result
        else:
            # In non-fast mode, all codes use the same date range, so we can use the batch date range method
            start_date = datetime_normalize(GCONF.DEFAULTSTART)
            end_date = datetime.now()
            return self.sync_batch_codes_with_date_range(codes, start_date, end_date, frequency)

    def get_bars(
        self,
        code: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY,
        as_dataframe: bool = True,
        adjustment_type: ADJUSTMENT_TYPES = ADJUSTMENT_TYPES.NONE,
        **kwargs,
    ) -> Union[pd.DataFrame, List[Any]]:
        """
        Retrieves bar data from the database with optional price adjustment.

        Args:
            code: Stock code filter
            start_date: Start date filter
            end_date: End date filter
            frequency: Data frequency filter
            as_dataframe: Return format
            adjustment_type: Price adjustment type (NONE/FORE/BACK)
            **kwargs: Additional filters

        Returns:
            Bar data as DataFrame or list of models, optionally price-adjusted
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
        if frequency:
            filters["frequency"] = frequency

        # Get original bar data - 现在可以安全传递，不会有参数冲突
        original_data = self.crud_repo.find(filters=filters, as_dataframe=as_dataframe, **kwargs)

        # Return original data if no adjustment needed
        if adjustment_type == ADJUSTMENT_TYPES.NONE:
            return original_data

        # Apply price adjustment if requested
        return self._apply_price_adjustment(original_data, code, adjustment_type, as_dataframe)

    def get_bars_adjusted(
        self,
        code: str,
        adjustment_type: ADJUSTMENT_TYPES = ADJUSTMENT_TYPES.FORE,
        start_date: datetime = None,
        end_date: datetime = None,
        frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY,
        as_dataframe: bool = True,
        **kwargs,
    ) -> Union[pd.DataFrame, List[Any]]:
        """
        Convenience method to get price-adjusted bar data.

        Args:
            code: Stock code (required for adjustment)
            adjustment_type: Price adjustment type (FORE/BACK)
            start_date: Start date filter
            end_date: End date filter
            frequency: Data frequency filter
            as_dataframe: Return format
            **kwargs: Additional filters

        Returns:
            Price-adjusted bar data as DataFrame or list of models
        """
        if adjustment_type == ADJUSTMENT_TYPES.NONE:
            self._logger.WARN("Use get_bars() for unadjusted data")

        return self.get_bars(
            code=code,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            as_dataframe=as_dataframe,
            adjustment_type=adjustment_type,
            **kwargs,
        )

    def _apply_price_adjustment(
        self,
        bars_data: Union[pd.DataFrame, List[Any]],
        code: str,
        adjustment_type: ADJUSTMENT_TYPES,
        as_dataframe: bool,
    ) -> Union[pd.DataFrame, List[Any]]:
        """
        Applies price adjustment factors to bar data.

        Args:
            bars_data: Original bar data (DataFrame or list of models)
            code: Stock code for getting adjustment factors
            adjustment_type: Type of adjustment (FORE/BACK)
            as_dataframe: Whether bars_data is DataFrame format

        Returns:
            Price-adjusted bar data in the same format as input
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
            if as_dataframe:
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

            adjustfactors_df = self.adjustfactor_service.get_adjustfactors(
                code=code, start_date=start_date, end_date=end_date, as_dataframe=True
            )

            if adjustfactors_df.empty:
                self._logger.WARN(f"No adjustment factors found for {code}, returning original data")
                return bars_data

            # Apply adjustment factors
            adjusted_df = self._calculate_adjusted_prices(bars_df, adjustfactors_df, adjustment_type)

            # Return in original format
            if as_dataframe:
                return adjusted_df
            else:
                # Convert back to list of models
                from ..models.model_bar import MBar

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

    def get_latest_timestamp_for_code(self, code: str, frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY) -> datetime:
        """
        Gets the latest timestamp for a specific code and frequency.

        Args:
            code: Stock code
            frequency: Data frequency

        Returns:
            Latest timestamp or default start date if no data exists
        """
        latest_records = self.crud_repo.find(
            filters={"code": code, "frequency": frequency}, page_size=1, order_by="timestamp", desc_order=True
        )

        if latest_records:
            return latest_records[0].timestamp
        else:
            return datetime_normalize(GCONF.DEFAULTSTART)

    def _get_fetch_date_range(self, code: str, fast_mode: bool) -> tuple:
        """Determines the date range for fetching data."""
        end_date = datetime.now()

        if not fast_mode:
            start_date = self._get_intelligent_start_date(code)
        else:
            start_date = self.get_latest_timestamp_for_code(code) + timedelta(days=1)

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
            stockinfo = self.stockinfo_service.get_stockinfo_by_code(code)
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
            return self.data_source.fetch_cn_stock_daybar(code=code, start_date=start_date, end_date=end_date)
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
                row_models = mappers.dataframe_to_bar_models(single_row_df, code, frequency)
                models.extend(row_models)
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

    def _filter_existing_data(self, models_to_add: List[Any], code: str, frequency: FREQUENCY_TYPES) -> List[Any]:
        """
        Filters out existing data to avoid duplicates.

        Args:
            models_to_add: List of models to potentially add
            code: Stock code
            frequency: Data frequency

        Returns:
            List of models that don't already exist in database
        """
        if not models_to_add:
            return []

        try:
            # Get timestamps of models to add
            timestamps_to_add = [model.timestamp for model in models_to_add]

            # Check which timestamps already exist in database
            existing_records = self.crud_repo.find(
                filters={"code": code, "timestamp__in": timestamps_to_add, "frequency": frequency}
            )

            existing_timestamps = {record.timestamp for record in existing_records}

            # Filter out existing records
            new_models = [model for model in models_to_add if model.timestamp not in existing_timestamps]

            if len(existing_timestamps) > 0:
                self._logger.DEBUG(f"Filtered out {len(existing_timestamps)} existing records for {code}")

            return new_models

        except Exception as e:
            self._logger.WARN(f"Error filtering existing data for {code}: {e}, proceeding with all models")
            return models_to_add

    def count_bars(self, code: str = None, frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY, **kwargs) -> int:
        """
        Counts the number of bar records matching the filters.

        Args:
            code: Stock code filter
            frequency: Data frequency filter
            **kwargs: Additional filters

        Returns:
            Number of matching records
        """
        filters = kwargs.copy()
        if code:
            filters["code"] = code
        if frequency:
            filters["frequency"] = frequency

        return self.crud_repo.count(filters=filters)

    def get_available_codes(self, frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY) -> List[str]:
        """
        Gets list of available stock codes for a given frequency.

        Args:
            frequency: Data frequency

        Returns:
            List of unique stock codes
        """
        try:
            return self.crud_repo.find(filters={"frequency": frequency}, distinct_field="code")
        except Exception as e:
            self._logger.ERROR(f"Failed to get available codes: {e}")
            return []

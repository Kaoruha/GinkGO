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

from ...libs import GCONF, datetime_normalize, cache_with_expiration, retry, to_decimal
from .. import mappers
from .base_service import DataService


class AdjustfactorService(DataService):
    def __init__(self, crud_repo, data_source, stockinfo_service):
        """Initializes the service with its dependencies."""
        super().__init__(crud_repo=crud_repo, data_source=data_source, stockinfo_service=stockinfo_service)

    def sync_for_code(self, code: str, fast_mode: bool = True) -> Dict[str, Any]:
        """
        Synchronizes adjustment factors for a single stock code.
        This method is transactional and includes enhanced error handling.

        Args:
            code: Stock code to sync
            fast_mode: If True, only fetch data from last available date

        Returns:
            Dictionary with sync results and statistics
        """
        result = {
            "code": code,
            "success": False,
            "records_processed": 0,
            "records_added": 0,
            "error": None,
            "warnings": [],
        }

        # Validate stock code
        if not self.stockinfo_service.is_code_in_stocklist(code):
            result["error"] = f"Code {code} not in stock list"
            self._logger.DEBUG(f"Skipping adjustfactor sync for {code} as it's not in the stock list.")
            return result

        start_date = self._get_fetch_start_date(code, fast_mode)
        end_date = datetime.now()
        self._logger.INFO(f"Syncing adjustfactors for {code} from {start_date.date()} to {end_date.date()}")

        # Fetch data with retry mechanism
        try:
            raw_data = self._fetch_adjustfactor_data(code, start_date, end_date)
        except Exception as e:
            result["error"] = f"Failed to fetch data from source: {e}"
            return result

        if raw_data is None:
            result["error"] = "Failed to fetch data from source"
            return result

        if raw_data.empty:
            result["success"] = True
            result["warnings"].append("No new data available from source")
            self._logger.INFO(f"No new adjustfactor data for {code} from source.")
            return result

        result["records_processed"] = len(raw_data)

        # Convert data with error handling
        models_to_add, mapping_errors = self._convert_to_models(raw_data, code)
        if mapping_errors:
            result["warnings"].extend(mapping_errors)

        if not models_to_add:
            result["error"] = "No valid records after data conversion"
            return result

        # Database operations with enhanced transaction handling
        success = self._save_to_database(code, models_to_add, fast_mode)
        if success:
            result["success"] = True
            result["records_added"] = len(models_to_add)
            self._logger.INFO(f"Successfully synced {len(models_to_add)} adjustfactors for {code}")
        else:
            result["error"] = "Database operation failed"

        return result

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

    def _save_to_database(self, code: str, models_to_add: List[Any], fast_mode: bool) -> bool:
        """
        Saves adjustment factor models to database with enhanced error handling.

        Args:
            code: Stock code
            models_to_add: List of adjustment factor models
            fast_mode: Whether to use fast mode (incremental update)

        Returns:
            True if successful, False otherwise
        """
        try:
            if not fast_mode:
                # Remove existing data in date range
                min_date = min(item.timestamp for item in models_to_add)
                max_date = max(item.timestamp for item in models_to_add)
                removed_count = self.crud_repo.remove(
                    filters={"code": code, "timestamp__gte": min_date, "timestamp__lte": max_date}
                )
                removed_count = removed_count or 0  # Handle None return value
                if removed_count > 0:
                    self._logger.INFO(f"Removed {removed_count} existing records for {code}")

            # Add new data
            self.crud_repo.add_batch(models_to_add)

            self._logger.INFO(f"Successfully saved {len(models_to_add)} adjustfactors for {code}")
            return True

        except Exception as e:
            self._logger.ERROR(f"Failed to save adjustfactors for {code}. Error: {e}")
            return False

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

    def get_adjustfactors(
        self,
        code: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        as_dataframe: bool = True,
        **kwargs,
    ) -> Union[pd.DataFrame, List[Any]]:
        """
        Retrieves adjustment factor data from the database with caching.

        Args:
            code: Stock code filter
            start_date: Start date filter
            end_date: End date filter
            as_dataframe: Return format
            **kwargs: Additional filters

        Returns:
            Adjustment factor data as DataFrame or list of models
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

        return self.crud_repo.find(filters=filters, as_dataframe=as_dataframe, **kwargs)

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
            return datetime_normalize(GCONF.DEFAULTSTART)

        latest_timestamp = self.get_latest_adjustfactor_for_code(code)
        return latest_timestamp + timedelta(days=1)

    def recalculate_adjust_factors_for_code(self, code: str) -> Dict[str, Any]:
        """
        Recalculates fore/back adjust factors for a single stock code based on existing adj_factor data.

        This method implements the separated architecture where:
        1. Original adj_factor data is already in database (via update command)
        2. This method calculates fore/back factors independently

        Args:
            code: Stock code to recalculate

        Returns:
            Dict containing calculation results and statistics
        """
        result = {
            "code": code,
            "success": False,
            "records_processed": 0,
            "records_updated": 0,
            "error": None,
            "warnings": [],
        }

        # Validate stock code
        if not self.stockinfo_service.is_code_in_stocklist(code):
            result["error"] = f"Code {code} not in stock list"
            self._logger.DEBUG(f"Skipping adjust factor calculation for {code} as it's not in the stock list.")
            return result

        try:
            # Get all existing adjustfactor records for this code
            existing_records = self.crud_repo.find(
                filters={"code": code}, order_by="timestamp", desc_order=False  # Ascending order for calculation
            )

            if not existing_records:
                result["error"] = f"No adjustfactor data found for {code}"
                self._logger.WARN(f"No adjustfactor data found for {code}")
                return result

            result["records_processed"] = len(existing_records)

            # Calculate fore/back adjust factors for all records (including single record)
            try:
                updated_records = self._calculate_fore_back_factors(existing_records, code)

                # Use efficient remove + add_batch approach for ClickHouse compatibility
                # 1. Remove all existing records for this code
                self.crud_repo.remove(filters={"code": code})

                # 2. Batch insert updated records
                self.crud_repo.add_batch(updated_records)

                result["records_updated"] = len(updated_records)
                result["success"] = True
                self._logger.INFO(
                    f"Successfully recalculated adjust factors for {code}: {len(updated_records)} records"
                )

            except Exception as calc_error:
                result["error"] = f"Failed to calculate adjust factors: {str(calc_error)}"
                self._logger.ERROR(f"Failed to calculate adjust factors for {code}: {calc_error}")
                return result

        except Exception as e:
            result["error"] = f"Database operation failed: {str(e)}"
            self._logger.ERROR(f"Failed to recalculate adjust factors for {code}: {e}")

        return result

    def recalculate_adjust_factors_batch(self, codes: List[str] = None) -> Dict[str, Any]:
        """
        Batch recalculates fore/back adjust factors for multiple stock codes.

        Args:
            codes: List of stock codes. If None, processes all available codes

        Returns:
            Dict containing batch calculation results and statistics
        """
        from ginkgo.libs import RichProgress

        # Get codes to process
        if codes is None:
            codes = self.get_available_codes()
            self._logger.INFO(f"Processing all available codes: {len(codes)} stocks")
        else:
            # Filter out invalid codes
            valid_codes = [code for code in codes if self.stockinfo_service.is_code_in_stocklist(code)]
            if len(valid_codes) != len(codes):
                invalid_codes = set(codes) - set(valid_codes)
                self._logger.WARN(f"Filtered out invalid codes: {invalid_codes}")
            codes = valid_codes

        batch_result = {
            # Standard fields (consistent with single method)
            "success": True,  # Overall success flag
            "error": None,  # Overall error message
            "warnings": [],  # Overall warnings
            # Batch-specific fields
            "total_codes": len(codes),
            "successful_codes": 0,
            "failed_codes": 0,
            "total_records_processed": 0,
            "total_records_updated": 0,
            "results": [],  # List of individual results
            "failures": [],  # List of failure details
        }

        if not codes:
            batch_result["failures"].append({"error": "No valid codes to process"})
            return batch_result

        with RichProgress() as progress:
            task = progress.add_task("[cyan]Recalculating Adjust Factors", total=len(codes))

            for code in codes:
                try:
                    progress.update(task, description=f"Processing {code}")
                    result = self.recalculate_adjust_factors_for_code(code)

                    batch_result["results"].append(result)
                    batch_result["total_records_processed"] += result["records_processed"]

                    if result["success"]:
                        batch_result["successful_codes"] += 1
                        batch_result["total_records_updated"] += result["records_updated"]
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

        # Set final success status and error information
        batch_result["success"] = batch_result["failed_codes"] == 0

        if batch_result["failed_codes"] > 0:
            batch_result["error"] = (
                f"Failed to calculate {batch_result['failed_codes']} out of {batch_result['total_codes']} codes"
            )

        # Collect warnings from individual results
        all_warnings = []
        for result in batch_result["results"]:
            if result.get("warnings"):
                all_warnings.extend(result["warnings"])
        batch_result["warnings"] = all_warnings

        # Log summary
        self._logger.INFO(
            f"Batch adjust factor calculation completed: {batch_result['successful_codes']}/{batch_result['total_codes']} successful"
        )
        if batch_result["failures"]:
            self._logger.WARN(f"Failed to calculate {batch_result['failed_codes']} codes")
            for failure in batch_result["failures"][:5]:  # Show first 5 failures
                self._logger.WARN(f"  - {failure.get('code', 'Unknown')}: {failure['error']}")

        return batch_result

    def _calculate_fore_back_factors(self, records: List[Any], code: str) -> List[Any]:
        """
        Calculates fore/back adjust factors for a list of records.

        Calculation logic:
        - Fore adjust factor = latest_adj_factor / current_adj_factor (newest as base)
        - Back adjust factor = current_adj_factor / earliest_adj_factor (oldest as base)

        Args:
            records: List of adjustfactor records sorted by timestamp (ascending)
            code: Stock code for logging

        Returns:
            List of updated records with calculated fore/back factors
        """
        if not records:
            raise ValueError(f"No records provided for {code}")

        if len(records) == 1:
            # Single record case
            records[0].foreadjustfactor = to_decimal(1.0)
            records[0].backadjustfactor = to_decimal(1.0)
            return records

        try:
            # Extract and validate adj_factors - keep as Decimal for precision
            adj_factors = []
            valid_records = []

            for record in records:
                if record.adjustfactor > 0:
                    adj_factors.append(record.adjustfactor)  # Keep as Decimal
                    valid_records.append(record)
                else:
                    self._logger.WARN(f"Invalid adj_factor {record.adjustfactor} for {code} at {record.timestamp}")

            if len(valid_records) == 0:
                raise ValueError(f"All adj_factors are invalid for {code}")

            # Calculate factors using Decimal arithmetic for precision
            latest_factor = adj_factors[-1]  # Last element (newest) - Decimal
            earliest_factor = adj_factors[0]  # First element (oldest) - Decimal

            for i, record in enumerate(valid_records):
                current_factor = adj_factors[i]  # Decimal

                # Fore adjust factor: latest as base - Decimal division
                fore_factor = latest_factor / current_factor

                # Back adjust factor: earliest as base - Decimal division
                back_factor = current_factor / earliest_factor

                # Direct assignment - already Decimal, no conversion needed
                record.foreadjustfactor = fore_factor
                record.backadjustfactor = back_factor

            self._logger.DEBUG(f"Calculated adjust factors for {code}: {len(valid_records)} records")
            return valid_records

        except Exception as e:
            self._logger.ERROR(f"Error calculating adjust factors for {code}: {e}")
            raise

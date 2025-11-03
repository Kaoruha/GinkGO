"""
StockInfo Data Service (Class-based)

This service handles the business logic for synchronizing stock information.

Enhanced with comprehensive error handling, retry mechanisms, and structured returns.
"""

import pandas as pd
from typing import List, Any, Union, Dict

from ginkgo.libs import RichProgress, cache_with_expiration, retry
from ginkgo.data import mappers
from ginkgo.data.services.base_service import DataService


class StockinfoService(DataService):
    def __init__(self, crud_repo, data_source):
        """Initializes the service with its dependencies."""
        super().__init__(crud_repo=crud_repo, data_source=data_source)

    @retry(max_try=3)
    def sync_all(self) -> Dict[str, Any]:
        """
        Synchronizes stock information for all stocks with comprehensive error handling.
        Uses error tolerance mechanism - individual failures don't affect other records.

        Returns:
            Dictionary containing comprehensive sync results and statistics
        """
        result = {
            "success": 0,  # Count of successfully processed records
            "failed": 0,  # Count of failed records
            "total": 0,  # Total records processed
            "error": None,  # API-level error message
            "warnings": [],  # Warning messages (only when present)
            "failed_records": [],  # Details of failed records (only when present)
        }

        try:
            raw_data = self.data_source.fetch_cn_stockinfo()
            if raw_data is None or raw_data.empty:
                result["warnings"].append("No stock info data returned from source")
                self._logger.WARN("No stock info data returned from source.")
                return result
        except Exception as e:
            result["error"] = f"Failed to fetch stock info from source: {str(e)}"
            self._logger.ERROR(f"Failed to fetch stock info from source: {e}")
            return result

        result["total"] = len(raw_data)

        with RichProgress() as progress:
            task = progress.add_task("[cyan]Upserting Stock Info", total=len(raw_data))

            for _, row in raw_data.iterrows():
                # Try to convert each row individually with error tolerance
                try:
                    item = mappers.row_to_stockinfo_upsert_dict(row)
                except Exception as e:
                    # Skip this record if mapping fails (e.g., invalid date format)
                    result["failed"] += 1
                    code = row.get("ts_code", "Unknown")
                    code_name = row.get("name", "Unknown")
                    error_msg = f"Failed to map stock info for {code}: {e}"
                    result["failed_records"].append({"code": code, "code_name": code_name, "error": str(e)})
                    progress.update(task, advance=1, description=f":x: {code} {code_name}")
                    self._logger.ERROR(error_msg)
                    continue

                code = item["code"]
                code_name = item.get("code_name", "Unknown")

                try:
                    # Each stock info update uses its own transaction
                    if self.crud_repo.exists(filters={"code": code}):
                        self.crud_repo.modify(filters={"code": code}, updates=item)
                        result["success"] += 1
                        progress.update(task, advance=1, description=f":arrows_counterclockwise: {code} {code_name}")
                        self._logger.DEBUG(f"Successfully updated stock info for {code}")
                    else:
                        self.crud_repo.create(**item)
                        result["success"] += 1
                        progress.update(task, advance=1, description=f":white_check_mark: {code} {code_name}")
                        self._logger.DEBUG(f"Successfully added stock info for {code}")

                except Exception as e:
                    result["failed"] += 1
                    error_msg = f"Failed to upsert stock info for {code}: {e}"
                    result["failed_records"].append({"code": code, "code_name": code_name, "error": str(e)})
                    progress.update(task, advance=1, description=f":x: {code} {code_name}")
                    self._logger.ERROR(error_msg)

                    # Continue processing other records instead of failing completely
                    continue

        # Generate summary report
        self._logger.INFO(
            f"Stock info sync completed: {result['success']}/{result['total']} successful, "
            f"{result['failed']} failed"
        )

        # Add warning if there were failures
        if result["failed_records"]:
            result["warnings"].append(f"Failed to update {result['failed']} stock records")
            for record in result["failed_records"][:5]:  # Show first 5 failures
                self._logger.WARN(f"  - {record['code']} ({record['code_name']}): {record['error']}")
            if len(result["failed_records"]) > 5:
                self._logger.WARN(f"  ... and {len(result['failed_records']) - 5} more failures")

        # Clean up empty arrays to keep response minimal (keep failed_records for compatibility)
        if not result["warnings"]:
            del result["warnings"]

        return result

    @retry(max_try=3)
    def retry_failed_records(self, failed_records: List[dict]) -> Dict[str, Any]:
        """
        Retry updating failed stock records with comprehensive error handling.

        Args:
            failed_records: List of failed record dictionaries from sync_all()

        Returns:
            Dictionary containing comprehensive retry results and statistics
        """
        result = {
            "success": 0,  # Count of successfully processed records
            "failed": 0,  # Count of failed records
            "total": len(failed_records) if failed_records else 0,  # Total records to process
            "error": None,  # API-level error message
            "warnings": [],  # Warning messages (only when present)
            "failed_records": [],  # Details of failed records (only when present)
        }

        if not failed_records:
            result["warnings"].append("No failed records to retry")
            self._logger.INFO("No failed records to retry")
            return result

        self._logger.INFO(f"Retrying {len(failed_records)} failed stock records")

        # Re-fetch latest data to ensure we have current information
        try:
            raw_data = self.data_source.fetch_cn_stockinfo()
            if raw_data is None or raw_data.empty:
                result["error"] = "Cannot retry: No stock info data available from source"
                result["failed"] = len(failed_records)  # All failed
                self._logger.ERROR(result["error"])
                return result
        except Exception as e:
            result["error"] = f"Cannot retry: Failed to fetch stock info from source: {str(e)}"
            result["failed"] = len(failed_records)  # All failed
            self._logger.ERROR(result["error"])
            return result

        # Convert to lookup dict for efficient access
        try:
            upsert_list = mappers.dataframe_to_stockinfo_upsert_list(raw_data)
            upsert_dict = {item["code"]: item for item in upsert_list}
        except Exception as e:
            result["error"] = f"Failed to process source data: {str(e)}"
            result["failed"] = len(failed_records)  # All failed
            self._logger.ERROR(result["error"])
            return result

        with RichProgress() as progress:
            task = progress.add_task("[yellow]Retrying Failed Records", total=len(failed_records))

            for failed_record in failed_records:
                code = failed_record["code"]
                code_name = failed_record.get("code_name", "Unknown")

                if code not in upsert_dict:
                    result["failed"] += 1
                    result["failed_records"].append(
                        {"code": code, "code_name": code_name, "error": "Code not found in current data"}
                    )
                    progress.update(task, advance=1, description=f":warning: {code} (not found)")
                    self._logger.WARN(f"Code {code} not found in current data, skipping retry")
                    continue

                item = upsert_dict[code]

                try:
                    if self.crud_repo.exists(filters={"code": code}):
                        self.crud_repo.modify(filters={"code": code}, updates=item)
                        result["success"] += 1
                        progress.update(task, advance=1, description=f":arrows_counterclockwise: {code} {code_name}")
                        self._logger.INFO(f"Successfully retried and updated stock info for {code}")
                    else:
                        self.crud_repo.create(**item)
                        result["success"] += 1
                        progress.update(task, advance=1, description=f":white_check_mark: {code} {code_name}")
                        self._logger.INFO(f"Successfully retried and added stock info for {code}")

                except Exception as e:
                    result["failed"] += 1
                    error_msg = f"Retry failed for {code}: {e}"
                    result["failed_records"].append({"code": code, "code_name": code_name, "error": str(e)})
                    progress.update(task, advance=1, description=f":x: {code} {code_name}")
                    self._logger.ERROR(error_msg)

        # Generate summary report
        self._logger.INFO(
            f"Retry completed: {result['success']}/{result['total']} successful, " f"{result['failed']} still failed"
        )

        # Add warning if there were failures
        if result["failed_records"]:
            result["warnings"].append(f"Still failed after retry: {len(result['failed_records'])} records")
            for record in result["failed_records"][:3]:
                self._logger.WARN(f"  - {record['code']} ({record['code_name']}): {record['error']}")

        # Clean up empty arrays to keep response minimal (keep failed_records for compatibility)
        if not result["warnings"]:
            del result["warnings"]

        return result

    def get_stockinfos(self, as_dataframe: bool = True, *args, **kwargs) -> Union[pd.DataFrame, List[Any]]:
        """Retrieves stock information from the database."""
        # For read operations, we can either get a new session or assume it's read-only
        # For simplicity, we'll let CRUD handle the session for reads if not provided externally.
        return self.crud_repo.find(as_dataframe=as_dataframe, *args, **kwargs)

    def get_stockinfo_codes_set(self) -> set:
        """Gets a set of all stock codes for efficient O(1) lookups."""
        df = self.get_stockinfos(as_dataframe=True)
        if df is not None and not df.empty:
            return set(df["code"].values)
        return set()

    def is_code_in_stocklist(self, code: str) -> bool:
        """
        Checks if a code exists in the stock list using the cached set.
        This method is not transactional and can use a default session.
        """
        return code in self.get_stockinfo_codes_set()

    def get_stockinfo_by_code(self, code: str):
        """
        Gets stock information for a specific code.

        Args:
            code: Stock code (e.g., '000001.SZ')

        Returns:
            Stock info model or None if not found
        """
        try:
            results = self.crud_repo.find(filters={"code": code}, page_size=1, as_dataframe=False)
            return results[0] if results else None
        except Exception as e:
            self._logger.ERROR(f"Failed to get stock info for {code}: {e}")
            return None

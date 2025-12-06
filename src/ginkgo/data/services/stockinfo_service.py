"""
StockInfo Data Service (Class-based)

This service handles the business logic for synchronizing stock information.

Enhanced with comprehensive error handling, retry mechanisms, and structured returns.
Following BarService standard for unified architecture.
"""

import time
import pandas as pd
from typing import List, Any, Union, Dict, Optional
from datetime import datetime

from ginkgo.libs import RichProgress, cache_with_expiration, retry, time_logger
from ginkgo.libs.data.results import DataSyncResult, DataValidationResult, DataIntegrityCheckResult
from ginkgo.data import mappers
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.crud.model_conversion import ModelList


class StockinfoService(BaseService):
    def __init__(self, crud_repo, data_source, **additional_deps):
        """
        Initializes the service with its dependencies following BarService pattern.

        Args:
            crud_repo: CRUD repository for database operations
            data_source: Data source for fetching stock information
            **additional_deps: Additional dependencies (ServiceHub pattern)
        """
        super().__init__(crud_repo=crud_repo, data_source=data_source, **additional_deps)

    # 注意：add、update、delete方法已移除，股票信息通过sync_all方法批量更新

    def health_check(self) -> ServiceResult:
        """
        健康检查

        Returns:
            ServiceResult: 健康状态
        """
        try:
            # 检查依赖服务
            data_source_healthy = self._data_source and hasattr(self._data_source, 'fetch_cn_stockinfo')

            # 检查数据库连接
            total_count = 0
            try:
                count_result = self.count()
                total_count = count_result.data if count_result.success else 0
            except:
                total_count = 0

            health_data = {
                "service_name": self._service_name,
                "status": "healthy" if data_source_healthy else "unhealthy",
                "dependencies": {
                    "data_source": "healthy" if data_source_healthy else "unavailable"
                },
                "total_records": total_count
            }

            return ServiceResult.success(data=health_data, message="StockinfoService健康检查完成")

        except Exception as e:
            error_msg = f"健康检查失败: {str(e)}"
            self._logger.ERROR(error_msg)
            return ServiceResult.error(error_msg)

    @retry(max_try=3)
    @time_logger
    def sync(self) -> ServiceResult:
        """
        Synchronizes stock information for all stocks with comprehensive error handling.
        Uses error tolerance mechanism - individual failures don't affect other records.

        Returns:
            ServiceResult containing DataSyncResult with comprehensive sync statistics
        """
        start_time = time.time()
        self._log_operation_start("sync")

        try:
            # Fetch stock information from data source
            raw_data = self._data_source.fetch_cn_stockinfo()
            if raw_data is None or raw_data.empty:
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="stockinfo",
                    entity_identifier="all",
                    sync_strategy="full_sync"
                )
                sync_result.add_warning("No stock info data returned from source")
                self._logger.WARN("No stock info data returned from source.")
                return ServiceResult.failure(
                    data=sync_result,
                    message="No stock info data available from source - sync task failed"
                )

        except Exception as e:
            sync_result = DataSyncResult.create_for_entity(
                entity_type="stockinfo",
                entity_identifier="all",
                sync_strategy="full_sync"
            )
            sync_result.add_error(0, f"Failed to fetch stock info from source: {str(e)}")
            duration = time.time() - start_time
            self._log_operation_end("sync", False, duration)
            return ServiceResult.failure(
                message=f"Failed to fetch stock info from source: {str(e)}",
                data=sync_result
            )

        # Initialize sync result
        sync_result = DataSyncResult.create_for_entity(
            entity_type="stockinfo",
            entity_identifier="all",
            sync_strategy="full_sync"
        )
        sync_result.set_metadata("initial_records", len(raw_data))

        success_count = 0
        failed_count = 0
        failed_records = []

        with RichProgress() as progress:
            task = progress.add_task("[cyan]Upserting Stock Info", total=len(raw_data))

            for _, row in raw_data.iterrows():
                # Try to convert each row individually with error tolerance
                try:
                    item = mappers.row_to_stockinfo_upsert_dict(row)
                except Exception as e:
                    # Skip this record if mapping fails
                    failed_count += 1
                    code = row.get("ts_code", "Unknown")
                    code_name = row.get("name", "Unknown")
                    error_msg = f"Failed to map stock info for {code}: {e}"
                    failed_records.append({"code": code, "code_name": code_name, "error": str(e)})
                    progress.update(task, advance=1, description=f":x: {code} {code_name}")
                    self._logger.ERROR(error_msg)
                    continue

                code = item["code"]
                code_name = item.get("code_name", "Unknown")

                try:
                    # Each stock info update uses its own transaction
                    if self._crud_repo.exists(filters={"code": code}):
                        self._crud_repo.modify(filters={"code": code}, updates=item)
                        success_count += 1
                        progress.update(task, advance=1, description=f":arrows_counterclockwise: {code} {code_name}")
                        self._logger.DEBUG(f"Successfully updated stock info for {code}")
                    else:
                        self._crud_repo.create(**item)
                        success_count += 1
                        progress.update(task, advance=1, description=f":white_check_mark: {code} {code_name}")
                        self._logger.DEBUG(f"Successfully added stock info for {code}")

                except Exception as e:
                    failed_count += 1
                    error_msg = f"Failed to upsert stock info for {code}: {e}"
                    failed_records.append({"code": code, "code_name": code_name, "error": str(e)})
                    progress.update(task, advance=1, description=f":x: {code} {code_name}")
                    self._logger.ERROR(error_msg)
                    continue

        # Update sync result statistics
        duration = time.time() - start_time
        sync_result.records_processed = len(raw_data)
        sync_result.records_added = success_count
        sync_result.records_updated = 0  # StockinfoService uses upsert, counted as added
        sync_result.records_skipped = 0  # No skipping in current implementation
        sync_result.records_failed = failed_count
        sync_result.sync_duration = duration
        sync_result.is_idempotent = True

        # Add failed records to sync result
        for failed_record in failed_records:
            sync_result.add_error(
                failed_record["code"],
                f"{failed_record['code_name']}: {failed_record['error']}"
            )

        # Add warning if there were failures
        if failed_count > 0:
            sync_result.add_warning(f"Failed to update {failed_count} stock records")
            for record in failed_records[:5]:  # Show first 5 failures
                self._logger.WARN(f"  - {record['code']} ({record['code_name']}): {record['error']}")
            if len(failed_records) > 5:
                self._logger.WARN(f"  ... and {len(failed_records) - 5} more failures")

        # Generate summary report
        self._logger.INFO(
            f"Stock info sync completed: {success_count}/{len(raw_data)} successful, "
            f"{failed_count} failed"
        )

        self._log_operation_end("sync", True, duration)

        # Return success result
        if failed_count == 0:
            return ServiceResult.success(
                data=sync_result,
                message=f"Stock info sync completed successfully: {success_count} records processed"
            )
        else:
            return ServiceResult.success(
                data=sync_result,
                message=f"Stock info sync completed with {failed_count} failures: {success_count} successful"
            )

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
            raw_data = self._data_source.fetch_cn_stockinfo()
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
                    if self._crud_repo.exists(filters={"code": code}):
                        self._crud_repo.modify(filters={"code": code}, updates=item)
                        result["success"] += 1
                        progress.update(task, advance=1, description=f":arrows_counterclockwise: {code} {code_name}")
                        self._logger.INFO(f"Successfully retried and updated stock info for {code}")
                    else:
                        self._crud_repo.create(**item)
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

    @time_logger
    def get(self, *args, **kwargs) -> ServiceResult:
        """
        Retrieves stock information from the database following BarService standard.

        Returns:
            ServiceResult containing ModelList of stock information
        """
        try:
            model_list = self._crud_repo.find(*args, **kwargs)
            return ServiceResult.success(
                data=model_list,
                message=f"Successfully retrieved {len(model_list) if model_list else 0} stock records"
            )
        except Exception as e:
            self._logger.ERROR(f"Failed to retrieve stock information: {e}")
            return ServiceResult.failure(
                message=f"Failed to retrieve stock information: {str(e)}"
            )

    @time_logger
    def count(self, *args, **kwargs) -> ServiceResult:
        """
        Counts stock information records following BarService standard.

        Returns:
            ServiceResult containing count of stock records
        """
        try:
            model_list = self._crud_repo.find(*args, **kwargs)
            count = len(model_list) if model_list else 0
            return ServiceResult.success(
                data=count,
                message=f"Successfully counted {count} stock records"
            )
        except Exception as e:
            self._logger.ERROR(f"Failed to count stock information: {e}")
            return ServiceResult.failure(
                message=f"Failed to count stock information: {str(e)}"
            )

    @time_logger
    def validate(self, *args, **kwargs) -> ServiceResult:
        """
        Validates stock information data quality following BarService standard.

        Returns:
            ServiceResult containing DataValidationResult
        """
        try:
            # Get data to validate
            model_list = self._crud_repo.find(*args, **kwargs)

            validation_result = DataValidationResult.create_for_entity(
                entity_type="stockinfo",
                entity_identifier="validation_check"
            )

            if not model_list or len(model_list) == 0:
                validation_result.add_warning("No stock info data to validate")
                return ServiceResult.success(
                    data=validation_result,
                    message="No stock info data to validate"
                )

            # Perform validation checks
            valid_count = 0
            total_count = len(model_list)

            df = model_list.to_dataframe()

            # Check required fields
            if 'code' in df.columns:
                missing_codes = df['code'].isna().sum()
                if missing_codes > 0:
                    validation_result.add_error(f"Found {missing_codes} records with missing codes")

            if 'name' in df.columns:
                missing_names = df['name'].isna().sum()
                if missing_names > 0:
                    validation_result.add_error(f"Found {missing_names} records with missing names")

            valid_count = total_count - validation_result.error_count
            validation_result.set_metadata("total_records", total_count)
            validation_result.set_metadata("valid_records", valid_count)
            validation_result.set_metadata("invalid_records", total_count - valid_count)

            # Set overall validation status
            if validation_result.error_count == 0:
                validation_result.set_metadata("is_valid", True)
                message = f"All {total_count} stock records passed validation"
            else:
                validation_result.set_metadata("is_valid", False)
                message = f"Found {validation_result.error_count} validation issues in {total_count} records"

            return ServiceResult.success(
                data=validation_result,
                message=message
            )

        except Exception as e:
            self._logger.ERROR(f"Failed to validate stock information: {e}")
            validation_result = DataValidationResult.create_for_entity(
                entity_type="stockinfo",
                entity_identifier="validation_check"
            )
            validation_result.add_error(f"Validation exception: {str(e)}")
            return ServiceResult.failure(
                message=f"Failed to validate stock information: {str(e)}",
                data=validation_result
            )

    @time_logger
    def check_integrity(self, *args, **kwargs) -> ServiceResult:
        """
        Checks data integrity of stock information following BarService standard.

        Returns:
            ServiceResult containing DataIntegrityCheckResult
        """
        try:
            # Get data to check
            model_list = self._crud_repo.find(*args, **kwargs)

            integrity_result = DataIntegrityCheckResult.create_for_entity(
                entity_type="stockinfo",
                entity_identifier="integrity_check",
                check_range=(datetime.now(), datetime.now())
            )

            if not model_list or len(model_list) == 0:
                integrity_result.add_issue("no_data", "No stock info data available for integrity check")
                return ServiceResult.success(
                    data=integrity_result,
                    message="No stock info data available for integrity check"
                )

            # Perform integrity checks
            df = model_list.to_dataframe()
            total_records = len(df)

            # Check for duplicate codes
            if 'code' in df.columns:
                duplicate_codes = df['code'].duplicated().sum()
                if duplicate_codes > 0:
                    integrity_result.add_issue("duplicate_codes", f"Found {duplicate_codes} duplicate stock codes")

            # Check data consistency
            missing_codes = df['code'].isna().sum() if 'code' in df.columns else total_records
            if missing_codes > 0:
                integrity_result.add_issue("missing_codes", f"Found {missing_codes} records with missing codes")

            missing_names = df['name'].isna().sum() if 'name' in df.columns else total_records
            if missing_names > 0:
                integrity_result.add_issue("missing_names", f"Found {missing_names} records with missing names")

            # Calculate integrity score
            issues_count = len(integrity_result.integrity_issues)
            integrity_score = max(0, 100 - (issues_count / total_records * 100)) if total_records > 0 else 0

            integrity_result.set_metadata("total_records", total_records)
            integrity_result.set_metadata("integrity_score", integrity_score)
            integrity_result.set_metadata("issues_count", issues_count)

            # Set overall health status
            integrity_result.set_metadata("is_healthy", integrity_score >= 90)

            if integrity_score >= 90:
                message = f"Stock info data integrity check passed: {integrity_score:.1f}% score"
            else:
                message = f"Stock info data integrity issues found: {integrity_score:.1f}% score"

            return ServiceResult.success(
                data=integrity_result,
                message=message
            )

        except Exception as e:
            self._logger.ERROR(f"Failed to check stock info integrity: {e}")
            integrity_result = DataIntegrityCheckResult.create_for_entity(
                entity_type="stockinfo",
                entity_identifier="integrity_check",
                check_range=(datetime.now(), datetime.now())
            )
            integrity_result.add_issue("check_exception", str(e))
            return ServiceResult.failure(
                message=f"Failed to check stock info integrity: {str(e)}",
                data=integrity_result
            )

    def exists(self, code: str) -> ServiceResult:
        """
        Check if a stock code exists in the stock list.

        Args:
            code: Stock code to check (e.g., '000001.SZ')

        Returns:
            ServiceResult containing existence check result
        """
        try:
            records = self._crud_repo.find(filters={"code": code}, page_size=1)
            exists = len(records) > 0
            return ServiceResult.success(
                data=exists,  # 直接封装bool值
                message=f"Stock code {code} exists: {exists}"
            )
        except Exception as e:
            self._logger.ERROR(f"Failed to check if code {code} exists: {e}")
            return ServiceResult.error(f"Failed to check if code {code} exists: {str(e)}")

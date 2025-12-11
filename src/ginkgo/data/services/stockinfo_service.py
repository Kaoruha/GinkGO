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
        Initialize stock information service following BarService pattern.

        Args:
            crud_repo: Database CRUD operation repository
            data_source: Stock information data source
            **additional_deps: Additional dependencies
        """
        super().__init__(crud_repo=crud_repo, data_source=data_source, **additional_deps)

    # 注意：add、update、delete方法已移除，股票信息通过sync_all方法批量更新

    def health_check(self) -> ServiceResult:
        """
        Perform service health check, verifying data source and database connection status.

        Returns:
            ServiceResult: Health status and dependency check results
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
        Sync all stock basic information data from data source to database.

        Uses fault-tolerant mechanism where individual stock sync failures won't affect others.

        Returns:
            ServiceResult: Sync result with processing statistics and error details
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

        # Parse and validate all data first
        valid_items = []
        failed_count = 0
        failed_records = []

        self._logger.INFO(f"Processing {len(raw_data)} stock records for sync...")

        # Step 1: Convert all rows to dict format with error tolerance
        for _, row in raw_data.iterrows():
            try:
                item = mappers.row_to_stockinfo_upsert_dict(row)
                valid_items.append(item)
            except Exception as e:
                # Skip this record if mapping fails
                failed_count += 1
                code = row.get("ts_code", "Unknown")
                code_name = row.get("name", "Unknown")
                error_msg = f"Failed to map stock info for {code}: {e}"
                failed_records.append({"code": code, "code_name": code_name, "error": str(e)})
                self._logger.ERROR(error_msg)

        if not valid_items:
            sync_result.records_processed = len(raw_data)
            sync_result.records_added = 0
            sync_result.records_failed = failed_count
            sync_result.sync_duration = time.time() - start_time
            return ServiceResult.failure(
                message="No valid stock info records to process",
                data=sync_result
            )

        self._logger.INFO(f"Successfully parsed {len(valid_items)} records, {failed_count} failed mapping")

        # Step 2: Check existing records in batch
        all_codes = [item["code"] for item in valid_items]
        try:
            # Get all existing codes in one query
            existing_records = self._crud_repo.find(filters={"code__in": all_codes})
            existing_codes = set()
            for record in existing_records:
                if hasattr(record, 'code'):
                    existing_codes.add(record.code)

            self._logger.INFO(f"Found {len(existing_codes)} existing records out of {len(all_codes)} total codes")

        except Exception as e:
            self._logger.WARN(f"Failed to check existing codes, treating all as new: {e}")
            existing_codes = set()

        # Step 3: Separate new and update items
        new_items = []
        update_items = []

        for item in valid_items:
            code = item["code"]
            if code in existing_codes:
                update_items.append(item)
            else:
                new_items.append(item)

        self._logger.INFO(f"New records: {len(new_items)}, Update records: {len(update_items)}")

        # Step 4: Batch process new items
        success_count = 0
        with RichProgress() as progress:
            # Process new items in batch
            if new_items:
                task_new = progress.add_task("[green]Adding New Stock Info", total=len(new_items))
                try:
                    self._crud_repo.add_batch(new_items)
                    success_count += len(new_items)
                    self._logger.INFO(f"Successfully batch inserted {len(new_items)} new stock records")
                    progress.update(task_new, completed=len(new_items))
                except Exception as e:
                    # Fallback to individual inserts if batch fails
                    self._logger.WARN(f"Batch insert failed, falling back to individual inserts: {e}")
                    for item in new_items:
                        try:
                            self._crud_repo.create(**item)
                            success_count += 1
                            progress.update(task_new, advance=1)
                        except Exception as individual_e:
                            failed_count += 1
                            code = item.get("code", "Unknown")
                            code_name = item.get("code_name", "Unknown")
                            error_msg = f"Failed to insert {code}: {individual_e}"
                            failed_records.append({"code": code, "code_name": code_name, "error": str(individual_e)})
                            progress.update(task_new, advance=1)

            # Process update items individually (for now, as modify is needed)
            if update_items:
                task_update = progress.add_task("[blue]Updating Stock Info", total=len(update_items))
                for item in update_items:
                    try:
                        code = item["code"]
                        code_name = item.get("code_name", "Unknown")
                        self._crud_repo.modify(filters={"code": code}, updates=item)
                        success_count += 1
                        progress.update(task_update, advance=1)
                        self._logger.DEBUG(f"Successfully updated stock info for {code}")
                    except Exception as e:
                        failed_count += 1
                        code = item.get("code", "Unknown")
                        code_name = item.get("code_name", "Unknown")
                        error_msg = f"Failed to update {code}: {e}"
                        failed_records.append({"code": code, "code_name": code_name, "error": str(e)})
                        progress.update(task_update, advance=1)

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

    
    @time_logger
    def get(self, code: str = None, name: str = None, exchange: str = None,
            industry: str = None, market: str = None, status: str = None,
            limit: int = None, offset: int = None, order_by: str = None,
            desc_order: bool = False) -> ServiceResult:
        """
        Query stock basic information with specific filter conditions.

        Args:
            code: Stock code or code list
            name: Stock name or name fragment
            exchange: Exchange code
            industry: Industry classification
            market: Market type
            status: Listing status
            limit: Query result count limit
            offset: Pagination offset
            order_by: Sort field
            desc_order: Whether to sort in descending order

        Returns:
            ServiceResult: Query result with ModelList object and statistics

        Note:
            Returned ModelList object supports to_entities() and to_dataframe() conversion methods
        """
        try:
            # Build filters from specific parameters
            filters = {}
            if code is not None:
                filters['code'] = code
            if name is not None:
                filters['name__contains'] = name
            if exchange is not None:
                filters['exchange'] = exchange
            if industry is not None:
                filters['industry'] = industry
            if market is not None:
                filters['market'] = market
            if status is not None:
                filters['status'] = status

            # Handle pagination and sorting
            query_params = {}
            if limit is not None:
                query_params['limit'] = limit
            if offset is not None:
                query_params['offset'] = offset
            if order_by is not None:
                query_params['order_by'] = order_by
                query_params['desc_order'] = desc_order

            # Use CRUD repository to get data
            model_list = self._crud_repo.find(filters=filters, **query_params)

            return ServiceResult.success(
                data=model_list,
                message=f"Successfully retrieved {len(model_list) if model_list else 0} stock records"
            )

        except Exception as e:
            self._logger.ERROR(f"Failed to get stock information: {e}")
            return ServiceResult.failure(
                message=f"Failed to get stock information: {str(e)}"
            )

    @time_logger
    def count(self, code: str = None, name: str = None, exchange: str = None,
              industry: str = None, market: str = None, status: str = None) -> ServiceResult:
        """
        Count stock information records with specific filter conditions.

        Args:
            code: Stock code or code list
            name: Stock name or name fragment
            exchange: Exchange code
            industry: Industry classification
            market: Market type
            status: Listing status

        Returns:
            ServiceResult: Result containing count statistics
        """
        try:
            # Build filters from specific parameters
            filters = {}
            if code is not None:
                filters['code'] = code
            if name is not None:
                filters['name__contains'] = name
            if exchange is not None:
                filters['exchange'] = exchange
            if industry is not None:
                filters['industry'] = industry
            if market is not None:
                filters['market'] = market
            if status is not None:
                filters['status'] = status

            # Use CRUD repository to count data
            model_list = self._crud_repo.find(filters=filters)
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
        Validate stock information data quality, checking required fields and data integrity.

        Args:
            *args, **kwargs: Filter conditions for data validation

        Returns:
            ServiceResult: Validation result containing DataValidationResult
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
        Check stock information data integrity, finding duplicate records and missing fields.

        Args:
            *args, **kwargs: Filter conditions for data integrity check

        Returns:
            ServiceResult: Check result containing DataIntegrityCheckResult
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
        Check if stock code exists in stock list.

        Args:
            code: Stock code, e.g., '000001.SZ'

        Returns:
            ServiceResult: Boolean existence check result
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

# Upstream: BarService (K线复权计算使用)、Data Sync Commands (ginkgo data update adjustfactor)
# Downstream: BaseService (继承提供服务基础能力@time_logger/@retry/@cache)、AdjustfactorCRUD (复权因子CRUD操作)、Data Sources (Tushare/其他数据源)、StockinfoService (股票信息验证)
# Role: AdjustfactorService复权因子数据业务服务协调数据源和CRUD操作提供同步/获取/统计/验证等方法






"""
Adjustfactor Data Service (扁平化架构)

This service, implemented as a class, handles the business logic for
synchronizing adjustment factor data. It relies on dependency injection
for its data source and CRUD repository, and manages transactions.

Enhanced with comprehensive error handling, retry mechanisms, and structured returns.
"""

import time
from datetime import datetime, timedelta
from typing import List, Union, Any, Dict
import pandas as pd

from ginkgo.libs import GCONF, datetime_normalize, cache_with_expiration, to_decimal
from ginkgo.libs.data.results import DataValidationResult, DataIntegrityCheckResult, DataSyncResult
from ginkgo.data import mappers
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.crud.model_conversion import ModelList


class AdjustfactorService(BaseService):
    def __init__(self, crud_repo, data_source, stockinfo_service):
        """Initializes the service with its dependencies."""
        super().__init__(crud_repo=crud_repo, data_source=data_source, stockinfo_service=stockinfo_service)

    def sync(self, code: str, start_date: datetime = None, end_date: datetime = None, fast_mode: bool = True) -> ServiceResult:
        """
        Sync adjustment factor data for a single stock code, supporting incremental and full sync.

        Args:
            code (str): Stock code, format like '000001.SZ'
            start_date (datetime, optional): Sync start time, auto-determined if empty
            end_date (datetime, optional): Sync end time, current time if empty
            fast_mode (bool): Fast mode, sync from latest data if True, default True

        Returns:
            ServiceResult: Sync result with detailed statistics and error handling
        """
        start_time = time.time()

        try:
            # Validate stock code
            if not self._stockinfo_service.exists(code):
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="adjustfactors",
                    entity_identifier=code,
                    sync_strategy="single"
                )
                sync_result.add_error(0, f"Stock code {code} not in stock list")
                return ServiceResult(success=False,
                                   message=f"Stock code {code} not in stock list",
                                   data=sync_result)

            # Set date range
            if start_date is None or end_date is None:
                start_date = self._get_fetch_start_date(code, fast_mode)
                end_date = datetime.now()
            else:
                start_date = datetime_normalize(start_date)
                end_date = datetime_normalize(end_date)

            self._logger.INFO(f"Syncing adjustfactors for {code} from {start_date.date()} to {end_date.date()}")

            # Fetch data with retry mechanism
            try:
                raw_data = self._fetch_adjustfactor_data(code, start_date, end_date)
            except Exception as e:
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="adjustfactors",
                    entity_identifier=code,
                    sync_range=(start_date, end_date),
                    sync_strategy="single"
                )
                sync_result.add_error(0, f"Failed to fetch data from source: {e}")
                return ServiceResult(success=False,
                                   message=f"Failed to fetch data from source: {e}",
                                   data=sync_result)

            if raw_data is None or raw_data.empty:
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="adjustfactors",
                    entity_identifier=code,
                    sync_range=(start_date, end_date),
                    sync_strategy="single"
                )
                sync_result.set_metadata("fast_mode", fast_mode)
                sync_result.add_warning("No new data available from source")
                return ServiceResult(success=True,
                                   message=f"No new adjustfactor data available for {code}",
                                   data=sync_result)

            # Convert to models
            try:
                adjustfactor_models = mappers.dataframe_to_adjustfactor_models(raw_data, code)
            except Exception as e:
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="adjustfactors",
                    entity_identifier=code,
                    sync_range=(start_date, end_date),
                    sync_strategy="single"
                )
                sync_result.records_failed = len(raw_data)
                sync_result.add_error(0, f"Failed to convert data to models: {e}")
                return ServiceResult(success=False,
                                   message=f"Failed to convert data to models: {e}",
                                   data=sync_result)

            # Process models with existing data check
            records_processed = len(adjustfactor_models)
            records_added = 0
            records_updated = 0
            records_skipped = 0
            errors = []

            for i, model in enumerate(adjustfactor_models):
                try:
                    # Check if record exists. 真实模型唯一键为 (code, timestamp)，
                    # 不存在 adjust_type 维度（前/后复权是同一行的不同列）。
                    existing_filters = {
                        'code': model.code,
                        'timestamp': model.timestamp,
                    }

                    if self._crud_repo and self._crud_repo.exists(filters=existing_filters):
                        # Update existing record
                        if self._crud_repo and hasattr(self._crud_repo, 'update'):
                            self._crud_repo.update(filters=existing_filters, updates=model.to_dict())
                            records_updated += 1
                        else:
                            records_skipped += 1
                    else:
                        # Add new record
                        if self._crud_repo:
                            self._crud_repo.add(model)
                            records_added += 1

                except Exception as e:
                    errors.append((i, str(e)))

            # Create sync result
            sync_result = DataSyncResult.create_for_entity(
                entity_type="adjustfactors",
                entity_identifier=code,
                sync_range=(start_date, end_date),
                sync_strategy="single"
            )
            sync_result.records_processed = records_processed
            sync_result.records_added = records_added
            sync_result.records_updated = records_updated
            sync_result.records_skipped = records_skipped
            sync_result.records_failed = len(errors)
            sync_result.sync_duration = time.time() - start_time
            sync_result.is_idempotent = True
            sync_result.set_metadata("fast_mode", fast_mode)

            for error in errors:
                sync_result.add_error(error[0], error[1])

            # Determine success
            success = sync_result.records_failed == 0 and (sync_result.records_added > 0 or sync_result.records_updated > 0)
            message = f"Adjustfactor sync for {code}: {records_added} added, {records_updated} updated, {records_skipped} skipped, {len(errors)} failed"

            return ServiceResult(success=success, message=message, data=sync_result)

        except Exception as e:
            sync_result = DataSyncResult.create_for_entity(
                entity_type="adjustfactors",
                entity_identifier=code,
                sync_range=(start_date, end_date) if start_date and end_date else (None, None),
                sync_strategy="single"
            )
            sync_result.records_failed = 1
            sync_result.sync_duration = time.time() - start_time
            sync_result.add_error(0, f"Unexpected error: {e}")
            return ServiceResult(success=False,
                               message=f"Unexpected error during adjustfactor sync: {e}",
                               data=sync_result)

    def _get_fetch_start_date(self, code: str, fast_mode: bool) -> datetime:
        """
        Get data sync start date, supporting fast mode sync from latest data.

        Args:
            code: Stock code
            fast_mode: Whether to use fast mode starting from latest data

        Returns:
            datetime: Calculated sync start date
        """
        if fast_mode and self._crud_repo:
            # Get latest record for the code
            latest_filters = {'code': code}
            try:
                latest_records = self._crud_repo.find(
                    filters=latest_filters,
                    order_by='timestamp',
                    desc_order=True,
                    page_size=1
                )
                if latest_records:
                    return latest_records[0].timestamp
            except Exception:
                pass  # Fall back to default

        # Default to 1 year ago
        return datetime.now() - timedelta(days=365)

    def _fetch_adjustfactor_data(self, code: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        从数据源获取指定时间范围的复权因子数据。

        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            pd.DataFrame: 包含复权因子数据
        """
        # 数据源方法名不统一：Tushare 暴露 fetch_cn_stock_adjustfactor，tdx 暴露 fetch_adjustfactor。
        # 按优先级探测首个可用方法。#5909 根因A：旧代码探测不存在的 get_adjustfactor_data，
        # 而真实源只有 fetch_cn_stock_adjustfactor → 永远 NotImplementedError → 永远落不了库。
        for method_name in ("fetch_cn_stock_adjustfactor", "fetch_adjustfactor", "get_adjustfactor_data"):
            method = getattr(self._data_source, method_name, None)
            if method is None:
                continue
            return method(code, start_date, end_date)
        raise NotImplementedError("Adjustfactor data source not implemented")


    def get(self, code: str = None, start_date: datetime = None, end_date: datetime = None,
            adjust_type: str = None, limit: int = None,
            page: int = None, page_size: int = None) -> ServiceResult:
        """
        Query adjustment factor data with stock code, time range and adjustment type filtering.

        Args:
            code (str, optional): Stock code, format like '000001.SZ', empty for all stocks
            start_date (datetime, optional): Start time, query factors after this time
            end_date (datetime, optional): End time, query factors before this time
            adjust_type (str, optional): Adjustment type filter ('fore', 'back', 'original', etc.)
            limit (int, optional): Maximum number of records to return
            page (int, optional): Page number (0-based) for server-side pagination
            page_size (int, optional): Items per page for server-side pagination

        Returns:
            ServiceResult: Query result with adjustment factor data list
        """
        try:
            filters = {}
            if code:
                filters['code'] = code
            if start_date:
                filters['timestamp__gte'] = start_date
            if end_date:
                filters['timestamp__lte'] = end_date
            if adjust_type:
                filters['adjust_type'] = adjust_type

            if self._crud_repo:
                find_kwargs = {}
                if page is not None:
                    find_kwargs['page'] = page
                if page_size is not None:
                    find_kwargs['page_size'] = page_size
                adjustfactor_data = self._crud_repo.find(filters=filters, **find_kwargs)

                # Compute total count when paginating
                total = None
                if page is not None and page_size is not None:
                    total = self._crud_repo.count(filters=filters)

                return ServiceResult(success=True,
                                   message=f"Retrieved {len(adjustfactor_data)} adjustfactor records",
                                   data={"data": adjustfactor_data, "total": total} if total is not None else adjustfactor_data)
            else:
                return ServiceResult(success=False,
                                   message="CRUD repository not available",
                                   data=[])

        except Exception as e:
            return ServiceResult(success=False,
                               message=f"Failed to get adjustfactor data: {e}",
                               data=[])

    def count(self, code: str = None, adjust_type: str = None, start_date: datetime = None,
              end_date: datetime = None) -> ServiceResult:
        """Count adjustfactor records with optional filtering.

        Args:
            code (str, optional): Stock code to count records for
            adjust_type (str, optional): Filter by adjustment type
            start_date (datetime, optional): Count records after this date
            end_date (datetime, optional): Count records before this date
        """
        try:
            filters = {}
            if code:
                filters['code'] = code
            if adjust_type:
                filters['adjust_type'] = adjust_type
            if start_date:
                filters['timestamp__gte'] = start_date
            if end_date:
                filters['timestamp__lte'] = end_date

            if self._crud_repo:
                count = self._crud_repo.count(filters=filters)
                return ServiceResult(success=True,
                                   message=f"Count of adjustfactor records: {count}",
                                   data=count)
            else:
                return ServiceResult(success=False,
                                   message="CRUD repository not available",
                                   data=0)

        except Exception as e:
            return ServiceResult(success=False,
                               message=f"Failed to count adjustfactor data: {e}",
                               data=0)

    def validate(self, adjustfactor_data: Union[List[Any], pd.DataFrame, ModelList]) -> ServiceResult:
        """
        Validate adjustment factor data integrity and correctness, checking required fields and data quality.

        Args:
            adjustfactor_data: Adjustment factor data, supports multiple formats

        Returns:
            ServiceResult: Validation result with data quality report
        """
        try:
            validation_result = DataValidationResult(
                is_valid=True,
                error_count=0,
                warning_count=0,
                validation_timestamp=datetime.now(),
                validation_type="adjustfactor_data",
                entity_type="adjustfactor",
                entity_identifier="batch"
            )

            # Convert to DataFrame if needed
            if isinstance(adjustfactor_data, list):
                df = pd.DataFrame([{
                    'code': a.code,
                    'timestamp': a.timestamp,
                    'adjust_type': a.adjust_type,
                    'adjust_factor': float(a.adjust_factor),
                    'before_price': float(a.before_price),
                    'after_price': float(a.after_price),
                    'dividend': float(a.dividend),
                    'split_ratio': float(a.split_ratio)
                } for a in adjustfactor_data])
            elif hasattr(adjustfactor_data, 'to_dataframe'):
                df = adjustfactor_data.to_dataframe()
            else:
                df = adjustfactor_data

            # Basic validations
            if df.empty:
                validation_result.is_valid = False
                validation_result.add_error("No adjustfactor data provided")
                validation_result.error_count = 1
                return ServiceResult(success=False, data=validation_result)

            # Check required fields
            required_fields = ['code', 'timestamp', 'adjust_type', 'adjust_factor']
            missing_fields = [field for field in required_fields if field not in df.columns]
            if missing_fields:
                validation_result.is_valid = False
                validation_result.add_error(f"Missing required fields: {missing_fields}")
                validation_result.error_count += 1

            # Check data quality
            invalid_adjust_factors = df[df['adjust_factor'] <= 0]
            if not invalid_adjust_factors.empty:
                validation_result.add_warning(f"Found {len(invalid_adjust_factors)} records with non-positive adjust factors")
                validation_result.warning_count += len(invalid_adjust_factors)

            invalid_split_ratios = df[df['split_ratio'] <= 0]
            if not invalid_split_ratios.empty:
                validation_result.add_warning(f"Found {len(invalid_split_ratios)} records with non-positive split ratios")
                validation_result.warning_count += len(invalid_split_ratios)

            validation_result.data_quality_score = 100.0 - (validation_result.warning_count * 5.0)

            return ServiceResult(success=True, data=validation_result)

        except Exception as e:
            return ServiceResult(success=False,
                               message=f"Failed to validate adjustfactor data: {e}",
                               data=None)

    def check_integrity(self, code: str, start_date: datetime, end_date: datetime) -> ServiceResult:
        """
        Check adjustment factor data integrity in specified time range, verifying duplicate records and data gaps.

        Args:
            code: Stock code
            start_date: Start date
            end_date: End date

        Returns:
            ServiceResult: Report containing integrity check results
        """
        try:
            # Get adjustfactor data for the range
            result = self.get(code=code, start_date=start_date, end_date=end_date)

            if not result.success:
                return ServiceResult(success=False,
                                   message=f"Failed to retrieve data for integrity check: {result.error}",
                                   data=None)

            adjustfactor_data = result.data

            integrity_result = DataIntegrityCheckResult(
                entity_type="adjustfactor",
                entity_identifier=code,
                check_range=(start_date, end_date),
                total_records=len(adjustfactor_data),
                missing_records=0,
                duplicate_records=0,
                integrity_score=100.0,
                check_duration=0.0
            )

            # Check for data gaps
            if len(adjustfactor_data) == 0:
                integrity_result.integrity_score = 0.0
                integrity_result.add_issue("no_data", "No adjustfactor data found in the specified range")

            # Check for duplicates based on timestamp and adjust_type
            if hasattr(adjustfactor_data, '__len__') and len(adjustfactor_data) > 0:
                unique_keys = set()
                duplicates = 0
                for record in adjustfactor_data:
                    if hasattr(record, 'timestamp') and hasattr(record, 'adjust_type'):
                        key = (record.timestamp, record.adjust_type)
                        if key in unique_keys:
                            duplicates += 1
                        else:
                            unique_keys.add(key)

                if duplicates > 0:
                    integrity_result.duplicate_records = duplicates
                    integrity_result.integrity_score -= duplicates * 20
                    integrity_result.add_issue("duplicate_records", f"Found {duplicates} duplicate adjustfactor records")

            return ServiceResult(success=True, data=integrity_result)

        except Exception as e:
            return ServiceResult(success=False,
                               message=f"Failed to check adjustfactor data integrity: {e}",
                               data=None)

    def sync_batch(self, codes: List[str], start_date: datetime = None, end_date: datetime = None, fast_mode: bool = True) -> ServiceResult:
        """
        Batch sync adjustment factor data for multiple stocks with parallel processing and detailed statistics.

        Args:
            codes: List of stock codes
            start_date: Sync start date (optional)
            end_date: Sync end date (optional)
            fast_mode: Fast mode, sync from latest data if True, default True

        Returns:
            ServiceResult: Detailed information containing all sync result lists
        """
        start_time = time.time()
        sync_results = []

        # 处理None参数
        if codes is None:
            codes = []

        total_codes = len(codes)

        self._logger.INFO(f"Starting batch adjustfactor sync for {total_codes} codes")

        for i, code in enumerate(codes):
            try:
                result = self.sync(code=code, start_date=start_date, end_date=end_date, fast_mode=fast_mode)
                # 始终收集 DataSyncResult（result.data 即是），让失败 code 的 records_failed
                # 也进入统计；旧代码失败时收集的是 ServiceResult 本身，无 records_* 属性 → 被求和忽略。
                sync_results.append(result.data if result.data is not None else result)
            except Exception as e:
                error_result = DataSyncResult.create_for_entity(
                    entity_type="adjustfactors",
                    entity_identifier=code,
                    sync_range=(start_date, end_date),
                    sync_strategy="batch"
                )
                error_result.records_failed = 1
                error_result.add_error(0, f"Batch sync failed: {e}")
                sync_results.append(error_result)

        # Calculate batch statistics
        total_records_processed = sum(r.records_processed for r in sync_results if hasattr(r, 'records_processed'))
        total_records_added = sum(r.records_added for r in sync_results if hasattr(r, 'records_added'))
        total_records_updated = sum(r.records_updated for r in sync_results if hasattr(r, 'records_updated'))
        total_records_failed = sum(r.records_failed for r in sync_results if hasattr(r, 'records_failed'))

        # #5909 根因B：旧代码无条件 success=True，吞掉全部逐 code 失败 → handler 误报 200。
        # 诚实规则：请求了 code 却一条都没落库（added+updated==0）即视为失败，
        # 让 handler/history 诚实报错；空 code 列表不算错误。
        any_persisted = (total_records_added + total_records_updated) > 0
        batch_success = (total_codes == 0) or any_persisted
        if batch_success:
            message = f"Batch adjustfactor sync completed: {total_records_added} added, {total_records_updated} updated, {total_records_failed} failed"
        else:
            message = f"Batch adjustfactor sync failed: 0 records persisted across {total_codes} codes ({total_records_failed} failed)"

        batch_result = ServiceResult(
            success=batch_success,
            message=message,
            data=sync_results
        )
        batch_result.set_metadata("total_codes", total_codes)
        batch_result.set_metadata("total_records_processed", total_records_processed)
        batch_result.set_metadata("total_records_added", total_records_added)
        batch_result.set_metadata("total_records_failed", total_records_failed)
        batch_result.set_metadata("batch_duration", time.time() - start_time)

        return batch_result

    def calculate(self, code: str) -> ServiceResult:
        """
        Calculate fore and back adjustment factors for a single stock using DataFrame vectorized computation.

        Args:
            code (str): Stock code to process, format like '000001.SZ'

        Returns:
            ServiceResult: Calculation result with processing statistics and backup status
        """
        start_time = time.time()

        # 备份信息
        backup_info = None
        original_records = []

        try:
            # 第一步：验证股票代码
            if not code:
                return ServiceResult(success=False, message="股票代码不能为空")

            # 第二步：获取并备份原始数据
            if not self._crud_repo:
                return ServiceResult(success=False, message="CRUD repository not available")

            original_records = self._crud_repo.find(filters={"code": code})

            if len(original_records) < 2:
                return ServiceResult(
                    success=True,
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
            if hasattr(original_records, 'to_dataframe'):
                df_records = original_records.to_dataframe()
            else:
                # 手动转换为DataFrame
                df_records = pd.DataFrame([{
                    'uuid': r.uuid,
                    'code': r.code,
                    'timestamp': r.timestamp,
                    'adjustfactor': float(r.adjust_factor) if hasattr(r, 'adjust_factor') else float(r.adjustfactor),
                    'before_price': float(r.before_price) if hasattr(r, 'before_price') else 0.0,
                    'after_price': float(r.after_price) if hasattr(r, 'after_price') else 0.0,
                    'dividend': float(r.dividend) if hasattr(r, 'dividend') else 0.0,
                    'split_ratio': float(r.split_ratio) if hasattr(r, 'split_ratio') else 1.0,
                    'adjust_type': getattr(r, 'adjust_type', 'fore')
                } for r in original_records])

            df_records = df_records.sort_values('timestamp').reset_index(drop=True)

            # 检查必要的字段
            if 'adjustfactor' not in df_records.columns and 'adjust_factor' not in df_records.columns:
                # 使用adjust_factor字段
                factor_col = 'adjust_factor'
            else:
                factor_col = 'adjustfactor'

            if factor_col not in df_records.columns:
                return ServiceResult(success=False, message=f"股票 {code} 数据缺少adjustfactor字段")

            # 一次性处理adjustfactor列：转换类型 + 处理0值 + 统计
            df_records[factor_col] = pd.to_numeric(df_records[factor_col], errors='coerce').fillna(1.0)
            zero_mask = df_records[factor_col] == 0
            zero_count = zero_mask.sum()
            if zero_count > 0:
                self._logger.WARN(f"股票 {code} 发现 {zero_count} 条记录的adjustfactor为0，将替换为1.0")
                df_records.loc[zero_mask, factor_col] = 1.0

            # 使用DataFrame向量化计算复权系数
            original_factors = df_records[factor_col].values

            # 验证原始因子数据
            if len(original_factors) == 0 or all(f == 1.0 for f in original_factors):
                self._logger.WARN(f"股票 {code} 的adjustfactor值全为1.0，计算结果可能与原始数据相同")

            # 计算前复权系数：相对于最新时间的系数
            latest_factor = original_factors[-1]
            fore_factors = latest_factor / original_factors

            # 计算后复权系数：相对于最早时间的系数
            earliest_factor = original_factors[0]
            back_factors = original_factors / earliest_factor

            # 更新DataFrame中的复权因子列
            df_records['foreadjustfactor'] = fore_factors
            df_records['backadjustfactor'] = back_factors

            # 详细的统计日志
            self._logger.INFO(
                f"股票 {code} 复权因子计算完成 | "
                f"记录数: {len(df_records)} | "
                f"前复权范围: {fore_factors.min():.6f}-{fore_factors.max():.6f} | "
                f"后复权范围: {back_factors.min():.6f}-{back_factors.max():.6f}"
            )

            # 第四步：更新数据库记录
            updated_count = 0
            errors = []

            for _, row in df_records.iterrows():
                try:
                    # 更新记录
                    update_data = {
                        'foreadjustfactor': to_decimal(row['foreadjustfactor']),
                        'backadjustfactor': to_decimal(row['backadjustfactor'])
                    }

                    filters = {
                        'uuid': row['uuid'],
                        'code': row['code'],
                        'timestamp': row['timestamp']
                    }

                    # 使用modify方法进行ClickHouse兼容的更新操作（内部使用replace）
                    try:
                        # 获取更新前的值
                        before_update = self._crud_repo.find(filters=filters)
                        if len(before_update) == 1:
                            # 使用modify方法（内部使用replace实现原子删除后插入）
                            modified_count = self._crud_repo.modify(filters=filters, updates=update_data)

                            # 只要modify操作成功执行，就计数为更新成功
                            if modified_count > 0:
                                updated_count += 1
                    except Exception as e:
                        errors.append((str(row.get('uuid', 'unknown')), str(e)))

                except Exception as e:
                    errors.append((str(row.get('uuid', 'unknown')), str(e)))

            # 创建计算结果
            calculate_result = {
                'code': code,
                'processed_records': len(df_records),
                'updated_records': updated_count,
                'error_count': len(errors),
                'fore_factor_range': [float(fore_factors.min()), float(fore_factors.max())],
                'back_factor_range': [float(back_factors.min()), float(back_factors.max())],
                'original_factor_range': [float(original_factors.min()), float(original_factors.max())],
                'backup_used': True,
                'calculation_duration': time.time() - start_time
            }

            if errors:
                calculate_result['errors'] = errors

            success = len(errors) == 0 and updated_count > 0
            message = f"股票 {code} 复权因子计算完成: {updated_count}/{len(df_records)} 条记录更新成功"

            return ServiceResult(success=success, message=message, data=calculate_result)

        except Exception as e:
            # 如果出错且备份信息存在，尝试恢复数据
            if backup_info and original_records:
                try:
                    self._logger.ERROR(f"计算股票 {code} 复权因子时出错，尝试恢复原始数据: {e}")

                    # 恢复原始数据
                    for record in original_records:
                        try:
                            if hasattr(self._crud_repo, 'update'):
                                # 移除计算字段，恢复原始状态
                                update_data = {
                                    'foreadjustfactor': None,
                                    'backadjustfactor': None
                                }
                                filters = {
                                    'uuid': record.uuid,
                                    'code': record.code,
                                    'timestamp': record.timestamp
                                }
                                self._crud_repo.update(filters=filters, updates=update_data)
                        except Exception as restore_error:
                            self._logger.ERROR(f"恢复记录 {record.uuid} 失败: {restore_error}")

                    self._logger.INFO(f"股票 {code} 原始数据恢复完成")

                    return ServiceResult(
                        success=False,
                        message=f"计算失败但数据已恢复: {e}",
                        data={"code": code, "backup_used": True, "error": str(e)}
                    )
                except Exception as restore_error:
                    self._logger.ERROR(f"恢复股票 {code} 数据失败: {restore_error}")

            # 如果没有备份或恢复失败，返回错误
            return ServiceResult(
                success=False,
                message=f"股票 {code} 复权因子计算失败: {e}",
                data={"code": code, "backup_used": backup_info is not None, "error": str(e)}
            )
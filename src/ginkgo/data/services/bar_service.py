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
from ginkgo.data import mappers
from ginkgo.enums import FREQUENCY_TYPES, ADJUSTMENT_TYPES
from ginkgo.data.services.base_service import DataService, ServiceResult
from ginkgo.data.crud.model_conversion import ModelList


class BarService(DataService):
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
        self.adjustfactor_service = adjustfactor_service

    @retry(max_try=3)
    def sync_for_code_with_date_range(
        self,
        code: str,
        start_date: datetime = None,
        end_date: datetime = None,
        frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY,
    ) -> ServiceResult:
        """
        Synchronizes bar data for a single stock code within specified date range.

        Args:
            code: Stock code (e.g., '000001.SZ')
            start_date: Start date for data sync (if None, determined by existing logic)
            end_date: End date for data sync (if None, defaults to today)
            frequency: Data frequency (currently only DAY supported)

        Returns:
            ServiceResult - 包装同步结果数据，使用result.data获取详细信息
        """
        start_time = time.time()
        self._log_operation_start("sync_for_code_with_date_range", code=code, start_date=start_date,
                                end_date=end_date, frequency=frequency.value)

        try:
            # Validate stock code
            if not self.stockinfo_service.is_code_in_stocklist(code):
                return ServiceResult.failure(
                    message=f"Stock code {code} not in stock list",
                    data={"code": code, "records_added": 0}
                )

            # Validate and set date range
            validated_start, validated_end = self._validate_and_set_date_range(start_date, end_date)

            self._logger.INFO(
                f"Syncing {frequency.value} bars for {code} from {validated_start.date()} to {validated_end.date()}"
            )

            # Fetch data with retry mechanism
            try:
                raw_data = self._fetch_raw_data(code, validated_start, validated_end, frequency)
                if raw_data is None or raw_data.empty:
                    return ServiceResult.success(
                        data={"code": code, "records_added": 0, "records_processed": 0, "date_range": f"{validated_start.date()} to {validated_end.date()}"},
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
                models_to_add = mappers.dataframe_to_bar_models(raw_data, code, frequency)
                if not models_to_add:
                    return ServiceResult.success(
                        data={"code": code, "records_added": 0, "records_processed": 0},
                        message="No valid models generated from data"
                    )
            except Exception as e:
                # Fallback: try row-by-row conversion
                self._logger.WARN(f"Batch conversion failed for {code}, attempting row-by-row: {e}")
                models_to_add = self._convert_rows_individually(raw_data, code, frequency)
                if not models_to_add:
                    return ServiceResult.failure(
                        message=f"Data mapping failed: {str(e)}",
                        data={"code": code, "records_added": 0, "records_processed": 0}
                    )

            # Smart duplicate checking and database operations
            final_models = self._filter_existing_data(models_to_add, code, frequency)

            if not final_models:
                return ServiceResult.success(
                    data={"code": code, "records_added": 0, "records_processed": len(raw_data)},
                    message="All data already exists in database"
                )

            # Use BaseCRUD.replace method for atomic operation
            if start_date is not None or end_date is not None:
                # For limited date range, replace data in that range
                min_date = min(item.timestamp for item in final_models)
                max_date = max(item.timestamp for item in final_models)
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

            replaced_models = self.crud_repo.replace(filters=filters, new_items=final_models)
            records_added = len(replaced_models)

            # If replace returned empty (no existing data), use add_batch instead
            if records_added == 0:
                inserted_models = self.crud_repo.add_batch(final_models)
                records_added = len(inserted_models)
                self._logger.INFO(f"Successfully inserted {records_added} new bar records for {code}")
                removed_count = 0
            else:
                self._logger.INFO(f"Successfully replaced {records_added} bar records for {code}")
                removed_count = len(replaced_models)  # All were replaced

            duration = time.time() - start_time
            self._log_operation_end("sync_for_code_with_date_range", True, duration)

            return ServiceResult.success(
                data={
                    "code": code,
                    "records_added": records_added,
                    "records_processed": len(raw_data),
                    "date_range": f"{validated_start.date()} to {validated_end.date()}",
                    "removed_count": removed_count
                },
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
    def sync_for_code(
        self, code: str, fast_mode: bool = True, frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY
    ) -> ServiceResult:
        """
        Synchronizes bar data for a single stock code with enhanced error handling.

        Args:
            code: Stock code (e.g., '000001.SZ')
            fast_mode: If True, only fetch data from last available date
            frequency: Data frequency (currently only DAY supported)

        Returns:
            ServiceResult - 包装同步结果，使用result.data获取详细信息
        """
        start_time = time.time()
        self._log_operation_start("sync_for_code", code=code, fast_mode=fast_mode, frequency=frequency.value)

        try:
            # Determine date range based on fast_mode
            start_date, end_date = self._get_fetch_date_range(code, fast_mode)

            # Call the new date range method
            sync_result = self.sync_for_code_with_date_range(code, start_date, end_date, frequency)

            # Convert dict result to ServiceResult
            duration = time.time() - start_time
            self._log_operation_end("sync_for_code", sync_result.success, duration)

            if sync_result.success:
                return ServiceResult.success(
                    data=sync_result.data,
                    message=f"Successfully synced {sync_result.data.get('records_added', 0)} bar records for {code}"
                )
            else:
                return ServiceResult.failure(
                    message=sync_result.error,
                    data=sync_result.data
                )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation_end("sync_for_code", False, duration)
            self._logger.ERROR(f"Failed to sync bar data for {code}: {e}")
            return ServiceResult.error(
                error=f"Sync operation failed: {str(e)}"
            )

    def sync_batch_codes_with_date_range(
        self,
        codes: List[str],
        start_date: datetime = None,
        end_date: datetime = None,
        frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY,
    ) -> ServiceResult:
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
                    batch_result["total_records_processed"] += result.data.get("records_processed", 0)
                    batch_result["total_records_added"] += result.data.get("records_added", 0)

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
        return ServiceResult.success(
            data=batch_result,
            message=f"Batch sync completed: {batch_result['successful_codes']}/{batch_result['total_codes']} successful"
        )

    def sync_batch_codes(
        self, codes: List[str], fast_mode: bool = True, frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY
    ) -> ServiceResult:
        """
        Synchronizes bar data for multiple stock codes with comprehensive error tracking.

        Args:
            codes: List of stock codes
            fast_mode: If True, only fetch data from last available date
            frequency: Data frequency

        Returns:
            ServiceResult containing batch sync results and statistics
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

            try:
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
                            batch_result["total_records_processed"] += result.data.get("records_processed", 0)
                            batch_result["total_records_added"] += result.data.get("records_added", 0)

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

                return ServiceResult.success(
                    data=batch_result,
                    message=f"Batch sync completed: {batch_result['successful_codes']}/{batch_result['total_codes']} successful"
                )

            except Exception as e:
                self._logger.ERROR(f"Batch sync failed: {str(e)}")
                return ServiceResult.error(f"Batch sync operation failed: {str(e)}")
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
        adjustment_type: ADJUSTMENT_TYPES = ADJUSTMENT_TYPES.FORE,
        page: int = None,
        page_size: int = None,
        order_by: str = "timestamp",
        desc_order: bool = False,
        *args,
        **kwargs,
    ) -> ServiceResult:
        """
        Retrieves bar data from the database with optional price adjustment.

        Args:
            code: Stock code filter
            start_date: Start date filter
            end_date: End date filter
            frequency: Data frequency filter
            adjustment_type: Price adjustment type (NONE/FORE/BACK)
            page: Page number (0-based)
            page_size: Number of items per page
            order_by: Field name to order by (default: timestamp)
            desc_order: Whether to use descending order (default: False)
            *args: Additional positional arguments (for future extension)
            **kwargs: Additional keyword arguments (for future extension)

        Returns:
            ServiceResult - 包装ModelList数据，使用result.data获取数据
                           data支持to_dataframe()和to_entities()方法
        """
        start_time = time.time()
        self._log_operation_start("get_bars", code=code, start_date=start_date,
                                end_date=end_date, frequency=frequency.value,
                                adjustment_type=adjustment_type.value)

        try:
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
            model_list = self.crud_repo.find(
                filters=filters,
                page=page,
                page_size=page_size,
                order_by=order_by,
                desc_order=desc_order,
                *args,
                **kwargs
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

            adjustfactors_df = self.adjustfactor_service.get_adjustfactors(
                code=code, start_date=start_date, end_date=end_date, as_dataframe=True
            )

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
            result = self.adjustfactor_service.get_adjustfactors(
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
            return ModelList([], self.crud_repo)

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

            return ModelList(bars, self.crud_repo)

        except Exception as e:
            self._logger.ERROR(f"Failed to convert DataFrame to ModelList: {e}")
            # 返回空ModelList
            from ginkgo.data.crud.model_conversion import ModelList
            return ModelList([], self.crud_repo)

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

    def get_latest_timestamp_for_code(self, code: str, frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY) -> ServiceResult:
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
            latest_records = self.crud_repo.find(
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

    def _get_fetch_date_range(self, code: str, fast_mode: bool) -> tuple:
        """Determines the date range for fetching data."""
        end_date = datetime.now()

        if not fast_mode:
            start_date = self._get_intelligent_start_date(code)
        else:
            latest_timestamp_result = self.get_latest_timestamp_for_code(code)
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

    def count_bars(self, code: str = None, frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY, **kwargs) -> ServiceResult:
        """
        Counts the number of bar records matching the filters.

        Args:
            code: Stock code filter
            frequency: Data frequency filter
            **kwargs: Additional filters

        Returns:
            ServiceResult - 包装计数结果，使用result.data获取数量
        """
        start_time = time.time()
        self._log_operation_start("count_bars", code=code, frequency=frequency.value)

        try:
            filters = kwargs.copy()
            if code:
                filters["code"] = code
            if frequency:
                filters["frequency"] = frequency

            count = self.crud_repo.count(filters=filters)
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
            codes = self.crud_repo.find(filters={"frequency": frequency}, distinct_field="code")

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

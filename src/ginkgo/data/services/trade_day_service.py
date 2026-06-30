# Upstream: DataWorker/CLI (调用 sync 同步交易日历)、PaperTradingWorker (查询 is_open 判断开市 #6488)
# Downstream: BaseService (继承提供标准服务能力)、TradeDayCRUD (MySQL trade_day 持久化)、GinkgoTushare (trade_cal 数据源)
# Role: TradeDayService 交易日历业务服务镜像 StockinfoService.sync 提供 calendar 同步




"""
TradeDay Data Service (Class-based)

This service handles the business logic for synchronizing the trading calendar.
Mirrors StockinfoService.sync —— 「加一种 data_type」对称扩展（#6488）。

paper worker _run_live_paper_cycle 通过 trade_day_crud.find(...).is_open 判断是否开市，
表空则整轮 skip 致 0 signal（#6488）。本服务接通 sync 链路：data_source → TradeDay → DB。
"""

import time

from ginkgo.libs import RichProgress, retry
from ginkgo.libs.data.results import DataSyncResult
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.entities import TradeDay
from ginkgo.enums import MARKET_TYPES, SOURCE_TYPES


class TradeDayService(BaseService):
    def __init__(self, crud_repo, data_source, **additional_deps):
        """
        Initialize trade calendar service following StockinfoService pattern.

        Args:
            crud_repo: Database CRUD operation repository
            data_source: Trade calendar data source (GinkgoTushare)
            **additional_deps: Additional dependencies
        """
        super().__init__(crud_repo=crud_repo, data_source=data_source, **additional_deps)

    @retry(max_try=3)
    def sync(self) -> ServiceResult:
        """
        Sync trading calendar from data source to database.

        Mirrors StockinfoService.sync. trade_cal 返回全量日历（含开市/休市），
        is_open 为 int 0/1，须 bool(int(...)) 双层转换以满足 TradeDay entity 的
        严格 isinstance(is_open, bool) 校验（numpy int64 直接 bool() 不可靠）。
        日历是权威全量覆盖，直接 add_batch，无需 new/update 分离。

        Returns:
            ServiceResult: Sync result with processing statistics
        """
        start_time = time.time()
        self._log_operation_start("sync")

        try:
            raw_data = self._data_source.fetch_cn_stock_trade_day()
            if raw_data is None or raw_data.empty:
                sync_result = DataSyncResult.create_for_entity(
                    entity_type="trade_day",
                    entity_identifier="all",
                    sync_strategy="full_sync",
                )
                sync_result.add_warning("No trade calendar data returned from source")
                self._logger.WARN("No trade calendar data returned from source.")
                return ServiceResult.failure(
                    data=sync_result,
                    message="No trade calendar data available from source - sync task failed",
                )
        except Exception as e:
            sync_result = DataSyncResult.create_for_entity(
                entity_type="trade_day",
                entity_identifier="all",
                sync_strategy="full_sync",
            )
            sync_result.add_error(0, f"Failed to fetch trade calendar from source: {str(e)}")
            duration = time.time() - start_time
            self._log_operation_end("sync", False, duration)
            return ServiceResult.failure(
                message=f"Failed to fetch trade calendar from source: {str(e)}",
                data=sync_result,
            )

        # Initialize sync result
        sync_result = DataSyncResult.create_for_entity(
            entity_type="trade_day",
            entity_identifier="all",
            sync_strategy="full_sync",
        )
        sync_result.set_metadata("initial_records", len(raw_data))

        valid_items = []
        failed_count = 0

        self._logger.INFO(f"Processing {len(raw_data)} trade calendar records for sync...")

        # Step 1: Convert all rows to TradeDay business objects with error tolerance
        for _, row in raw_data.iterrows():
            try:
                td = TradeDay(
                    market=MARKET_TYPES.CHINA,
                    is_open=bool(int(row["is_open"])),
                    timestamp=row["cal_date"],
                )
                # Store source information as attribute for CRUD layer
                td._source = SOURCE_TYPES.TUSHARE
                valid_items.append(td)
            except Exception as e:
                failed_count += 1
                cal_date = row.get("cal_date", "Unknown")
                self._logger.ERROR(f"Failed to create TradeDay for {cal_date}: {e}")

        if not valid_items:
            sync_result.records_processed = len(raw_data)
            sync_result.records_added = 0
            sync_result.records_failed = failed_count
            sync_result.sync_duration = time.time() - start_time
            return ServiceResult.failure(
                message="No valid trade calendar records to process",
                data=sync_result,
            )

        self._logger.INFO(f"Successfully parsed {len(valid_items)} records, {failed_count} failed mapping")

        # Step 2: Batch persist all trade calendar records
        success_count = 0
        with RichProgress() as progress:
            task = progress.add_task("[green]Syncing Trade Calendar", total=len(valid_items))
            try:
                self._crud_repo.add_batch(valid_items)
                success_count = len(valid_items)
                self._logger.INFO(f"Successfully batch inserted {len(valid_items)} trade calendar records")
                progress.update(task, completed=len(valid_items))
            except Exception as e:
                self._logger.WARN(f"Batch insert failed: {e}")
                failed_count += len(valid_items)

        # Update sync result statistics
        duration = time.time() - start_time
        sync_result.records_processed = len(raw_data)
        sync_result.records_added = success_count
        sync_result.records_failed = failed_count
        sync_result.sync_duration = duration
        sync_result.is_idempotent = True

        self._logger.INFO(
            f"Trade calendar sync completed: {success_count}/{len(raw_data)} successful, "
            f"{failed_count} failed"
        )

        self._log_operation_end("sync", True, duration)

        if failed_count == 0:
            return ServiceResult.success(
                data=sync_result,
                message=f"Trade calendar sync completed successfully: {success_count} records processed",
            )
        else:
            return ServiceResult.success(
                data=sync_result,
                message=f"Trade calendar sync completed with {failed_count} failures: {success_count} successful",
            )

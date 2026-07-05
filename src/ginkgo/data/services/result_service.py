# Upstream: CLI Commands (ginkgo results show)、Analysis Modules (回测结果分析)
# Downstream: BaseService (继承提供服务基础能力)、AnalyzerRecordCRUD (分析器记录CRUD操作)、MAnalyzerRecord (分析器记录模型)
# Role: ResultService回测结果查询和分析业务服务提供运行摘要/分析器值/记录/投资组合摘要等方法


"""
Result Service Module

提供回测结果查询和分析服务，支持按 task_id 查询 analyzer 指标数据。
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import pandas as pd

from ginkgo.data.crud.analyzer_record_crud import AnalyzerRecordCRUD
from ginkgo.data.models import MAnalyzerRecord
from ginkgo.libs import GLOG, retry, datetime_normalize
from ginkgo.data.services.base_service import ServiceResult, BaseService


class ResultService(BaseService):
    """
    Result Service Layer

    提供回测结果查询、聚合和统计分析功能：
    - 按 task_id 查询 analyzer 记录
    - 支持多 portfolio、多 analyzer 聚合
    - 提供 DataFrame 格式输出，支持绘图
    """

    def __init__(self, analyzer_crud: AnalyzerRecordCRUD):
        """
        初始化 ResultService

        Args:
            analyzer_crud: AnalyzerRecord 数据访问对象
        """
        super().__init__(crud_repo=analyzer_crud)
        self._crud_repo = analyzer_crud

    def get_run_summary(self, task_id: str) -> ServiceResult:
        """
        获取某次运行会话的摘要信息

        Args:
            task_id: 任务ID

        Returns:
            ServiceResult[Dict]: 包含 portfolios、analyzers、时间范围等摘要信息
        """
        try:
            if not task_id:
                return ServiceResult.error("task_id 不能为空")

            # 获取该 task_id 的所有记录
            records = self._crud_repo.get_by_task_id(task_id, page_size=10000)

            if not records:
                return ServiceResult.error(f"未找到 task_id={task_id} 的记录")

            # 聚合摘要信息
            portfolios = list(set(r.portfolio_id for r in records if r.portfolio_id))
            analyzers = list(set(r.name for r in records if r.name))

            # 时间范围
            timestamps = [r.timestamp for r in records if r.timestamp]
            time_range = {
                "start": min(timestamps) if timestamps else None,
                "end": max(timestamps) if timestamps else None,
            }

            summary = {
                "task_id": task_id,
                "engine_id": records[0].engine_id if records else None,
                "portfolio_count": len(portfolios),
                "portfolios": portfolios,
                "analyzer_count": len(analyzers),
                "analyzers": analyzers,
                "total_records": len(records),
                "time_range": time_range,
            }

            GLOG.INFO(f"获取 task_id={task_id} 的摘要信息成功")
            return ServiceResult.success(summary)

        except Exception as e:
            GLOG.ERROR(f"获取运行摘要失败: {e}")
            return ServiceResult.error(f"获取运行摘要失败: {e}")

    def get_analyzer_values(
        self, task_id: str, portfolio_id: Optional[str] = None, analyzer_name: Optional[str] = None
    ) -> ServiceResult:
        """
        获取 analyzer 指标值

        Args:
            task_id: 任务ID
            portfolio_id: 投资组合ID（可选）
            analyzer_name: 分析器名称（可选）

        Returns:
            ServiceResult[ModelList]: 可调用 to_dataframe() 转换为 DataFrame
        """
        try:
            if not task_id:
                return ServiceResult.error("task_id 不能为空")

            # 使用 CRUD 的 get_by_task_id 方法
            result = self._crud_repo.get_by_task_id(
                task_id=task_id, portfolio_id=portfolio_id, analyzer_name=analyzer_name, page_size=10000
            )

            GLOG.INFO(f"获取 task_id={task_id} 的 analyzer 值成功")
            return ServiceResult.success(result)

        except Exception as e:
            GLOG.ERROR(f"获取 analyzer 值失败: {e}")
            return ServiceResult.error(f"获取 analyzer 值失败: {e}")

    def get_analyzer_values_df(
        self, task_id: str, portfolio_id: Optional[str] = None, analyzer_name: Optional[str] = None
    ) -> ServiceResult:
        """出口①：data 是 pandas.DataFrame（类型即契约）。

        ADR-010：API/CLI 消费 DataFrame 语义时走此出口，不接触 ORM ModelList、
        不再绕 ``result.data.to_dataframe()``。内部 get_by_task_id 返 ModelList 后调
        ``to_dataframe()``；空结果返空 ``pd.DataFrame()``。

        filter 域与 get_analyzer_values() 一致（task_id / portfolio_id / analyzer_name）。
        """
        try:
            if not task_id:
                return ServiceResult.error("task_id 不能为空")

            result = self._crud_repo.get_by_task_id(
                task_id=task_id, portfolio_id=portfolio_id, analyzer_name=analyzer_name, page_size=10000
            )
            df = result.to_dataframe() if result else pd.DataFrame()

            GLOG.INFO(f"获取 task_id={task_id} 的 analyzer 值(df)成功")
            return ServiceResult.success(df)

        except Exception as e:
            GLOG.ERROR(f"获取 analyzer 值(df)失败: {e}")
            return ServiceResult.error(f"获取 analyzer 值(df)失败: {e}")

    def get_multi_analyzer_data(self, task_id: str, portfolio_id: str, analyzer_names: List[str]) -> ServiceResult:
        """
        获取多个 analyzer 的数据，用于对比绘图

        Args:
            task_id: 运行会话ID
            portfolio_id: 投资组合ID
            analyzer_names: 分析器名称列表

        Returns:
            ServiceResult[Dict[str, ModelList]]: analyzer_name -> ModelList 的映射
        """
        try:
            if not task_id or not portfolio_id:
                return ServiceResult.error("task_id 和 portfolio_id 不能为空")

            if not analyzer_names:
                return ServiceResult.error("analyzer_names 列表不能为空")

            data_map = {}
            for analyzer_name in analyzer_names:
                model_list = self._crud_repo.get_by_task_id(
                    task_id=task_id, portfolio_id=portfolio_id, analyzer_name=analyzer_name, page_size=10000
                )
                data_map[analyzer_name] = model_list

            GLOG.INFO(f"获取多 analyzer 数据成功: {list(data_map.keys())}")
            return ServiceResult.success(data_map)

        except Exception as e:
            GLOG.ERROR(f"获取多 analyzer 数据失败: {e}")
            return ServiceResult.error(f"获取多 analyzer 数据失败: {e}")

    def list_runs(
        self, engine_id: Optional[str] = None, portfolio_id: Optional[str] = None, limit: int = 100
    ) -> ServiceResult:
        """
        列出运行会话（task_id）

        Args:
            engine_id: 引擎ID筛选（可选）
            portfolio_id: 投资组合ID筛选（可选）
            limit: 返回数量限制

        Returns:
            ServiceResult[List[Dict]]: task_id 列表及其摘要
        """
        try:
            # 构建过滤条件
            filters = {}
            if engine_id:
                filters["engine_id"] = engine_id
            if portfolio_id:
                filters["portfolio_id"] = portfolio_id

            # 获取记录 - 使用 page_size 代替 limit
            records = self._crud_repo.find(
                filters=filters, page_size=limit * 100, order_by="timestamp", desc_order=True
            )

            # 按 task_id 分组
            run_map = {}
            engine_ids = set()
            portfolio_ids = set()

            for record in records:
                task_id = record.task_id
                if task_id and task_id not in run_map:
                    run_map[task_id] = {
                        "task_id": task_id,
                        "engine_id": record.engine_id,
                        "portfolio_id": record.portfolio_id,
                        "timestamp": record.timestamp,
                        "record_count": 1,
                    }
                    engine_ids.add(record.engine_id)
                    portfolio_ids.add(record.portfolio_id)
                elif task_id:
                    run_map[task_id]["record_count"] += 1

            # 获取 engine name 映射
            engine_name_map = {}
            if engine_ids:
                from ginkgo.data.containers import container

                engine_service = container.engine_service()
                for eid in engine_ids:
                    if eid:
                        engine_result = engine_service.get(engine_id=eid)
                        if engine_result.success and engine_result.data and len(engine_result.data) > 0:
                            engine_name_map[eid] = engine_result.data[0].name
                        else:
                            engine_name_map[eid] = eid

            # 获取 portfolio name 映射
            portfolio_name_map = {}
            if portfolio_ids:
                portfolio_service = container.portfolio_service()
                for pid in portfolio_ids:
                    if pid:
                        portfolio_result = portfolio_service.get(portfolio_id=pid)
                        if portfolio_result.success and portfolio_result.data and len(portfolio_result.data) > 0:
                            portfolio_name_map[pid] = portfolio_result.data[0].name
                        else:
                            portfolio_name_map[pid] = pid

            # 添加 engine name 和 portfolio name 到结果
            for run_info in run_map.values():
                run_info["engine_name"] = engine_name_map.get(run_info["engine_id"], run_info["engine_id"])
                run_info["portfolio_name"] = portfolio_name_map.get(run_info["portfolio_id"], run_info["portfolio_id"])

            # 转换为列表并排序
            runs = sorted(run_map.values(), key=lambda x: x["timestamp"] or datetime.min, reverse=True)[:limit]

            GLOG.INFO(f"列出运行会话成功: {len(runs)} 条")
            return ServiceResult.success(runs)

        except Exception as e:
            GLOG.ERROR(f"列出运行会话失败: {e}")
            return ServiceResult.error(f"列出运行会话失败: {e}")

    def get_portfolio_analyzers(self, task_id: str, portfolio_id: str) -> ServiceResult:
        """
        获取某个 portfolio 的所有 analyzer 列表

        Args:
            task_id: 运行会话ID
            portfolio_id: 投资组合ID

        Returns:
            ServiceResult[List[str]]: analyzer 名称列表
        """
        try:
            records = self._crud_repo.get_by_task_id(task_id=task_id, portfolio_id=portfolio_id, page_size=10000)

            analyzers = list(set(r.name for r in records if r.name))

            GLOG.INFO(f"获取 portfolio={portfolio_id} 的 analyzer 列表成功: {len(analyzers)} 个")
            return ServiceResult.success(analyzers)

        except Exception as e:
            GLOG.ERROR(f"获取 analyzer 列表失败: {e}")
            return ServiceResult.error(f"获取 analyzer 列表失败: {e}")

    def get_analyzer_stats(self, task_id: str, portfolio_id: str, analyzer_name: str) -> ServiceResult:
        """
        获取某个 analyzer 的统计信息

        Args:
            task_id: 运行会话ID
            portfolio_id: 投资组合ID
            analyzer_name: 分析器名称

        Returns:
            ServiceResult[Dict]: 统计信息（min, max, avg, latest等）
        """
        try:
            records = self._crud_repo.get_by_task_id(
                task_id=task_id, portfolio_id=portfolio_id, analyzer_name=analyzer_name, page_size=10000
            )

            if not records:
                return ServiceResult.error(f"未找到 analyzer={analyzer_name} 的记录")

            # 提取数值
            values = [float(r.value) for r in records if r.value is not None]

            if not values:
                return ServiceResult.error("没有有效的数值数据")

            # get_by_task_id 使用降序排列 (desc_order=True)
            # values[0] 是最新值，values[-1] 是最旧值
            stats = {
                "analyzer_name": analyzer_name,
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "latest": values[0] if values else None,
                "first": values[-1] if values else None,
                "change": values[0] - values[-1] if len(values) >= 2 else 0,
            }

            GLOG.INFO(f"获取 analyzer={analyzer_name} 的统计信息成功")
            return ServiceResult.success(stats)

        except Exception as e:
            GLOG.ERROR(f"获取统计信息失败: {e}")
            return ServiceResult.error(f"获取统计信息失败: {e}")

    def get_signals(
        self, task_id: str, portfolio_id: Optional[str] = None, page: int = 0, page_size: int = 100
    ) -> ServiceResult:
        """
        获取回测信号记录

        Args:
            task_id: 运行会话ID
            portfolio_id: 投资组合ID（可选）
            page: 页码
            page_size: 每页数量

        Returns:
            ServiceResult[List]: 信号记录列表
        """
        try:
            if not task_id:
                return ServiceResult.error("task_id 不能为空")

            from ginkgo.data.crud.signal_crud import SignalCRUD

            signal_crud = SignalCRUD()

            filters = {"task_id": task_id}
            if portfolio_id:
                filters["portfolio_id"] = portfolio_id

            result = signal_crud.find(
                filters=filters, page=page, page_size=page_size, order_by="timestamp", desc_order=True
            )

            total = signal_crud.count(filters)

            GLOG.INFO(f"获取 task_id={task_id} 的信号记录成功: {len(result)} 条")
            return ServiceResult.success({"data": result, "total": total, "page": page, "page_size": page_size})

        except Exception as e:
            GLOG.ERROR(f"获取信号记录失败: {e}")
            return ServiceResult.error(f"获取信号记录失败: {e}")

    def get_orders(
        self,
        task_id: str,
        portfolio_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 0,
    ) -> ServiceResult:
        """
        获取回测订单（去重后，每个 order_id 取时间最新的最终态）。

        与 get_order_records 区分: 本方法返回的是"订单"语义——同一 order_id 的
        多条状态流转(NEW→SUBMITTED→FILLED)只保留最终态一条; 失败单
        (CANCELED/REJECTED)也保留其终态。完整状态流水见 get_order_records。

        分页在去重之后做: 不能下推到 crud.find, 否则按流水切片会切断同一 order_id
        的多条状态记录, 跨页去重丢失订单。total 为去重后唯一订单总数, 独立于当前页。

        Args:
            task_id: 运行会话ID
            portfolio_id: 投资组合ID（可选）
            page: 页码(从 1 起)
            page_size: 每页数量

        Returns:
            ServiceResult[Dict]: {"data": 当前页订单, "total": 唯一订单总数}
        """
        try:
            if not task_id:
                return ServiceResult.error("task_id 不能为空")

            records = self._find_order_records(task_id, portfolio_id)

            # find 已按 timestamp desc 返回, 首次出现的即该 order_id 的最新最终态
            seen: set = set()
            unique = []
            for r in records:
                oid = getattr(r, "order_id", "")
                if oid in seen:
                    continue
                seen.add(oid)
                unique.append(r)

            total = len(unique)
            # 去重后内存分页(page 从 1 起); page/page_size 非法时回退全量
            if page >= 1 and page_size >= 1:
                start = (page - 1) * page_size
                paged = unique[start : start + page_size]
            else:
                paged = unique

            GLOG.INFO(
                f"获取 task_id={task_id} 的订单成功: {total} 个唯一订单 (流水 {len(records)} 条), 返回第 {page} 页 {len(paged)} 条"
            )
            return ServiceResult.success({"data": paged, "total": total, "page": page, "page_size": page_size})

        except Exception as e:
            GLOG.ERROR(f"获取订单失败: {e}")
            return ServiceResult.error(f"获取订单失败: {e}")

    def get_order_records(self, task_id: str, portfolio_id: Optional[str] = None) -> ServiceResult:
        """
        获取回测订单记录（完整状态流水，不去重）。

        与 get_orders 区分: 本方法返回的是"订单记录"语义——同一 order_id 的
        每一次状态变更(NEW/SUBMITTED/PARTIAL_FILLED/FILLED/CANCELED/REJECTED)
        各保留一行, 用于还原订单的完整生命周期。去重后的订单见 get_orders。

        Args:
            task_id: 运行会话ID
            portfolio_id: 投资组合ID（可选）

        Returns:
            ServiceResult[Dict]: {"data": 全部订单记录流水, "total": 流水总数}
        """
        try:
            if not task_id:
                return ServiceResult.error("task_id 不能为空")

            records = self._find_order_records(task_id, portfolio_id)
            total = len(records)

            GLOG.INFO(f"获取 task_id={task_id} 的订单记录流水成功: {total} 条")
            return ServiceResult.success({"data": records, "total": total})

        except Exception as e:
            GLOG.ERROR(f"获取订单记录失败: {e}")
            return ServiceResult.error(f"获取订单记录失败: {e}")

    def _find_order_records(self, task_id: str, portfolio_id: Optional[str] = None) -> list:
        """查询订单记录流水(按 timestamp desc), 供 get_orders/get_order_records 共用。"""
        from ginkgo.data.crud.order_record_crud import OrderRecordCRUD

        order_record_crud = OrderRecordCRUD()

        filters = {"task_id": task_id}
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id

        return order_record_crud.find(filters=filters, order_by="timestamp", desc_order=True)

    def get_positions(self, task_id: str, portfolio_id: Optional[str] = None) -> ServiceResult:
        """
        获取回测持仓记录

        Args:
            task_id: 运行会话ID
            portfolio_id: 投资组合ID（可选）

        Returns:
            ServiceResult[List]: 持仓记录列表
        """
        try:
            if not task_id:
                return ServiceResult.error("task_id 不能为空")

            from ginkgo.data.crud.position_record_crud import PositionRecordCRUD

            position_record_crud = PositionRecordCRUD()

            filters = {"task_id": task_id}
            if portfolio_id:
                filters["portfolio_id"] = portfolio_id

            result = position_record_crud.find(filters=filters, order_by="timestamp", desc_order=True)

            total = position_record_crud.count(filters)

            GLOG.INFO(f"获取 task_id={task_id} 的持仓记录成功: {len(result)} 条")
            return ServiceResult.success({"data": result, "total": total})

        except Exception as e:
            GLOG.ERROR(f"获取持仓记录失败: {e}")
            return ServiceResult.error(f"获取持仓记录失败: {e}")

    def get_positions_df(
        self,
        portfolio_id: Optional[str] = None,
        engine_id: Optional[str] = None,
        task_id: Optional[str] = None,
        page: int = 0,
        page_size: int = 50,
    ) -> ServiceResult:
        """出口①：data 是 pandas.DataFrame（查 MPositionRecord 流水表）。

        #5341: 回测持仓经 create_position_record 写 MPositionRecord（持仓流水），
        非 MPosition（当前态表）。record position 读 MPosition 永远空，须查流水表。
        filter 域与 position_service.get_positions_df 对称（portfolio/engine/task），
        出口契约同为 DataFrame（ADR-010）。
        """
        try:
            from ginkgo.data.crud.position_record_crud import PositionRecordCRUD

            position_record_crud = PositionRecordCRUD()

            filters = {"is_del": False}
            if portfolio_id:
                filters["portfolio_id"] = portfolio_id
            if engine_id:
                filters["engine_id"] = engine_id
            if task_id:
                filters["task_id"] = task_id

            model_list = position_record_crud.find(
                filters=filters,
                page=page if page_size > 0 else None,
                page_size=page_size if page_size > 0 else None,
                order_by="timestamp",
                desc_order=True,
            )
            df = model_list.to_dataframe() if model_list else pd.DataFrame()
            return ServiceResult.success(
                data=df,
                message=f"Retrieved {len(df)} position records (DataFrame)",
            )
        except Exception as e:
            GLOG.ERROR(f"查询持仓记录(df)失败: {str(e)}")
            return ServiceResult.error(f"查询持仓记录(df)失败: {str(e)}")

    @retry(max_try=3)
    def create_order_record(self, **kwargs) -> ServiceResult:
        """
        创建订单记录

        Args:
            order_id: 订单ID
            portfolio_id: 投资组合ID
            engine_id: 引擎ID
            task_id: 运行会话ID
            code: 股票代码
            direction: 交易方向
            order_type: 订单类型
            status: 订单状态
            volume: 委托数量
            limit_price: 限价
            transaction_price: 成交价格
            transaction_volume: 成交数量
            timestamp: 时间戳
            business_timestamp: 业务时间戳
            **kwargs: 其他参数

        Returns:
            ServiceResult: 创建结果
        """
        try:
            from ginkgo.data.crud.order_record_crud import OrderRecordCRUD

            order_record_crud = OrderRecordCRUD()

            order_record_crud.create(**kwargs)

            GLOG.INFO(f"订单记录创建成功: code={kwargs.get('code')} task_id={kwargs.get('task_id')}")
            return ServiceResult.success({"message": "Order record created"})

        except Exception as e:
            GLOG.ERROR(f"创建订单记录失败: {e}")
            return ServiceResult.error(f"创建订单记录失败: {e}")

    @retry(max_try=3)
    def create_position_record(self, **kwargs) -> ServiceResult:
        """
        创建持仓记录

        Args:
            portfolio_id: 投资组合ID
            engine_id: 引擎ID
            task_id: 运行会话ID
            code: 股票代码
            volume: 持仓数量
            cost: 成本
            price: 当前价格
            frozen_volume: 冻结数量
            frozen_money: 冻结金额
            fee: 手续费
            timestamp: 时间戳
            business_timestamp: 业务时间戳
            **kwargs: 其他参数

        Returns:
            ServiceResult: 创建结果
        """
        try:
            from ginkgo.data.crud.position_record_crud import PositionRecordCRUD

            position_record_crud = PositionRecordCRUD()

            position_record_crud.create(**kwargs)

            GLOG.INFO(f"持仓记录创建成功: code={kwargs.get('code')} task_id={kwargs.get('task_id')}")
            return ServiceResult.success({"message": "Position record created"})

        except Exception as e:
            GLOG.ERROR(f"创建持仓记录失败: {e}")
            return ServiceResult.error(f"创建持仓记录失败: {e}")

    def get_orders_by_portfolio(
        self,
        portfolio_id: str,
        status: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> ServiceResult:
        """按 portfolio 查询订单记录（不依赖 task_id，用于实盘/模拟盘）"""
        try:
            from ginkgo.data.crud.order_record_crud import OrderRecordCRUD

            crud = OrderRecordCRUD()

            filters = {"portfolio_id": portfolio_id}
            if status is not None:
                filters["status"] = status

            result = crud.find(
                filters=filters,
                page_size=page_size,
                order_by="timestamp",
                desc_order=True,
            )
            total = crud.count(filters)

            return ServiceResult.success({"data": result, "total": total})
        except Exception as e:
            GLOG.ERROR(f"查询订单失败: {e}")
            return ServiceResult.error(str(e))

    def get_current_positions(
        self,
        portfolio_id: str,
        min_volume: Optional[int] = None,
    ) -> ServiceResult:
        """查询当前持仓（不依赖 task_id，用于实盘/模拟盘）"""
        try:
            from ginkgo.data.crud.position_record_crud import PositionRecordCRUD

            crud = PositionRecordCRUD()

            result = crud.find_current_positions(
                portfolio_id=portfolio_id,
                min_volume=min_volume,
            )
            return ServiceResult.success(result)
        except Exception as e:
            GLOG.ERROR(f"查询持仓失败: {e}")
            return ServiceResult.error(str(e))

    def cancel_order(self, order_id: str) -> ServiceResult:
        """取消订单"""
        try:
            from ginkgo.data.crud.order_record_crud import OrderRecordCRUD

            crud = OrderRecordCRUD()

            records = crud.find_by_order_id(order_id)
            if not records:
                return ServiceResult.error("Order not found")

            record = records[0]
            crud.update_by_uuid(record.uuid, data={"status": 4})  # 4 = CANCELLED

            return ServiceResult.success({"cancelled": True})
        except Exception as e:
            GLOG.ERROR(f"取消订单失败: {e}")
            return ServiceResult.error(str(e))

    def get_orders_by_portfolio_date(
        self,
        portfolio_id: str,
        start_date=None,
        end_date=None,
        page_size: Optional[int] = None,
    ) -> ServiceResult:
        """按 portfolio + 日期范围查询订单（不依赖 task_id）"""
        try:
            from ginkgo.data.crud.order_record_crud import OrderRecordCRUD

            crud = OrderRecordCRUD()

            result = crud.find_by_portfolio(
                portfolio_id=portfolio_id,
                start_date=start_date,
                end_date=end_date,
                page_size=page_size,
            )
            return ServiceResult.success(result)
        except Exception as e:
            GLOG.ERROR(f"查询订单失败: {e}")
            return ServiceResult.error(str(e))

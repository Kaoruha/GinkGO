# Upstream: CLI Commands (ginkgo results show)、Analysis Modules (回测结果分析)
# Downstream: BaseService (继承提供服务基础能力)、AnalyzerRecordCRUD (分析器记录CRUD操作)、MAnalyzerRecord (分析器记录模型)
# Role: ResultService回测结果查询和分析业务服务提供运行摘要/分析器值/记录/投资组合摘要等方法






"""
Result Service Module

提供回测结果查询和分析服务，支持按 run_id 查询 analyzer 指标数据。
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import pandas as pd

from ginkgo.data.crud.analyzer_record_crud import AnalyzerRecordCRUD
from ginkgo.data.models.model_analyzer_record import MAnalyzerRecord
from ginkgo.libs import GLOG, time_logger, retry, datetime_normalize
from ginkgo.data.services.base_service import ServiceResult, BaseService


class ResultService(BaseService):
    """
    Result Service Layer

    提供回测结果查询、聚合和统计分析功能：
    - 按 run_id 查询 analyzer 记录
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

    @time_logger
    @retry(max_try=3)
    def get_run_summary(self, run_id: str) -> ServiceResult:
        """
        获取某次运行会话的摘要信息

        Args:
            run_id: 运行会话ID

        Returns:
            ServiceResult[Dict]: 包含 portfolios、analyzers、时间范围等摘要信息
        """
        try:
            if not run_id:
                return ServiceResult.error("run_id 不能为空")

            # 获取该 run_id 的所有记录
            records = self._crud_repo.get_by_run_id(run_id, page_size=10000)

            if not records:
                return ServiceResult.error(f"未找到 run_id={run_id} 的记录")

            # 聚合摘要信息
            portfolios = list(set(r.portfolio_id for r in records if r.portfolio_id))
            analyzers = list(set(r.name for r in records if r.name))

            # 时间范围
            timestamps = [r.timestamp for r in records if r.timestamp]
            time_range = {
                "start": min(timestamps) if timestamps else None,
                "end": max(timestamps) if timestamps else None
            }

            summary = {
                "run_id": run_id,
                "engine_id": records[0].engine_id if records else None,
                "portfolio_count": len(portfolios),
                "portfolios": portfolios,
                "analyzer_count": len(analyzers),
                "analyzers": analyzers,
                "total_records": len(records),
                "time_range": time_range
            }

            GLOG.INFO(f"获取 run_id={run_id} 的摘要信息成功")
            return ServiceResult.success(summary)

        except Exception as e:
            GLOG.ERROR(f"获取运行摘要失败: {e}")
            return ServiceResult.error(f"获取运行摘要失败: {e}")

    @time_logger
    @retry(max_try=3)
    def get_analyzer_values(
        self,
        run_id: str,
        portfolio_id: Optional[str] = None,
        analyzer_name: Optional[str] = None
    ) -> ServiceResult:
        """
        获取 analyzer 指标值

        Args:
            run_id: 运行会话ID
            portfolio_id: 投资组合ID（可选）
            analyzer_name: 分析器名称（可选）

        Returns:
            ServiceResult[ModelList]: 可调用 to_dataframe() 转换为 DataFrame
        """
        try:
            if not run_id:
                return ServiceResult.error("run_id 不能为空")

            # 使用 CRUD 的 get_by_run_id 方法
            result = self._crud_repo.get_by_run_id(
                run_id=run_id,
                portfolio_id=portfolio_id,
                analyzer_name=analyzer_name,
                page_size=10000
            )

            GLOG.INFO(f"获取 run_id={run_id} 的 analyzer 值成功")
            return ServiceResult.success(result)

        except Exception as e:
            GLOG.ERROR(f"获取 analyzer 值失败: {e}")
            return ServiceResult.error(f"获取 analyzer 值失败: {e}")

    @time_logger
    @retry(max_try=3)
    def get_multi_analyzer_data(
        self,
        run_id: str,
        portfolio_id: str,
        analyzer_names: List[str]
    ) -> ServiceResult:
        """
        获取多个 analyzer 的数据，用于对比绘图

        Args:
            run_id: 运行会话ID
            portfolio_id: 投资组合ID
            analyzer_names: 分析器名称列表

        Returns:
            ServiceResult[Dict[str, ModelList]]: analyzer_name -> ModelList 的映射
        """
        try:
            if not run_id or not portfolio_id:
                return ServiceResult.error("run_id 和 portfolio_id 不能为空")

            if not analyzer_names:
                return ServiceResult.error("analyzer_names 列表不能为空")

            data_map = {}
            for analyzer_name in analyzer_names:
                model_list = self._crud_repo.get_by_run_id(
                    run_id=run_id,
                    portfolio_id=portfolio_id,
                    analyzer_name=analyzer_name,
                    page_size=10000
                )
                data_map[analyzer_name] = model_list

            GLOG.INFO(f"获取多 analyzer 数据成功: {list(data_map.keys())}")
            return ServiceResult.success(data_map)

        except Exception as e:
            GLOG.ERROR(f"获取多 analyzer 数据失败: {e}")
            return ServiceResult.error(f"获取多 analyzer 数据失败: {e}")

    @time_logger
    @retry(max_try=3)
    def list_runs(
        self,
        engine_id: Optional[str] = None,
        portfolio_id: Optional[str] = None,
        limit: int = 100
    ) -> ServiceResult:
        """
        列出运行会话（run_id）

        Args:
            engine_id: 引擎ID筛选（可选）
            portfolio_id: 投资组合ID筛选（可选）
            limit: 返回数量限制

        Returns:
            ServiceResult[List[Dict]]: run_id 列表及其摘要
        """
        try:
            # 构建过滤条件
            filters = {}
            if engine_id:
                filters["engine_id"] = engine_id
            if portfolio_id:
                filters["portfolio_id"] = portfolio_id

            # 获取记录 - 使用 page_size 代替 limit
            records = self._crud_repo.find(filters=filters, page_size=limit * 100, order_by="timestamp", desc_order=True)

            # 按 run_id 分组
            run_map = {}
            engine_ids = set()
            portfolio_ids = set()

            for record in records:
                run_id = record.run_id
                if run_id and run_id not in run_map:
                    run_map[run_id] = {
                        "run_id": run_id,
                        "engine_id": record.engine_id,
                        "portfolio_id": record.portfolio_id,
                        "timestamp": record.timestamp,
                        "record_count": 1
                    }
                    engine_ids.add(record.engine_id)
                    portfolio_ids.add(record.portfolio_id)
                elif run_id:
                    run_map[run_id]["record_count"] += 1

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

    @time_logger
    @retry(max_try=3)
    def get_portfolio_analyzers(
        self,
        run_id: str,
        portfolio_id: str
    ) -> ServiceResult:
        """
        获取某个 portfolio 的所有 analyzer 列表

        Args:
            run_id: 运行会话ID
            portfolio_id: 投资组合ID

        Returns:
            ServiceResult[List[str]]: analyzer 名称列表
        """
        try:
            records = self._crud_repo.get_by_run_id(
                run_id=run_id,
                portfolio_id=portfolio_id,
                page_size=10000
            )

            analyzers = list(set(r.name for r in records if r.name))

            GLOG.INFO(f"获取 portfolio={portfolio_id} 的 analyzer 列表成功: {len(analyzers)} 个")
            return ServiceResult.success(analyzers)

        except Exception as e:
            GLOG.ERROR(f"获取 analyzer 列表失败: {e}")
            return ServiceResult.error(f"获取 analyzer 列表失败: {e}")

    @time_logger
    @retry(max_try=3)
    def get_analyzer_stats(
        self,
        run_id: str,
        portfolio_id: str,
        analyzer_name: str
    ) -> ServiceResult:
        """
        获取某个 analyzer 的统计信息

        Args:
            run_id: 运行会话ID
            portfolio_id: 投资组合ID
            analyzer_name: 分析器名称

        Returns:
            ServiceResult[Dict]: 统计信息（min, max, avg, latest等）
        """
        try:
            records = self._crud_repo.get_by_run_id(
                run_id=run_id,
                portfolio_id=portfolio_id,
                analyzer_name=analyzer_name,
                page_size=10000
            )

            if not records:
                return ServiceResult.error(f"未找到 analyzer={analyzer_name} 的记录")

            # 提取数值
            values = [float(r.value) for r in records if r.value is not None]

            if not values:
                return ServiceResult.error("没有有效的数值数据")

            # get_by_run_id 使用降序排列 (desc_order=True)
            # values[0] 是最新值，values[-1] 是最旧值
            stats = {
                "analyzer_name": analyzer_name,
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "latest": values[0] if values else None,
                "first": values[-1] if values else None,
                "change": values[0] - values[-1] if len(values) >= 2 else 0
            }

            GLOG.INFO(f"获取 analyzer={analyzer_name} 的统计信息成功")
            return ServiceResult.success(stats)

        except Exception as e:
            GLOG.ERROR(f"获取统计信息失败: {e}")
            return ServiceResult.error(f"获取统计信息失败: {e}")

    @time_logger
    @retry(max_try=3)
    def get_signals(
        self,
        run_id: str,
        portfolio_id: Optional[str] = None,
        page: int = 0,
        page_size: int = 100
    ) -> ServiceResult:
        """
        获取回测信号记录

        Args:
            run_id: 运行会话ID
            portfolio_id: 投资组合ID（可选）
            page: 页码
            page_size: 每页数量

        Returns:
            ServiceResult[List]: 信号记录列表
        """
        try:
            if not run_id:
                return ServiceResult.error("run_id 不能为空")

            from ginkgo.data.crud.signal_crud import SignalCRUD
            signal_crud = SignalCRUD()

            filters = {"run_id": run_id}
            if portfolio_id:
                filters["portfolio_id"] = portfolio_id

            result = signal_crud.find(
                filters=filters,
                page=page,
                page_size=page_size,
                order_by="timestamp",
                desc_order=True
            )

            total = signal_crud.count(filters)

            GLOG.INFO(f"获取 run_id={run_id} 的信号记录成功: {len(result)} 条")
            return ServiceResult.success({"data": result, "total": total, "page": page, "page_size": page_size})

        except Exception as e:
            GLOG.ERROR(f"获取信号记录失败: {e}")
            return ServiceResult.error(f"获取信号记录失败: {e}")

    @time_logger
    @retry(max_try=3)
    def get_orders(
        self,
        run_id: str,
        portfolio_id: Optional[str] = None
    ) -> ServiceResult:
        """
        获取回测订单记录

        Args:
            run_id: 运行会话ID
            portfolio_id: 投资组合ID（可选）

        Returns:
            ServiceResult[List]: 订单记录列表
        """
        try:
            if not run_id:
                return ServiceResult.error("run_id 不能为空")

            from ginkgo.data.crud.order_record_crud import OrderRecordCRUD
            order_record_crud = OrderRecordCRUD()

            filters = {"run_id": run_id}
            if portfolio_id:
                filters["portfolio_id"] = portfolio_id

            result = order_record_crud.find(
                filters=filters,
                order_by="timestamp",
                desc_order=True
            )

            total = order_record_crud.count(filters)

            GLOG.INFO(f"获取 run_id={run_id} 的订单记录成功: {len(result)} 条")
            return ServiceResult.success({"data": result, "total": total})

        except Exception as e:
            GLOG.ERROR(f"获取订单记录失败: {e}")
            return ServiceResult.error(f"获取订单记录失败: {e}")

    @time_logger
    @retry(max_try=3)
    def get_positions(
        self,
        run_id: str,
        portfolio_id: Optional[str] = None
    ) -> ServiceResult:
        """
        获取回测持仓记录

        Args:
            run_id: 运行会话ID
            portfolio_id: 投资组合ID（可选）

        Returns:
            ServiceResult[List]: 持仓记录列表
        """
        try:
            if not run_id:
                return ServiceResult.error("run_id 不能为空")

            from ginkgo.data.crud.position_record_crud import PositionRecordCRUD
            position_record_crud = PositionRecordCRUD()

            filters = {"run_id": run_id}
            if portfolio_id:
                filters["portfolio_id"] = portfolio_id

            result = position_record_crud.find(
                filters=filters,
                order_by="timestamp",
                desc_order=True
            )

            total = position_record_crud.count(filters)

            GLOG.INFO(f"获取 run_id={run_id} 的持仓记录成功: {len(result)} 条")
            return ServiceResult.success({"data": result, "total": total})

        except Exception as e:
            GLOG.ERROR(f"获取持仓记录失败: {e}")
            return ServiceResult.error(f"获取持仓记录失败: {e}")

    @time_logger
    @retry(max_try=3)
    def create_order_record(self, **kwargs) -> ServiceResult:
        """
        创建订单记录

        Args:
            order_id: 订单ID
            portfolio_id: 投资组合ID
            engine_id: 引擎ID
            run_id: 运行会话ID
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

            GLOG.INFO(f"订单记录创建成功: code={kwargs.get('code')} run_id={kwargs.get('run_id')}")
            return ServiceResult.success({"message": "Order record created"})

        except Exception as e:
            GLOG.ERROR(f"创建订单记录失败: {e}")
            return ServiceResult.error(f"创建订单记录失败: {e}")

    @time_logger
    @retry(max_try=3)
    def create_position_record(self, **kwargs) -> ServiceResult:
        """
        创建持仓记录

        Args:
            portfolio_id: 投资组合ID
            engine_id: 引擎ID
            run_id: 运行会话ID
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

            GLOG.INFO(f"持仓记录创建成功: code={kwargs.get('code')} run_id={kwargs.get('run_id')}")
            return ServiceResult.success({"message": "Position record created"})

        except Exception as e:
            GLOG.ERROR(f"创建持仓记录失败: {e}")
            return ServiceResult.error(f"创建持仓记录失败: {e}")

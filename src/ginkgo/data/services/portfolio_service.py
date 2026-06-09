# Upstream: CLI Commands (ginkgo portfolio命令)、PaperTradingWorker (状态持久化/恢复)、LiveCore (组合加载)
# Downstream: BaseService (继承服务基类)、PortfolioCRUD (组合CRUD)、PortfolioFileMappingCRUD (文件映射CRUD)
# Role: 投资组合业务服务，提供 CRUD 封装、组件绑定、状态持久化/恢复、组合完整加载与实例化






"""
Portfolio Management Service (Class-based)

This service handles the business logic for managing investment portfolios,
including portfolio creation, file associations, and parameter management.

Enhanced with comprehensive error handling, retry mechanisms, and structured returns.
"""

import time

from typing import List, Union, Any, Optional, Dict
import pandas as pd
from datetime import datetime

from ginkgo.libs import cache_with_expiration, retry, GLOG
from ginkgo.enums import FILE_TYPES, PORTFOLIO_MODE_TYPES, PORTFOLIO_RUNSTATE_TYPES
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.crud.model_conversion import ModelList


class PortfolioService(BaseService):
    def __init__(self, crud_repo, portfolio_file_mapping_crud, deployment_crud=None):
        """
        初始化PortfolioService，设置投资组合和文件映射仓储依赖

        Args:
            crud_repo: 投资组合数据CRUD仓储实例
            portfolio_file_mapping_crud: 投资组合文件映射CRUD仓储实例
            deployment_crud: 部署CRUD仓储实例（可选，用于冻结判定）
        """
        super().__init__(
            crud_repo=crud_repo, portfolio_file_mapping_crud=portfolio_file_mapping_crud
        )
        self._deployment_crud = deployment_crud

    def is_portfolio_frozen(self, portfolio_id: str) -> bool:
        """检查组合是否已部署（冻结）

        通过查询 MDeployment 判定：存在 source_portfolio_id 匹配且
        target 未删除且状态为 DEPLOYED 的记录时返回 True。
        """
        if not hasattr(self, '_deployment_crud') or self._deployment_crud is None:
            return False

        deployments = self._deployment_crud.find(
            filters={"source_portfolio_id": portfolio_id}
        )

        for d in deployments:
            if getattr(d, 'status', -1) != 1:  # DEPLOYMENT_STATUS.DEPLOYED = 1
                continue
            target_id = getattr(d, 'target_portfolio_id', None)
            if not target_id:
                continue
            targets = self._crud_repo.find(
                filters={"uuid": target_id, "is_del": False}
            )
            if targets and len(targets) > 0:
                return True

        return False

    # fix(#4582): 封装分页查询，避免 API 层直调 _crud_repo
    # fix(#4589): 改用 BaseService._paginated_query() 通用方法
    def list_paginated(
        self,
        filters: Optional[Dict] = None,
        page: int = 0,
        page_size: int = 20,
        order_by: str = "update_at",
        desc_order: bool = True,
    ) -> ServiceResult:
        """分页查询投资组合列表"""
        return self._paginated_query(
            filters=filters, page=page, page_size=page_size,
            order_by=order_by, desc_order=desc_order,
        )

    @retry(max_try=3)
    def add(
        self,
        name: str,
        mode: PORTFOLIO_MODE_TYPES = PORTFOLIO_MODE_TYPES.BACKTEST,
        description: str = None,
        initial_capital: float = None,
        **kwargs
    ) -> ServiceResult:
        """
        创建新的投资组合

        Args:
            name: 投资组合名称
            mode: 运行模式 (BACKTEST/PAPER/LIVE)
            description: 可选描述
            initial_capital: 初始资金（默认 1000000.0）

        Returns:
            ServiceResult: 操作结果
        """
        try:
            # 输入验证
            if not name or not name.strip():
                return ServiceResult.error("投资组合名称不能为空")

            if len(name) > 100:  # 合理的名称长度限制
                name = name[:100]

            # 检查投资组合名称是否已存在
            try:
                exists_result = self.exists(name=name)
                if exists_result.is_success() and exists_result.data.get("exists", False):
                    return ServiceResult.error(f"投资组合名称 '{name}' 已存在")
            except Exception as e:
                GLOG.WARN(f"无法检查投资组合存在性: {str(e)}")

            # 获取模式名称
            mode_name = mode.name if hasattr(mode, 'name') else str(mode)

            # 创建投资组合
            capital = initial_capital if initial_capital is not None else 1000000.0
            with self._crud_repo.get_session() as session:
                portfolio_record = self._crud_repo.create(
                    name=name,
                    mode=PORTFOLIO_MODE_TYPES.validate_input(mode) or PORTFOLIO_MODE_TYPES.BACKTEST.value,
                    state=PORTFOLIO_RUNSTATE_TYPES.INITIALIZED.value,
                    desc=description or f"{mode_name} portfolio: {name}",
                    initial_capital=capital,
                    current_capital=capital,
                    cash=capital,
                    session=session,
                )

                portfolio_info = {
                    "uuid": portfolio_record.uuid,
                    "name": portfolio_record.name,
                    "mode": portfolio_record.mode,
                    "state": portfolio_record.state,
                    "desc": portfolio_record.desc,
                }

                GLOG.INFO(f"成功创建投资组合 '{name}' (模式: {mode_name})")

                return ServiceResult.success(
                    data=portfolio_info,
                    message=f"投资组合创建成功: {name}"
                )

        except Exception as e:
            GLOG.ERROR(f"创建投资组合失败 '{name}': {str(e)}")
            return ServiceResult.error(f"创建投资组合失败: {str(e)}")

    @retry(max_try=3)
    def update(
        self,
        portfolio_id: str,
        name: str = None,
        mode: PORTFOLIO_MODE_TYPES = None,
        state: PORTFOLIO_RUNSTATE_TYPES = None,
        description: str = None,
        cash=None,
        frozen=None,
        current_capital=None,
        total_fee=None,
        total_profit=None,
        **kwargs
    ) -> ServiceResult:
        """
        更新现有投资组合的信息，支持部分字段更新

        Args:
            portfolio_id: 投资组合UUID标识符
            name: 新的投资组合名称（可选）
            mode: 新的运行模式（可选）
            state: 新的运行状态（可选）
            description: 新的描述信息（可选）

        Returns:
            ServiceResult: 包含更新状态和操作结果的详细信息
        """
        warnings = []
        updates_applied = []

        # Input validation
        if not portfolio_id or not portfolio_id.strip():
            return ServiceResult.error("Portfolio ID cannot be empty")

        # 冻结检查（state 由 Worker 运行时控制，不阻止）
        _only_state = state is not None and all(
            v is None for k, v in [
                ("name", name), ("mode", mode), ("description", description),
                ("cash", cash), ("frozen", frozen), ("current_capital", current_capital),
                ("total_fee", total_fee), ("total_profit", total_profit),
            ]
        )
        if not _only_state and self.is_portfolio_frozen(portfolio_id):
            return ServiceResult.error("组合已部署，不可修改")

        updates = {}
        if name is not None:
            if not name.strip():
                return ServiceResult.error("Portfolio name cannot be empty")
            if len(name) > 100:
                warnings.append("Portfolio name truncated to 100 characters")
                name = name[:100]
            updates["name"] = name
            updates_applied.append("name")


        if mode is not None:
            GLOG.WARN(
                f"Portfolio {portfolio_id}: mode modification ignored. "
                "Use DeploymentService.deploy() or PortfolioService.add()."
            )
            warnings.append("mode modification is not allowed, use deploy instead")

        if state is not None:
            updates["state"] = PORTFOLIO_RUNSTATE_TYPES.validate_input(state)
            updates_applied.append("state")

        if description is not None:
            updates["desc"] = description
            updates_applied.append("description")

        if cash is not None:
            updates["cash"] = cash
            updates_applied.append("cash")

        if frozen is not None:
            updates["frozen"] = frozen
            updates_applied.append("frozen")

        if current_capital is not None:
            updates["current_capital"] = current_capital
            updates_applied.append("current_capital")

        if total_fee is not None:
            updates["total_fee"] = total_fee
            updates_applied.append("total_fee")

        if total_profit is not None:
            updates["total_profit"] = total_profit
            updates_applied.append("total_profit")

        if not updates:
            return ServiceResult.success({}, "No updates provided for portfolio update", warnings)

        # Check if name conflicts with existing portfolio (if name is being updated)
        if "name" in updates:
            try:
                existing_portfolios = self.get_portfolios(name=name)
                if len(existing_portfolios) > 0:
                    # Check if the existing portfolio is not the one we're updating
                    df = existing_portfolios.to_dataframe()
                    existing_uuids = df["uuid"].tolist()
                    if portfolio_id not in existing_uuids:
                        return ServiceResult.error(f"Portfolio with name '{name}' already exists")
            except Exception as e:
                warnings.append(f"Could not check name conflict: {str(e)}")

        try:
            self._crud_repo.modify(filters={"uuid": portfolio_id}, updates=updates)

            GLOG.INFO(f"Successfully updated portfolio {portfolio_id} with {len(updates)} changes")

        except Exception as e:
            return ServiceResult.error(f"Database operation failed: {str(e)}")

        # 返回更新结果
        result_data = {
            "portfolio_id": portfolio_id,
            "updates_applied": updates_applied,
            "warnings": warnings
        }
        return ServiceResult.success(result_data, f"Portfolio updated successfully")

    def update_performance(
        self,
        portfolio_id: str,
        annual_return: float = None,
        sharpe_ratio: float = None,
        max_drawdown: float = None,
        win_rate: float = None,
        total_trades: int = None,
        winning_trades: int = None,
    ) -> ServiceResult:
        """更新 Portfolio 绩效指标字段

        回测完成后由结果聚合器调用，批量更新组合的绩效指标。

        Args:
            portfolio_id: 投资组合UUID
            annual_return: 年化收益率
            sharpe_ratio: 夏普比率
            max_drawdown: 最大回撤
            win_rate: 胜率
            total_trades: 总交易次数
            winning_trades: 盈利交易次数

        Returns:
            ServiceResult: 更新结果
        """
        try:
            if not portfolio_id or not portfolio_id.strip():
                return ServiceResult.error("Portfolio ID cannot be empty")

            updates = {}
            if annual_return is not None:
                updates["annual_return"] = annual_return
            if sharpe_ratio is not None:
                updates["sharpe_ratio"] = sharpe_ratio
            if max_drawdown is not None:
                updates["max_drawdown"] = max_drawdown
            if win_rate is not None:
                updates["win_rate"] = win_rate
            if total_trades is not None:
                updates["total_trades"] = total_trades
            if winning_trades is not None:
                updates["winning_trades"] = winning_trades

            if not updates:
                return ServiceResult.success(data=None, message="No fields to update")

            self._crud_repo.modify(filters={"uuid": portfolio_id}, updates=updates)
            GLOG.INFO(f"Updated performance for portfolio {portfolio_id[:8]}: {list(updates.keys())}")
            return ServiceResult.success(
                data={"portfolio_id": portfolio_id, "updated_fields": list(updates.keys())},
                message="Performance updated",
            )
        except Exception as e:
            GLOG.ERROR(f"Failed to update performance for portfolio {portfolio_id}: {e}")
            return ServiceResult.error(f"Failed to update performance: {e}")

    def persist_portfolio_state(self, portfolio_id: str, state: dict) -> ServiceResult:
        """
        将 Portfolio 运行时状态持久化到 MySQL

        更新 portfolio 表的 cash/frozen/total_fee/current_capital，
        全量替换 position 表的持仓快照。

        Args:
            portfolio_id: 投资组合UUID
            state: snapshot_state() 返回的状态字典

        Returns:
            ServiceResult
        """
        try:
            from decimal import Decimal

            # 1. 更新 portfolio 表的运行时字段
            positions = state.get("positions", [])
            position_value = sum(
                Decimal(p.get("price", 0)) * int(p.get("volume", 0))
                for p in positions
            )
            current_capital = Decimal(state["cash"]) + Decimal(state["frozen"]) + position_value

            portfolio_updates = {
                "cash": state["cash"],
                "frozen": state["frozen"],
                "total_fee": state["fee"],
                "current_capital": str(current_capital),
            }
            self._crud_repo.modify(filters={"uuid": portfolio_id}, updates=portfolio_updates)

            # 2. 全量替换 position 表（通过 CRUD 层 batch_create）
            if positions:
                position_crud = self._get_position_crud()
                position_crud.delete_by_portfolio(portfolio_id)
                position_crud.batch_create(positions)

            GLOG.INFO(
                f"Persisted state for portfolio {portfolio_id[:8]}: "
                f"cash={state['cash']}, positions={len(positions)}"
            )
            return ServiceResult.success({"portfolio_id": portfolio_id})

        except Exception as e:
            GLOG.ERROR(f"Failed to persist portfolio state: {e}")
            return ServiceResult.error(f"Database operation failed: {str(e)}")

    def load_persisted_state(self, portfolio_id: str) -> ServiceResult:
        """
        从 MySQL 加载 Portfolio 的运行时状态

        读取 portfolio 表的 cash/frozen/total_fee 和 position 表的持仓快照。

        Args:
            portfolio_id: 投资组合UUID

        Returns:
            ServiceResult: data 为 state dict（兼容 restore_state()）
        """
        try:
            # 1. 读取 portfolio 表的运行时字段
            portfolios = self._crud_repo.find(filters={"uuid": portfolio_id})
            if not portfolios:
                return ServiceResult.error(f"Portfolio {portfolio_id} not found")

            p = portfolios[0]

            # 2. 读取 position 表的持仓快照
            position_crud = self._get_position_crud()
            m_positions = position_crud.find(filters={"portfolio_id": portfolio_id})

            positions_data = []
            for m_pos in m_positions:
                positions_data.append({
                    "portfolio_id": m_pos.portfolio_id,
                    "engine_id": m_pos.engine_id,
                    "task_id": m_pos.task_id,
                    "code": m_pos.code,
                    "cost": str(m_pos.cost),
                    "volume": m_pos.volume,
                    "frozen_volume": m_pos.frozen_volume,
                    "settlement_frozen_volume": m_pos.settlement_frozen_volume,
                    "settlement_days": m_pos.settlement_days,
                    "settlement_queue_json": m_pos.settlement_queue_json,
                    "frozen_money": str(m_pos.frozen_money),
                    "price": str(m_pos.price),
                    "fee": str(m_pos.fee),
                    "uuid": m_pos.uuid,
                })

            has_state = float(p.cash) > 0 or len(positions_data) > 0

            return ServiceResult.success({
                "cash": str(p.cash),
                "frozen": str(p.frozen),
                "fee": str(p.total_fee),
                "positions": positions_data,
                "has_state": has_state,
            })

        except Exception as e:
            GLOG.ERROR(f"Failed to load persisted portfolio state: {e}")
            return ServiceResult.error(f"Database operation failed: {str(e)}")

    def _get_position_crud(self):
        """获取 PositionCRUD 实例（延迟导入避免循环依赖）"""
        from ginkgo import services
        return services.data.cruds.position()

    def reset_stale_running(self) -> ServiceResult:
        """
        将 PAPER/LIVE 模式下 RUNNING 或 STOPPING 状态的组合重置为 STOPPED。

        用于 Worker 启动时清理上次异常退出残留的状态：
        - RUNNING：Worker crash 后未来得及设 STOPPED
        - STOPPING：Service.stop() 已设 STOPPING 但 Worker 未收到 unload 命令
        """
        try:
            reset_count = 0
            stale_states = (PORTFOLIO_RUNSTATE_TYPES.RUNNING.value, PORTFOLIO_RUNSTATE_TYPES.STOPPING.value)
            for mode_value in (PORTFOLIO_MODE_TYPES.PAPER.value, PORTFOLIO_MODE_TYPES.LIVE.value):
                for stale_state in stale_states:
                    portfolios = self._crud_repo.find(
                        filters={"mode": mode_value, "state": stale_state}
                    )
                    for p in portfolios:
                        self._crud_repo.modify(
                            filters={"uuid": p.uuid},
                            updates={"state": PORTFOLIO_RUNSTATE_TYPES.STOPPED.value},
                        )
                        reset_count += 1
                        state_name = "RUNNING" if stale_state == 1 else "STOPPING"
                        GLOG.INFO(f"Reset stale {state_name} portfolio {p.uuid[:8]} -> STOPPED")

            if reset_count > 0:
                GLOG.INFO(f"Reset {reset_count} stale RUNNING portfolios")

            return ServiceResult.success(
                {"reset_count": reset_count},
                f"重置 {reset_count} 个残留 RUNNING 组合"
            )
        except Exception as e:
            GLOG.ERROR(f"重置残留 RUNNING 组合失败: {e}")
            return ServiceResult.error(f"重置残留 RUNNING 组合失败: {str(e)}")

    def stop(self, portfolio_id: str) -> ServiceResult:
        """
        停止 PAPER/LIVE portfolio（发送 Kafka unload 命令）

        Args:
            portfolio_id: 投资组合UUID

        Returns:
            ServiceResult: 操作结果
        """
        try:
            if not portfolio_id or not portfolio_id.strip():
                return ServiceResult.error("投资组合ID不能为空")

            # 查询 portfolio 信息
            portfolios = self._crud_repo.find(filters={"uuid": portfolio_id})
            if not portfolios:
                return ServiceResult.error(f"投资组合不存在: {portfolio_id}")

            portfolio = portfolios[0]
            mode = getattr(portfolio, 'mode', -1)
            state = getattr(portfolio, 'state', 0)

            # 校验 mode
            if mode == PORTFOLIO_MODE_TYPES.BACKTEST.value:
                return ServiceResult.error("回测模式组合不支持 stop，请直接删除")

            # 校验 state
            if state == PORTFOLIO_RUNSTATE_TYPES.STOPPED.value:
                return ServiceResult.error("组合已停止")
            if state == PORTFOLIO_RUNSTATE_TYPES.STOPPING.value:
                return ServiceResult.error("组合正在停止中，请等待")

            # 更新 state 为 STOPPING
            self._crud_repo.modify(
                filters={"uuid": portfolio_id},
                updates={"state": PORTFOLIO_RUNSTATE_TYPES.STOPPING.value},
            )
            GLOG.INFO(f"Portfolio {portfolio_id[:8]} state -> STOPPING")

            # 发送 Kafka unload 命令
            from ginkgo.messages.control_command import ControlCommand
            from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
            from ginkgo.interfaces.kafka_topics import KafkaTopics

            cmd = ControlCommand.unload(portfolio_id)
            producer = GinkgoProducer()
            success = producer.send(KafkaTopics.CONTROL_COMMANDS, cmd.to_dict())

            if success:
                GLOG.INFO(f"[STOP] Kafka unload command sent for {portfolio_id[:8]}")
            else:
                GLOG.WARN(f"[STOP] Failed to send Kafka unload command for {portfolio_id[:8]}")

            return ServiceResult.success(
                {"portfolio_id": portfolio_id},
                "停止命令已发送"
            )

        except Exception as e:
            GLOG.ERROR(f"停止投资组合失败: {e}")
            return ServiceResult.error(f"停止投资组合失败: {str(e)}")

    @retry(max_try=3)
    def delete(self, portfolio_id: str, **kwargs) -> ServiceResult:
        """
        删除投资组合（包括清理相关文件映射和参数）

        Args:
            portfolio_id: 投资组合UUID

        Returns:
            ServiceResult: 删除结果
        """
        try:
            # 输入验证
            if not portfolio_id or not portfolio_id.strip():
                return ServiceResult.error("投资组合ID不能为空")

            # 检查投资组合是否存在
            exists_result = self.exists(portfolio_id=portfolio_id)
            if not exists_result.is_success():
                return ServiceResult.error(f"检查投资组合存在性失败: {exists_result.error}")

            if not exists_result.data.get("exists", False):
                return ServiceResult.error(f"投资组合不存在: {portfolio_id}")

            # 检查 PAPER/LIVE 运行状态保护
            portfolios = self._crud_repo.find(filters={"uuid": portfolio_id})
            if portfolios:
                p = portfolios[0]
                mode = getattr(p, 'mode', -1)
                state = getattr(p, 'state', 0)
                if mode in (PORTFOLIO_MODE_TYPES.PAPER.value, PORTFOLIO_MODE_TYPES.LIVE.value):
                    if state in (PORTFOLIO_RUNSTATE_TYPES.RUNNING.value, PORTFOLIO_RUNSTATE_TYPES.STOPPING.value):
                        state_name = {v.value: k for k, v in PORTFOLIO_RUNSTATE_TYPES.__members__.items()}.get(state, str(state))
                        return ServiceResult.error(
                            f"组合正在{state_name}状态，请先停止后再删除"
                        )

            deleted_count = 0
            mappings_deleted = 0
            parameters_deleted = 0
            warnings = []

            # 清理投资组合-文件映射和参数
            try:
                file_mappings = self._portfolio_file_mapping_crud.find(
                    filters={"portfolio_id": portfolio_id}
                )

                for mapping in file_mappings:
                    # 删除关联参数
                    try:
                        self._param_crud.remove(
                            filters={"mapping_id": mapping.uuid}
                        )
                    except Exception as e:
                        warnings.append(f"删除映射参数失败 {mapping.uuid}: {str(e)}")

                # 删除投资组合-文件映射
                self._portfolio_file_mapping_crud.remove(
                    filters={"portfolio_id": portfolio_id}
                )

            except Exception as e:
                warnings.append(f"清理映射关系时出错: {str(e)}")

            # 软删除投资组合
            self._crud_repo.soft_remove(
                filters={"uuid": portfolio_id}
            )

            # 如果是已部署的 target，将对应 deployment 状态更新为 STOPPED
            if hasattr(self, '_deployment_crud') and self._deployment_crud:
                deployments = self._deployment_crud.find(
                    filters={"target_portfolio_id": portfolio_id}
                )
                for d in deployments:
                    if getattr(d, 'status', -1) == 1:  # DEPLOYED
                        self._deployment_crud.modify(
                            filters={"uuid": d.uuid},
                            updates={"status": 3},  # STOPPED
                        )

            GLOG.INFO(f"成功删除投资组合 {portfolio_id}")

            result_data = {
                "portfolio_id": portfolio_id,
                "mappings_deleted": mappings_deleted,
                "parameters_deleted": parameters_deleted,
                "warnings": warnings
            }

            message = f"投资组合删除成功: {portfolio_id}"
            if warnings:
                message += f" (附带{len(warnings)}个警告)"

            return ServiceResult.success(result_data, message)

        except Exception as e:
            GLOG.ERROR(f"删除投资组合失败 {portfolio_id}: {str(e)}")
            return ServiceResult.error(f"删除投资组合失败: {str(e)}")

    # ==================== 投资组合组件管理方法 ====================

    @retry(max_try=3)
    def mount_component(
        self, portfolio_id: str, component_id: str, component_name: str, component_type: FILE_TYPES
    ) -> ServiceResult:
        """
        为投资组合挂载量化交易组件，建立组合与组件的关联关系

        Args:
            portfolio_id: 投资组合UUID标识符
            component_id: 组件文件的UUID标识符
            component_name: 组件在投资组合中的显示名称
            component_type: 组件类型枚举值，确定组件功能分类

        Returns:
            ServiceResult: 包含挂载状态和操作信息的详细结果

        """
        try:
            # 输入验证
            if not portfolio_id or not portfolio_id.strip():
                return ServiceResult.error("投资组合ID不能为空")

            if not component_id or not component_id.strip():
                return ServiceResult.error("组件ID不能为空")

            if not component_name or not component_name.strip():
                return ServiceResult.error("组件名称不能为空")

            # 检查投资组合是否存在
            exists_result = self.exists(portfolio_id=portfolio_id)
            if not exists_result.is_success():
                return ServiceResult.error(f"检查投资组合存在性失败: {exists_result.error}")

            if not exists_result.data.get("exists", False):
                return ServiceResult.error(f"投资组合不存在: {portfolio_id}")

            # 检查组件是否已经挂载
            try:
                existing_components = self.get_components(portfolio_id=portfolio_id)
                if existing_components.is_success():
                    for component in existing_components.data:
                        if component.get("file_id") == component_id:
                            return ServiceResult.error(f"组件已挂载到投资组合: {component_name}")
            except Exception as e:
                GLOG.WARN(f"检查组件挂载状态失败: {str(e)}")

            # 创建挂载关系
            with self._portfolio_file_mapping_crud.get_session() as session:
                mapping_record = self._portfolio_file_mapping_crud.create(
                    portfolio_id=portfolio_id,
                    file_id=component_id,
                    name=component_name,
                    type=component_type,
                    session=session
                )

                mount_info = {
                    "mount_id": mapping_record.uuid,
                    "portfolio_id": portfolio_id,
                    "component_id": component_id,
                    "component_name": component_name,
                    "component_type": component_type.name if hasattr(component_type, "name") else str(component_type),
                }

                GLOG.INFO(f"成功为投资组合 {portfolio_id} 挂载组件 {component_name}")

                return ServiceResult.success(mount_info, f"组件挂载成功: {component_name}")

        except Exception as e:
            GLOG.ERROR(f"挂载组件失败 {component_name}: {str(e)}")
            return ServiceResult.error(f"挂载组件失败: {str(e)}")

    @retry(max_try=3)
    def unmount_component(self, mount_id: str) -> ServiceResult:
        """
        卸载投资组合的组件

        Args:
            mount_id: 挂载关系UUID

        Returns:
            ServiceResult: 卸载结果
        """
        try:
            # 输入验证
            if not mount_id or not mount_id.strip():
                return ServiceResult.error("挂载ID不能为空")

            # 软删除挂载关系
            self._portfolio_file_mapping_crud.soft_remove(
                filters={"uuid": mount_id}
            )

            GLOG.INFO(f"成功卸载组件挂载 {mount_id}")

            return ServiceResult.success(
                {"mount_id": mount_id},
                f"组件卸载成功: {mount_id}"
            )

        except Exception as e:
            GLOG.ERROR(f"卸载组件失败 {mount_id}: {str(e)}")
            return ServiceResult.error(f"卸载组件失败: {str(e)}")

    def get_components(self, portfolio_id: str = None, component_type: FILE_TYPES = None) -> ServiceResult:
        """
        获取投资组合的组件列表

        Args:
            portfolio_id: 投资组合UUID
            component_type: 组件类型过滤

        Returns:
            ServiceResult: 组件列表
        """
        try:
            filters = {"is_del": False}

            if portfolio_id:
                filters["portfolio_id"] = portfolio_id

            if component_type:
                filters["type"] = component_type

            mappings = self._portfolio_file_mapping_crud.find(filters=filters)

            # 转换为统一的组件信息格式
            components = []
            for mapping in mappings or []:
                component_info = {
                    "mount_id": mapping.uuid,
                    "portfolio_id": mapping.portfolio_id,
                    "component_id": mapping.file_id,
                    "component_name": mapping.name,
                    "component_type": mapping.type.name if hasattr(mapping.type, "name") else str(mapping.type),
                    "created_at": mapping.created_at.isoformat() if hasattr(mapping, 'created_at') else None,
                }
                components.append(component_info)

            return ServiceResult.success(components, f"获取到{len(components)}个组件")

        except Exception as e:
            GLOG.ERROR(f"获取组件列表失败: {str(e)}")
            return ServiceResult.error(f"获取组件列表失败: {str(e)}")

  
    # ==================== 标准接口方法 ====================

    def get_names_by_ids(self, portfolio_ids: List[str]) -> Dict[str, str]:
        """批量查询组合名称

        Args:
            portfolio_ids: 组合 UUID 列表

        Returns:
            Dict[str, str]: {uuid: name} 映射
        """
        if not portfolio_ids:
            return {}
        try:
            portfolios = self._crud_repo.find(filters={"uuid__in": list(portfolio_ids)})
            return {getattr(p, 'uuid', ''): getattr(p, 'name', '') for p in portfolios}
        except Exception as e:
            GLOG.ERROR(f"批量查询组合名称失败: {e}")
            return {}

    def get(self, portfolio_id: str = None, name: str = None, mode: PORTFOLIO_MODE_TYPES = None, state: PORTFOLIO_RUNSTATE_TYPES = None, **kwargs) -> ServiceResult:
        """
        获取投资组合数据

        Args:
            portfolio_id: 投资组合UUID
            name: 投资组合名称
            mode: 运行模式筛选
            state: 运行状态筛选
            **kwargs: 其他过滤条件

        Returns:
            ServiceResult: 查询结果
        """
        try:
            if portfolio_id:
                # 按UUID查询
                portfolios = self._crud_repo.find(filters={"uuid": portfolio_id, "is_del": False})
                if not portfolios:
                    return ServiceResult.error(f"投资组合不存在: {portfolio_id}")
                return ServiceResult.success(portfolios, "获取投资组合成功")

            elif name:
                # 按名称查询
                portfolios = self._crud_repo.find(filters={"name": name, "is_del": False})
                return ServiceResult.success(portfolios, f"获取到{len(portfolios)}个投资组合")

            else:
                # 按条件查询
                filters = kwargs.get('filters', {})
                filters['is_del'] = False

                if mode is not None:
                    filters['mode'] = PORTFOLIO_MODE_TYPES.validate_input(mode)

                if state is not None:
                    filters['state'] = PORTFOLIO_RUNSTATE_TYPES.validate_input(state)

                portfolios = self._crud_repo.find(filters=filters)
                return ServiceResult.success(portfolios, f"获取到{len(portfolios)}个投资组合")

        except Exception as e:
            GLOG.ERROR(f"获取投资组合失败: {str(e)}")
            return ServiceResult.error(f"获取投资组合失败: {str(e)}")

    def count(self, name: str = None, mode: PORTFOLIO_MODE_TYPES = None, state: PORTFOLIO_RUNSTATE_TYPES = None, **kwargs) -> ServiceResult:
        """
        统计投资组合数量

        Args:
            name: 投资组合名称筛选
            mode: 运行模式筛选
            state: 运行状态筛选
            **kwargs: 其他过滤条件

        Returns:
            ServiceResult: 统计结果
        """
        try:
            filters = kwargs.get('filters', {})
            filters['is_del'] = False

            if name:
                filters['name'] = name
            if mode is not None:
                filters['mode'] = PORTFOLIO_MODE_TYPES.validate_input(mode)
            if state is not None:
                filters['state'] = PORTFOLIO_RUNSTATE_TYPES.validate_input(state)

            count = self._crud_repo.count(filters=filters)

            return ServiceResult.success(
                {"count": count},
                f"统计到{count}个投资组合"
            )

        except Exception as e:
            GLOG.ERROR(f"统计投资组合失败: {str(e)}")
            return ServiceResult.error(f"统计投资组合失败: {str(e)}")

    def get_stats(self) -> ServiceResult:
        """获取 Portfolio 聚合统计（数据库级别 O(1)）"""
        try:
            from sqlalchemy import func
            from ginkgo.data.models.model_portfolio import MPortfolio

            crud = self._crud_repo

            total = crud.count(filters={"is_del": False})
            running = crud.count(filters={"is_del": False, "state": 1})

            conn = crud._get_connection()
            with conn.get_session() as s:
                row = s.query(
                    func.sum(MPortfolio.initial_capital),
                    func.avg(MPortfolio.cash / MPortfolio.initial_capital),
                ).filter(
                    MPortfolio.is_del == False,
                    MPortfolio.initial_capital > 0,
                ).one()

            total_assets = float(row[0] or 0)
            avg_net_value = round(float(row[1] or 1.0), 4)

            return ServiceResult.success({
                "total": total,
                "running": running,
                "avg_net_value": avg_net_value,
                "total_assets": total_assets,
            })
        except Exception as e:
            GLOG.ERROR(f"获取 Portfolio 统计失败: {e}")
            return ServiceResult.success({
                "total": 0,
                "running": 0,
                "avg_net_value": 1.0,
                "total_assets": 0,
            })

    def exists(self, portfolio_id: str = None, name: str = None, **kwargs) -> ServiceResult:
        """
        检查投资组合是否存在

        Args:
            portfolio_id: 投资组合UUID
            name: 投资组合名称
            **kwargs: 其他检查条件

        Returns:
            ServiceResult: 检查结果
        """
        try:
            if not portfolio_id and not name:
                return ServiceResult.error("必须提供portfolio_id或name参数")

            if portfolio_id:
                exists = self._crud_repo.exists(filters={"uuid": portfolio_id, "is_del": False})
            else:
                exists = self._crud_repo.exists(filters={"name": name, "is_del": False})

            return ServiceResult.success(
                {"exists": exists},
                f"投资组合{'存在' if exists else '不存在'}"
            )

        except Exception as e:
            GLOG.ERROR(f"检查投资组合存在性失败: {str(e)}")
            return ServiceResult.error(f"检查投资组合存在性失败: {str(e)}")

    def health_check(self) -> ServiceResult:
        """
        服务健康检查

        Returns:
            ServiceResult: 健康检查结果
        """
        try:
            health_info = {
                "service_name": "PortfolioService",
                "status": "healthy",
                "checks": {}
            }

            # 检查CRUD依赖
            if self._crud_repo is None:
                return ServiceResult.error("PortfolioCRUD依赖未初始化")

            health_info["checks"]["crud_dependency"] = {"status": "passed", "message": "PortfolioCRUD依赖正常"}

            # 检查数据库连接
            try:
                self._crud_repo.find()
                health_info["checks"]["database_connection"] = {"status": "passed", "message": "数据库连接正常"}
            except Exception as db_error:
                return ServiceResult.error(f"数据库连接失败: {str(db_error)}")

            # 检查服务功能
            try:
                count_result = self.count()
                if count_result.is_success():
                    total_count = count_result.data.get("count", 0)
                    health_info["checks"]["service_functionality"] = {
                        "status": "passed",
                        "message": f"服务功能正常，共{total_count}个投资组合"
                    }
                    health_info["total_portfolios"] = total_count
                else:
                    return ServiceResult.error("服务功能检查失败")
            except Exception as func_error:
                return ServiceResult.error(f"服务功能检查失败: {str(func_error)}")

            message = f"PortfolioService运行正常，共{health_info.get('total_portfolios', 0)}个投资组合"
            return ServiceResult.success(health_info, message)

        except Exception as e:
            GLOG.ERROR(f"PortfolioService健康检查失败: {str(e)}")
            return ServiceResult.error(f"健康检查失败: {str(e)}")

    def validate(self, portfolio_data: Dict[str, Any]) -> ServiceResult:
        """
        验证投资组合数据有效性

        Args:
            portfolio_data: 待验证的投资组合数据

        Returns:
            ServiceResult: 验证结果
        """
        try:
            if not isinstance(portfolio_data, dict):
                return ServiceResult.error("数据必须是字典格式")

            # 必填字段验证
            required_fields = ['name']
            missing_fields = [field for field in required_fields if not portfolio_data.get(field)]

            if missing_fields:
                return ServiceResult.error(
                    data={
                        "valid": False,
                        "missing_fields": missing_fields
                    },
                    error=f"缺少必填字段: {', '.join(missing_fields)}"
                )

            # 名称长度验证
            name = portfolio_data['name']
            if not name or not name.strip():
                return ServiceResult.error("投资组合名称不能为空")

            if len(name) > 100:
                return ServiceResult.error("投资组合名称不能超过100个字符")

            # 枚举值验证
            if 'mode' in portfolio_data:
                mode_value = portfolio_data['mode']
                if isinstance(mode_value, PORTFOLIO_MODE_TYPES):
                    pass  # Valid enum
                elif isinstance(mode_value, int):
                    try:
                        PORTFOLIO_MODE_TYPES(mode_value)
                    except ValueError:
                        return ServiceResult.error("mode字段值无效")
                else:
                    return ServiceResult.error("mode字段必须是枚举或整数")

            if 'state' in portfolio_data:
                state_value = portfolio_data['state']
                if isinstance(state_value, PORTFOLIO_RUNSTATE_TYPES):
                    pass  # Valid enum
                elif isinstance(state_value, int):
                    try:
                        PORTFOLIO_RUNSTATE_TYPES(state_value)
                    except ValueError:
                        return ServiceResult.error("state字段值无效")
                else:
                    return ServiceResult.error("state字段必须是枚举或整数")

            return ServiceResult.success(
                data={"valid": True},
                message="投资组合数据验证通过"
            )

        except Exception as e:
            GLOG.ERROR(f"投资组合数据验证失败: {str(e)}")
            return ServiceResult.error(f"数据验证失败: {str(e)}")

    def check_integrity(self, portfolio_id: str = None) -> ServiceResult:
        """
        检查投资组合数据完整性

        Args:
            portfolio_id: 投资组合UUID，为空则检查所有

        Returns:
            ServiceResult: 完整性检查结果
        """
        try:
            issues = []

            if portfolio_id:
                # 检查单个投资组合
                get_result = self.get(portfolio_id=portfolio_id)
                if not get_result.is_success():
                    return ServiceResult.error(f"获取投资组合失败: {get_result.error}")

                portfolios = get_result.data
            else:
                # 检查所有投资组合
                get_result = self.get()
                if not get_result.is_success():
                    return ServiceResult.error(f"获取投资组合列表失败: {get_result.error}")

                portfolios = get_result.data

            total_count = len(portfolios) if portfolios else 0

            for portfolio in portfolios or []:
                portfolio_issues = []

                if not portfolio.name:
                    portfolio_issues.append("缺少投资组合名称")

                if portfolio_issues:
                    issues.append({
                        "portfolio_id": portfolio.uuid,
                        "portfolio_name": portfolio.name,
                        "issues": portfolio_issues
                    })

            integrity_score = 1.0
            if total_count > 0:
                integrity_score = (total_count - len(issues)) / total_count

            result = {
                "total_portfolios": total_count,
                "portfolios_with_issues": len(issues),
                "integrity_score": integrity_score,
                "issues": issues
            }

            message = f"完整性检查完成，{total_count}个投资组合中{len(issues)}个存在问题"
            return ServiceResult.success(result, message)

        except Exception as e:
            GLOG.ERROR(f"投资组合完整性检查失败: {str(e)}")
            return ServiceResult.error(f"完整性检查失败: {str(e)}")

    def build_position_writer(self):
        """构建持仓持久化 writer（委托给 PositionService）。"""
        from ginkgo.data.containers import container
        from ginkgo.data.services.position_service import PositionService
        position_crud = container.cruds.position()
        return PositionService(crud_repo=position_crud)

    def build_redis_writer(self):
        """构建 Redis 状态 writer（委托给 RedisService）。"""
        from ginkgo.data.containers import container
        return container.redis_service()

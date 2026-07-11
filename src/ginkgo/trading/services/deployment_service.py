# Upstream: API Server, CLI
# Downstream: PortfolioService, FileService, MappingService, BacktestTaskService
# Role: 部署编排服务 - 从组合一键部署到模拟盘/实盘

from typing import Optional, List
from ginkgo.libs import GLOG
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.enums import PORTFOLIO_MODE_TYPES, FILE_TYPES
from ginkgo.data.models import MDeployment
from ginkgo.enums import DEPLOYMENT_STATUS

# #6285: int→枚举名映射，供 info/list 输出人类可读部署状态。
# 动态收集 DEPLOYMENT_STATUS 类属性，新增成员自动覆盖，无需手维护 dict。
_DEPLOYMENT_STATUS_NAMES = {
    v: k for k, v in vars(DEPLOYMENT_STATUS).items()
    if not k.startswith("_") and isinstance(v, int)
}


def _status_name(status: int) -> str:
    """裸 int → 枚举名（未知值降级为字符串形式，不抛错）。"""
    return _DEPLOYMENT_STATUS_NAMES.get(status, str(status))


class DeploymentService(BaseService):
    """部署编排服务"""

    def __init__(
        self,
        portfolio_service=None,
        mapping_service=None,
        file_service=None,
        deployment_crud=None,
        broker_instance_crud=None,
        live_account_service=None,
        mongo_driver=None,
        param_crud=None,
        backtest_task_service=None,
        capacity_checker=None,
    ):
        self._portfolio_service = portfolio_service
        self._mapping_service = mapping_service
        self._file_service = file_service
        self._deployment_crud = deployment_crud
        self._broker_instance_crud = broker_instance_crud
        self._live_account_service = live_account_service
        self._mongo_driver = mongo_driver
        self._param_crud = param_crud
        # #5196: deploy 自动溯源回测→部署链路(未显式传 source_task_id 时取 portfolio 最近 completed 回测)
        self._backtest_task_service = backtest_task_service
        # #4800: 集群容量预检 callable，返回 {"healthy_nodes","max_per_node",
        # "total_slots","used_slots","available_slots"}。None=跳过预检(向后兼容，
        # 容量查询依赖 Redis，未注入时不阻塞 deploy)。
        self._capacity_checker = capacity_checker

    def deploy(
        self,
        portfolio_id: str,
        mode: PORTFOLIO_MODE_TYPES,
        account_id: Optional[str] = None,
        name: Optional[str] = None,
        source_task_id: Optional[str] = None,
    ) -> ServiceResult:
        """
        一键部署：从组合部署到模拟盘/实盘

        Args:
            portfolio_id: 源组合 portfolio_id
            mode: PAPER 或 LIVE
            account_id: MLiveAccount.uuid (live模式必填)
            name: 新Portfolio名称 (可选，自动生成)
            source_task_id: 源回测任务 id (可选, #6285 记录回测→部署链路便于追溯)

        Returns:
            ServiceResult with data: {"portfolio_id": str, "deployment_id": str}
        """
        # 1. 验证源 Portfolio 存在
        portfolio_result = self._portfolio_service.get(portfolio_id=portfolio_id)
        if not portfolio_result.success or not portfolio_result.data:
            return ServiceResult(success=False, error=f"组合不存在: {portfolio_id}")

        portfolio_list = portfolio_result.data
        portfolio_obj = portfolio_list[0] if portfolio_list else None
        if not portfolio_obj:
            return ServiceResult(success=False, error=f"组合不存在: {portfolio_id}")

        # 1.5 #4800: 集群容量预检（best-effort，防"假成功"）
        # deploy 与 worker 端 Scheduler 跨进程解耦: deploy 只写记录+发 Kafka，真正分配由
        # LoadBalancer 异步完成。容量满时 worker 仅 logger.warning，deploy 侧无从知晓仍报成功。
        # 此处注入 capacity_checker(查询 Redis 心跳键聚合可用槽位)，满载则早失败 + 明确提示，
        # 不写 PENDING 记录避免假成功 + 垃圾记录。None=未注入(向后兼容)，跳过预检。
        _checker = getattr(self, "_capacity_checker", None)
        if _checker is not None:
            cap = _checker() or {}
            available = cap.get("available_slots", 1)
            if available <= 0:
                healthy = cap.get("healthy_nodes", 0)
                max_per = cap.get("max_per_node", 0)
                return ServiceResult(
                    success=False,
                    error=(
                        f"集群容量已满: 当前 {healthy} 个健康节点, "
                        f"每节点上限 {max_per}, 可用槽位 0。"
                        f"建议扩容 worker 或清理历史 paper portfolio。"
                    ),
                )

        # 2. 检查是否已冻结
        if self._portfolio_service.is_portfolio_frozen(portfolio_id):
            return ServiceResult(success=False, error="组合已部署，不可再次部署")

        # 3. 实盘模式验证账号
        if mode == PORTFOLIO_MODE_TYPES.LIVE and not account_id:
            return ServiceResult(success=False, error="实盘部署需要提供 account_id")

        # 3a. #6281: account 存在性预检
        # 非法 account 不应直冲下游查询，否则环境层 DB 列漂移时抛裸 1054 (见 arch_create_all_no_alter_drift)。
        if mode == PORTFOLIO_MODE_TYPES.LIVE and account_id:
            account_res = self._live_account_service.get_account_by_uuid(account_id)
            if not account_res or not account_res.get("success"):
                return ServiceResult(
                    success=False, error=f"实盘账户不存在: {account_id}"
                )

        # 3c. 检查 live_account 是否已被其他 Portfolio 绑定
        if mode == PORTFOLIO_MODE_TYPES.LIVE and account_id:
            existing_brokers = self._broker_instance_crud.get_broker_by_live_account(account_id)
            if existing_brokers:
                return ServiceResult(success=False, error="该实盘账号已被其他组合绑定")

        # 3d. #5196: 自动溯源回测→部署链路
        # 调用方未显式传 source_task_id 时, 从 portfolio 最近一次 completed 回测取 task_id 填入,
        # 使 deploy info 的"源回测任务"字段可追溯。无 completed 回测时留空并 INFO(不阻断部署)。
        # 显式 source_task_id 优先, 不覆盖调用方意图。
        if source_task_id is None and self._backtest_task_service is not None:
            bt_res = self._backtest_task_service.get_latest_completed_task_id(portfolio_id)
            if bt_res and getattr(bt_res, "success", False) and bt_res.data:
                source_task_id = bt_res.data
                GLOG.INFO(f"自动溯源源回测任务: {source_task_id[:8]}... (portfolio={portfolio_id[:8]}...)")
            else:
                GLOG.INFO(f"组合 {portfolio_id[:8]}... 无已完成回测, source_task_id 留空")

        # 3b. 创建 PENDING deployment 记录
        deployment = MDeployment(
            source_task_id=source_task_id,
            target_portfolio_id="",
            source_portfolio_id=portfolio_id,
            mode=mode.value,
            account_id=account_id,
            status=DEPLOYMENT_STATUS.PENDING,
        )
        self._deployment_crud.add(deployment)
        deployment_id = deployment.uuid

        # 4-8. 核心部署流程（失败时标记 deployment 为 FAILED）
        try:
            return self._deploy_core(
                source_portfolio_id=portfolio_id,
                mode=mode,
                account_id=account_id,
                name=name,
                portfolio_name=getattr(portfolio_obj, "name", None) or portfolio_id,
                deployment_id=deployment_id,
                # #6200: 目标组合继承源组合 initial_capital(原漏传致重置为 service 默认 1000000)
                initial_capital=float(getattr(portfolio_obj, "initial_capital", 0) or 0),
            )
        except Exception as e:
            GLOG.ERROR(f"部署流程异常: {e}")
            try:
                self._deployment_crud.modify(
                    filters={"uuid": deployment_id},
                    updates={"status": DEPLOYMENT_STATUS.FAILED},
                )
            except Exception as e:
                GLOG.WARNING(f"{e}")
                pass
            return ServiceResult(success=False, error=str(e))

    def _deploy_core(
        self,
        source_portfolio_id: str,
        mode: PORTFOLIO_MODE_TYPES,
        account_id: Optional[str],
        name: Optional[str],
        portfolio_name: str,
        deployment_id: str,
        initial_capital: float = 0,
    ) -> ServiceResult:
        """核心部署流程: 步骤 4-8。失败时由调用方标记 FAILED。"""
        # 4. 读取原 Portfolio 的组件映射
        mappings_result = self._mapping_service.get_portfolio_mappings(
            source_portfolio_id, include_params=True
        )
        if not mappings_result.success:
            raise RuntimeError(f"读取Portfolio组件映射失败: {mappings_result.error}")

        mappings = mappings_result.data if mappings_result.data else []

        # 5. 创建新 Portfolio
        if not name:
            mode_label = "PAPER" if mode == PORTFOLIO_MODE_TYPES.PAPER else "LIVE"
            name = f"{portfolio_name}_{mode_label}"

        portfolio_result = self._portfolio_service.add(
            name=name,
            mode=mode,
            description=f"部署自组合 {source_portfolio_id}",
            initial_capital=initial_capital,
        )
        if not portfolio_result.success:
            raise RuntimeError(f"创建Portfolio失败: {portfolio_result.error}")

        new_portfolio_id = portfolio_result.data.get("uuid")
        GLOG.INFO(f"创建新Portfolio: {new_portfolio_id} (mode={mode.value})")

        # 5c. Live模式: 回写 live_account_id 到 Portfolio
        # #6073: 检查 update 返回值，失败时终止部署（否则 live_account_id 未写入但部署仍标记成功）
        if mode == PORTFOLIO_MODE_TYPES.LIVE and account_id:
            update_result = self._portfolio_service.update(
                portfolio_id=new_portfolio_id,
                live_account_id=account_id,
            )
            if not update_result.success:
                GLOG.ERROR(f"回写 live_account_id 失败: {update_result.error}")
                raise RuntimeError(f"回写 live_account_id 失败: {update_result.error}")

        # 5. 引用组件: Mapping(新建, 引用源file_id) + Param(原始值复制)
        for mapping in mappings:
            if isinstance(mapping, dict):
                file_id = mapping.get("file_id")
                file_type = mapping.get("type")
                mapping_name = mapping.get("name", "")
                mapping_uuid = mapping.get("uuid", "")
            else:
                file_id = getattr(mapping, "file_id", None)
                file_type = getattr(mapping, "type", None)
                mapping_name = getattr(mapping, "name", "")
                mapping_uuid = getattr(mapping, "uuid", "")
            if not file_id:
                continue

            file_type_enum = FILE_TYPES(file_type) if file_type else None

            # 5a. Create new Mapping (引用源文件，不克隆)
            add_result = self._mapping_service.add_file(
                portfolio_uuid=new_portfolio_id,
                file_id=file_id,
                file_type=file_type_enum,
                name=mapping_name,
            )
            if not add_result.success:
                GLOG.WARN(f"创建映射失败: {add_result.error}")
                continue

            # 5b. Copy Params (原始值，不经过 json 序列化)
            if mapping_uuid:
                new_mapping_id = add_result.data.get("mapping_id")
                if new_mapping_id:
                    self._copy_params_raw(mapping_uuid, new_mapping_id)

        # 6. Copy MongoDB Graph
        try:
            self._copy_graph(source_portfolio_id, new_portfolio_id)
        except Exception as e:
            GLOG.WARN(f"图结构拷贝失败(非致命): {e}")

        # 7. Live模式: 创建 MBrokerInstance
        if mode == PORTFOLIO_MODE_TYPES.LIVE and account_id:
            try:
                self._broker_instance_crud.add_broker_instance(
                    portfolio_id=new_portfolio_id,
                    live_account_id=account_id,
                    state="uninitialized",
                )
            except Exception as e:
                GLOG.ERROR(f"创建Broker实例失败: {e}")
                raise RuntimeError(f"创建Broker实例失败: {str(e)}")

        # 8. 更新 MDeployment 状态为 DEPLOYED
        try:
            self._deployment_crud.modify(
                filters={"uuid": deployment_id},
                updates={
                    "target_portfolio_id": new_portfolio_id,
                    "status": DEPLOYMENT_STATUS.DEPLOYED,
                },
            )
        except Exception as e:
            GLOG.WARN(f"更新部署记录状态失败(非致命): {e}")

        # 9. 发送 Kafka deploy 命令通知 PaperTradingWorker
        try:
            from ginkgo.messages.control_command import ControlCommand
            from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
            from ginkgo.interfaces.kafka_topics import KafkaTopics

            cmd = ControlCommand.deploy(new_portfolio_id)
            producer = GinkgoProducer()
            success = producer.send(KafkaTopics.CONTROL_COMMANDS, cmd.to_dict())
            if success:
                GLOG.INFO(f"[DEPLOY] Kafka deploy command sent for {new_portfolio_id[:8]}")
            else:
                GLOG.WARN(f"[DEPLOY] Failed to send Kafka deploy command for {new_portfolio_id[:8]}")
        except Exception as e:
            GLOG.WARN(f"[DEPLOY] Kafka notification failed (non-fatal): {e}")

        GLOG.INFO(f"部署完成: {new_portfolio_id} <- {source_portfolio_id}")
        result = ServiceResult(success=True)
        result.data = {
            "portfolio_id": new_portfolio_id,
            "deployment_id": deployment_id,
        }
        return result

    def get_deployment_info(self, portfolio_id: str) -> ServiceResult:
        """获取部署信息"""
        records = self._deployment_crud.get_by_target_portfolio(portfolio_id)
        if not records:
            return ServiceResult(success=False, error="未找到部署记录")

        deployment = records[0]
        result = ServiceResult(success=True)
        result.data = {
            "source_task_id": deployment.source_task_id,
            "target_portfolio_id": deployment.target_portfolio_id,
            "source_portfolio_id": deployment.source_portfolio_id,
            "mode": deployment.mode,
            "account_id": deployment.account_id,
            "status": deployment.status,
            "status_name": _status_name(deployment.status),  # #6285
            "create_at": str(deployment.create_at) if deployment.create_at else None,
        }
        return result

    def _deployment_to_dict(self, r) -> dict:
        """部署记录 → dict（list_deployments / find_by_* 共用，#3882 统一返回类型）。"""
        return {
            "deployment_id": r.uuid,
            "source_task_id": r.source_task_id,
            "target_portfolio_id": r.target_portfolio_id,
            "source_portfolio_id": r.source_portfolio_id,
            "mode": r.mode,
            "account_id": r.account_id,
            "status": r.status,
            "status_name": _status_name(r.status),  # #6285
            "create_at": str(r.create_at) if r.create_at else None,
        }

    def get_deployment_by_id(self, deployment_id: str) -> ServiceResult:
        """按部署记录 UUID 获取部署信息（#5335：deploy info <deployment_id>）"""
        records = self._deployment_crud.get_by_uuid(deployment_id)
        if not records:
            return ServiceResult(success=False, error="未找到部署记录")

        deployment = records[0]
        result = ServiceResult(success=True)
        result.data = {
            "source_task_id": deployment.source_task_id,
            "target_portfolio_id": deployment.target_portfolio_id,
            "source_portfolio_id": deployment.source_portfolio_id,
            "mode": deployment.mode,
            "account_id": deployment.account_id,
            "status": deployment.status,
            "status_name": _status_name(deployment.status),  # #6285
            "create_at": str(deployment.create_at) if deployment.create_at else None,
        }
        return result

    def list_deployments(self, portfolio_id: str = None) -> ServiceResult:
        """列出部署记录"""
        if portfolio_id:
            records = self._deployment_crud.get_by_source_portfolio(portfolio_id)
        else:
            records = self._deployment_crud.find()

        if not records:
            return ServiceResult(success=True, data=[])

        result = ServiceResult(success=True)
        result.data = [self._deployment_to_dict(r) for r in records]
        return result

    # #3867: API 层不再直调 CRUD，通过 Service 封装

    def find_by_source_portfolio(self, source_portfolio_id: str) -> ServiceResult:
        """查找源组合的所有部署记录（返回 dict 列表，字段对齐 list_deployments，#3882）。"""
        try:
            records = self._deployment_crud.get_by_source_portfolio(source_portfolio_id)
            return ServiceResult.success(data=[self._deployment_to_dict(r) for r in (records or [])])
        except Exception as e:
            GLOG.ERROR(f"Failed to find deployments by source: {e}")
            return ServiceResult.error(f"Failed to find deployments: {str(e)}")

    def find_by_target_portfolio(self, target_portfolio_id: str) -> ServiceResult:
        """查找目标组合的所有部署记录（返回 dict 列表，字段对齐 list_deployments，#3882）。"""
        try:
            records = self._deployment_crud.get_by_target_portfolio(target_portfolio_id)
            return ServiceResult.success(data=[self._deployment_to_dict(r) for r in (records or [])])
        except Exception as e:
            GLOG.ERROR(f"Failed to find deployments by target: {e}")
            return ServiceResult.error(f"Failed to find deployments: {str(e)}")

    def undeploy(self, deployment_id: str) -> ServiceResult:
        """撤销部署：停止目标 Portfolio，并将部署记录标记为 STOPPED。"""
        try:
            if not deployment_id or not deployment_id.strip():
                return ServiceResult(success=False, error="部署记录 ID 或 Portfolio ID 不能为空")

            records = []
            for finder in (
                self._deployment_crud.get_by_uuid,
                self._deployment_crud.get_by_source_portfolio,
                self._deployment_crud.get_by_target_portfolio,
            ):
                found = finder(deployment_id) or []
                records.extend(found)
                if found:
                    break

            if not records:
                return ServiceResult(success=False, error="未找到部署记录")

            deployment = next(
                (r for r in records if getattr(r, "status", None) == DEPLOYMENT_STATUS.DEPLOYED),
                records[0],
            )
            if getattr(deployment, "status", None) == DEPLOYMENT_STATUS.STOPPED:
                return ServiceResult(success=False, error="部署已停止")
            if getattr(deployment, "status", None) != DEPLOYMENT_STATUS.DEPLOYED:
                return ServiceResult(
                    success=False,
                    error=f"部署状态不允许撤销: {_status_name(getattr(deployment, 'status', None))}",
                )

            target_portfolio_id = getattr(deployment, "target_portfolio_id", "")
            if not target_portfolio_id:
                return ServiceResult(success=False, error="部署记录缺少目标 Portfolio")

            stop_result = self._portfolio_service.stop(target_portfolio_id)
            if not stop_result.success and "已停止" not in (stop_result.error or ""):
                return ServiceResult(success=False, error=stop_result.error)

            self._deployment_crud.modify(
                filters={"uuid": deployment.uuid},
                updates={"status": DEPLOYMENT_STATUS.STOPPED},
            )

            return ServiceResult(
                success=True,
                data={
                    "deployment_id": deployment.uuid,
                    "target_portfolio_id": target_portfolio_id,
                },
                message="撤销部署成功",
            )
        except Exception as e:
            GLOG.ERROR(f"撤销部署失败: {e}")
            return ServiceResult(success=False, error=f"撤销部署失败: {str(e)}")

    def _copy_params_raw(self, old_mapping_id: str, new_mapping_id: str) -> None:
        """原始值复制参数，不经过 json 序列化/反序列化"""
        from ginkgo.data.models import MParam

        source_params = self._param_crud.find_by_mapping_id(old_mapping_id)
        for p in source_params:
            new_param = MParam(
                mapping_id=new_mapping_id,
                index=p.index,
                value=p.value,
                source=p.source,
            )
            self._param_crud.add(new_param)

    def _copy_graph(self, source_portfolio_id: str, target_portfolio_id: str) -> None:
        """复制MongoDB图结构"""
        if not self._mongo_driver:
            return

        graph_result = self._mapping_service.get_portfolio_graph(source_portfolio_id)
        if not graph_result.success or not graph_result.data:
            return

        self._mapping_service.create_from_graph_editor(
            portfolio_uuid=target_portfolio_id,
            graph_data=graph_result.data,
            name=f"deploy_{target_portfolio_id[:8]}",
            # #6279: MySQL 映射已由 _deploy_core step5 从源组合权威复制（全类型+原始参数）。
            # 此处仅搬运 Mongo 图供 UI，绝不能按（经 CLI bind-component 绑定时可能不完整的）
            # 源图删除已建的 strategy/sizer 映射，否则 paper 组合装配 Strategies:0。
            sync_mysql=False,
        )

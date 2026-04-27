# Upstream: API Server, CLI
# Downstream: PortfolioService, FileService, MappingService, BacktestTaskService
# Role: 部署编排服务 - 从组合一键部署到模拟盘/实盘

from typing import Optional, List
from ginkgo.libs import GLOG
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.enums import PORTFOLIO_MODE_TYPES, FILE_TYPES
from ginkgo.data.models.model_deployment import MDeployment, DEPLOYMENT_STATUS


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
    ):
        self._portfolio_service = portfolio_service
        self._mapping_service = mapping_service
        self._file_service = file_service
        self._deployment_crud = deployment_crud
        self._broker_instance_crud = broker_instance_crud
        self._live_account_service = live_account_service
        self._mongo_driver = mongo_driver

    def deploy(
        self,
        portfolio_id: str,
        mode: PORTFOLIO_MODE_TYPES,
        account_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> ServiceResult:
        """
        一键部署：从组合部署到模拟盘/实盘

        Args:
            portfolio_id: 源组合 portfolio_id
            mode: PAPER 或 LIVE
            account_id: MLiveAccount.uuid (live模式必填)
            name: 新Portfolio名称 (可选，自动生成)

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

        # 2. 检查是否已冻结
        if self._portfolio_service.is_portfolio_frozen(portfolio_id):
            return ServiceResult(success=False, error="组合已部署，不可再次部署")

        # 3. 实盘模式验证账号
        if mode == PORTFOLIO_MODE_TYPES.LIVE and not account_id:
            return ServiceResult(success=False, error="实盘部署需要提供 account_id")

        # 3b. 创建 PENDING deployment 记录
        deployment = MDeployment(
            source_task_id=None,
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
            )
        except Exception as e:
            GLOG.ERROR(f"部署流程异常: {e}")
            try:
                self._deployment_crud.modify(
                    filters={"uuid": deployment_id},
                    updates={"status": DEPLOYMENT_STATUS.FAILED},
                )
            except Exception:
                pass
            return ServiceResult(success=False, error=f"部署失败: {str(e)}")

    def _deploy_core(
        self,
        source_portfolio_id: str,
        mode: PORTFOLIO_MODE_TYPES,
        account_id: Optional[str],
        name: Optional[str],
        portfolio_name: str,
        deployment_id: str,
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
        )
        if not portfolio_result.success:
            raise RuntimeError(f"创建Portfolio失败: {portfolio_result.error}")

        new_portfolio_id = portfolio_result.data.get("uuid")
        GLOG.INFO(f"创建新Portfolio: {new_portfolio_id} (mode={mode.value})")

        # 5. 深拷贝组件: MFile(clone) + Mapping(新建) + Param(复制)
        for mapping in mappings:
            old_file_id = getattr(mapping, "file_id", None)
            if not old_file_id:
                continue

            file_type = getattr(mapping, "type", None)
            mapping_name = getattr(mapping, "name", "")
            mapping_uuid = getattr(mapping, "uuid", "")

            # 5a. Clone MFile
            clone_name = f"{mapping_name}_{new_portfolio_id[:8]}"
            clone_result = self._file_service.clone(old_file_id, clone_name, file_type)
            if not clone_result.success:
                GLOG.WARN(f"克隆文件失败 {old_file_id}: {clone_result.error}")
                continue

            new_file_id = clone_result.data["file_info"]["uuid"]

            # 5b. Create new Mapping
            add_result = self._mapping_service.add_file(
                portfolio_uuid=new_portfolio_id,
                file_id=new_file_id,
                file_type=FILE_TYPES(file_type) if file_type else None,
                name=mapping_name,
            )
            if not add_result.success:
                GLOG.WARN(f"创建映射失败: {add_result.error}")
                continue

            # 5c. Copy Params from old mapping to new mapping
            if mapping_uuid:
                params_result = self._mapping_service.get_mapping_params(mapping_uuid)
                if params_result.success and params_result.data:
                    new_mapping_id = add_result.data.get("mapping_id")
                    if new_mapping_id:
                        self._copy_params(mapping_uuid, new_mapping_id, params_result.data)

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
        result.data = [
            {
                "deployment_id": r.uuid,
                "source_task_id": r.source_task_id,
                "target_portfolio_id": r.target_portfolio_id,
                "source_portfolio_id": r.source_portfolio_id,
                "mode": r.mode,
                "account_id": r.account_id,
                "status": r.status,
                "create_at": str(r.create_at) if r.create_at else None,
            }
            for r in records
        ]
        return result

    def _copy_params(self, old_mapping_id: str, new_mapping_id: str, params: List) -> None:
        """复制参数从旧mapping到新mapping"""
        from ginkgo.data.containers import container
        param_crud = container.cruds.param()

        for param in params:
            index = getattr(param, "index", 0)
            value = getattr(param, "value", "")
            source = getattr(param, "source", -1)
            param_crud.set_param_value(new_mapping_id, index, value, source)

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
        )

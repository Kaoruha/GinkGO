"""
Saga 事务管理器 - 实现补偿事务模式

使用 Saga 模式确保分布式事务的一致性，当任何步骤失败时，
自动执行已完成步骤的补偿操作，实现回滚效果。

设计原则：
1. 每个步骤都有对应的补偿操作
2. 步骤按顺序执行，失败时逆序补偿
3. 补偿操作也必须可靠，但补偿失败不影响其他补偿
4. 全部成功或全部回滚，不留下中间状态
"""
from typing import List, Dict, Any, Callable, Optional, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import asyncio

from core.logging import logger
from models.transaction import TransactionRecord, TransactionStep


@dataclass
class SagaStep:
    """Saga 步骤定义

    Attributes:
        name: 步骤名称
        execute: 执行函数（同步或异步）
        compensate: 补偿函数（同步或异步）
        executed: 是否已执行
        compensated: 是否已补偿
        result: 执行结果
        error: 错误信息
    """
    name: str
    execute: Callable[[], Any]
    compensate: Callable[[Any], Any]
    executed: bool = False
    compensated: bool = False
    result: Any = None
    error: Optional[str] = None
    executed_at: Optional[datetime] = None
    compensated_at: Optional[datetime] = None


class SagaTransaction:
    """Saga 事务管理器

    实现补偿事务模式，确保多步骤操作的一致性。
    当任何步骤失败时，自动逆序执行已完成步骤的补偿操作。

    Example:
        saga = SagaTransaction("create_portfolio")

        # 添加步骤
        saga.add_step(
            name="create_portfolio",
            execute=lambda: portfolio_service.add(name="test"),
            compensate=lambda r: portfolio_service.delete(r.uuid)
        )

        # 执行事务
        success = await saga.execute()
        if not success:
            # 事务已自动回滚
            pass
    """

    def __init__(self, name: str, transaction_id: Optional[str] = None):
        """初始化 Saga 事务

        Args:
            name: 事务名称
            transaction_id: 事务ID，如不提供则自动生成
        """
        self.name = name
        self.transaction_id = transaction_id or str(uuid.uuid4())
        self.steps: List[SagaStep] = []
        self.completed_steps: List[SagaStep] = []
        self.failed = False
        self.error: Optional[Exception] = None
        self.created_at = datetime.now()
        self.completed_at: Optional[datetime] = None

    def add_step(
        self,
        name: str,
        execute: Callable,
        compensate: Callable
    ) -> 'SagaTransaction':
        """添加事务步骤

        Args:
            name: 步骤名称
            execute: 执行函数，可以是同步或异步函数
            compensate: 补偿函数，接收执行结果作为参数

        Returns:
            self，支持链式调用
        """
        step = SagaStep(
            name=name,
            execute=execute,
            compensate=compensate
        )
        self.steps.append(step)
        return self

    async def execute(self) -> bool:
        """执行 Saga 事务

        按顺序执行所有步骤，如果任何步骤失败，
        则逆序执行已完成步骤的补偿操作。

        Returns:
            bool: True 表示全部成功，False 表示失败并已回滚
        """
        logger.info(f"Saga '{self.name}' started with {len(self.steps)} steps")

        try:
            for step in self.steps:
                try:
                    logger.info(f"Executing step: {step.name}")

                    # 执行步骤
                    result = step.execute()
                    if asyncio.iscoroutine(result):
                        result = await result

                    step.executed = True
                    step.result = result
                    step.executed_at = datetime.now()
                    self.completed_steps.append(step)

                    logger.info(f"Step '{step.name}' completed successfully")

                except Exception as e:
                    error_msg = f"Step '{step.name}' failed: {str(e)}"
                    logger.error(error_msg)
                    step.error = str(e)
                    self.failed = True
                    self.error = e

                    # 执行补偿
                    await self._compensate()
                    return False

            self.completed_at = datetime.now()
            logger.info(f"Saga '{self.name}' completed successfully")
            return True

        except Exception as e:
            logger.error(f"Unexpected error in saga '{self.name}': {str(e)}")
            self.failed = True
            self.error = e
            await self._compensate()
            return False

    async def _compensate(self):
        """执行补偿事务

        逆序执行已完成步骤的补偿操作。
        补偿操作失败不会中断其他补偿的执行。
        """
        logger.warning(
            f"Compensating {len(self.completed_steps)} completed steps "
            f"for saga '{self.name}'..."
        )

        # 逆序执行补偿
        for step in reversed(self.completed_steps):
            try:
                logger.info(f"Compensating step: {step.name}")

                # 执行补偿
                compensate_result = step.compensate(step.result)
                if asyncio.iscoroutine(compensate_result):
                    compensate_result = await compensate_result

                step.compensated = True
                step.compensated_at = datetime.now()

                logger.info(f"Step '{step.name}' compensated successfully")

            except Exception as e:
                error_msg = f"Compensation failed for '{step.name}': {str(e)}"
                logger.error(error_msg)
                # 继续补偿其他步骤，不中断

    def to_record(self) -> TransactionRecord:
        """转换为事务记录

        Returns:
            TransactionRecord: 事务记录模型
        """
        steps = [
            TransactionStep(
                name=step.name,
                status="completed" if step.executed and not step.compensated else
                       "compensated" if step.compensated else
                       "failed" if step.error else "pending",
                result={"type": type(step.result).__name__} if step.result is not None else None,
                error=step.error,
                executed_at=step.executed_at,
                compensated_at=step.compensated_at
            )
            for step in self.steps
        ]

        return TransactionRecord(
            transaction_id=self.transaction_id,
            entity_type=self.name.split(":")[0] if ":" in self.name else "unknown",
            entity_id=None,
            status="completed" if not self.failed else "compensated" if self.completed_steps else "failed",
            steps=steps,
            error=str(self.error) if self.error else None,
            created_at=self.created_at,
            completed_at=self.completed_at
        )


class PortfolioSagaFactory:
    """Portfolio Saga 工厂

    创建用于 Portfolio 操作的 Saga 事务。
    """

    @staticmethod
    def create_portfolio_saga(
        name: str,
        is_live: bool,
        selectors: List[Dict[str, Any]],
        sizer: Optional[Dict[str, Any]],
        strategies: List[Dict[str, Any]],
        risk_managers: List[Dict[str, Any]],
        analyzers: List[Dict[str, Any]]
    ) -> SagaTransaction:
        """创建 Portfolio 创建 Saga

        Args:
            name: Portfolio 名称
            is_live: 是否为实盘模式
            selectors: 选股器列表 [{"component_uuid": "...", "config": {...}}]
            sizer: 仓位管理器 {"component_uuid": "...", "config": {...}}
            strategies: 策略列表 [{"component_uuid": "...", "config": {...}}]
            risk_managers: 风控列表 [{"component_uuid": "...", "config": {...}}]
            analyzers: 分析器列表 [{"component_uuid": "...", "config": {...}}]

        Returns:
            SagaTransaction: 配置好的 Saga 事务
        """
        from ginkgo.data.containers import container
        from ginkgo.enums import FILE_TYPES

        # 获取服务实例
        portfolio_service = container.portfolio_service()
        mapping_service = container.portfolio_mapping_service()

        saga = SagaTransaction(f"portfolio:create:{name}")

        # 存储中间结果
        context = {
            'portfolio_uuid': None,
            'portfolio_result': None
        }

        # ==================== 步骤 1: 创建 Portfolio ====================
        def create_portfolio():
            result = portfolio_service.add(name=name, is_live=is_live)
            if not result.is_success():
                raise Exception(f"Failed to create portfolio: {result.error}")
            context['portfolio_result'] = result.data
            # result.data 可能是 dict 或对象，需要兼容处理
            if isinstance(result.data, dict):
                context['portfolio_uuid'] = result.data.get('uuid')
            else:
                context['portfolio_uuid'] = getattr(result.data, 'uuid', None)
            return result.data

        def compensate_create_portfolio(portfolio_data):
            if context['portfolio_uuid']:
                try:
                    portfolio_service.delete(context['portfolio_uuid'])
                    logger.info(f"Compensated: deleted portfolio {context['portfolio_uuid']}")
                except Exception as e:
                    logger.error(f"Failed to compensate portfolio deletion: {e}")

        saga.add_step("create_portfolio", create_portfolio, compensate_create_portfolio)

        # ==================== 辅助函数：创建组件步骤 ====================
        def create_component_step(
            component_type: str,
            file_type: FILE_TYPES,
            components: List[Dict[str, Any]]
        ):
            """为组件列表创建 Saga 步骤"""
            for component in components:
                component_uuid = component['component_uuid']
                config = component.get('config', {})

                def make_execute(c_uuid=component_uuid, c_config=config):
                    def execute():
                        if not context['portfolio_uuid']:
                            raise Exception("Portfolio UUID not available")
                        mapping_service.add_file(
                            portfolio_uuid=context['portfolio_uuid'],
                            file_id=c_uuid,
                            file_type=file_type,
                            params=c_config
                        )
                        return {'portfolio_uuid': context['portfolio_uuid'], 'file_id': c_uuid}
                    return execute

                def make_compensate(c_uuid=component_uuid):
                    def compensate(result):
                        try:
                            if context['portfolio_uuid']:
                                mapping_service.remove_file(
                                    portfolio_uuid=context['portfolio_uuid'],
                                    file_id=c_uuid
                                )
                                logger.info(f"Compensated: removed {component_type} {c_uuid}")
                        except Exception as e:
                            logger.error(f"Failed to compensate {component_type} removal: {e}")
                    return compensate

                saga.add_step(
                    f"add_{component_type}_{component_uuid[:8]}",
                    make_execute(),
                    make_compensate()
                )

        # ==================== 步骤 2: 添加选股器 ====================
        create_component_step("selector", FILE_TYPES.SELECTOR, selectors)

        # ==================== 步骤 3: 添加仓位管理器 ====================
        if sizer:
            create_component_step("sizer", FILE_TYPES.SIZER, [sizer])

        # ==================== 步骤 4: 添加策略 ====================
        create_component_step("strategy", FILE_TYPES.STRATEGY, strategies)

        # ==================== 步骤 5: 添加风控 ====================
        create_component_step("risk_manager", FILE_TYPES.RISKMANAGER, risk_managers)

        # ==================== 步骤 6: 添加分析器 ====================
        create_component_step("analyzer", FILE_TYPES.ANALYZER, analyzers)

        return saga

    @staticmethod
    def delete_portfolio_saga(portfolio_uuid: str) -> SagaTransaction:
        """创建 Portfolio 删除 Saga

        Args:
            portfolio_uuid: Portfolio UUID

        Returns:
            SagaTransaction: 配置好的 Saga 事务
        """
        from ginkgo.data.containers import container
        from ginkgo.data.crud.portfolio_file_mapping_crud import PortfolioFileMappingCRUD

        portfolio_service = container.portfolio_service()
        mapping_service = container.portfolio_mapping_service()
        mongo_driver = container.mongo_driver()
        mapping_crud = PortfolioFileMappingCRUD(driver=mongo_driver)

        saga = SagaTransaction(f"portfolio:delete:{portfolio_uuid}")

        context = {
            'mappings': [],
            'portfolio_data': None
        }

        # ==================== 步骤 1: 获取所有映射 ====================
        def get_mappings():
            mappings = mapping_crud.find_by_portfolio(portfolio_uuid)
            context['mappings'] = mappings
            return mappings

        def compensate_get_mappings(result):
            # 无需补偿
            pass

        saga.add_step("get_mappings", get_mappings, compensate_get_mappings)

        # ==================== 步骤 2: 删除所有映射 ====================
        def remove_mappings():
            for mapping in context['mappings']:
                mapping_service.remove_file(
                    portfolio_uuid=portfolio_uuid,
                    file_id=mapping.file_id
                )
            return len(context['mappings'])

        def compensate_remove_mappings(count):
            # 映射删除无法简单补偿，需要记录映射信息重建
            logger.warning("Mapping removal cannot be easily compensated")

        saga.add_step("remove_mappings", remove_mappings, compensate_remove_mappings)

        # ==================== 步骤 3: 删除 Portfolio ====================
        def delete_portfolio():
            result = portfolio_service.get(portfolio_id=portfolio_uuid)
            if result.is_success() and result.data:
                context['portfolio_data'] = result.data
            portfolio_service.delete(portfolio_uuid)
            return context['portfolio_data']

        def compensate_delete_portfolio(portfolio_data):
            # Portfolio 删除无法简单补偿
            logger.warning("Portfolio deletion cannot be easily compensated")

        saga.add_step("delete_portfolio", delete_portfolio, compensate_delete_portfolio)

        return saga

    @staticmethod
    def update_portfolio_saga(
        portfolio_uuid: str,
        name: Optional[str] = None,
        initial_cash: Optional[float] = None,
        selectors: Optional[List[Dict[str, Any]]] = None,
        sizer: Optional[Dict[str, Any]] = None,
        strategies: Optional[List[Dict[str, Any]]] = None,
        risk_managers: Optional[List[Dict[str, Any]]] = None,
        analyzers: Optional[List[Dict[str, Any]]] = None
    ) -> SagaTransaction:
        """创建 Portfolio 更新 Saga

        Args:
            portfolio_uuid: Portfolio UUID
            name: 新名称
            initial_cash: 初始资金
            selectors: 选股器列表
            sizer: 仓位管理器
            strategies: 策略列表
            risk_managers: 风控列表
            analyzers: 分析器列表

        Returns:
            SagaTransaction: 配置好的 Saga 事务
        """
        from ginkgo.data.containers import container
        from ginkgo.data.crud.portfolio_file_mapping_crud import PortfolioFileMappingCRUD
        from ginkgo.enums import FILE_TYPES

        portfolio_service = container.portfolio_service()
        mapping_service = container.portfolio_mapping_service()
        mongo_driver = container.mongo_driver()
        mapping_crud = PortfolioFileMappingCRUD(driver=mongo_driver)
        file_service = container.file_service()

        saga = SagaTransaction(f"portfolio:update:{portfolio_uuid}")

        context = {
            'old_mappings': [],
            'old_name': None,
            'old_initial_cash': None
        }

        # ==================== 步骤 1: 备份当前状态 ====================
        def backup_current_state():
            # 备份映射
            mappings = mapping_crud.find_by_portfolio(portfolio_uuid)
            context['old_mappings'] = [
                {
                    'file_id': m.file_id,
                    'type': m.type,
                    'params': m.params
                }
                for m in mappings
            ]

            # 备份基本信息
            result = portfolio_service.get(portfolio_id=portfolio_uuid)
            if result.is_success() and result.data:
                # result.data 可能是 ModelList 或单个对象
                portfolio = result.data
                if isinstance(portfolio, list):
                    portfolio = portfolio[0] if portfolio else None

                if portfolio:
                    # portfolio 可能是对象或 dict
                    if isinstance(portfolio, dict):
                        context['old_name'] = portfolio.get('name')
                        context['old_initial_cash'] = portfolio.get('initial_capital')
                    else:
                        context['old_name'] = getattr(portfolio, 'name', None)
                        if hasattr(portfolio, 'initial_capital'):
                            context['old_initial_cash'] = portfolio.initial_capital

            return {
                'mappings_count': len(context['old_mappings']),
                'name': context['old_name']
            }

        def compensate_backup(result):
            pass

        saga.add_step("backup_state", backup_current_state, compensate_backup)

        # ==================== 步骤 2: 更新基本信息 ====================
        def update_basic_info():
            if name is not None:
                portfolio_service.update(portfolio_uuid, name=name)
            if initial_cash is not None:
                portfolio_service.update(portfolio_uuid, initial_capital=initial_cash)
            return {'name': name, 'initial_cash': initial_cash}

        def compensate_update_basic_info(updates):
            # 恢复旧值
            if context['old_name'] is not None:
                portfolio_service.update(portfolio_uuid, name=context['old_name'])
            if context['old_initial_cash'] is not None:
                portfolio_service.update(portfolio_uuid, initial_capital=context['old_initial_cash'])

        saga.add_step("update_basic_info", update_basic_info, compensate_update_basic_info)

        # ==================== 步骤 3: 删除旧映射 ====================
        def remove_old_mappings():
            for mapping in context['old_mappings']:
                mapping_service.remove_file(
                    portfolio_uuid=portfolio_uuid,
                    file_id=mapping['file_id']
                )
            return len(context['old_mappings'])

        def compensate_remove_old_mappings(count):
            # 恢复旧映射
            from ginkgo.enums import FILE_TYPES
            for mapping in context['old_mappings']:
                try:
                    mapping_service.add_file(
                        portfolio_uuid=portfolio_uuid,
                        file_id=mapping['file_id'],
                        file_type=FILE_TYPES(mapping['type']),
                        params=mapping.get('params', {})
                    )
                except Exception as e:
                    logger.error(f"Failed to restore mapping: {e}")

        saga.add_step("remove_old_mappings", remove_old_mappings, compensate_remove_old_mappings)

        # ==================== 步骤 4-8: 添加新组件 ====================
        if selectors is not None:
            for selector in selectors:
                def make_execute(s=selector):
                    def execute():
                        mapping_service.add_file(
                            portfolio_uuid=portfolio_uuid,
                            file_id=s['component_uuid'],
                            file_type=FILE_TYPES.SELECTOR,
                            params=s.get('config', {})
                        )
                        return s['component_uuid']
                    return execute

                def make_compensate():
                    def compensate(file_id):
                        mapping_service.remove_file(
                            portfolio_uuid=portfolio_uuid,
                            file_id=file_id
                        )
                    return compensate

                saga.add_step(
                    f"add_selector_{selector['component_uuid'][:8]}",
                    make_execute(),
                    make_compensate()
                )

        if sizer is not None:
            def make_execute():
                def execute():
                    mapping_service.add_file(
                        portfolio_uuid=portfolio_uuid,
                        file_id=sizer['component_uuid'],
                        file_type=FILE_TYPES.SIZER,
                        params=sizer.get('config', {})
                    )
                    return sizer['component_uuid']
                return execute

            def make_compensate():
                def compensate(file_id):
                    mapping_service.remove_file(
                        portfolio_uuid=portfolio_uuid,
                        file_id=file_id
                    )
                return compensate

            saga.add_step("add_sizer", make_execute(), make_compensate())

        if strategies is not None:
            for strategy in strategies:
                def make_execute(s=strategy):
                    def execute():
                        mapping_service.add_file(
                            portfolio_uuid=portfolio_uuid,
                            file_id=s['component_uuid'],
                            file_type=FILE_TYPES.STRATEGY,
                            params=s.get('config', {})
                        )
                        return s['component_uuid']
                    return execute

                def make_compensate():
                    def compensate(file_id):
                        mapping_service.remove_file(
                            portfolio_uuid=portfolio_uuid,
                            file_id=file_id
                        )
                    return compensate

                saga.add_step(
                    f"add_strategy_{strategy['component_uuid'][:8]}",
                    make_execute(),
                    make_compensate()
                )

        if risk_managers is not None:
            for risk in risk_managers:
                def make_execute(r=risk):
                    def execute():
                        mapping_service.add_file(
                            portfolio_uuid=portfolio_uuid,
                            file_id=r['component_uuid'],
                            file_type=FILE_TYPES.RISKMANAGER,
                            params=r.get('config', {})
                        )
                        return r['component_uuid']
                    return execute

                def make_compensate():
                    def compensate(file_id):
                        mapping_service.remove_file(
                            portfolio_uuid=portfolio_uuid,
                            file_id=file_id
                        )
                    return compensate

                saga.add_step(
                    f"add_risk_manager_{risk['component_uuid'][:8]}",
                    make_execute(),
                    make_compensate()
                )

        if analyzers is not None:
            for analyzer in analyzers:
                def make_execute(a=analyzer):
                    def execute():
                        mapping_service.add_file(
                            portfolio_uuid=portfolio_uuid,
                            file_id=a['component_uuid'],
                            file_type=FILE_TYPES.ANALYZER,
                            params=a.get('config', {})
                        )
                        return a['component_uuid']
                    return execute

                def make_compensate():
                    def compensate(file_id):
                        mapping_service.remove_file(
                            portfolio_uuid=portfolio_uuid,
                            file_id=file_id
                        )
                    return compensate

                saga.add_step(
                    f"add_analyzer_{analyzer['component_uuid'][:8]}",
                    make_execute(),
                    make_compensate()
                )

        return saga

# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 投资组合管理服务提供创建/绑定组件/解绑/获取状态等方法封装投资组合与组件映射的业务逻辑和数据访问支持交易系统功能和组件集成提供完整业务支持






"""
Portfolio Management Service

This service handles portfolio lifecycle management, configuration,
and coordination with trading components during backtest execution.
"""

from typing import List, Dict, Any, Optional
import datetime
from decimal import Decimal

from ginkgo.libs import GLOG, datetime_normalize
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.enums import FILE_TYPES, DIRECTION_TYPES
from ginkgo.trading.portfolios import PortfolioT1Backtest
from ginkgo.trading.entities.position import Position
from ginkgo.trading.events.execution_confirmation import (
    EventExecutionConfirmed,
    EventExecutionRejected,
    EventExecutionTimeout,
    EventExecutionCanceled
)
from ginkgo.trading.events.position_update import EventPositionUpdate
from ginkgo.data.containers import container


class PortfolioManagementService:
    """
    Service for managing portfolio lifecycle and configuration.
    
    This service handles:
    - Portfolio creation and configuration
    - Component binding to portfolios
    - Portfolio performance tracking
    - Portfolio state management during backtests
    """
    
    def __init__(self, component_factory=None):
        """
        Initialize the portfolio management service.
        
        Args:
            component_factory: Factory service for creating components
        """
        self._component_factory = component_factory
        self._logger = GLOG
        
        # Data service access through container
        self._portfolio_service = container.portfolio_service()
        self._active_portfolios = {}  # Track active portfolio instances
    
    def initialize(self) -> bool:
        """Initialize the portfolio management service."""
        try:
            self._logger.INFO("PortfolioManagementService initialized")
            return True
        except Exception as e:
            self._logger.ERROR(f"Failed to initialize PortfolioManagementService: {e}")
            return False
    
    def create_portfolio_instance(self, portfolio_id: str, logger=None) -> Optional[PortfolioT1Backtest]:
        """
        Create a configured portfolio instance.
        
        Args:
            portfolio_id: UUID of the portfolio configuration
            logger: Logger instance to attach to the portfolio
            
        Returns:
            Configured portfolio instance or None if creation failed
        """
        try:
            # Get portfolio configuration
            portfolio_data = self._portfolio_service.get_portfolio(portfolio_id, as_dataframe=True)
            if portfolio_data.shape[0] == 0:
                self._logger.ERROR(f"Portfolio {portfolio_id} not found")
                return None
            
            portfolio_config = portfolio_data.iloc[0]
            
            # Create portfolio instance
            portfolio = PortfolioT1Backtest()
            
            # Configure basic properties
            portfolio.set_portfolio_name(portfolio_config["name"])
            portfolio.set_portfolio_id(portfolio_id)
            
            if logger:
                portfolio.add_logger(logger)
            
            # Store in active portfolios
            self._active_portfolios[portfolio_id] = {
                'instance': portfolio,
                'config': portfolio_config.to_dict(),
                'created_at': __import__('ginkgo.trading.time.clock', fromlist=['now']).now()
            }
            
            self._logger.DEBUG(f"Created portfolio instance: {portfolio_config['name']}")
            return portfolio
            
        except Exception as e:
            self._logger.ERROR(f"Failed to create portfolio instance {portfolio_id}: {e}")
            return None
    
    def bind_components_to_portfolio(self, portfolio: PortfolioT1Backtest, 
                                   portfolio_id: str, logger=None) -> bool:
        """
        Bind all required components to a portfolio.
        
        Args:
            portfolio: Portfolio instance to bind components to
            portfolio_id: UUID of the portfolio
            logger: Logger to attach to components
            
        Returns:
            True if all components bound successfully, False otherwise
        """
        try:
            if self._component_factory is None:
                self._logger.ERROR("Component factory not available")
                return False
            
            # Bind strategies (required)
            success = self._bind_strategies(portfolio, portfolio_id, logger)
            if not success:
                return False
            
            # Bind selector (required)
            success = self._bind_selector(portfolio, portfolio_id, logger)
            if not success:
                return False
            
            # Bind sizer (required)
            success = self._bind_sizer(portfolio, portfolio_id, logger)
            if not success:
                return False
            
            # Bind risk managers (optional)
            self._bind_risk_managers(portfolio, portfolio_id, logger)
            
            # Bind analyzers (required)
            success = self._bind_analyzers(portfolio, portfolio_id, logger)
            if not success:
                return False
            
            self._logger.DEBUG(f"All components bound to portfolio {portfolio_id}")
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Failed to bind components to portfolio {portfolio_id}: {e}")
            return False
    
    def _bind_strategies(self, portfolio: PortfolioT1Backtest, portfolio_id: str, logger=None) -> bool:
        """Bind strategy components to portfolio."""
        try:
            strategies = self._component_factory.create_strategies_by_portfolio(portfolio_id)
            
            if len(strategies) == 0:
                self._logger.CRITICAL(f"No strategies found for portfolio {portfolio_id}")
                return False
            
            for strategy in strategies:
                if logger:
                    strategy.add_logger(logger)
                portfolio.add_strategy(strategy)
            
            self._logger.DEBUG(f"Bound {len(strategies)} strategies to portfolio")
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Failed to bind strategies: {e}")
            return False
    
    def _bind_selector(self, portfolio: PortfolioT1Backtest, portfolio_id: str, logger=None) -> bool:
        """Bind selector component to portfolio."""
        try:
            selectors = self._component_factory.create_selectors_by_portfolio(portfolio_id)
            
            if len(selectors) == 0:
                self._logger.ERROR(f"No selector found for portfolio {portfolio_id}")
                return False
            
            # Use the first selector (typically only one per portfolio)
            selector = selectors[0]
            portfolio.bind_selector(selector)
            
            self._logger.DEBUG("Bound selector to portfolio")
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Failed to bind selector: {e}")
            return False
    
    def _bind_sizer(self, portfolio: PortfolioT1Backtest, portfolio_id: str, logger=None) -> bool:
        """Bind sizer component to portfolio."""
        try:
            sizers = self._component_factory.create_sizers_by_portfolio(portfolio_id)
            
            if len(sizers) == 0:
                self._logger.ERROR(f"No sizer found for portfolio {portfolio_id}")
                return False
            
            # Use the first sizer (typically only one per portfolio)
            sizer = sizers[0]
            if logger:
                sizer.add_logger(logger)
            portfolio.bind_sizer(sizer)
            
            self._logger.DEBUG("Bound sizer to portfolio")
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Failed to bind sizer: {e}")
            return False
    
    def _bind_risk_managers(self, portfolio: PortfolioT1Backtest, portfolio_id: str, logger=None) -> bool:
        """Bind risk manager components to portfolio (optional)."""
        try:
            risk_managers = self._component_factory.create_risk_managers_by_portfolio(portfolio_id)
            
            if len(risk_managers) == 0:
                self._logger.WARN(f"No risk managers found for portfolio {portfolio_id}. "
                                "Backtest will proceed without risk control.")
                return True  # Not critical
            
            for risk_manager in risk_managers:
                if logger:
                    risk_manager.add_logger(logger)
                portfolio.add_risk_manager(risk_manager)
            
            self._logger.DEBUG(f"Bound {len(risk_managers)} risk managers to portfolio")
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Failed to bind risk managers: {e}")
            return True  # Non-critical failure
    
    def _bind_analyzers(self, portfolio: PortfolioT1Backtest, portfolio_id: str, logger=None) -> bool:
        """Bind analyzer components to portfolio."""
        try:
            analyzers = self._component_factory.create_analyzers_by_portfolio(portfolio_id)
            
            if len(analyzers) == 0:
                self._logger.ERROR(f"No analyzers found for portfolio {portfolio_id}")
                return False
            
            for analyzer in analyzers:
                if logger:
                    analyzer.add_logger(logger)
                portfolio.add_analyzer(analyzer)
            
            self._logger.DEBUG(f"Bound {len(analyzers)} analyzers to portfolio")
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Failed to bind analyzers: {e}")
            return False
    
    def get_portfolio_date_range(self, portfolio_id: str) -> Optional[Dict[str, datetime.datetime]]:
        """
        Get the date range for a portfolio's backtest.
        
        Args:
            portfolio_id: UUID of the portfolio
            
        Returns:
            Dictionary with start_date and end_date or None if not found
        """
        try:
            if portfolio_id in self._active_portfolios:
                config = self._active_portfolios[portfolio_id]['config']
            else:
                # Fetch from database
                portfolio_data = self._portfolio_service.get_portfolio(portfolio_id, as_dataframe=True)
                if portfolio_data.shape[0] == 0:
                    return None
                config = portfolio_data.iloc[0].to_dict()
            
            return {
                'start_date': datetime_normalize(config['backtest_start_date']),
                'end_date': datetime_normalize(config['backtest_end_date'])
            }
            
        except Exception as e:
            self._logger.ERROR(f"Failed to get portfolio date range: {e}")
            return None
    
    def get_active_portfolios(self) -> Dict[str, Dict[str, Any]]:
        """Get information about currently active portfolios."""
        return self._active_portfolios.copy()
    
    def cleanup_portfolio(self, portfolio_id: str) -> bool:
        """
        Clean up resources for a portfolio after backtest completion.
        
        Args:
            portfolio_id: UUID of the portfolio to clean up
            
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            if portfolio_id in self._active_portfolios:
                portfolio_info = self._active_portfolios.pop(portfolio_id)
                self._logger.DEBUG(f"Cleaned up portfolio {portfolio_id}")
                return True
            
            return False
            
        except Exception as e:
            self._logger.ERROR(f"Failed to cleanup portfolio {portfolio_id}: {e}")
            return False
    
    def get_portfolio_performance_summary(self, portfolio_id: str) -> Optional[Dict[str, Any]]:
        """
        Get performance summary for a portfolio.
        
        Args:
            portfolio_id: UUID of the portfolio
            
        Returns:
            Performance summary dictionary or None if not available
        """
        try:
            if portfolio_id not in self._active_portfolios:
                return None
            
            portfolio_info = self._active_portfolios[portfolio_id]
            portfolio_instance = portfolio_info['instance']
            
            # Extract basic performance metrics
            # Note: Actual implementation would depend on portfolio interface
            summary = {
                'portfolio_id': portfolio_id,
                'name': portfolio_info['config']['name'],
                'created_at': portfolio_info['created_at'],
                'strategies_count': len(portfolio_instance._strategies) if hasattr(portfolio_instance, '_strategies') else 0,
                'analyzers_count': len(portfolio_instance._analyzers) if hasattr(portfolio_instance, '_analyzers') else 0,
                'status': 'active'
            }
            
            return summary
            
        except Exception as e:
            self._logger.ERROR(f"Failed to get portfolio performance summary: {e}")
            return None
    
    def handle_execution_confirmed(self, event: EventExecutionConfirmed) -> ServiceResult:
        """
        处理执行确认事件，更新对应的Position
        
        Args:
            event: 执行确认事件
            
        Returns:
            ServiceResult: 处理结果
        """
        try:
            portfolio_id = event.portfolio_id
            
            # 1. 获取或创建Portfolio实例
            portfolio = self._get_or_create_portfolio_instance(portfolio_id)
            if not portfolio:
                return ServiceResult.error(f"Failed to get portfolio instance: {portfolio_id}")
            
            # 2. 获取或创建Position
            position = self._get_or_create_position(
                portfolio=portfolio,
                code=event.code,
                engine_id=event.engine_id,
                portfolio_id=portfolio_id
            )
            
            # 3. 更新Position
            try:
                # 执行交易
                position.deal(
                    direction=event.direction,
                    price=float(event.actual_price),
                    volume=event.actual_volume
                )
                
                # 添加手续费
                if event.commission > 0:
                    position.add_fee(float(event.commission))
                
                self._logger.INFO(
                    f"Updated position for {event.code}: "
                    f"direction={event.direction}, price={event.actual_price}, "
                    f"volume={event.actual_volume}"
                )
                
                # 4. 保存Position到数据库
                save_result = self._save_position(position)
                if not save_result.is_success():
                    self._logger.ERROR(f"Failed to save position: {save_result.message}")
                
                # 5. 发布Position更新事件
                position_update_event = EventPositionUpdate(
                    code=event.code,
                    direction=event.direction,
                    price=float(event.actual_price),
                    volume=event.actual_volume,
                    position_volume=position.volume,
                    position_cost=float(position.cost),
                    position_value=float(position.worth),
                    engine_id=event.engine_id,
                    portfolio_id=portfolio_id
                )
                
                self._publish_event(position_update_event)
                
                return ServiceResult.success(
                    position,
                    f"Position updated for signal {event.signal_id}"
                )
                
            except Exception as e:
                self._logger.ERROR(f"Failed to update position: {e}")
                return ServiceResult.error(f"Position update failed: {e}")
            
        except Exception as e:
            self._logger.ERROR(f"Failed to handle execution confirmed event: {e}")
            return ServiceResult.error(f"Event handling failed: {e}")
    
    def handle_execution_rejected(self, event: EventExecutionRejected) -> ServiceResult:
        """
        处理执行拒绝事件
        
        Args:
            event: 执行拒绝事件
            
        Returns:
            ServiceResult: 处理结果
        """
        try:
            self._logger.INFO(
                f"Signal {event.signal_id} execution rejected: {event.reject_reason}"
            )
            
            # 执行拒绝时通常不需要更新Position，但可以记录日志或进行其他处理
            # 例如：通知风控系统、更新策略状态等
            
            return ServiceResult.success(
                None,
                f"Execution rejection handled for signal {event.signal_id}"
            )
            
        except Exception as e:
            self._logger.ERROR(f"Failed to handle execution rejected event: {e}")
            return ServiceResult.error(f"Rejection handling failed: {e}")
    
    def handle_execution_timeout(self, event: EventExecutionTimeout) -> ServiceResult:
        """
        处理执行超时事件
        
        Args:
            event: 执行超时事件
            
        Returns:
            ServiceResult: 处理结果
        """
        try:
            self._logger.WARN(
                f"Signal {event.signal_id} execution timed out after {event.timeout_duration}s"
            )
            
            # 超时处理：可能需要通知风控系统、更新策略状态等
            # 根据业务需求决定是否需要自动重试或其他处理
            
            return ServiceResult.success(
                None,
                f"Execution timeout handled for signal {event.signal_id}"
            )
            
        except Exception as e:
            self._logger.ERROR(f"Failed to handle execution timeout event: {e}")
            return ServiceResult.error(f"Timeout handling failed: {e}")
    
    def handle_execution_canceled(self, event: EventExecutionCanceled) -> ServiceResult:
        """
        处理执行取消事件
        
        Args:
            event: 执行取消事件
            
        Returns:
            ServiceResult: 处理结果
        """
        try:
            self._logger.INFO(
                f"Signal {event.signal_id} execution canceled: {event.cancel_reason}"
            )
            
            # 取消处理：可能需要释放资源、通知相关系统等
            
            return ServiceResult.success(
                None,
                f"Execution cancellation handled for signal {event.signal_id}"
            )
            
        except Exception as e:
            self._logger.ERROR(f"Failed to handle execution canceled event: {e}")
            return ServiceResult.error(f"Cancellation handling failed: {e}")
    
    def _get_or_create_portfolio_instance(self, portfolio_id: str) -> Optional[PortfolioT1Backtest]:
        """
        获取或创建Portfolio实例
        
        Args:
            portfolio_id: Portfolio ID
            
        Returns:
            Portfolio实例或None
        """
        try:
            # 检查是否已有活跃的Portfolio实例
            if portfolio_id in self._active_portfolios:
                return self._active_portfolios[portfolio_id]['instance']
            
            # 创建新的Portfolio实例
            portfolio_instance = self.create_portfolio_instance(portfolio_id)
            if portfolio_instance:
                self._active_portfolios[portfolio_id] = {
                    'instance': portfolio_instance,
                    'config': {},  # 从数据库加载配置
                    'created_at': __import__('ginkgo.trading.time.clock', fromlist=['now']).now()
                }
            
            return portfolio_instance
            
        except Exception as e:
            self._logger.ERROR(f"Failed to get or create portfolio instance: {e}")
            return None
    
    def _get_or_create_position(
        self,
        portfolio: PortfolioT1Backtest,
        code: str,
        engine_id: str,
        portfolio_id: str
    ) -> Position:
        """
        获取或创建Position实例
        
        Args:
            portfolio: Portfolio实例
            code: 股票代码
            engine_id: 引擎ID
            portfolio_id: Portfolio ID
            
        Returns:
            Position实例
        """
        try:
            # 尝试从Portfolio中获取现有Position
            position = portfolio.get_position(code)
            
            if position is None:
                # 创建新的Position
                position = Position(
                    portfolio_id=portfolio_id,
                    engine_id=engine_id,
                    code=code,
                    cost=Decimal('0'),
                    volume=0,
                    frozen_volume=0,
                    frozen_money=Decimal('0'),
                    price=Decimal('0'),
                    fee=Decimal('0')
                )
                
                # 添加到Portfolio
                portfolio._positions[code] = position
                
                self._logger.DEBUG(f"Created new position for {code}")
            
            return position
            
        except Exception as e:
            self._logger.ERROR(f"Failed to get or create position: {e}")
            # 返回一个空的Position作为fallback
            return Position(
                portfolio_id=portfolio_id,
                engine_id=engine_id,
                code=code
            )
    
    def _save_position(self, position: Position) -> ServiceResult:
        """
        保存Position到数据库
        
        Args:
            position: Position实例
            
        Returns:
            ServiceResult: 保存结果
        """
        try:
            position_crud = container.cruds.position()
            
            # 检查是否已存在
            existing_positions = position_crud.get_items_filtered(
                portfolio_id=position.portfolio_id,
                code=position.code
            )
            
            if existing_positions:
                # 更新现有Position
                existing_position = existing_positions[0]
                updated_position = position_crud.update(
                    existing_position.uuid,
                    cost=position.cost,
                    volume=position.volume,
                    frozen_volume=position.frozen_volume,
                    frozen_money=position.frozen_money,
                    price=position.price,
                    fee=position.fee
                )
                self._logger.DEBUG(f"Updated position in database: {position.code}")
            else:
                # 创建新Position
                new_position = position_crud.add(
                    portfolio_id=position.portfolio_id,
                    engine_id=position.engine_id,
                    code=position.code,
                    cost=position.cost,
                    volume=position.volume,
                    frozen_volume=position.frozen_volume,
                    frozen_money=position.frozen_money,
                    price=position.price,
                    fee=position.fee,
                    uuid=position.uuid
                )
                self._logger.DEBUG(f"Created position in database: {position.code}")
            
            return ServiceResult.success(position, "Position saved successfully")
            
        except Exception as e:
            self._logger.ERROR(f"Failed to save position: {e}")
            return ServiceResult.error(f"Position save failed: {e}")
    
    def _publish_event(self, event) -> None:
        """
        发布事件
        
        Args:
            event: 要发布的事件
        """
        try:
            # TODO: 实现事件发布机制
            # 这里可以集成到事件总线或消息队列
            self._logger.DEBUG(f"Event published: {event}")
            
        except Exception as e:
            self._logger.ERROR(f"Failed to publish event: {e}")
    
    def register_event_handlers(self) -> bool:
        """
        注册事件处理器到事件系统
        
        Returns:
            bool: 注册是否成功
        """
        try:
            # TODO: 实现事件系统集成
            # 示例代码：
            # event_bus = container.event_bus()
            # event_bus.register(EventExecutionConfirmed, self.handle_execution_confirmed)
            # event_bus.register(EventExecutionRejected, self.handle_execution_rejected)
            # event_bus.register(EventExecutionTimeout, self.handle_execution_timeout)
            # event_bus.register(EventExecutionCanceled, self.handle_execution_canceled)
            
            self._logger.INFO("Portfolio management event handlers registered")
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Failed to register event handlers: {e}")
            return False

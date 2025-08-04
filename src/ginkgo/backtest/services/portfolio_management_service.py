"""
Portfolio Management Service

This service handles portfolio lifecycle management, configuration,
and coordination with trading components during backtest execution.
"""

from typing import List, Dict, Any, Optional
import datetime

from ginkgo.libs import GLOG, datetime_normalize
from ginkgo.enums import FILE_TYPES
from ginkgo.backtest.execution.portfolios import PortfolioT1Backtest
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
                'created_at': datetime.datetime.now()
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
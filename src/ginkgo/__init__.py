"""
Ginkgo Unified Services Entry Point

Provides unified access to all module services.

Usage:
    from ginkgo import services
    
    # Data services (already perfect)
    bar_crud = services.data.cruds.bar()
    stockinfo_service = services.data.stockinfo_service()
    
    # Backtest services
    engine = services.backtest.engines.historic()
    
    # Core services
    adapter = services.core.adapters.mode()
    
    # ML services
    model = services.ml.models.sklearn()
"""

# Import data module container (already well implemented)
from .data.containers import container as data


class Services:
    """
    Unified service access point with lazy loading and enhanced error handling.
    """
    
    def __init__(self):
        """Initialize services with diagnostic capabilities."""
        self._module_errors = {}
        self._debug_mode = False
    
    def enable_debug(self):
        """Enable debug mode for detailed error reporting."""
        self._debug_mode = True
        print(":magnifying_glass_tilted_left: Debug mode enabled - detailed error reporting is now active")
    
    def disable_debug(self):
        """Disable debug mode."""
        self._debug_mode = False
        print(":muted_speaker: Debug mode disabled")
    
    def get_module_status(self):
        """Get detailed status of all modules."""
        status = {}
        for module_name in ['data', 'backtest', 'core', 'ml', 'features']:
            try:
                module = getattr(self, module_name)
                if module is not None:
                    status[module_name] = {
                        'available': True, 
                        'type': type(module).__name__,
                        'error': None
                    }
                else:
                    status[module_name] = {
                        'available': False,
                        'type': None,
                        'error': self._module_errors.get(module_name, 'Unknown error')
                    }
            except Exception as e:
                status[module_name] = {
                    'available': False,
                    'type': None, 
                    'error': str(e)
                }
        return status
    
    def diagnose_issues(self):
        """Diagnose and report service issues."""
        status = self.get_module_status()
        issues = []
        
        for module_name, info in status.items():
            if not info['available']:
                issues.append(f"{module_name} module: {info['error']}")
        
        if issues:
            print(":magnifying_glass_tilted_left: Service Diagnostic Report:")
            for issue in issues:
                print(f"  :x: {issue}")
            print("\nSuggestions:")
            print("  1. Check module dependencies and imports")
            print("  2. Verify container configurations")
            print("  3. Run: services.enable_debug() for detailed error info")
        else:
            print(":white_check_mark: All services are working correctly!")
        
        return issues
    
    @property
    def data(self):
        """Data module container (always available)"""
        try:
            # Data module is already perfect, use it directly
            return data
        except Exception as e:
            self._module_errors['data'] = str(e)
            if self._debug_mode:
                print(f":x: Data module error: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    @property
    def backtest(self):
        """Lazy load backtest module container"""
        try:
            from ginkgo.backtest.core.containers import backtest_container
            return backtest_container
        except Exception as e:
            self._module_errors['backtest'] = str(e)
            if self._debug_mode:
                print(f":x: Backtest module error: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    @property  
    def core(self):
        """Lazy load core module container"""
        try:
            from ginkgo.core.core_containers import container as core_container
            return core_container
        except Exception as e:
            self._module_errors['core'] = str(e)
            if self._debug_mode:
                print(f":x: Core module error: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    @property
    def ml(self):
        """Lazy load ml module container"""
        try:
            from ginkgo.quant_ml.containers import container as ml_container
            return ml_container
        except Exception as e:
            self._module_errors['ml'] = str(e)
            if self._debug_mode:
                print(f":x: ML module error: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    @property
    def features(self):
        """Lazy load features module container"""
        try:
            from ginkgo.features.containers import feature_container, configure_features_container
            
            # 配置features容器的外部依赖
            configure_features_container(self.data)
            
            return feature_container
            
        except Exception as e:
            self._module_errors['features'] = str(e)
            if self._debug_mode:
                print(f":x: Features module error: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    def list_available_modules(self):
        """List all available modules"""
        available = ["data"]  # data module is always available
        
        for module_name in ["backtest", "core", "ml", "features"]:
            try:
                module = getattr(self, module_name)
                if module is not None:
                    available.append(module_name)
            except Exception:
                # Module not available, skip
                pass
            
        return available


# Create global service access instance
services = Services()

# Export main interfaces
__all__ = ['services']
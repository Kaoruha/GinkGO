"""
Data Layer Utilities - Backward Compatibility Layer

:warning:  NOTICE: This module provides backward compatibility functions.
For new code, please use the DI Container instead:

    # Instead of:
    from ginkgo.data.utils import get_crud
    crud = get_crud('bar')
    
    # Use:
    from ginkgo.data.containers import container
    crud = container.cruds.bar()
    
    # Or for dependency injection:
    from dependency_injector.wiring import inject, Provide
    from ginkgo.data.containers import Container
    
    @inject
    def your_function(bar_crud: BaseCRUD = Provide[Container.cruds.bar]):
        # Use bar_crud here
        pass

This module provides shared helper functions for the data layer to avoid circular imports.
The functions here are kept for backward compatibility and legacy code support.
"""
from typing import List, Any, Union

from ginkgo.data.crud import BaseCRUD
from ginkgo.data import crud # Import crud package to access CRUD classes

# Centralized CRUD instance management
_crud_instances = {}

def get_crud(model_name: str) -> BaseCRUD:
    """
    Factory function to get a cached CRUD instance for a given model.
    
    :warning:  DEPRECATION NOTICE:
    This function is kept for backward compatibility. For new code, 
    please use the DI Container instead:
    
    # Instead of:
    bar_crud = get_crud('bar')
    
    # Use:
    from ginkgo.data.containers import container
    bar_crud = container.cruds.bar()
    
    # Or for dependency injection in classes:
    from dependency_injector.wiring import inject, Provide
    from ginkgo.data.containers import Container
    
    class YourService:
        @inject
        def __init__(self, bar_crud: BaseCRUD = Provide[Container.cruds.bar]):
            self.bar_crud = bar_crud
    
    Args:
        model_name: The name of the model/CRUD to get (e.g., 'bar', 'signal', 'order_record')
        
    Returns:
        BaseCRUD: A cached CRUD instance for the given model
        
    Raises:
        AttributeError: If the CRUD class is not found
        
    Note:
        This function is primarily used by the DI Container internally and for 
        backward compatibility. New code should use the DI Container directly.
    """
    if model_name not in _crud_instances:
        class_name = f"{''.join([s.capitalize() for s in model_name.split('_')])}CRUD"
        crud_class = getattr(crud, class_name, None)
        if crud_class:
            _crud_instances[model_name] = crud_class()
        else:
            available_cruds = get_available_crud_names()
            raise AttributeError(
                f"CRUD class '{class_name}' not found in the ginkgo.data.crud module.\n"
                f"Available CRUDs: {', '.join(available_cruds)}"
            )
    return _crud_instances[model_name]

def get_available_crud_names() -> List[str]:
    """
    Get list of available CRUD names by inspecting the crud module.
    """
    available_cruds = []
    for attr_name in dir(crud):
        if attr_name.endswith('CRUD') and not attr_name.startswith('_'):
            # Convert CamelCase to snake_case
            crud_name = _camel_to_snake(attr_name[:-4])  # Remove 'CRUD' suffix
            available_cruds.append(crud_name)
    return sorted(available_cruds)

def _camel_to_snake(name: str) -> str:
    """
    Convert CamelCase to snake_case.
    """
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def clear_crud_cache():
    """
    Clear the CRUD instance cache. Useful for testing.
    """
    global _crud_instances
    _crud_instances.clear()
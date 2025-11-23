"""
Engine Management Service (Class-based)

This service handles the business logic for managing backtest engines,
including engine creation, status management, and portfolio associations.

Enhanced with comprehensive error handling, retry mechanisms, and structured returns.
"""

import time
from typing import List, Union, Any, Optional, Dict
import pandas as pd
from datetime import datetime

from ginkgo.libs import cache_with_expiration, retry
from ginkgo.enums import ENGINESTATUS_TYPES, SOURCE_TYPES
from ginkgo.data.services.base_service import ManagementService


class EngineService(ManagementService):
    def __init__(self, crud_repo, engine_portfolio_mapping_crud):
        """Initializes the service with its dependencies."""
        super().__init__(crud_repo=crud_repo, engine_portfolio_mapping_crud=engine_portfolio_mapping_crud)

    @retry(max_try=3)
    def create_engine(self, name: str, is_live: bool = False, description: str = None) -> Dict[str, Any]:
        """
        Creates a new backtest engine with comprehensive error handling.

        Args:
            name: Engine name
            is_live: Whether this is a live trading engine
            description: Optional description

        Returns:
            Dictionary containing engine information and operation status
        """
        result = {
            "success": False,
            "name": name,
            "is_live": is_live,
            "error": None,
            "warnings": [],
            "engine_info": None,
        }

        # Input validation
        if not name or not name.strip():
            result["error"] = "Engine name cannot be empty"
            return result

        if len(name) > 50:  # Assuming reasonable name length limit
            result["warnings"].append("Engine name truncated to 50 characters")
            name = name[:50]

        # Check if engine name already exists
        try:
            if self.engine_exists(name):
                result["error"] = f"Engine with name '{name}' already exists"
                return result
        except Exception as e:
            result["warnings"].append(f"Could not check engine existence: {str(e)}")

        try:
            with self.crud_repo.get_session() as session:
                engine_record = self.crud_repo.create(
                    name=name,
                    is_live=is_live,
                    status=ENGINESTATUS_TYPES.IDLE,
                    desc=description or f"{'Live' if is_live else 'Backtest'} engine: {name}",
                    source=SOURCE_TYPES.SIM,
                    session=session,
                )

                result["success"] = True
                result["engine_info"] = {
                    "uuid": engine_record.uuid,
                    "name": engine_record.name,
                    "is_live": engine_record.is_live,
                    "status": (
                        engine_record.status.name
                        if hasattr(engine_record.status, "name")
                        else str(engine_record.status)
                    ),
                    "desc": engine_record.desc,
                }
                self._logger.INFO(f"Successfully created engine '{name}' (live: {is_live})")

        except Exception as e:
            result["error"] = f"Database operation failed: {str(e)}"
            self._logger.ERROR(f"Failed to create engine '{name}': {e}")

        return result

    @retry(max_try=3)
    def update_engine(
        self, engine_id: str, name: str = None, is_live: bool = None, description: str = None
    ) -> Dict[str, Any]:
        """
        Updates an existing engine with comprehensive error handling.

        Args:
            engine_id: UUID of the engine to update
            name: Optional new name
            is_live: Optional new live status
            description: Optional new description

        Returns:
            Dictionary containing operation status and update information
        """
        result = {
            "success": False,
            "engine_id": engine_id,
            "error": None,
            "warnings": [],
            "updates_applied": [],
            "updated_count": 0,
        }

        # Input validation
        if not engine_id or not engine_id.strip():
            result["error"] = "Engine ID cannot be empty"
            return result

        updates = {}
        if name is not None:
            if not name.strip():
                result["error"] = "Engine name cannot be empty"
                return result
            if len(name) > 50:
                result["warnings"].append("Engine name truncated to 50 characters")
                name = name[:50]
            updates["name"] = name
            result["updates_applied"].append("name")

        if is_live is not None:
            updates["is_live"] = is_live
            result["updates_applied"].append("is_live")

        if description is not None:
            updates["desc"] = description
            result["updates_applied"].append("description")

        if not updates:
            result["success"] = True  # No updates is not an error
            result["warnings"].append("No updates provided for engine update")
            return result

        # Check if name conflicts with existing engine (if name is being updated)
        if "name" in updates:
            try:
                existing_engines = self.get_engines(name=name, as_dataframe=True)
                if not existing_engines.empty:
                    # Check if the existing engine is not the one we're updating
                    existing_uuids = existing_engines["uuid"].tolist()
                    if engine_id not in existing_uuids:
                        result["error"] = f"Engine with name '{name}' already exists"
                        return result
            except Exception as e:
                result["warnings"].append(f"Could not check name conflict: {str(e)}")

        try:
            with self.crud_repo.get_session() as session:
                updated_count = self.crud_repo.modify(filters={"uuid": engine_id}, updates=updates, session=session)

                result["success"] = True
                result["updated_count"] = updated_count if updated_count is not None else 1

                if result["updated_count"] == 0:
                    result["warnings"].append(f"No engine found with ID {engine_id} to update")

                self._logger.INFO(f"Successfully updated engine {engine_id} with {len(updates)} changes")

        except Exception as e:
            result["error"] = f"Database operation failed: {str(e)}"
            self._logger.ERROR(f"Failed to update engine {engine_id}: {e}")

        return result

    @retry(max_try=3)
    def update_engine_status(self, engine_id: str, status: ENGINESTATUS_TYPES) -> Dict[str, Any]:
        """
        Updates the status of an engine with comprehensive error handling.

        Args:
            engine_id: UUID of the engine
            status: New engine status

        Returns:
            Dictionary containing operation status and update information
        """
        result = {
            "success": False,
            "engine_id": engine_id,
            "new_status": status.name if hasattr(status, "name") else str(status),
            "error": None,
            "warnings": [],
            "updated_count": 0,
        }

        # Input validation
        if not engine_id or not engine_id.strip():
            result["error"] = "Engine ID cannot be empty"
            return result

        if not isinstance(status, ENGINESTATUS_TYPES):
            result["error"] = f"Invalid engine status type: {type(status)}"
            return result

        try:
            with self.crud_repo.get_session() as session:
                updated_count = self.crud_repo.modify(
                    filters={"uuid": engine_id}, updates={"status": status}, session=session
                )

                result["success"] = True
                result["updated_count"] = updated_count if updated_count is not None else 1

                if result["updated_count"] == 0:
                    result["warnings"].append(f"No engine found with ID {engine_id} to update")

                self._logger.INFO(
                    f"Updated engine {engine_id} status to {status.name if hasattr(status, 'name') else status}"
                )

        except Exception as e:
            result["error"] = f"Database operation failed: {str(e)}"
            self._logger.ERROR(f"Failed to update engine {engine_id} status: {e}")

        return result

    @retry(max_try=3)
    def delete_engine(self, engine_id: str) -> Dict[str, Any]:
        """
        Deletes an engine by ID with comprehensive error handling and cleanup.

        Args:
            engine_id: UUID of the engine to delete

        Returns:
            Dictionary containing operation status and deletion information
        """
        result = {
            "success": False,
            "engine_id": engine_id,
            "error": None,
            "warnings": [],
            "deleted_count": 0,
            "mappings_deleted": 0,
        }

        # Input validation
        if not engine_id or not engine_id.strip():
            result["error"] = "Engine ID cannot be empty"
            return result

        try:
            with self.crud_repo.get_session() as session:
                # Also clean up engine-portfolio mappings first
                try:
                    mappings_deleted = self.engine_portfolio_mapping_crud.remove(
                        filters={"engine_id": engine_id}, session=session
                    )
                    result["mappings_deleted"] = mappings_deleted if mappings_deleted is not None else 0
                    if result["mappings_deleted"] > 0:
                        self._logger.INFO(
                            f"Deleted {result['mappings_deleted']} portfolio mappings for engine {engine_id}"
                        )
                except Exception as e:
                    result["warnings"].append(f"Failed to clean up portfolio mappings: {str(e)}")

                # Delete the engine (hard delete)
                deleted_count = self.crud_repo.remove(filters={"uuid": engine_id}, session=session)

                result["success"] = True
                result["deleted_count"] = deleted_count if deleted_count is not None else 1

                if result["deleted_count"] == 0:
                    result["warnings"].append(f"No engine found with ID {engine_id} to delete")

                self._logger.INFO(f"Successfully deleted engine {engine_id}")

        except Exception as e:
            result["error"] = f"Database operation failed: {str(e)}"
            self._logger.ERROR(f"Failed to delete engine {engine_id}: {e}")

        return result

    def delete_engines(self, engine_ids: List[str]) -> Dict[str, Any]:
        """
        Deletes multiple engines by their IDs with comprehensive tracking.

        Args:
            engine_ids: List of engine UUIDs to delete

        Returns:
            Dictionary containing batch deletion results and statistics
        """
        result = {
            "success": False,
            "total_requested": len(engine_ids),
            "successful_deletions": 0,
            "failed_deletions": 0,
            "total_mappings_deleted": 0,
            "warnings": [],
            "failures": [],
        }

        # Input validation
        if not engine_ids:
            result["warnings"].append("Empty engine list provided")
            result["success"] = True  # Empty list is not an error
            return result

        for engine_id in engine_ids:
            try:
                delete_result = self.delete_engine(engine_id)
                if delete_result["success"]:
                    result["successful_deletions"] += delete_result["deleted_count"]
                    result["total_mappings_deleted"] += delete_result["mappings_deleted"]
                    if delete_result["warnings"]:
                        result["warnings"].extend(delete_result["warnings"])
                else:
                    result["failed_deletions"] += 1
                    result["failures"].append({"engine_id": engine_id, "error": delete_result["error"]})
            except Exception as e:
                result["failed_deletions"] += 1
                result["failures"].append({"engine_id": engine_id, "error": f"Unexpected error: {str(e)}"})
                self._logger.ERROR(f"Failed to delete engine {engine_id}: {e}")
                continue

        # Determine overall success
        result["success"] = result["failed_deletions"] == 0

        self._logger.INFO(
            f"Batch engine deletion completed: {result['successful_deletions']} successful, "
            f"{result['failed_deletions']} failed, {result['total_mappings_deleted']} mappings cleaned up"
        )
        return result

    def get_engines(
        self,
        name: str = None,
        is_live: bool = None,
        status: ENGINESTATUS_TYPES = None,
        as_dataframe: bool = True,
        **kwargs,
    ) -> Union[pd.DataFrame, List[Any]]:
        """
        Retrieves engines from the database with caching.

        Args:
            name: Engine name filter
            is_live: Live status filter
            status: Engine status filter
            as_dataframe: Return format
            **kwargs: Additional filters

        Returns:
            Engine data as DataFrame or list of models
        """
        # 提取filters参数并从kwargs中移除，避免重复传递
        filters = kwargs.pop("filters", {})

        # 具体参数优先级高于filters中的对应字段
        if name:
            filters["name"] = name
        if is_live is not None:
            filters["is_live"] = is_live
        if status:
            filters["status"] = status

        # Always exclude soft-deleted records
        filters["is_del"] = False

        return self.crud_repo.find(filters=filters, as_dataframe=as_dataframe, **kwargs)

    def get_engine(self, engine_id: str, as_dataframe: bool = False) -> Union[pd.DataFrame, Any, None]:
        """
        Retrieves a single engine by ID.

        Args:
            engine_id: UUID of the engine
            as_dataframe: Return format

        Returns:
            Engine data or None if not found
        """
        # Use CRUD's find method directly with uuid filter
        result = self.crud_repo.find(filters={"uuid": engine_id, "is_del": False}, as_dataframe=as_dataframe)
        if as_dataframe:
            return result if result is not None and not result.empty else pd.DataFrame()
        else:
            return result[0] if result else None

    def get_engine_status(self, engine_id: str) -> Optional[ENGINESTATUS_TYPES]:
        """
        Gets the current status of an engine.

        Args:
            engine_id: UUID of the engine

        Returns:
            Engine status or None if not found
        """
        engine = self.get_engine(engine_id, as_dataframe=True)
        if engine is not None and not engine.empty:
            return ENGINESTATUS_TYPES(engine.iloc[0]["status"])
        return None

    def count_engines(self, is_live: bool = None, status: ENGINESTATUS_TYPES = None, **kwargs) -> int:
        """
        Counts the number of engines matching the filters.

        Args:
            is_live: Live status filter
            status: Engine status filter
            **kwargs: Additional filters

        Returns:
            Number of matching engines
        """
        # 提取filters参数并从kwargs中移除，避免重复传递
        filters = kwargs.pop("filters", {})

        # 具体参数优先级高于filters中的对应字段
        if is_live is not None:
            filters["is_live"] = is_live
        if status:
            filters["status"] = status

        # Always exclude soft-deleted records
        filters["is_del"] = False

        return self.crud_repo.count(filters=filters)

    def engine_exists(self, name: str) -> bool:
        """
        Checks if an engine exists by name.

        Args:
            name: Engine name

        Returns:
            True if engine exists
        """
        return self.crud_repo.exists(filters={"name": name, "is_del": False})

    @retry(max_try=3)
    def add_portfolio_to_engine(
        self, engine_id: str, portfolio_id: str, engine_name: str = None, portfolio_name: str = None
    ) -> Dict[str, Any]:
        """
        Associates a portfolio with an engine with comprehensive error handling.

        Args:
            engine_id: UUID of the engine
            portfolio_id: UUID of the portfolio
            engine_name: Optional engine name for mapping
            portfolio_name: Optional portfolio name for mapping

        Returns:
            Dictionary containing mapping information and operation status
        """
        result = {
            "success": False,
            "engine_id": engine_id,
            "portfolio_id": portfolio_id,
            "error": None,
            "warnings": [],
            "mapping_info": None,
        }

        # Input validation
        if not engine_id or not engine_id.strip():
            result["error"] = "Engine ID cannot be empty"
            return result

        if not portfolio_id or not portfolio_id.strip():
            result["error"] = "Portfolio ID cannot be empty"
            return result

        # Check if mapping already exists
        try:
            existing_mappings = self.get_engine_portfolio_mappings(
                engine_id=engine_id, portfolio_id=portfolio_id, as_dataframe=True
            )
            if not existing_mappings.empty:
                result["error"] = f"Portfolio {portfolio_id} is already mapped to engine {engine_id}"
                return result
        except Exception as e:
            result["warnings"].append(f"Could not check existing mapping: {str(e)}")

        try:
            with self.engine_portfolio_mapping_crud.get_session() as session:
                mapping_record = self.engine_portfolio_mapping_crud.create(
                    engine_id=engine_id,
                    portfolio_id=portfolio_id,
                    engine_name=engine_name or "",
                    portfolio_name=portfolio_name or "",
                    session=session,
                )

                result["success"] = True
                result["mapping_info"] = {
                    "uuid": mapping_record.uuid,
                    "engine_id": mapping_record.engine_id,
                    "portfolio_id": mapping_record.portfolio_id,
                    "engine_name": mapping_record.engine_name,
                    "portfolio_name": mapping_record.portfolio_name,
                }
                self._logger.INFO(f"Successfully mapped portfolio {portfolio_id} to engine {engine_id}")

        except Exception as e:
            result["error"] = f"Database operation failed: {str(e)}"
            self._logger.ERROR(f"Failed to map portfolio {portfolio_id} to engine {engine_id}: {e}")

        return result

    @retry(max_try=3)
    def remove_portfolio_from_engine(self, engine_id: str, portfolio_id: str) -> Dict[str, Any]:
        """
        Removes a portfolio association from an engine with comprehensive error handling.

        Args:
            engine_id: UUID of the engine
            portfolio_id: UUID of the portfolio

        Returns:
            Dictionary containing operation status and removal information
        """
        result = {
            "success": False,
            "engine_id": engine_id,
            "portfolio_id": portfolio_id,
            "error": None,
            "warnings": [],
            "removed_count": 0,
        }

        # Input validation
        if not engine_id or not engine_id.strip():
            result["error"] = "Engine ID cannot be empty"
            return result

        if not portfolio_id or not portfolio_id.strip():
            result["error"] = "Portfolio ID cannot be empty"
            return result

        try:
            with self.engine_portfolio_mapping_crud.get_session() as session:
                removed_count = self.engine_portfolio_mapping_crud.soft_remove(
                    filters={"engine_id": engine_id, "portfolio_id": portfolio_id}, session=session
                )

                result["success"] = True
                result["removed_count"] = removed_count if removed_count is not None else 1

                if result["removed_count"] == 0:
                    result["warnings"].append(
                        f"No mapping found between engine {engine_id} and portfolio {portfolio_id}"
                    )

                self._logger.INFO(f"Successfully removed portfolio {portfolio_id} from engine {engine_id}")

        except Exception as e:
            result["error"] = f"Database operation failed: {str(e)}"
            self._logger.ERROR(f"Failed to remove portfolio {portfolio_id} from engine {engine_id}: {e}")

        return result

    def get_engine_portfolio_mappings(
        self, engine_id: str = None, portfolio_id: str = None, as_dataframe: bool = True, **kwargs
    ) -> Union[pd.DataFrame, List[Any]]:
        """
        Retrieves engine-portfolio mappings with caching.

        Args:
            engine_id: Engine ID filter
            portfolio_id: Portfolio ID filter
            as_dataframe: Return format
            **kwargs: Additional filters

        Returns:
            Mapping data as DataFrame or list of models
        """
        # 提取filters参数并从kwargs中移除，避免重复传递
        filters = kwargs.pop("filters", {})

        # 具体参数优先级高于filters中的对应字段
        if engine_id:
            filters["engine_id"] = engine_id
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id

        return self.engine_portfolio_mapping_crud.find(filters=filters, as_dataframe=as_dataframe, **kwargs)

    def get_portfolios_for_engine(self, engine_id: str, as_dataframe: bool = True) -> Union[pd.DataFrame, List[Any]]:
        """
        Gets all portfolios associated with an engine.

        Args:
            engine_id: UUID of the engine
            as_dataframe: Return format

        Returns:
            Portfolio mappings for the engine
        """
        return self.get_engine_portfolio_mappings(engine_id=engine_id, as_dataframe=as_dataframe)

    def get_engines_for_portfolio(self, portfolio_id: str, as_dataframe: bool = True) -> Union[pd.DataFrame, List[Any]]:
        """
        Gets all engines associated with a portfolio.

        Args:
            portfolio_id: UUID of the portfolio
            as_dataframe: Return format

        Returns:
            Engine mappings for the portfolio
        """
        return self.get_engine_portfolio_mappings(portfolio_id=portfolio_id, as_dataframe=as_dataframe)

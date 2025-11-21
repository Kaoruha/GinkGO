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

from ginkgo.libs import cache_with_expiration, retry
from ginkgo.enums import FILE_TYPES
from ginkgo.data.services.base_service import ManagementService
from ginkgo.data.crud.model_conversion import ModelList


class PortfolioService(ManagementService):
    def __init__(self, crud_repo, portfolio_file_mapping_crud, param_crud):
        """Initializes the service with its dependencies."""
        super().__init__(
            crud_repo=crud_repo, portfolio_file_mapping_crud=portfolio_file_mapping_crud, param_crud=param_crud
        )

    @retry(max_try=3)
    def create_portfolio(
        self,
        name: str,
        backtest_start_date: str,
        backtest_end_date: str,
        is_live: bool = False,
        description: str = None,
    ) -> Dict[str, Any]:
        """
        Creates a new investment portfolio with comprehensive error handling.

        Args:
            name: Portfolio name
            backtest_start_date: Start date for backtesting (YYYY-MM-DD)
            backtest_end_date: End date for backtesting (YYYY-MM-DD)
            is_live: Whether this is a live trading portfolio
            description: Optional description

        Returns:
            Dictionary containing portfolio information and operation status
        """
        result = {
            "success": False,
            "name": name,
            "backtest_start_date": backtest_start_date,
            "backtest_end_date": backtest_end_date,
            "is_live": is_live,
            "error": None,
            "warnings": [],
            "portfolio_info": None,
        }

        # Input validation
        if not name or not name.strip():
            result["error"] = "Portfolio name cannot be empty"
            return result

        if len(name) > 100:  # Reasonable name length limit
            result["warnings"].append("Portfolio name truncated to 100 characters")
            name = name[:100]

        if not backtest_start_date or not backtest_end_date:
            result["error"] = "Backtest start and end dates are required"
            return result

        # Check if portfolio name already exists
        try:
            if self.portfolio_exists(name):
                result["error"] = f"Portfolio with name '{name}' already exists"
                return result
        except Exception as e:
            result["warnings"].append(f"Could not check portfolio existence: {str(e)}")

        try:
            with self.crud_repo.get_session() as session:
                portfolio_record = self.crud_repo.create(
                    name=name,
                    backtest_start_date=backtest_start_date,
                    backtest_end_date=backtest_end_date,
                    is_live=is_live,
                    desc=description or f"{'Live' if is_live else 'Backtest'} portfolio: {name}",
                    session=session,
                )

                result["success"] = True
                result["portfolio_info"] = {
                    "uuid": portfolio_record.uuid,
                    "name": portfolio_record.name,
                    "backtest_start_date": portfolio_record.backtest_start_date,
                    "backtest_end_date": portfolio_record.backtest_end_date,
                    "is_live": portfolio_record.is_live,
                    "desc": portfolio_record.desc,
                }
                self._logger.INFO(f"Successfully created portfolio '{name}' (live: {is_live})")

        except Exception as e:
            result["error"] = f"Database operation failed: {str(e)}"
            self._logger.ERROR(f"Failed to create portfolio '{name}': {e}")

        return result

    @retry(max_try=3)
    def update_portfolio(
        self,
        portfolio_id: str,
        name: str = None,
        backtest_start_date: str = None,
        backtest_end_date: str = None,
        is_live: bool = None,
        description: str = None,
    ) -> Dict[str, Any]:
        """
        Updates an existing portfolio with comprehensive error handling.

        Args:
            portfolio_id: UUID of the portfolio to update
            name: Optional new name
            backtest_start_date: Optional new start date
            backtest_end_date: Optional new end date
            is_live: Optional new live status
            description: Optional new description

        Returns:
            Dictionary containing operation status and update information
        """
        result = {
            "success": False,
            "portfolio_id": portfolio_id,
            "error": None,
            "warnings": [],
            "updates_applied": [],
            "updated_count": 0,
        }

        # Input validation
        if not portfolio_id or not portfolio_id.strip():
            result["error"] = "Portfolio ID cannot be empty"
            return result

        updates = {}
        if name is not None:
            if not name.strip():
                result["error"] = "Portfolio name cannot be empty"
                return result
            if len(name) > 100:
                result["warnings"].append("Portfolio name truncated to 100 characters")
                name = name[:100]
            updates["name"] = name
            result["updates_applied"].append("name")

        if backtest_start_date is not None:
            updates["backtest_start_date"] = backtest_start_date
            result["updates_applied"].append("backtest_start_date")

        if backtest_end_date is not None:
            updates["backtest_end_date"] = backtest_end_date
            result["updates_applied"].append("backtest_end_date")

        if is_live is not None:
            updates["is_live"] = is_live
            result["updates_applied"].append("is_live")

        if description is not None:
            updates["desc"] = description
            result["updates_applied"].append("description")

        if not updates:
            result["success"] = True  # No updates is not an error
            result["warnings"].append("No updates provided for portfolio update")
            return result

        # Check if name conflicts with existing portfolio (if name is being updated)
        if "name" in updates:
            try:
                existing_portfolios = self.get_portfolios(name=name)
                if len(existing_portfolios) > 0:
                    # Check if the existing portfolio is not the one we're updating
                    df = existing_portfolios.to_dataframe()
                    existing_uuids = df["uuid"].tolist()
                    if portfolio_id not in existing_uuids:
                        result["error"] = f"Portfolio with name '{name}' already exists"
                        return result
            except Exception as e:
                result["warnings"].append(f"Could not check name conflict: {str(e)}")

        try:
            with self.crud_repo.get_session() as session:
                updated_count = self.crud_repo.modify(filters={"uuid": portfolio_id}, updates=updates, session=session)

                result["success"] = True
                result["updated_count"] = updated_count if updated_count is not None else 1

                if result["updated_count"] == 0:
                    result["warnings"].append(f"No portfolio found with ID {portfolio_id} to update")

                self._logger.INFO(f"Successfully updated portfolio {portfolio_id} with {len(updates)} changes")

        except Exception as e:
            result["error"] = f"Database operation failed: {str(e)}"
            self._logger.ERROR(f"Failed to update portfolio {portfolio_id}: {e}")

        return result

    @retry(max_try=3)
    def delete_portfolio(self, portfolio_id: str) -> Dict[str, Any]:
        """
        Deletes a portfolio by ID with comprehensive error handling and cleanup.

        Args:
            portfolio_id: UUID of the portfolio to delete

        Returns:
            Dictionary containing operation status and deletion information
        """
        result = {
            "success": False,
            "portfolio_id": portfolio_id,
            "error": None,
            "warnings": [],
            "deleted_count": 0,
            "mappings_deleted": 0,
            "parameters_deleted": 0,
        }

        # Input validation
        if not portfolio_id or not portfolio_id.strip():
            result["error"] = "Portfolio ID cannot be empty"
            return result

        try:
            with self.crud_repo.get_session() as session:
                # Clean up portfolio-file mappings and parameters first
                try:
                    file_mappings = self.portfolio_file_mapping_crud.find(
                        filters={"portfolio_id": portfolio_id}, session=session
                    )

                    parameters_deleted = 0
                    for mapping in file_mappings:
                        # Delete associated parameters (hard delete)
                        try:
                            params_deleted = self.param_crud.remove(
                                filters={"mapping_id": mapping.uuid}, session=session
                            )
                            parameters_deleted += params_deleted if params_deleted is not None else 0
                        except Exception as e:
                            result["warnings"].append(
                                f"Failed to delete parameters for mapping {mapping.uuid}: {str(e)}"
                            )

                    result["parameters_deleted"] = parameters_deleted

                    # Delete portfolio-file mappings (hard delete)
                    mappings_deleted = self.portfolio_file_mapping_crud.remove(
                        filters={"portfolio_id": portfolio_id}, session=session
                    )
                    result["mappings_deleted"] = mappings_deleted if mappings_deleted is not None else 0

                    if result["mappings_deleted"] > 0:
                        self._logger.INFO(
                            f"Deleted {result['mappings_deleted']} file mappings and {result['parameters_deleted']} parameters for portfolio {portfolio_id}"
                        )

                except Exception as e:
                    result["warnings"].append(f"Failed to clean up portfolio mappings and parameters: {str(e)}")

                # Delete the portfolio (hard delete)
                deleted_count = self.crud_repo.remove(filters={"uuid": portfolio_id}, session=session)

                result["success"] = True
                result["deleted_count"] = deleted_count if deleted_count is not None else 1

                if result["deleted_count"] == 0:
                    result["warnings"].append(f"No portfolio found with ID {portfolio_id} to delete")

                self._logger.INFO(f"Successfully deleted portfolio {portfolio_id} and related data")

        except Exception as e:
            result["error"] = f"Database operation failed: {str(e)}"
            self._logger.ERROR(f"Failed to delete portfolio {portfolio_id}: {e}")

        return result

    def delete_portfolios(self, portfolio_ids: List[str]) -> Dict[str, Any]:
        """
        Deletes multiple portfolios by their IDs with comprehensive tracking.

        Args:
            portfolio_ids: List of portfolio UUIDs to delete

        Returns:
            Dictionary containing batch deletion results and statistics
        """
        result = {
            "success": False,
            "total_requested": len(portfolio_ids),
            "successful_deletions": 0,
            "failed_deletions": 0,
            "total_mappings_deleted": 0,
            "total_parameters_deleted": 0,
            "warnings": [],
            "failures": [],
        }

        # Input validation
        if not portfolio_ids:
            result["warnings"].append("Empty portfolio list provided")
            result["success"] = True  # Empty list is not an error
            return result

        for portfolio_id in portfolio_ids:
            try:
                delete_result = self.delete_portfolio(portfolio_id)
                if delete_result["success"]:
                    result["successful_deletions"] += delete_result["deleted_count"]
                    result["total_mappings_deleted"] += delete_result["mappings_deleted"]
                    result["total_parameters_deleted"] += delete_result["parameters_deleted"]
                    if delete_result["warnings"]:
                        result["warnings"].extend(delete_result["warnings"])
                else:
                    result["failed_deletions"] += 1
                    result["failures"].append({"portfolio_id": portfolio_id, "error": delete_result["error"]})
            except Exception as e:
                result["failed_deletions"] += 1
                result["failures"].append({"portfolio_id": portfolio_id, "error": f"Unexpected error: {str(e)}"})
                self._logger.ERROR(f"Failed to delete portfolio {portfolio_id}: {e}")
                continue

        # Determine overall success
        result["success"] = result["failed_deletions"] == 0

        self._logger.INFO(
            f"Batch portfolio deletion completed: {result['successful_deletions']} successful, "
            f"{result['failed_deletions']} failed, {result['total_mappings_deleted']} mappings and "
            f"{result['total_parameters_deleted']} parameters cleaned up"
        )
        return result

    def get_portfolios(
        self, name: str = None, is_live: bool = None, **kwargs
    ):
        """
        Retrieves portfolios from the database with caching.

        Args:
            name: Portfolio name filter
            is_live: Live status filter
            as_dataframe: Return format
            **kwargs: Additional filters

        Returns:
            Portfolio data as DataFrame or list of models
        """
        # 提取filters参数并从kwargs中移除，避免重复传递
        filters = kwargs.pop("filters", {})

        # 具体参数优先级高于filters中的对应字段
        if name:
            filters["name"] = name
        if is_live is not None:
            filters["is_live"] = is_live

        # Always exclude soft-deleted records
        filters["is_del"] = False

        return self.crud_repo.find(filters=filters, **kwargs)

    def get_portfolio(self, portfolio_id: str, as_dataframe: bool = False) -> Union[pd.DataFrame, Any, None]:
        """
        Retrieves a single portfolio by ID.

        Args:
            portfolio_id: UUID of the portfolio
            as_dataframe: Return format

        Returns:
            Portfolio data or None if not found
        """
        # Use CRUD's find method directly with uuid filter
        result = self.crud_repo.find(filters={"uuid": portfolio_id, "is_del": False}, as_dataframe=as_dataframe)
        if as_dataframe:
            return result if result is not None and not result.empty else pd.DataFrame()
        else:
            return result[0] if result else None

    def count_portfolios(self, is_live: bool = None, **kwargs) -> int:
        """
        Counts the number of portfolios matching the filters.

        Args:
            is_live: Live status filter
            **kwargs: Additional filters

        Returns:
            Number of matching portfolios
        """
        # 提取filters参数并从kwargs中移除，避免重复传递
        filters = kwargs.pop("filters", {})

        # 具体参数优先级高于filters中的对应字段
        if is_live is not None:
            filters["is_live"] = is_live

        # Always exclude soft-deleted records
        filters["is_del"] = False

        return self.crud_repo.count(filters=filters)

    def portfolio_exists(self, name: str) -> bool:
        """
        Checks if a portfolio exists by name.

        Args:
            name: Portfolio name

        Returns:
            True if portfolio exists
        """
        return self.crud_repo.exists(filters={"name": name, "is_del": False})

    @retry(max_try=3)
    def add_file_to_portfolio(
        self, portfolio_id: str, file_id: str, name: str, file_type: FILE_TYPES
    ) -> Dict[str, Any]:
        """
        Associates a file with a portfolio with comprehensive error handling.

        Args:
            portfolio_id: UUID of the portfolio
            file_id: UUID of the file
            name: Name for this mapping
            file_type: Type of file being mapped

        Returns:
            Dictionary containing mapping information and operation status
        """
        result = {
            "success": False,
            "portfolio_id": portfolio_id,
            "file_id": file_id,
            "name": name,
            "file_type": file_type.name if hasattr(file_type, "name") else str(file_type),
            "error": None,
            "warnings": [],
            "mapping_info": None,
        }

        # Input validation
        if not portfolio_id or not portfolio_id.strip():
            result["error"] = "Portfolio ID cannot be empty"
            return result

        if not file_id or not file_id.strip():
            result["error"] = "File ID cannot be empty"
            return result

        if not name or not name.strip():
            result["error"] = "Mapping name cannot be empty"
            return result

        if len(name) > 200:  # Reasonable mapping name length limit
            result["warnings"].append("Mapping name truncated to 200 characters")
            name = name[:200]

        # Check if mapping already exists
        try:
            existing_mappings = self.get_portfolio_file_mappings(portfolio_id=portfolio_id, as_dataframe=True)
            if not existing_mappings.empty:
                # Check if same file is already mapped
                if file_id in existing_mappings["file_id"].values:
                    result["error"] = f"File {file_id} is already mapped to portfolio {portfolio_id}"
                    return result
        except Exception as e:
            result["warnings"].append(f"Could not check existing mapping: {str(e)}")

        try:
            with self.portfolio_file_mapping_crud.get_session() as session:
                mapping_record = self.portfolio_file_mapping_crud.create(
                    portfolio_id=portfolio_id, file_id=file_id, name=name, type=file_type, session=session
                )

                result["success"] = True
                result["mapping_info"] = {
                    "uuid": mapping_record.uuid,
                    "portfolio_id": mapping_record.portfolio_id,
                    "file_id": mapping_record.file_id,
                    "name": mapping_record.name,
                    "type": (
                        mapping_record.type.name if hasattr(mapping_record.type, "name") else str(mapping_record.type)
                    ),
                }
                self._logger.INFO(f"Successfully mapped file {file_id} to portfolio {portfolio_id}")

        except Exception as e:
            result["error"] = f"Database operation failed: {str(e)}"
            self._logger.ERROR(f"Failed to map file {file_id} to portfolio {portfolio_id}: {e}")

        return result

    @retry(max_try=3)
    def remove_file_from_portfolio(self, mapping_id: str) -> Dict[str, Any]:
        """
        Removes a file association from a portfolio with comprehensive error handling.

        Args:
            mapping_id: UUID of the portfolio-file mapping

        Returns:
            Dictionary containing operation status and removal information
        """
        result = {
            "success": False,
            "mapping_id": mapping_id,
            "error": None,
            "warnings": [],
            "removed_count": 0,
            "parameters_deleted": 0,
        }

        # Input validation
        if not mapping_id or not mapping_id.strip():
            result["error"] = "Mapping ID cannot be empty"
            return result

        try:
            with self.portfolio_file_mapping_crud.get_session() as session:
                # Delete associated parameters first
                try:
                    parameters_deleted = self.param_crud.soft_remove(
                        filters={"mapping_id": mapping_id}, session=session
                    )
                    result["parameters_deleted"] = parameters_deleted if parameters_deleted is not None else 0
                    if result["parameters_deleted"] > 0:
                        self._logger.INFO(f"Deleted {result['parameters_deleted']} parameters for mapping {mapping_id}")
                except Exception as e:
                    result["warnings"].append(f"Failed to delete parameters: {str(e)}")

                # Delete the mapping
                removed_count = self.portfolio_file_mapping_crud.soft_remove(
                    filters={"uuid": mapping_id}, session=session
                )

                result["success"] = True
                result["removed_count"] = removed_count if removed_count is not None else 1

                if result["removed_count"] == 0:
                    result["warnings"].append(f"No mapping found with ID {mapping_id} to remove")

                self._logger.INFO(f"Successfully removed file mapping {mapping_id}")

        except Exception as e:
            result["error"] = f"Database operation failed: {str(e)}"
            self._logger.ERROR(f"Failed to remove file mapping {mapping_id}: {e}")

        return result

    def get_portfolio_file_mappings(
        self, portfolio_id: str = None, file_type: FILE_TYPES = None, as_dataframe: bool = True, **kwargs
    ) -> Union[pd.DataFrame, List[Any]]:
        """
        Retrieves portfolio-file mappings with caching.

        Args:
            portfolio_id: Portfolio ID filter
            file_type: File type filter
            as_dataframe: Return format
            **kwargs: Additional filters

        Returns:
            Mapping data as DataFrame or list of models
        """
        # 提取filters参数并从kwargs中移除，避免重复传递
        filters = kwargs.pop("filters", {})

        # 具体参数优先级高于filters中的对应字段
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        if file_type:
            filters["type"] = file_type

        # Always exclude soft-deleted records
        filters["is_del"] = False

        return self.portfolio_file_mapping_crud.find(filters=filters, as_dataframe=as_dataframe, **kwargs)

    def get_files_for_portfolio(
        self, portfolio_id: str, file_type: FILE_TYPES = None, as_dataframe: bool = True
    ) -> Union[pd.DataFrame, List[Any]]:
        """
        Gets all files associated with a portfolio, optionally filtered by type.

        Args:
            portfolio_id: UUID of the portfolio
            file_type: Optional file type filter
            as_dataframe: Return format

        Returns:
            File mappings for the portfolio
        """
        return self.get_portfolio_file_mappings(
            portfolio_id=portfolio_id, file_type=file_type, as_dataframe=as_dataframe
        )

    @retry(max_try=3)
    def add_parameter(self, mapping_id: str, index: int, value: str) -> Dict[str, Any]:
        """
        Adds a parameter to a portfolio-file mapping with comprehensive error handling.

        Args:
            mapping_id: UUID of the portfolio-file mapping
            index: Parameter order/index
            value: Parameter value

        Returns:
            Dictionary containing parameter information and operation status
        """
        result = {
            "success": False,
            "mapping_id": mapping_id,
            "index": index,
            "value": value,
            "error": None,
            "warnings": [],
            "parameter_info": None,
        }

        # Input validation
        if not mapping_id or not mapping_id.strip():
            result["error"] = "Mapping ID cannot be empty"
            return result

        if index is None or index < 0:
            result["error"] = "Parameter index must be a non-negative integer"
            return result

        if value is None:
            result["error"] = "Parameter value cannot be None"
            return result

        if len(str(value)) > 1000:  # Reasonable parameter value length limit
            result["warnings"].append("Parameter value truncated to 1000 characters")
            value = str(value)[:1000]

        try:
            with self.param_crud.get_session() as session:
                param_record = self.param_crud.create(
                    mapping_id=mapping_id, index=index, value=str(value), session=session
                )

                result["success"] = True
                result["parameter_info"] = {
                    "uuid": param_record.uuid,
                    "mapping_id": param_record.mapping_id,
                    "index": param_record.index,
                    "value": param_record.value,
                }
                self._logger.INFO(f"Successfully added parameter to mapping {mapping_id}")

        except Exception as e:
            result["error"] = f"Database operation failed: {str(e)}"
            self._logger.ERROR(f"Failed to add parameter to mapping {mapping_id}: {e}")

        return result

    def get_parameters_for_mapping(self, mapping_id: str, as_dataframe: bool = True) -> Union[pd.DataFrame, List[Any]]:
        """
        Gets all parameters for a portfolio-file mapping.

        Args:
            mapping_id: UUID of the portfolio-file mapping
            as_dataframe: Return format

        Returns:
            Parameters for the mapping
        """
        return self.param_crud.find(
            filters={"mapping_id": mapping_id, "is_del": False}, order_by="order", as_dataframe=as_dataframe
        )

    @retry(max_try=3)
    def clean_orphaned_mappings(self) -> Dict[str, Any]:
        """
        Cleans up orphaned portfolio-file mappings and parameters with comprehensive error handling.

        Returns:
            Dictionary containing operation status and cleanup statistics
        """
        result = {
            "success": False,
            "cleaned_mappings": 0,
            "cleaned_parameters": 0,
            "mappings_checked": 0,
            "error": None,
            "warnings": [],
            "skipped_mappings": 0,
        }

        try:
            # Get all portfolio-file mappings
            all_mappings = self.get_portfolio_file_mappings(as_dataframe=True)

            if all_mappings.empty:
                result["success"] = True
                result["warnings"].append("No portfolio-file mappings found to clean")
                self._logger.INFO("No portfolio-file mappings found to clean")
                return result

            result["mappings_checked"] = len(all_mappings)

            with self.portfolio_file_mapping_crud.get_session() as session:
                for _, mapping in all_mappings.iterrows():
                    mapping_id = mapping["uuid"]
                    portfolio_id = mapping["portfolio_id"]
                    file_id = mapping["file_id"]

                    try:
                        # Check if portfolio exists
                        portfolio_exists = self.crud_repo.exists(filters={"uuid": portfolio_id})

                        # Check if file exists
                        file_exists = False
                        try:
                            from ginkgo.data.utils import get_crud

                            file_crud = get_crud("file")
                            file_exists = file_crud.exists(filters={"uuid": file_id})
                        except Exception as e:
                            result["warnings"].append(f"Could not check file existence for {file_id}: {str(e)}")
                            result["skipped_mappings"] += 1
                            continue

                        if not portfolio_exists or not file_exists:
                            # Remove parameters first
                            try:
                                params_deleted = self.param_crud.soft_remove(
                                    filters={"mapping_id": mapping_id}, session=session
                                )
                                result["cleaned_parameters"] += params_deleted if params_deleted is not None else 0
                            except Exception as e:
                                result["warnings"].append(
                                    f"Failed to delete parameters for mapping {mapping_id}: {str(e)}"
                                )

                            # Remove mapping
                            try:
                                mapping_deleted = self.portfolio_file_mapping_crud.soft_remove(
                                    filters={"uuid": mapping_id}, session=session
                                )
                                if mapping_deleted and mapping_deleted > 0:
                                    result["cleaned_mappings"] += 1
                                    self._logger.DEBUG(
                                        f"Cleaned orphaned mapping {mapping_id} (portfolio_exists: {portfolio_exists}, file_exists: {file_exists})"
                                    )
                            except Exception as e:
                                result["warnings"].append(f"Failed to delete mapping {mapping_id}: {str(e)}")

                    except Exception as e:
                        result["warnings"].append(f"Error processing mapping {mapping_id}: {str(e)}")
                        result["skipped_mappings"] += 1
                        continue

            result["success"] = True
            self._logger.INFO(
                f"Cleaned {result['cleaned_mappings']} orphaned mappings and {result['cleaned_parameters']} parameters "
                f"(checked {result['mappings_checked']} mappings, skipped {result['skipped_mappings']})"
            )

        except Exception as e:
            result["error"] = f"Database operation failed: {str(e)}"
            self._logger.ERROR(f"Failed to clean orphaned mappings: {e}")

        return result

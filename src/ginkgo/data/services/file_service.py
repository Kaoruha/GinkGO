"""
File Management Service (Class-based)

This service handles the business logic for managing files including strategies,
analyzers, selectors, sizers, and risk managers.

Enhanced with comprehensive error handling, retry mechanisms, and structured returns.
"""

import os
from typing import List, Union, Any, Optional, Dict
import pandas as pd

from ginkgo.libs import cache_with_expiration, GCONF, retry
from ginkgo.enums import FILE_TYPES
from ginkgo.data.services.base_service import ManagementService


class FileService(ManagementService):
    def __init__(self, crud_repo):
        """Initializes the service with its dependencies."""
        super().__init__(crud_repo=crud_repo)

    @retry(max_try=3)
    def add_file(self, name: str, file_type: FILE_TYPES, data: bytes, description: str = None) -> Dict[str, Any]:
        """
        Adds a new file to the database with comprehensive error handling.

        Args:
            name: File name (without extension)
            file_type: Type of file (strategy, analyzer, etc.)
            data: File content as bytes
            description: Optional description

        Returns:
            Dictionary containing file information and operation status
        """
        result = {
            "success": False,
            "name": name,
            "file_type": file_type.name if hasattr(file_type, "name") else str(file_type),
            "error": None,
            "warnings": [],
            "file_info": None,
        }

        # Input validation
        if not name or not name.strip():
            result["error"] = "File name cannot be empty"
            return result

        if not isinstance(data, bytes):
            result["error"] = "File data must be bytes"
            return result

        if len(data) == 0:
            result["warnings"].append("File data is empty")

        if len(name) > 40:
            result["warnings"].append("File name truncated to 40 characters")
            name = name[:40]

        try:
            with self.crud_repo.get_session() as session:
                file_record = self.crud_repo.create(
                    name=name,
                    type=file_type,
                    data=data,
                    desc=description or f"{file_type.value} file: {name}",
                    session=session,
                )

                result["success"] = True
                result["file_info"] = {
                    "uuid": file_record.uuid,
                    "name": file_record.name,
                    "type": file_record.type,
                    "desc": file_record.desc,
                    "data_size": len(data),
                }
                self._logger.INFO(f"Successfully added file '{name}' of type {file_type.value} ({len(data)} bytes)")

        except Exception as e:
            result["error"] = f"Database operation failed: {str(e)}"
            self._logger.ERROR(f"Failed to add file '{name}': {e}")

        return result

    @retry(max_try=3)
    def copy_file(self, clone_id: str, new_name: str, file_type: FILE_TYPES = None) -> Dict[str, Any]:
        """
        Creates a copy of an existing file with a new name and comprehensive error handling.

        Args:
            clone_id: UUID of the file to copy
            new_name: Name for the new file
            file_type: Optional new file type (defaults to original)

        Returns:
            Dictionary containing operation status and new file information
        """
        result = {
            "success": False,
            "clone_id": clone_id,
            "new_name": new_name,
            "error": None,
            "warnings": [],
            "file_info": None,
        }

        # Input validation
        if not clone_id or not clone_id.strip():
            result["error"] = "Source file ID cannot be empty"
            return result

        if not new_name or not new_name.strip():
            result["error"] = "New file name cannot be empty"
            return result

        try:
            # Get the source file content
            source_content = self.get_file_content(clone_id)
            if source_content is None:
                result["error"] = f"Source file with ID {clone_id} not found"
                return result
            elif len(source_content) == 0:
                result["warnings"].append("Source file content is empty")

            # Get source file info to determine type if not specified
            if file_type is None:
                source_file = self.get_files(uuid=clone_id, as_dataframe=True)
                if source_file.empty:
                    result["error"] = f"Source file with ID {clone_id} not found"
                    return result
                file_type = FILE_TYPES(source_file.to_dataframe().iloc[0]["type"])
                result["warnings"].append(f"Using original file type: {file_type.value}")

            # Create the copy using enhanced add_file method
            copy_result = self.add_file(new_name, file_type, source_content, f"Copy of {clone_id}")

            if copy_result["success"]:
                result["success"] = True
                result["file_info"] = copy_result["file_info"]
                result["warnings"].extend(copy_result["warnings"])
                self._logger.INFO(f"Successfully copied file {clone_id} to {new_name}")
            else:
                result["error"] = f"Failed to create copy: {copy_result['error']}"
                result["warnings"].extend(copy_result["warnings"])

        except Exception as e:
            result["error"] = f"Copy operation failed: {str(e)}"
            self._logger.ERROR(f"Failed to copy file {clone_id} to {new_name}: {e}")

        return result

    @retry(max_try=3)
    def update_file(
        self, file_id: str, name: str = None, data: bytes = None, description: str = None
    ) -> Dict[str, Any]:
        """
        Updates an existing file with comprehensive error handling.

        Args:
            file_id: UUID of the file to update
            name: Optional new name
            data: Optional new file content
            description: Optional new description

        Returns:
            Dictionary containing operation status and update information
        """
        result = {
            "success": False,
            "file_id": file_id,
            "error": None,
            "warnings": [],
            "updates_applied": [],
            "updated_count": 0,
        }

        # Input validation
        if not file_id or not file_id.strip():
            result["error"] = "File ID cannot be empty"
            return result

        updates = {}
        if name is not None:
            if len(name) > 40:
                result["warnings"].append("File name truncated to 40 characters")
                name = name[:40]
            updates["name"] = name
            result["updates_applied"].append("name")

        if data is not None:
            if not isinstance(data, bytes):
                result["error"] = "File data must be bytes"
                return result
            if len(data) == 0:
                result["warnings"].append("File data is empty")
            updates["data"] = data
            result["updates_applied"].append("data")

        if description is not None:
            updates["desc"] = description
            result["updates_applied"].append("description")

        if not updates:
            result["warnings"].append("No updates provided for file update")
            result["success"] = True  # No updates is not an error
            return result

        try:
            with self.crud_repo.get_session() as session:
                updated_count = self.crud_repo.modify(filters={"uuid": file_id}, updates=updates, session=session)

                result["success"] = True
                result["updated_count"] = updated_count if updated_count is not None else 1
                self._logger.INFO(f"Successfully updated file {file_id} with {len(updates)} changes")

        except Exception as e:
            result["error"] = f"Database operation failed: {str(e)}"
            self._logger.ERROR(f"Failed to update file {file_id}: {e}")

        return result

    @retry(max_try=3)
    def delete_file(self, file_id: str) -> Dict[str, Any]:
        """
        Deletes a file by ID with comprehensive error handling.

        Args:
            file_id: UUID of the file to delete

        Returns:
            Dictionary containing operation status and deletion information
        """
        result = {"success": False, "file_id": file_id, "error": None, "warnings": [], "deleted_count": 0}

        # Input validation
        if not file_id or not file_id.strip():
            result["error"] = "File ID cannot be empty"
            return result

        try:
            with self.crud_repo.get_session() as session:
                deleted_count = self.crud_repo.soft_remove(filters={"uuid": file_id}, session=session)

                result["success"] = True
                result["deleted_count"] = deleted_count if deleted_count is not None else 1

                if result["deleted_count"] == 0:
                    result["warnings"].append(f"No file found with ID {file_id} to delete")

                self._logger.INFO(f"Successfully deleted file {file_id}")

        except Exception as e:
            result["error"] = f"Database operation failed: {str(e)}"
            self._logger.ERROR(f"Failed to delete file {file_id}: {e}")

        return result

    def delete_files(self, file_ids: List[str]) -> Dict[str, Any]:
        """
        Deletes multiple files by their IDs with comprehensive tracking.

        Args:
            file_ids: List of file UUIDs to delete

        Returns:
            Dictionary containing batch deletion results and statistics
        """
        result = {
            "success": False,
            "total_requested": len(file_ids),
            "successful_deletions": 0,
            "failed_deletions": 0,
            "warnings": [],
            "failures": [],
        }

        # Input validation
        if not file_ids:
            result["warnings"].append("Empty file list provided")
            result["success"] = True  # Empty list is not an error
            return result

        for file_id in file_ids:
            try:
                delete_result = self.delete_file(file_id)
                if delete_result["success"]:
                    result["successful_deletions"] += delete_result["deleted_count"]
                    if delete_result["warnings"]:
                        result["warnings"].extend(delete_result["warnings"])
                else:
                    result["failed_deletions"] += 1
                    result["failures"].append({"file_id": file_id, "error": delete_result["error"]})
            except Exception as e:
                result["failed_deletions"] += 1
                result["failures"].append({"file_id": file_id, "error": f"Unexpected error: {str(e)}"})
                self._logger.ERROR(f"Failed to delete file {file_id}: {e}")
                continue

        # Determine overall success
        result["success"] = result["failed_deletions"] == 0

        self._logger.INFO(
            f"Batch deletion completed: {result['successful_deletions']} successful, {result['failed_deletions']} failed"
        )
        return result

    def get_files(
        self, name: str = None, file_type: FILE_TYPES = None, as_dataframe: bool = True, **kwargs
    ) -> Union[pd.DataFrame, List[Any]]:
        """
        Retrieves files from the database with caching.

        Args:
            name: File name filter
            file_type: File type filter
            as_dataframe: Return format
            **kwargs: Additional filters

        Returns:
            File data as DataFrame or list of models
        """
        # 提取filters参数并从kwargs中移除，避免重复传递
        filters = kwargs.pop("filters", {})

        # 具体参数优先级高于filters中的对应字段
        if name:
            filters["name"] = name
        if file_type:
            filters["type"] = file_type
        
        # Always exclude soft-deleted records
        filters["is_del"] = False

        return self.crud_repo.find(filters=filters, as_dataframe=as_dataframe, **kwargs)

    def get_file_content(self, file_id: str) -> bytes:
        """
        Retrieves the content of a specific file.

        Args:
            file_id: UUID of the file

        Returns:
            File content as bytes, or None if file not found
        """
        file_data = self.crud_repo.find(filters={"uuid": file_id, "is_del": False})
        if not file_data:
            return None
        return file_data[0].data if hasattr(file_data[0], "data") else b""

    def get_files_by_type(self, file_type: FILE_TYPES, as_dataframe: bool = True) -> Union[pd.DataFrame, List[Any]]:
        """
        Gets all files of a specific type.

        Args:
            file_type: Type of files to retrieve
            as_dataframe: Return format

        Returns:
            Files of the specified type
        """
        return self.get_files(file_type=file_type, as_dataframe=as_dataframe)

    def count_files(self, file_type: FILE_TYPES = None, **kwargs) -> int:
        """
        Counts the number of files matching the filters.

        Args:
            file_type: File type filter
            **kwargs: Additional filters

        Returns:
            Number of matching files
        """
        # 提取filters参数并从kwargs中移除，避免重复传递
        filters = kwargs.pop("filters", {})

        # 具体参数优先级高于filters中的对应字段
        if file_type:
            filters["type"] = file_type
        
        # Always exclude soft-deleted records
        filters["is_del"] = False

        return self.crud_repo.count(filters=filters)

    def file_exists(self, name: str, file_type: FILE_TYPES = None) -> bool:
        """
        Checks if a file exists by name and optionally type.

        Args:
            name: File name
            file_type: Optional file type filter

        Returns:
            True if file exists
        """
        filters = {"name": name, "is_del": False}
        if file_type:
            filters["type"] = file_type

        return self.crud_repo.exists(filters=filters)

    @retry(max_try=3)
    def initialize_files_from_source(self, working_dir: str = None) -> Dict[str, Any]:
        """
        Initializes files from the source code directory with comprehensive error handling and progress tracking.

        Args:
            working_dir: Working directory path (defaults to GCONF.WORKING_PATH)

        Returns:
            Dictionary with comprehensive initialization results and statistics
        """
        result = {
            "success": False,
            "working_dir": working_dir or GCONF.WORKING_PATH,
            "total_files_processed": 0,
            "total_files_added": 0,
            "error": None,
            "warnings": [],
            "folder_results": {},
            "failures": [],
        }

        if working_dir is None:
            working_dir = GCONF.WORKING_PATH

        file_root = f"{working_dir}/src/ginkgo/backtest"

        # Validate base directory exists
        if not os.path.exists(file_root):
            result["error"] = f"Source directory {file_root} does not exist"
            self._logger.ERROR(result["error"])
            return result

        file_type_map = {
            "analysis/analyzers": FILE_TYPES.ANALYZER,
            "strategy/risk_managementss": FILE_TYPES.RISKMANAGER,
            "strategy/selectors": FILE_TYPES.SELECTOR,
            "strategy/sizers": FILE_TYPES.SIZER,
            "strategy/strategies": FILE_TYPES.STRATEGY,
        }

        black_list = ["__", "base"]

        try:
            for folder, file_type in file_type_map.items():
                folder_path = f"{file_root}/{folder}"
                folder_result = {
                    "files_processed": 0,
                    "files_added": 0,
                    "files_skipped": 0,
                    "files_failed": 0,
                    "failures": [],
                }

                if not os.path.exists(folder_path):
                    result["warnings"].append(f"Folder {folder_path} does not exist, skipping")
                    result["folder_results"][folder] = folder_result
                    continue

                try:
                    files = os.listdir(folder_path)
                except PermissionError as e:
                    result["warnings"].append(f"Permission denied accessing {folder_path}: {e}")
                    result["folder_results"][folder] = folder_result
                    continue

                for file_name in files:
                    # Skip blacklisted files
                    if any(substring in file_name for substring in black_list):
                        folder_result["files_skipped"] += 1
                        continue

                    file_path = f"{folder_path}/{file_name}"
                    if not os.path.isfile(file_path):
                        folder_result["files_skipped"] += 1
                        continue

                    name_without_ext = file_name.split(".")[0]
                    folder_result["files_processed"] += 1
                    result["total_files_processed"] += 1

                    try:
                        # Check if file already exists and delete it
                        existing_files = self.get_files(name=name_without_ext, as_dataframe=True)
                        if not existing_files.empty:
                            file_ids = existing_files["uuid"].tolist()
                            delete_result = self.delete_files(file_ids)
                            if delete_result["successful_deletions"] > 0:
                                self._logger.DEBUG(f"Deleted existing {file_type.value} file: {name_without_ext}")

                        # Read and add new file
                        with open(file_path, "rb") as file:
                            content = file.read()
                            add_result = self.add_file(name_without_ext, file_type, content)

                            if add_result["success"]:
                                folder_result["files_added"] += 1
                                result["total_files_added"] += 1
                                self._logger.DEBUG(
                                    f"Added {file_type.value} file: {name_without_ext} ({len(content)} bytes)"
                                )
                            else:
                                folder_result["files_failed"] += 1
                                folder_result["failures"].append({"file": file_name, "error": add_result["error"]})

                    except Exception as e:
                        folder_result["files_failed"] += 1
                        folder_result["failures"].append(
                            {"file": file_name, "error": f"File processing error: {str(e)}"}
                        )
                        self._logger.ERROR(f"Failed to process file {file_path}: {e}")
                        continue

                result["folder_results"][folder] = folder_result
                self._logger.INFO(
                    f"Processed {folder}: {folder_result['files_added']}/{folder_result['files_processed']} files added successfully"
                )

            # Determine overall success
            result["success"] = result["total_files_added"] > 0
            if result["total_files_processed"] == 0:
                result["warnings"].append("No files found to process")

            self._logger.INFO(
                f"File initialization completed: {result['total_files_added']}/{result['total_files_processed']} files added successfully"
            )

        except Exception as e:
            result["error"] = f"Initialization failed: {str(e)}"
            self._logger.ERROR(f"Failed to initialize files from source: {e}")

        return result

    @retry(max_try=3)
    def hard_delete_file(self, file_id: str) -> Dict[str, Any]:
        """
        Permanently deletes a file by ID (hard delete) with comprehensive error handling.

        Args:
            file_id: UUID of the file to delete

        Returns:
            Dictionary containing operation status and deletion information
        """
        result = {"success": False, "file_id": file_id, "error": None, "warnings": [], "deleted_count": 0}

        # Input validation
        if not file_id or not file_id.strip():
            result["error"] = "File ID cannot be empty"
            return result

        try:
            with self.crud_repo.get_session() as session:
                deleted_count = self.crud_repo.remove(filters={"uuid": file_id}, session=session)

                result["success"] = True
                result["deleted_count"] = deleted_count if deleted_count is not None else 1

                if result["deleted_count"] == 0:
                    result["warnings"].append(f"No file found with ID {file_id} to delete")

                self._logger.INFO(f"Successfully hard deleted file {file_id}")

        except Exception as e:
            result["error"] = f"Database operation failed: {str(e)}"
            self._logger.ERROR(f"Failed to hard delete file {file_id}: {e}")

        return result

    def hard_delete_files(self, file_ids: List[str]) -> Dict[str, Any]:
        """
        Permanently deletes multiple files by their IDs (hard delete) with comprehensive tracking.

        Args:
            file_ids: List of file UUIDs to delete

        Returns:
            Dictionary containing batch deletion results and statistics
        """
        result = {
            "success": False,
            "total_requested": len(file_ids),
            "successful_deletions": 0,
            "failed_deletions": 0,
            "warnings": [],
            "failures": [],
        }

        # Input validation
        if not file_ids:
            result["warnings"].append("Empty file list provided")
            result["success"] = True  # Empty list is not an error
            return result

        for file_id in file_ids:
            try:
                delete_result = self.hard_delete_file(file_id)
                if delete_result["success"]:
                    result["successful_deletions"] += delete_result["deleted_count"]
                    if delete_result["warnings"]:
                        result["warnings"].extend(delete_result["warnings"])
                else:
                    result["failed_deletions"] += 1
                    result["failures"].append({"file_id": file_id, "error": delete_result["error"]})
            except Exception as e:
                result["failed_deletions"] += 1
                result["failures"].append({"file_id": file_id, "error": f"Unexpected error: {str(e)}"})
                self._logger.ERROR(f"Failed to hard delete file {file_id}: {e}")
                continue

        # Determine overall success
        result["success"] = result["failed_deletions"] == 0

        self._logger.INFO(
            f"Batch hard deletion completed: {result['successful_deletions']} successful, {result['failed_deletions']} failed"
        )
        return result

    def get_available_file_types(self) -> Dict[str, Any]:
        """
        Gets list of file types that have files in the database with error handling.

        Returns:
            Dictionary containing available file types and operation status
        """
        result = {"success": False, "file_types": [], "error": None, "warnings": [], "count": 0}

        try:
            unique_types = self.crud_repo.find(distinct_field="type", filters={"is_del": False})

            # Convert to FILE_TYPES enum and filter out invalid types
            valid_types = []
            for file_type in unique_types:
                if file_type:
                    try:
                        enum_type = FILE_TYPES(file_type)
                        valid_types.append(enum_type)
                    except ValueError:
                        result["warnings"].append(f"Invalid file type found in database: {file_type}")

            result["success"] = True
            result["file_types"] = valid_types
            result["count"] = len(valid_types)

            if result["count"] == 0:
                result["warnings"].append("No valid file types found in database")

        except Exception as e:
            result["error"] = f"Failed to get available file types: {str(e)}"
            self._logger.ERROR(f"Failed to get available file types: {e}")

        return result

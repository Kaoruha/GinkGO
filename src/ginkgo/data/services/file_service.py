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
from ginkgo.data.services.base_service import ManagementService, ServiceResult


class FileService(ManagementService):
    def __init__(self, crud_repo):
        """Initializes the service with its dependencies."""
        super().__init__(crud_repo=crud_repo)

    @retry(max_try=3)
    def add(self, name: str, file_type: FILE_TYPES, data: bytes, description: str = None) -> ServiceResult:
        """
        Adds a new file to the database with comprehensive error handling.

        Args:
            name: File name (without extension)
            file_type: Type of file (strategy, analyzer, etc.)
            data: File content as bytes
            description: Optional description

        Returns:
            ServiceResult containing file information and operation status
        """
        try:
            # Input validation
            if not name or not name.strip():
                return ServiceResult.error("File name cannot be empty")

            if not isinstance(data, bytes):
                return ServiceResult.error("File data must be bytes")

            warnings = []
            if len(data) == 0:
                warnings.append("File data is empty")

            if len(name) > 40:
                warnings.append("File name truncated to 40 characters")
                name = name[:40]

            # Create file record
            with self._crud_repo.get_session() as session:
                file_record = self._crud_repo.create(
                    name=name,
                    type=file_type,
                    data=data,
                    desc=description or f"{file_type.value} file: {name}",
                    session=session,
                )

                file_info = {
                    "uuid": file_record.uuid,
                    "name": file_record.name,
                    "type": file_record.type,
                    "desc": file_record.desc,
                    "data_size": len(data),
                }

                self._logger.INFO(f"Successfully added file '{name}' of type {file_type.value} ({len(data)} bytes)")

                result = ServiceResult.success(
                    data={"file_info": file_info},
                    message=f"File '{name}' added successfully"
                )

                # Add warnings if any
                for warning in warnings:
                    result.add_warning(warning)

                return result

        except Exception as e:
            return ServiceResult.error(f"Failed to add file: {str(e)}")

    @retry(max_try=3)
    def clone(self, source_id: str, new_name: str, file_type: FILE_TYPES = None) -> ServiceResult:
        """
        Creates a copy of an existing file with a new name and comprehensive error handling.

        Args:
            source_id: UUID of the file to clone
            new_name: Name for the new file
            file_type: Optional new file type (defaults to original)

        Returns:
            ServiceResult containing operation status and new file information
        """
        # Input validation
        if not source_id or not source_id.strip():
            return ServiceResult.error("Source file ID cannot be empty")

        if not new_name or not new_name.strip():
            return ServiceResult.error("New file name cannot be empty")

        try:
            # Get the source file content
            source_content = self.get_content(source_id)
            if source_content is None:
                return ServiceResult.error(f"Source file with ID {source_id} not found")

            # Get source file info to determine type if not specified
            if file_type is None:
                source_file = self._crud_repo.find(filters={"uuid": source_id})
                if not source_file:
                    return ServiceResult.error(f"Source file with ID {source_id} not found")
                file_type = FILE_TYPES(source_file[0].type)

            # Create the copy using add method
            copy_result = self.add(new_name, file_type, source_content, f"Copy of {source_id}")

            if copy_result.success:
                result = ServiceResult.success(
                    data={
                        "source_id": source_id,
                        "new_name": new_name,
                        "file_info": copy_result.data["file_info"]
                    },
                    message=f"File cloned successfully from {source_id} to {new_name}"
                )

                # Add warnings from copy operation
                for warning in copy_result.warnings:
                    result.add_warning(warning)

                if len(source_content) == 0:
                    result.add_warning("Source file content is empty")

                self._logger.INFO(f"Successfully cloned file {source_id} to {new_name}")
                return result
            else:
                return ServiceResult.error(f"Failed to create clone: {copy_result.message}")

        except Exception as e:
            return ServiceResult.error(f"Clone operation failed: {str(e)}")

    @retry(max_try=3)
    def update(
        self, file_id: str, name: str = None, data: bytes = None, description: str = None
    ) -> ServiceResult:
        """
        Updates an existing file with comprehensive error handling.

        Args:
            file_id: UUID of the file to update
            name: Optional new name
            data: Optional new file content
            description: Optional new description

        Returns:
            ServiceResult containing operation status and update information
        """
        # Input validation
        if not file_id or not file_id.strip():
            return ServiceResult.error("File ID cannot be empty")

        updates = {}
        warnings = []
        updates_applied = []

        if name is not None:
            if len(name) > 40:
                warnings.append("File name truncated to 40 characters")
                name = name[:40]
            updates["name"] = name
            updates_applied.append("name")

        if data is not None:
            if not isinstance(data, bytes):
                return ServiceResult.error("File data must be bytes")
            if len(data) == 0:
                warnings.append("File data is empty")
            updates["data"] = data
            updates_applied.append("data")

        if description is not None:
            updates["desc"] = description
            updates_applied.append("description")

        if not updates:
            warnings.append("No updates provided for file update")
            return ServiceResult.success(
                data={"file_id": file_id, "updates_applied": [], "updated_count": 0},
                message="No updates needed"
            )

        try:
            with self._crud_repo.get_session() as session:
                updated_count = self._crud_repo.modify(filters={"uuid": file_id}, updates=updates, session=session)

                self._logger.INFO(f"Successfully updated file {file_id} with {len(updates)} changes")

                result = ServiceResult.success(
                    data={
                        "file_id": file_id,
                        "updates_applied": updates_applied,
                        "updated_count": updated_count if updated_count is not None else 1
                    },
                    message=f"File updated successfully with {len(updates)} changes"
                )

                # Add warnings if any
                for warning in warnings:
                    result.add_warning(warning)

                return result

        except Exception as e:
            return ServiceResult.error(f"Failed to update file: {str(e)}")

    @retry(max_try=3)
    def soft_delete(self, file_id: str) -> ServiceResult:
        """
        Soft deletes a file by ID with comprehensive error handling.

        Args:
            file_id: UUID of the file to soft delete

        Returns:
            ServiceResult containing operation status and deletion information
        """
        # Input validation
        if not file_id or not file_id.strip():
            return ServiceResult.error("File ID cannot be empty")

        try:
            with self._crud_repo.get_session() as session:
                deleted_count = self._crud_repo.soft_remove(filters={"uuid": file_id}, session=session)

                deleted_count = deleted_count if deleted_count is not None else 1

                result = ServiceResult.success(
                    data={
                        "file_id": file_id,
                        "deleted_count": deleted_count
                    },
                    message=f"File {file_id} soft deleted successfully"
                )

                if deleted_count == 0:
                    result.add_warning(f"No file found with ID {file_id} to delete")

                self._logger.INFO(f"Successfully deleted file {file_id}")
                return result

        except Exception as e:
            return ServiceResult.error(f"Failed to delete file: {str(e)}")

    def soft_delete_batch(self, file_ids: List[str]) -> ServiceResult:
        """
        Soft deletes multiple files by their IDs with comprehensive tracking.

        Args:
            file_ids: List of file UUIDs to soft delete

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
                delete_result = self.soft_delete(file_id)
                if delete_result.success:
                    result["successful_deletions"] += delete_result.data.get("deleted_count", 0)
                    if delete_result.warnings:
                        result["warnings"].extend(delete_result.warnings)
                else:
                    result["failed_deletions"] += 1
                    result["failures"].append({"file_id": file_id, "error": delete_result.error})
            except Exception as e:
                result["failed_deletions"] += 1
                result["failures"].append({"file_id": file_id, "error": f"Unexpected error: {str(e)}"})
                self._logger.ERROR(f"Failed to delete file {file_id}: {e}")
                continue

        # Determine overall success
        success = result["failed_deletions"] == 0

        self._logger.INFO(
            f"Batch deletion completed: {result['successful_deletions']} successful, {result['failed_deletions']} failed"
        )

        if success:
            service_result = ServiceResult.success(
                data={
                    "total_requested": result["total_requested"],
                    "successful_deletions": result["successful_deletions"],
                    "failed_deletions": result["failed_deletions"],
                    "failures": result["failures"]
                },
                message=f"Batch deletion completed: {result['successful_deletions']} successful, {result['failed_deletions']} failed"
            )
        else:
            service_result = ServiceResult.error(
                f"Batch deletion partially failed: {result['failed_deletions']} of {result['total_requested']} failed",
                data={
                    "total_requested": result["total_requested"],
                    "successful_deletions": result["successful_deletions"],
                    "failed_deletions": result["failed_deletions"],
                    "failures": result["failures"]
                }
            )

        # Add warnings if any
        for warning in result["warnings"]:
            service_result.add_warning(warning)

        return service_result

    def get(
        self, name: str = None, file_type: FILE_TYPES = None, as_dataframe: bool = True, **kwargs
    ) -> ServiceResult:
        """
        Retrieves files from the database with caching.

        Args:
            name: File name filter
            file_type: File type filter
            as_dataframe: Return format
            **kwargs: Additional filters

        Returns:
            ServiceResult containing file data as DataFrame or list of models
        """
        try:
            # 提取filters参数并从kwargs中移除，避免重复传递
            filters = kwargs.pop("filters", {})

            # 具体参数优先级高于filters中的对应字段
            if name:
                filters["name"] = name
            if file_type:
                filters["type"] = file_type

            # Always exclude soft-deleted records
            filters["is_del"] = False

            files = self._crud_repo.find(filters=filters, as_dataframe=as_dataframe, **kwargs)
            return ServiceResult.success(
                data={"files": files, "as_dataframe": as_dataframe, "count": len(files) if hasattr(files, '__len__') else 0},
                message=f"Retrieved files successfully"
            )
        except Exception as e:
            self._logger.ERROR(f"Failed to get files: {e}")
            return ServiceResult.error(f"Failed to get files: {str(e)}")

    def get_by_uuid(self, file_id: str) -> ServiceResult:
        """
        Get file by UUID.

        Args:
            file_id: File UUID

        Returns:
            ServiceResult containing file record or None if not found
        """
        try:
            if not file_id or not file_id.strip():
                return ServiceResult.error("File ID cannot be empty")

            filters = {"uuid": file_id, "is_del": False}
            files = self._crud_repo.find(filters=filters, page_size=1)

            if not files or len(files) == 0:
                return ServiceResult.success(
                    data={"file": None, "exists": False},
                    message=f"No file found with ID {file_id}"
                )

            return ServiceResult.success(
                data={"file": files[0], "exists": True},
                message=f"File {file_id} found successfully"
            )

        except Exception as e:
            self._logger.ERROR(f"Failed to get file by UUID: {e}")
            return ServiceResult.error(f"Failed to get file by UUID: {str(e)}")

    def get_by_name(self, name: str, file_type: Optional[FILE_TYPES] = None) -> ServiceResult:
        """
        Get file(s) by name.

        Args:
            name: File name
            file_type: Optional file type filter

        Returns:
            ServiceResult containing file(s) matching the name
        """
        try:
            if not name or not name.strip():
                return ServiceResult.error("File name cannot be empty")

            filters = {"name": name, "is_del": False}
            if file_type:
                filters["type"] = file_type

            files = self._crud_repo.find(filters=filters)

            return ServiceResult.success(
                data={"files": files.to_entities(), "count": len(files)},
                message=f"Found {len(files)} files with name '{name}'"
            )

        except Exception as e:
            self._logger.ERROR(f"Failed to get file by name: {e}")
            return ServiceResult.error(f"Failed to get file by name: {str(e)}")

    def get_by_type(self, file_type: FILE_TYPES) -> ServiceResult:
        """
        Get all files of a specific type.

        Args:
            file_type: Type of files to retrieve

        Returns:
            ServiceResult containing files of the specified type
        """
        try:
            filters = {"type": file_type, "is_del": False}
            files = self._crud_repo.find(filters=filters)

            return ServiceResult.success(
                data={"files": files.to_entities(), "count": len(files)},
                message=f"Found {len(files)} files of type {file_type.value}"
            )

        except Exception as e:
            self._logger.ERROR(f"Failed to get files by type: {e}")
            return ServiceResult.error(f"Failed to get files by type: {str(e)}")

    def get_content(self, file_id: str) -> bytes:
        """
        Retrieves the content of a specific file.

        Args:
            file_id: UUID of the file

        Returns:
            File content as bytes, or None if file not found
        """
        file_data = self._crud_repo.find(filters={"uuid": file_id, "is_del": False})
        if not file_data:
            return None
        return file_data[0].data if hasattr(file_data[0], "data") else b""

    
    
    @retry(max_try=3)
    def initialize(self, working_dir: str = None) -> ServiceResult:
        """
        Initialize files from the source code directory.

        Args:
            working_dir: Working directory path (defaults to GCONF.WORKING_PATH)

        Returns:
            ServiceResult with initialization results and statistics
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
            error_msg = f"Source directory {file_root} does not exist"
            self._logger.ERROR(error_msg)
            return ServiceResult.error(error_msg)

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
                        existing_files_result = self.get_by_name(name=name_without_ext)
                        if existing_files_result.success and existing_files_result.data["count"] > 0:
                            existing_files = existing_files_result.data["files"]
                            file_ids = [f.uuid for f in existing_files]
                            delete_result = self.hard_delete_batch(file_ids)
                            if delete_result["successful_deletions"] > 0:
                                self._logger.DEBUG(f"Deleted existing {file_type.value} file: {name_without_ext}")

                        # Read and add new file
                        with open(file_path, "rb") as file:
                            content = file.read()
                            add_result = self.add(name_without_ext, file_type, content)

                            if add_result.success:
                                folder_result["files_added"] += 1
                                result["total_files_added"] += 1
                                self._logger.DEBUG(
                                    f"Added {file_type.value} file: {name_without_ext} ({len(content)} bytes)"
                                )
                            else:
                                folder_result["files_failed"] += 1
                                folder_result["failures"].append({"file": file_name, "error": add_result.error})

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
            error_msg = f"Initialization failed: {str(e)}"
            self._logger.ERROR(f"Failed to initialize files from source: {e}")
            return ServiceResult.error(error_msg)

        # Convert result dict to ServiceResult
        success = result["total_files_added"] > 0 or result["total_files_processed"] == 0
        if success:
            service_result = ServiceResult.success(
                data={
                    "working_dir": result["working_dir"],
                    "total_files_processed": result["total_files_processed"],
                    "total_files_added": result["total_files_added"],
                    "folder_results": result["folder_results"],
                    "failures": result["failures"]
                },
                message=f"File initialization completed: {result['total_files_added']}/{result['total_files_processed']} files added successfully"
            )
        else:
            service_result = ServiceResult.error(
                f"Initialization failed to add any files: {result['total_files_processed']} processed, 0 added",
                data={
                    "working_dir": result["working_dir"],
                    "total_files_processed": result["total_files_processed"],
                    "total_files_added": result["total_files_added"],
                    "folder_results": result["folder_results"],
                    "failures": result["failures"]
                }
            )

        # Add warnings if any
        for warning in result["warnings"]:
            service_result.add_warning(warning)

        return service_result

    def get_available_names(self, file_type: FILE_TYPES = None) -> ServiceResult:
        """
        Gets list of available file names, optionally filtered by type.

        Args:
            file_type: Optional file type filter

        Returns:
            ServiceResult containing list of available file names
        """
        try:
            filters = {"is_del": False}
            if file_type:
                filters["type"] = file_type

            # Get distinct file names
            files = self._crud_repo.find(distinct_field="name", filters=filters)

            # Filter out empty names and sort
            available_names = [name for name in files if name and name.strip()]
            available_names.sort()

            return ServiceResult.success(
                data={"names": available_names, "count": len(available_names)},
                message=f"Found {len(available_names)} available file names"
            )
        except Exception as e:
            self._logger.ERROR(f"Failed to get available file names: {e}")
            return ServiceResult.error(f"Failed to get available file names: {str(e)}")

    def exists(self, name: str = None, file_id: str = None, **kwargs) -> ServiceResult:
        """
        Standardized file existence check.

        Args:
            name: File name to check
            file_id: File UUID to check
            **kwargs: Additional filters

        Returns:
            ServiceResult containing existence check result
        """
        try:
            filters = {"is_del": False}

            if file_id:
                filters["uuid"] = file_id
            elif name:
                filters["name"] = name

            # Add any additional filters
            filters.update({k: v for k, v in kwargs.items() if k != 'filters'})

            exists = self._crud_repo.exists(filters=filters)

            return ServiceResult.success(
                data=exists,  # 直接封装bool值
                message=f"File existence check: {exists}"
            )
        except Exception as e:
            self._logger.ERROR(f"Failed to check file existence: {e}")
            return ServiceResult.error(f"Failed to check file existence: {str(e)}")

    @retry(max_try=3)
    def hard_delete(self, file_id: str) -> ServiceResult:
        """
        Permanently deletes a file by ID (hard delete) with comprehensive error handling.

        Args:
            file_id: UUID of the file to delete

        Returns:
            ServiceResult containing operation status and deletion information
        """
        # Input validation
        if not file_id or not file_id.strip():
            return ServiceResult.error("File ID cannot be empty")

        try:
            with self._crud_repo.get_session() as session:
                deleted_count = self._crud_repo.remove(filters={"uuid": file_id}, session=session)

                deleted_count = deleted_count if deleted_count is not None else 1

                if deleted_count == 0:
                    result = ServiceResult.success(
                        data={"deleted_count": 0, "file_id": file_id},
                        message=f"No file found with ID {file_id} to delete"
                    )
                    result.add_warning(f"No file found with ID {file_id} to delete")
                    return result

                self._logger.INFO(f"Successfully hard deleted file {file_id}")
                return ServiceResult.success(
                    data={"deleted_count": deleted_count, "file_id": file_id},
                    message=f"File '{file_id}' permanently deleted successfully"
                )

        except Exception as e:
            self._logger.ERROR(f"Failed to hard delete file {file_id}: {e}")
            return ServiceResult.error(f"Database operation failed: {str(e)}")

    def hard_delete_batch(self, file_ids: List[str]) -> ServiceResult:
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
                delete_result = self.hard_delete(file_id)
                if delete_result.success:
                    result["successful_deletions"] += delete_result.data.get("deleted_count", 0)
                    if delete_result.warnings:
                        result["warnings"].extend(delete_result.warnings)
                else:
                    result["failed_deletions"] += 1
                    result["failures"].append({"file_id": file_id, "error": delete_result.error})
            except Exception as e:
                result["failed_deletions"] += 1
                result["failures"].append({"file_id": file_id, "error": f"Unexpected error: {str(e)}"})
                self._logger.ERROR(f"Failed to hard delete file {file_id}: {e}")
                continue

        # Determine overall success
        success = result["failed_deletions"] == 0

        self._logger.INFO(
            f"Batch hard deletion completed: {result['successful_deletions']} successful, {result['failed_deletions']} failed"
        )

        if success:
            service_result = ServiceResult.success(
                data={
                    "total_requested": result["total_requested"],
                    "successful_deletions": result["successful_deletions"],
                    "failed_deletions": result["failed_deletions"],
                    "failures": result["failures"]
                },
                message=f"Batch hard deletion completed: {result['successful_deletions']} successful, {result['failed_deletions']} failed"
            )
        else:
            service_result = ServiceResult.error(
                f"Batch hard deletion partially failed: {result['failed_deletions']} of {result['total_requested']} failed",
                data={
                    "total_requested": result["total_requested"],
                    "successful_deletions": result["successful_deletions"],
                    "failed_deletions": result["failed_deletions"],
                    "failures": result["failures"]
                }
            )

        # Add warnings if any
        for warning in result["warnings"]:
            service_result.add_warning(warning)

        return service_result

    def get_available_types(self) -> ServiceResult:
        """
        Gets list of file types that have files in the database with error handling.

        Returns:
            ServiceResult containing available file types and operation status
        """
        try:
            unique_types = self._crud_repo.find(distinct_field="type", filters={"is_del": False})

            # Convert to FILE_TYPES enum and filter out invalid types
            valid_types = []
            warnings = []
            for file_type in unique_types:
                if file_type:
                    try:
                        enum_type = FILE_TYPES(file_type)
                        valid_types.append(enum_type)
                    except ValueError:
                        warnings.append(f"Invalid file type found in database: {file_type}")

            if len(valid_types) == 0:
                warnings.append("No valid file types found in database")

            result = ServiceResult.success(
                data={"file_types": valid_types, "count": len(valid_types)},
                message=f"Found {len(valid_types)} valid file types"
            )

            # Add warnings if any
            for warning in warnings:
                result.add_warning(warning)

            return result

        except Exception as e:
            self._logger.ERROR(f"Failed to get available file types: {e}")
            return ServiceResult.error(f"Failed to get available file types: {str(e)}")

    
    def count(self, file_type: FILE_TYPES = None, **kwargs) -> ServiceResult:
        """
        Count files matching the given filters.

        Args:
            file_type: File type filter
            **kwargs: Additional filters

        Returns:
            ServiceResult containing count of matching files
        """
        try:
            # 提取filters参数并从kwargs中移除，避免重复传递
            filters = kwargs.pop("filters", {})

            # 具体参数优先级高于filters中的对应字段
            if file_type:
                filters["type"] = file_type

            # Always exclude soft-deleted records
            filters["is_del"] = False

            count = self._crud_repo.count(filters=filters)
            return ServiceResult.success(
                data={"count": count},
                message=f"Found {count} files matching the criteria"
            )
        except Exception as e:
            self._logger.ERROR(f"Failed to count files: {e}")
            return ServiceResult.error(f"Failed to count files: {str(e)}")

    def validate(self, name: str = None, file_type: FILE_TYPES = None, data: bytes = None, **kwargs) -> ServiceResult:
        """
        Validate file data and metadata.

        Args:
            name: File name to validate
            file_type: File type to validate
            data: File data to validate
            **kwargs: Additional validation parameters

        Returns:
            ServiceResult with validation outcome
        """
        from ginkgo.libs.data.results import DataValidationResult

        validation_result = DataValidationResult.create_for_entity(
            entity_type="file",
            entity_identifier=name or "unknown",
            validation_type="business_rules"
        )

        try:
            # Validate file name
            if name:
                if not name or not name.strip():
                    validation_result.add_error("File name cannot be empty")
                elif len(name) > 40:
                    validation_result.add_warning("File name exceeds 40 characters")

            # Validate file type
            if file_type:
                if not isinstance(file_type, FILE_TYPES):
                    validation_result.add_error("Invalid file type")

            # Validate file data
            if data is not None:
                if not isinstance(data, bytes):
                    validation_result.add_error("File data must be bytes")
                elif len(data) == 0:
                    validation_result.add_warning("File data is empty")

            # Determine overall success
            is_valid = validation_result.error_count == 0

            if is_valid:
                return ServiceResult.success(
                    data=validation_result,
                    message=f"File validation passed: {validation_result.records_validated} records checked"
                )
            else:
                return ServiceResult.error(
                    error=f"File validation failed: {validation_result.error_count} errors found",
                    data=validation_result
                )

        except Exception as e:
            return ServiceResult.error(
                error=f"File validation error: {str(e)}",
                data=validation_result
            )

    def search_by_name(
        self,
        keyword: str,
        file_type: Optional[FILE_TYPES] = None,
        exact_match: bool = False,
        case_sensitive: bool = False,
        page: int = 0,
        page_size: int = 50
    ) -> ServiceResult:
        """
        Search files by name with fuzzy matching capabilities and pagination.

        Args:
            keyword: Search keyword
            file_type: Optional file type filter
            exact_match: Whether to use exact match or contains
            case_sensitive: Whether search is case sensitive
            page: Page number (0-based)
            page_size: Number of results per page

        Returns:
            ServiceResult containing search results with pagination info
        """
        try:
            # Input validation
            if not keyword or not keyword.strip():
                return ServiceResult.error("Search keyword cannot be empty")

            # Build filters using database-level LIKE queries
            filters = {"is_del": False}
            if file_type:
                filters["type"] = file_type

            # Use database-level filtering
            if exact_match:
                # Exact match: use exact field filter
                filters["name"] = keyword
            else:
                # Fuzzy match: use LIKE operator
                filters["name__like"] = f"%{keyword}%"

            # Get total count for pagination
            total_count = self._crud_repo.count(filters=filters)

            # Query database with pagination
            files = self._crud_repo.find(
                filters=filters,
                page=page,
                page_size=page_size,
                order_by="create_at",
                desc_order=True
            )

            # Format results - no need for in-memory filtering
            search_results = []
            for file_record in files:
                search_results.append({
                    "uuid": file_record.uuid,
                    "name": file_record.name,
                    "type": file_record.type,
                    "desc": file_record.desc,
                    "create_at": file_record.create_at,
                    "update_at": file_record.update_at,
                    "relevance": "name_match"
                })

            # Calculate pagination info
            total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
            has_next = page < total_pages - 1
            has_prev = page > 0

            return ServiceResult.success(
                data={
                    "search_type": "name_search",
                    "keyword": keyword,
                    "file_type": file_type,
                    "exact_match": exact_match,
                    "case_sensitive": case_sensitive,
                    "results": search_results,
                    "count": len(search_results),  # 向后兼容
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_count": total_count,
                        "total_pages": total_pages,
                        "has_next": has_next,
                        "has_prev": has_prev,
                        "count_on_page": len(search_results)
                    }
                },
                message=f"Found {len(search_results)} files matching name '{keyword}' (page {page + 1}/{total_pages})"
            )

        except Exception as e:
            self._logger.ERROR(f"Failed to search files by name: {e}")
            return ServiceResult.error(f"Search by name failed: {str(e)}")

    def search_by_description(
        self,
        keyword: str,
        file_type: Optional[FILE_TYPES] = None,
        exact_match: bool = False,
        case_sensitive: bool = False,
        page: int = 0,
        page_size: int = 50
    ) -> ServiceResult:
        """
        Search files by description with fuzzy matching capabilities.

        Args:
            keyword: Search keyword
            file_type: Optional file type filter
            exact_match: Whether to use exact match or contains
            case_sensitive: Whether search is case sensitive
            limit: Maximum number of results to return

        Returns:
            ServiceResult containing search results
        """
        try:
            # Input validation
            if not keyword or not keyword.strip():
                return ServiceResult.error("Search keyword cannot be empty")

            # Build filters using database-level LIKE queries
            filters = {"is_del": False}
            if file_type:
                filters["type"] = file_type

            # Use database-level filtering
            if exact_match:
                # Exact match: use exact field filter
                filters["desc"] = keyword
            else:
                # Fuzzy match: use LIKE operator
                filters["desc__like"] = f"%{keyword}%"

            # Get total count for pagination
            total_count = self._crud_repo.count(filters=filters)

            # Query database with pagination
            files = self._crud_repo.find(
                filters=filters,
                page=page,
                page_size=page_size,
                order_by="create_at",
                desc_order=True
            )

            # Format results - no need for in-memory filtering
            search_results = []
            for file_record in files:
                search_results.append({
                    "uuid": file_record.uuid,
                    "name": file_record.name,
                    "type": file_record.type,
                    "desc": file_record.desc,
                    "create_at": file_record.create_at,
                    "update_at": file_record.update_at,
                    "relevance": "description_match"
                })

            # Calculate pagination info
            total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
            has_next = page < total_pages - 1
            has_prev = page > 0

            return ServiceResult.success(
                data={
                    "search_type": "description_search",
                    "keyword": keyword,
                    "file_type": file_type,
                    "exact_match": exact_match,
                    "case_sensitive": case_sensitive,
                    "results": search_results,
                    "count": len(search_results),  # 向后兼容
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_count": total_count,
                        "total_pages": total_pages,
                        "has_next": has_next,
                        "has_prev": has_prev,
                        "count_on_page": len(search_results)
                    }
                },
                message=f"Found {len(search_results)} files matching description '{keyword}' (page {page + 1}/{total_pages})"
            )

        except Exception as e:
            self._logger.ERROR(f"Failed to search files by description: {e}")
            return ServiceResult.error(f"Search by description failed: {str(e)}")

    def search_by_content(
        self,
        keyword: str,
        file_type: Optional[FILE_TYPES] = None,
        page: int = 0,
        page_size: int = 50
    ) -> ServiceResult:
        """
        Search files by content (binary data search using text encoding).

        Args:
            keyword: Search keyword
            file_type: Optional file type filter
            limit: Maximum number of results to return

        Returns:
            ServiceResult containing search results
        """
        try:
            # Input validation
            if not keyword or not keyword.strip():
                return ServiceResult.error("Search keyword cannot be empty")

            # Build filters
            filters = {"is_del": False}
            if file_type:
                filters["type"] = file_type

            # Get total count first (for pagination)
            total_count = self._crud_repo.count(filters=filters)

            # Get files with pagination for content search
            files = self._crud_repo.find(
                filters=filters,
                page=page,
                page_size=page_size,
                order_by="create_at",
                desc_order=True
            )

            # Search in content (application-level filtering is necessary for binary data)
            search_results = []
            keyword_bytes = keyword.encode('utf-8', errors='ignore')

            for file_record in files:
                if hasattr(file_record, 'data') and file_record.data:
                    # Search for keyword in binary data
                    if keyword_bytes.lower() in file_record.data.lower():
                        search_results.append({
                            "uuid": file_record.uuid,
                            "name": file_record.name,
                            "type": file_record.type,
                            "desc": file_record.desc,
                            "content_size": len(file_record.data),
                            "create_at": file_record.create_at,
                            "update_at": file_record.update_at,
                            "relevance": "content_match"
                        })

            # Calculate pagination info
            total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
            has_next = page < total_pages - 1
            has_prev = page > 0

            return ServiceResult.success(
                data={
                    "search_type": "content_search",
                    "keyword": keyword,
                    "file_type": file_type,
                    "results": search_results,
                    "count": len(search_results),  # 向后兼容
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_count": total_count,
                        "total_pages": total_pages,
                        "has_next": has_next,
                        "has_prev": has_prev,
                        "count_on_page": len(search_results)
                    }
                },
                message=f"Found {len(search_results)} files containing keyword '{keyword}' (page {page + 1}/{total_pages})"
            )

        except Exception as e:
            self._logger.ERROR(f"Failed to search files by content: {e}")
            return ServiceResult.error(f"Search by content failed: {str(e)}")

    def search(
        self,
        keyword: str,
        search_in: List[str] = ["name", "description"],
        file_type: Optional[FILE_TYPES] = None,
        exact_match: bool = False,
        case_sensitive: bool = False,
        page: int = 0,
        page_size: int = 50
    ) -> ServiceResult:
        """
        Unified search method that can search across multiple fields using a single database query.

        Args:
            keyword: Search keyword
            search_in: List of fields to search in ["name", "description"]
            file_type: Optional file type filter
            exact_match: Whether to use exact match or contains
            case_sensitive: Whether search is case sensitive (not implemented yet)
            page: Page number (0-based)
            page_size: Number of results per page

        Returns:
            ServiceResult containing search results from all specified fields
        """
        try:
            # Input validation
            if not keyword or not keyword.strip():
                return ServiceResult.error("Search keyword cannot be empty")

            if not search_in:
                return ServiceResult.error("Search fields cannot be empty")

            # Validate search fields
            valid_fields = ["name", "description"]
            invalid_fields = [field for field in search_in if field not in valid_fields]
            if invalid_fields:
                return ServiceResult.error(f"Invalid search fields: {invalid_fields}. Valid fields: {valid_fields}")

            # Use direct database query with OR conditions for better performance
            from sqlalchemy import or_
            from ginkgo.data.models import MFile

            conn = self._crud_repo._get_connection()
            with conn.get_session() as session:
                query = session.query(MFile).filter(MFile.is_del == False)

                # Build OR conditions for multi-field search
                or_conditions = []

                for field in search_in:
                    if field == "name":
                        if exact_match:
                            or_conditions.append(MFile.name == keyword)
                        else:
                            or_conditions.append(MFile.name.like(f"%{keyword}%"))
                    elif field == "description":
                        if exact_match:
                            or_conditions.append(MFile.desc == keyword)
                        else:
                            or_conditions.append(MFile.desc.like(f"%{keyword}%"))

                # Apply OR conditions
                if or_conditions:
                    query = query.filter(or_(*or_conditions))

                # Apply file type filter if specified
                if file_type is not None:
                    query = query.filter(MFile.type == file_type.value)

                # Count total results
                total_count = query.count()

                # Apply pagination and ordering
                query = query.order_by(MFile.create_at.desc())
                query = query.offset(page * page_size).limit(page_size)

                # Execute query
                files = query.all()

                # Format results similar to other search methods
                results = []
                for file_record in files:
                    results.append({
                        "uuid": file_record.uuid,
                        "name": file_record.name,
                        "type": file_record.type,
                        "desc": file_record.desc,
                        "create_at": file_record.create_at,
                        "update_at": file_record.update_at,
                        "relevance": "multi_field_match"
                    })

                self._logger.DEBUG(
                    f"Unified search completed: {total_count} files found, "
                    f"returning {len(results)} results (page {page})"
                )

                return ServiceResult.success(
                    data={
                        "search_type": "unified_search",
                        "keyword": keyword,
                        "search_in": search_in,
                        "file_type": file_type,
                        "exact_match": exact_match,
                        "case_sensitive": case_sensitive,
                        "results": results,
                        "count": len(results),  # 向后兼容
                        "total_found": total_count,
                        "pagination": {
                            "page": page,
                            "page_size": page_size,
                            "total_count": total_count,
                            "total_pages": (total_count + page_size - 1) // page_size,
                            "has_next": (page + 1) * page_size < total_count,
                            "has_prev": page > 0,
                            "count_on_page": len(results)
                        }
                    },
                    message=f"Found {total_count} files matching '{keyword}' in {search_in}"
                )

        except Exception as e:
            self._logger.ERROR(f"Failed to perform unified search: {e}")
            return ServiceResult.error(f"Unified search failed: {str(e)}")

    def check_integrity(self, name: str = None, file_type: FILE_TYPES = None, **kwargs) -> ServiceResult:
        """
        Check integrity of file data in database.

        Args:
            name: File name to check
            file_type: File type to check
            **kwargs: Additional integrity check parameters

        Returns:
            ServiceResult with integrity check outcome
        """
        from ginkgo.libs.data.results import DataIntegrityCheckResult

        integrity_result = DataIntegrityCheckResult.create_for_entity(
            entity_type="file",
            entity_identifier=name or "batch_check",
            check_range="all_files",
            check_duration=0.0
        )

        try:
            # Build filters for integrity check
            filters = {"is_del": False}
            if name:
                filters["name"] = name
            if file_type:
                filters["type"] = file_type

            # Get files for integrity check
            files = self._crud_repo.find(filters=filters, page_size=1000)  # Limit to prevent memory issues

            if not files:
                integrity_result.add_warning("No files found for integrity check")
                return ServiceResult.success(
                    data=integrity_result,
                    message="No files to check integrity"
                )

            # Check each file's integrity
            for file_record in files:
                try:
                    # Check UUID validity
                    if not file_record.uuid:
                        integrity_result.add_error(f"File {file_record.name}: Missing UUID")
                    else:
                        integrity_result.records_checked += 1

                    # Check name validity
                    if not file_record.name:
                        integrity_result.add_error(f"File UUID {file_record.uuid}: Missing name")

                    # Check type validity
                    if not file_record.type:
                        integrity_result.add_error(f"File {file_record.name}: Missing type")
                    else:
                        try:
                            FILE_TYPES(file_record.type)  # Validate enum
                        except ValueError:
                            integrity_result.add_error(f"File {file_record.name}: Invalid type {file_record.type}")

                    # Check data integrity
                    if hasattr(file_record, 'data') and file_record.data:
                        if not isinstance(file_record.data, bytes):
                            integrity_result.add_error(f"File {file_record.name}: Data is not bytes")

                    integrity_result.records_valid += 1

                except Exception as e:
                    integrity_result.add_error(f"File {getattr(file_record, 'name', 'unknown')}: {str(e)}")

            # Determine overall integrity
            has_integrity_issues = integrity_result.error_count > 0

            if has_integrity_issues:
                return ServiceResult.error(
                    error=f"File integrity check failed: {integrity_result.error_count} issues found",
                    data=integrity_result
                )
            else:
                return ServiceResult.success(
                    data=integrity_result,
                    message=f"File integrity check passed: {integrity_result.records_valid} files validated"
                )

        except Exception as e:
            return ServiceResult.error(
                error=f"File integrity check error: {str(e)}",
                data=integrity_result
            )

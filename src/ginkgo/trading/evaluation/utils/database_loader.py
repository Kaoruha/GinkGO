# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Database Loader模块提供DatabaseLoader数据库加载器提供数据加载功能支持评估数据获取功能支持回测评估和代码验证






"""
Database strategy loader for validating strategies stored in the database.

This module provides utilities to load strategy code from the database (MFile table)
into temporary files for validation, with automatic cleanup.
"""

import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Generator, List, Optional

from ginkgo.data.containers import container
from ginkgo.data.models import MFile, MPortfolioFileMapping
from ginkgo.enums import FILE_TYPES
from ginkgo.libs import GLOG


class DatabaseStrategyLoader:
    """
    Loader for strategies stored in the database.

    Provides methods to load strategy code from MFile table into temporary files,
    with automatic cleanup using context managers.

    Usage:
        loader = DatabaseStrategyLoader()

        # Load by file_id
        with loader.load_by_file_id(file_id) as temp_path:
            result = evaluator.evaluate(temp_path)

        # Load by portfolio_id
        with loader.load_by_portfolio_id(portfolio_id) as temp_path:
            result = evaluator.evaluate(temp_path)

        # List strategies
        strategies = loader.list_strategies(name_filter="MyStrategy")
    """

    def __init__(self):
        """Initialize the database strategy loader."""
        self._file_crud = None
        self._mapping_crud = None

    @property
    def file_crud(self):
        """Lazy load FileCRUD instance."""
        if self._file_crud is None:
            self._file_crud = container.file_crud()
        return self._file_crud

    @property
    def mapping_crud(self):
        """Lazy load PortfolioFileMappingCRUD instance."""
        if self._mapping_crud is None:
            self._mapping_crud = container.portfolio_file_mapping_crud()
        return self._mapping_crud

    @contextmanager
    def load_by_file_id(self, file_id: str) -> Generator[Path, None, None]:
        """
        Load strategy from database by file_id.

        Args:
            file_id: UUID of the file in MFile table

        Yields:
            Path: Temporary file path containing the strategy code

        Raises:
            FileNotFoundError: If file_id not found in database
            ValueError: If file data cannot be decoded
        """
        temp_file = None

        try:
            GLOG.DEBUG(f"Loading strategy by file_id: {file_id}")

            # Query file from database
            files = self.file_crud.find(filters={"uuid": file_id}, page_size=1)

            if not files or len(files) == 0:
                raise FileNotFoundError(f"File not found in database: {file_id}")

            file_record = files[0]

            # Validate file type is strategy (handle both enum and int values)
            file_type_value = file_record.type.value if hasattr(file_record.type, 'value') else file_record.type
            if file_type_value != FILE_TYPES.STRATEGY.value:
                GLOG.WARN(f"File {file_id} is not a strategy file (type={file_type_value})")

            # Decode binary data
            try:
                code_content = file_record.data.decode("utf-8")
            except UnicodeDecodeError as e:
                raise ValueError(f"Failed to decode file data: {e}")

            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                mode="w",
                suffix=f"_{file_record.name or 'strategy'}.py",
                delete=False,
                encoding="utf-8",
            )
            temp_file.write(code_content)
            temp_file.flush()
            temp_file.close()

            temp_path = Path(temp_file.name)
            GLOG.DEBUG(f"Created temp file: {temp_path}")

            yield temp_path

        finally:
            # Cleanup temp file
            if temp_file is not None:
                try:
                    temp_path = Path(temp_file.name)
                    temp_path.unlink(missing_ok=True)
                    GLOG.DEBUG(f"Cleaned up temp file: {temp_path}")
                except Exception as e:
                    GLOG.WARN(f"Failed to cleanup temp file: {e}")

    @contextmanager
    def load_by_portfolio_id(self, portfolio_id: str) -> Generator[Path, None, None]:
        """
        Load strategy from database by portfolio_id.

        Uses PortfolioFileMapping to find the associated file_id.

        Args:
            portfolio_id: Portfolio UUID to find strategy file

        Yields:
            Path: Temporary file path containing the strategy code

        Raises:
            FileNotFoundError: If portfolio_id or file not found
            ValueError: If file data cannot be decoded
        """
        temp_file = None

        try:
            GLOG.DEBUG(f"Loading strategy by portfolio_id: {portfolio_id}")

            # Query mapping to get file_id
            mappings = self.mapping_crud.find(
                filters={"portfolio_id": portfolio_id}, page_size=1
            )

            if not mappings or len(mappings) == 0:
                raise FileNotFoundError(f"Portfolio not found in database: {portfolio_id}")

            mapping = mappings[0]
            file_id = mapping.file_id

            # Load using file_id
            with self.load_by_file_id(file_id) as temp_path:
                yield temp_path

        finally:
            # Temp file cleanup handled by load_by_file_id
            pass

    def list_strategies(self, name_filter: Optional[str] = None) -> List[Dict]:
        """
        List all strategies in the database.

        Args:
            name_filter: Optional filter for strategy name (partial match)

        Returns:
            List[Dict]: List of strategy info dictionaries
                - file_id: UUID of the file
                - name: File name
                - portfolio_count: Number of portfolios using this strategy
        """
        GLOG.DEBUG(f"Listing strategies (filter={name_filter})")

        # Get all strategy files
        files = self.file_crud.find(filters={"type": FILE_TYPES.STRATEGY.value}, page_size=1000)

        result = []
        for file_record in files:
            # Apply name filter if provided
            if name_filter and name_filter.lower() not in file_record.name.lower():
                continue

            # Count portfolios using this strategy
            mappings = self.mapping_crud.find(
                filters={"file_id": file_record.uuid}, page_size=1000
            )

            result.append({
                "file_id": str(file_record.uuid),
                "name": file_record.name,
                "portfolio_count": len(mappings) if mappings else 0,
            })

        GLOG.DEBUG(f"Found {len(result)} strategies")
        return result

    def get_strategy_info(self, file_id: str) -> Optional[Dict]:
        """
        Get detailed information about a strategy.

        Args:
            file_id: UUID of the file

        Returns:
            Optional[Dict]: Strategy info or None if not found
                - file_id: UUID of the file
                - name: File name
                - type: File type enum
                - portfolio_count: Number of portfolios using this strategy
        """
        files = self.file_crud.find(filters={"uuid": file_id}, page_size=1)

        if not files or len(files) == 0:
            return None

        file_record = files[0]

        # Count portfolios
        mappings = self.mapping_crud.find(
            filters={"file_id": file_id}, page_size=1000
        )

        return {
            "file_id": str(file_record.uuid),
            "name": file_record.name,
            "type": file_record.type,
            "portfolio_count": len(mappings) if mappings else 0,
        }

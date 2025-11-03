from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MFile
from ginkgo.enums import SOURCE_TYPES, FILE_TYPES
from ginkgo.libs import GLOG
from ginkgo.trading.core.file_info import FileInfo
from ginkgo.data.access_control import restrict_crud_access


@restrict_crud_access
class FileCRUD(BaseCRUD[MFile]):
    """
    File CRUD operations.
    """

    # 类级别声明，支持自动注册

    _model_class = MFile

    def __init__(self):
        super().__init__(MFile)

    def _get_field_config(self) -> dict:
        """
        定义 File 数据的字段配置 - 必填字段验证
        
        Returns:
            dict: 字段配置字典
        """
        return {
            # 文件类型 - 枚举值
            'type': {
                'type': 'enum',
                'choices': [f for f in FILE_TYPES]
            },
            
            # 文件名 - 非空字符串，最大40字符（与模型String(40)一致）
            'name': {
                'type': 'string',
                'min': 1,
                'max': 40
            },
            
            # 文件数据 - 二进制数据
            'data': {
                'type': 'bytes'
            }
            
            # source字段移除验证配置，使用模型默认值 SOURCE_TYPES.OTHER
        }

    def _create_from_params(self, **kwargs) -> MFile:
        """
        Hook method: Create MFile from parameters.
        """
        # Convert string file_type to enum if needed
        file_type = kwargs.get("file_type", kwargs.get("type", FILE_TYPES.OTHER))
        if isinstance(file_type, str):
            # Map common string types to enum values
            type_mapping = {
                "TEXT": FILE_TYPES.OTHER,
                "PYTHON": FILE_TYPES.STRATEGY,
                "JSON": FILE_TYPES.OTHER,
                "ANALYZER": FILE_TYPES.ANALYZER,
                "INDEX": FILE_TYPES.INDEX,
                "STRATEGY": FILE_TYPES.STRATEGY,
                "ENGINE": FILE_TYPES.ENGINE,
                "HANDLER": FILE_TYPES.HANDLER,
            }
            file_type = type_mapping.get(file_type.upper(), FILE_TYPES.OTHER)
        
        return MFile(
            type=FILE_TYPES.validate_input(file_type),
            name=kwargs.get("filename", kwargs.get("name", "ginkgo_file")),
            data=kwargs.get("data", b""),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.SIM)),
        )

    def _convert_input_item(self, item: Any) -> Optional[MFile]:
        """
        Hook method: Convert file objects to MFile.
        """
        if isinstance(item, FileInfo):
            # Convert string type to enum if needed
            file_type = item.type
            if isinstance(file_type, str):
                type_mapping = {
                    "TEXT": FILE_TYPES.OTHER,
                    "PYTHON": FILE_TYPES.STRATEGY,
                    "JSON": FILE_TYPES.OTHER,
                    "ANALYZER": FILE_TYPES.ANALYZER,
                    "INDEX": FILE_TYPES.INDEX,
                    "STRATEGY": FILE_TYPES.STRATEGY,
                    "ENGINE": FILE_TYPES.ENGINE,
                    "HANDLER": FILE_TYPES.HANDLER,
                }
                file_type = type_mapping.get(file_type.upper(), FILE_TYPES.OTHER)
            
            return MFile(
                type=FILE_TYPES.validate_input(file_type),
                name=item.name,
                data=getattr(item, 'data', b""),
                source=SOURCE_TYPES.validate_input(item.source),
            )
        return None


    def _get_enum_mappings(self) -> Dict[str, Any]:
        """
        🎯 Define field-to-enum mappings.

        Returns:
            Dictionary mapping field names to enum classes
        """
        return {
            'file': FILE_TYPES,
            'source': SOURCE_TYPES
        }

    def _convert_models_to_business_objects(self, models: List) -> List:
        """
        🎯 Convert models to business objects.

        Args:
            models: List of models with enum fields already fixed

        Returns:
            List of models (business object doesn't exist yet)
        """
        # For now, return models as-is since business object doesn't exist yet
        return models

    def _convert_output_items(self, items: List, output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert objects for business layer.
        """
        return items

    def _convert_output_items(self, items: List[MFile], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MFile objects for business layer.
        """
        if output_type == "file_info":
            return [FileInfo(item) for item in items]
        return items

    # Business Helper Methods
    def find_by_file_id(self, file_id: str, as_dataframe: bool = False) -> Union[List[MFile], pd.DataFrame]:
        """
        Business helper: Find file by ID.
        """
        return self.find(filters={"uuid": file_id}, page_size=1,
                        as_dataframe=as_dataframe, output_type="model")

    def find_by_filename(self, filename: str, as_dataframe: bool = False) -> Union[List[MFile], pd.DataFrame]:
        """
        Business helper: Find files by filename pattern.
        """
        return self.find(filters={"name__like": filename}, order_by="update_at", desc_order=True,
                        as_dataframe=as_dataframe, output_type="model")

    def find_by_type(self, file_type: str, as_dataframe: bool = False) -> Union[List[MFile], pd.DataFrame]:
        """
        Business helper: Find files by type.
        """
        # Convert string type to enum if needed
        if isinstance(file_type, str):
            type_mapping = {
                "TEXT": FILE_TYPES.OTHER,
                "PYTHON": FILE_TYPES.STRATEGY,
                "JSON": FILE_TYPES.OTHER,
                "ANALYZER": FILE_TYPES.ANALYZER,
                "INDEX": FILE_TYPES.INDEX,
                "STRATEGY": FILE_TYPES.STRATEGY,
                "ENGINE": FILE_TYPES.ENGINE,
                "HANDLER": FILE_TYPES.HANDLER,
            }
            file_type = type_mapping.get(file_type.upper(), FILE_TYPES.OTHER)
        
        return self.find(filters={"type": file_type}, order_by="update_at", desc_order=True,
                        as_dataframe=as_dataframe, output_type="model")

    def find_by_size_range(self, min_size: int, max_size: int,
                          as_dataframe: bool = False) -> Union[List[MFile], pd.DataFrame]:
        """
        Business helper: Find files by size range (not supported by MFile model).
        """
        GLOG.DEBUG("File size range search not supported by MFile model")
        return self.find(filters={}, as_dataframe=as_dataframe, output_type="model")

    def get_total_size_by_type(self, file_type: str) -> int:
        """
        Business helper: Get total size of files by type (not supported by MFile model).
        """
        GLOG.DEBUG("File size calculation not supported by MFile model")
        files = self.find_by_type(file_type, as_dataframe=False)
        return len(files)

    def delete_by_file_id(self, file_id: str) -> None:
        """
        Business helper: Delete file by ID.
        """
        GLOG.DEBUG(f"删除文件记录: {file_id}")
        return self.remove({"uuid": file_id})

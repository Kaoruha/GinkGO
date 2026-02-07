# Upstream: CLI Commands, API Controllers, PortfolioGraphEditor (前端)
# Downstream: PortfolioFileMappingCRUD (MySQL), ParamCRUD (MySQL), GinkgoMongo (MongoDB), FileCRUD
# Role: PortfolioMappingService 投资组合映射服务 - MongoDB图结构与MySQL Mapping+Param双向同步


from typing import List, Optional, Dict, Any
import json
import uuid

from ginkgo.libs import GLOG, time_logger, retry
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.crud.portfolio_file_mapping_crud import PortfolioFileMappingCRUD
from ginkgo.data.crud.param_crud import ParamCRUD
from ginkgo.data.crud.file_crud import FileCRUD
from ginkgo.data.models import MPortfolioFileMapping, MParam
from ginkgo.enums import FILE_TYPES, SOURCE_TYPES
from ginkgo.data.drivers.ginkgo_mongo import GinkgoMongo


class PortfolioMappingService(BaseService):
    """
    投资组合映射服务

    实现 MongoDB 图结构与 MySQL Mapping + Param 的双向同步：
    1. 图编辑器创建 → 保存图到 MongoDB + 同步文件到 MySQL Mapping + 同步参数到 MParam
    2. 添加文件到投资组合 → 创建 MySQL Mapping + 自动生成图结构 + 同步默认参数到 MParam

    数据流：
    ┌─────────────────────────────────────────────────────────────┐
    │                    前端图编辑器 / CLI                        │
    └─────────────────────────────────────────────────────────────┘
                              ↓
    ┌─────────────────────────┴─────────────────────────────────┐
    │              PortfolioMappingService                       │
    │  ├── MongoDB: 完整图数据 (nodes + edges + viewport)        │
    │  └── MySQL:     ┌─────────────────────────────────────┐   │
    │                │  MPortfolioFileMapping  (文件映射)    │   │
    │                │  MParam                 (节点参数)    │   │
    │                └─────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────┘

    Attributes:
        _mapping_crud: PortfolioFileMappingCRUD 实例
        _param_crud: ParamCRUD 实例
        _mongo_driver: GinkgoMongo 驱动实例
        _file_crud: FileCRUD 实例
    """

    def __init__(
        self,
        mapping_crud: PortfolioFileMappingCRUD,
        param_crud: ParamCRUD,
        mongo_driver: GinkgoMongo,
        file_crud: FileCRUD,
    ):
        """
        初始化服务

        Args:
            mapping_crud: PortfolioFileMappingCRUD 实例
            param_crud: ParamCRUD 实例
            mongo_driver: GinkgoMongo 驱动实例
            file_crud: FileCRUD 实例
        """
        super().__init__(
            mapping_crud=mapping_crud,
            param_crud=param_crud,
            mongo_driver=mongo_driver,
            file_crud=file_crud,
        )

    # ==================== 方向 1: 图编辑器 → Mapping + Param ====================

    @time_logger
    @retry
    def create_from_graph_editor(
        self,
        portfolio_uuid: str,
        graph_data: Dict[str, Any],
        name: str,
    ) -> ServiceResult:
        """
        从图编辑器创建配置

        流程：
        1. 保存完整图数据到 MongoDB
        2. 解析 nodes 中的 file_id，同步到 MySQL Mapping
        3. 解析 nodes 中的 params，同步到 MySQL MParam

        Args:
            portfolio_uuid: 投资组合 UUID
            graph_data: 图数据 {"nodes": [...], "edges": [...], "viewport": {...}}
            name: 配置名称

        Returns:
            ServiceResult: 包含 mongo_id、mappings_count、params_count

        Examples:
            >>> result = service.create_from_graph_editor(
            ...     portfolio_uuid="portfolio123",
            ...     graph_data={
            ...         "nodes": [
            ...             {
            ...                 "id": "node-1",
            ...                 "type": "STRATEGY",
            ...                 "data": {
            ...                     "file_id": "file_strategy_1",
            ...                     "params": {"period": [5, 20], "fast_period": 3}
            ...                 }
            ...             }
            ...         ],
            ...         "edges": []
            ...     },
            ...     name="双均线策略"
            ... )
        """
        try:
            # 1. 提取图中的文件映射
            file_mappings = self._extract_files_from_graph(graph_data)

            # 2. 提取图中的节点参数
            node_params = self._extract_params_from_graph(graph_data)

            # 3. 保存到 MongoDB
            mongo_id = self._save_graph_to_mongo(
                portfolio_uuid=portfolio_uuid,
                graph_data=graph_data,
                name=name,
                source="GRAPH_EDITOR"
            )

            # 4. 同步到 MySQL Mapping
            mapping_sync_result = self._sync_mappings_from_files(
                portfolio_uuid=portfolio_uuid,
                file_mappings=file_mappings
            )

            # 5. 同步到 MySQL MParam
            param_sync_result = self._sync_params_from_nodes(
                portfolio_uuid=portfolio_uuid,
                node_params=node_params
            )

            GLOG.INFO(f"从图编辑器创建配置: {portfolio_uuid} ({mongo_id})")
            GLOG.DEBUG(f"  同步了 {len(file_mappings)} 个文件映射")
            GLOG.DEBUG(f"  同步了 {len(node_params)} 个节点参数")

            return ServiceResult.success(data={
                "mongo_id": mongo_id,
                "mappings_count": len(file_mappings),
                "params_count": len(node_params),
                "portfolio_uuid": portfolio_uuid,
            })

        except Exception as e:
            GLOG.ERROR(f"从图编辑器创建配置失败: {e}")
            return ServiceResult.error(f"从图编辑器创建配置失败: {str(e)}")

    @time_logger
    @retry
    def update_from_graph_editor(
        self,
        portfolio_uuid: str,
        graph_data: Dict[str, Any],
        name: Optional[str] = None,
    ) -> ServiceResult:
        """
        从图编辑器更新配置

        流程：
        1. 更新 MongoDB 图数据
        2. 同步文件映射到 MySQL
        3. 同步节点参数到 MySQL MParam

        Args:
            portfolio_uuid: 投资组合 UUID
            graph_data: 新的图数据
            name: 新的配置名称（可选）

        Returns:
            ServiceResult
        """
        try:
            # 1. 提取图中的文件映射和参数
            file_mappings = self._extract_files_from_graph(graph_data)
            node_params = self._extract_params_from_graph(graph_data)

            # 2. 更新 MongoDB
            mongo_id = self._update_graph_in_mongo(
                portfolio_uuid=portfolio_uuid,
                graph_data=graph_data,
                name=name,
                source="GRAPH_EDITOR"
            )

            # 3. 同步到 MySQL Mapping
            self._sync_mappings_from_files(
                portfolio_uuid=portfolio_uuid,
                file_mappings=file_mappings
            )

            # 4. 同步到 MySQL MParam
            self._sync_params_from_nodes(
                portfolio_uuid=portfolio_uuid,
                node_params=node_params
            )

            GLOG.INFO(f"从图编辑器更新配置: {portfolio_uuid}")

            return ServiceResult.success(data={
                "mongo_id": mongo_id,
                "mappings_count": len(file_mappings),
                "params_count": len(node_params),
            })

        except Exception as e:
            GLOG.ERROR(f"从图编辑器更新配置失败: {e}")
            return ServiceResult.error(f"从图编辑器更新配置失败: {str(e)}")

    # ==================== 方向 2: Mapping → 图结构 + Param ====================

    @time_logger
    @retry
    def add_file(
        self,
        portfolio_uuid: str,
        file_id: str,
        file_type: FILE_TYPES,
        name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> ServiceResult:
        """
        添加文件到投资组合

        流程：
        1. 创建 MySQL Mapping
        2. 同步默认参数到 MySQL MParam
        3. 自动在 MongoDB 图中生成对应节点

        Args:
            portfolio_uuid: 投资组合 UUID
            file_id: 文件 UUID
            file_type: 文件类型
            name: 映射名称（可选）
            params: 默认参数（可选）

        Returns:
            ServiceResult
        """
        try:
            # 1. 创建 MySQL Mapping
            mapping = MPortfolioFileMapping(
                portfolio_id=portfolio_uuid,
                file_id=file_id,
                name=name or f"auto_binding_{file_type.name}",
                type=file_type,
                source=SOURCE_TYPES.SIM
            )
            mapping_uuid = self._mapping_crud.add(mapping)

            # 2. 同步参数到 MParam（使用 mapping_uuid）
            if params:
                self._sync_params_for_mapping(
                    mapping_uuid=mapping_uuid,
                    params=params
                )

            GLOG.INFO(f"添加文件映射: {portfolio_uuid} -> {file_id}")

            # 3. 同步到 MongoDB 图结构
            self._sync_graph_from_mappings(portfolio_uuid)

            return ServiceResult.success(data={"file_id": file_id})

        except Exception as e:
            GLOG.ERROR(f"添加文件失败: {e}")
            return ServiceResult.error(f"添加文件失败: {str(e)}")

    @time_logger
    @retry
    def remove_file(
        self,
        portfolio_uuid: str,
        file_id: str,
    ) -> ServiceResult:
        """
        从投资组合移除文件

        流程：
        1. 删除 MySQL Mapping
        2. 删除对应的 MParam
        3. 从 MongoDB 图中移除对应节点

        Args:
            portfolio_uuid: 投资组合 UUID
            file_id: 文件 UUID

        Returns:
            ServiceResult
        """
        try:
            # 1. 获取要删除的 mapping
            mappings = self._mapping_crud.find(
                filters={"portfolio_id": portfolio_uuid, "file_id": file_id}
            )

            # 2. 删除对应的参数
            for mapping in mappings:
                self._param_crud.remove(filters={"mapping_id": mapping.uuid})

            # 3. 删除 MySQL Mapping
            self._mapping_crud.delete_mapping(portfolio_uuid, file_id)

            GLOG.INFO(f"移除文件映射: {portfolio_uuid} -> {file_id}")

            # 4. 同步更新 MongoDB 图结构
            self._sync_graph_from_mappings(portfolio_uuid)

            return ServiceResult.success(data={"file_id": file_id})

        except Exception as e:
            GLOG.ERROR(f"移除文件失败: {e}")
            return ServiceResult.error(f"移除文件失败: {str(e)}")

    # ==================== 查询方法 ====================

    @time_logger
    def get_portfolio_graph(
        self,
        portfolio_uuid: str,
    ) -> ServiceResult:
        """
        获取投资组合的图数据

        优先返回 MongoDB 中的图数据，
        如果不存在则从 MySQL Mapping 自动生成

        Args:
            portfolio_uuid: 投资组合 UUID

        Returns:
            ServiceResult: 包含 graph_data
        """
        try:
            collection = self._mongo_driver.get_collection("portfolio_graph_data")

            # 查找现有图数据（优先 GRAPH_EDITOR 来源的）
            graph_doc = collection.find_one(
                {"portfolio_uuid": portfolio_uuid},
                sort=[("metadata.source", 1), ("created_at", -1)]
            )

            if graph_doc:
                return ServiceResult.success(data={
                    "graph_data": graph_doc["graph_data"],
                    "metadata": graph_doc.get("metadata", {}),
                    "source": "MONGODB",
                    "mongo_id": graph_doc["_id"],
                })

            # 不存在，从 Mapping 自动生成
            GLOG.INFO(f"图数据不存在，从 Mapping 自动生成: {portfolio_uuid}")
            self._sync_graph_from_mappings(portfolio_uuid)

            # 再次查询
            graph_doc = collection.find_one({"portfolio_uuid": portfolio_uuid})
            return ServiceResult.success(data={
                "graph_data": graph_doc["graph_data"] if graph_doc else {"nodes": [], "edges": []},
                "metadata": graph_doc.get("metadata", {}) if graph_doc else {},
                "source": "AUTO_GENERATED",
            })

        except Exception as e:
            GLOG.ERROR(f"获取图数据失败: {e}")
            return ServiceResult.error(f"获取图数据失败: {str(e)}")

    @time_logger
    def get_portfolio_mappings(
        self,
        portfolio_uuid: str,
        include_params: bool = False,
    ) -> ServiceResult:
        """
        获取投资组合的文件映射

        Args:
            portfolio_uuid: 投资组合 UUID
            include_params: 是否包含参数

        Returns:
            ServiceResult: 包含映射列表
        """
        try:
            mappings = self._mapping_crud.find_by_portfolio(portfolio_uuid)

            result = []
            for m in mappings:
                mapping_data = {
                    "uuid": m.uuid,
                    "portfolio_id": m.portfolio_id,
                    "file_id": m.file_id,
                    "name": m.name,
                    "type": m.type,
                    "source": m.source,
                }

                # 如果需要包含参数
                if include_params:
                    params = self._param_crud.find_by_mapping_id(m.uuid)
                    # 将参数列表转换为字典
                    params_dict = {}
                    for p in params:
                        # 尝试解析 JSON 值
                        try:
                            value = json.loads(p.value) if p.value else {}
                        except:
                            value = p.value
                        params_dict[f"param_{p.index}"] = value

                    mapping_data["params"] = params_dict

                result.append(mapping_data)

            return ServiceResult.success(data=result)

        except Exception as e:
            GLOG.ERROR(f"获取映射失败: {e}")
            return ServiceResult.error(f"获取映射失败: {str(e)}")

    @time_logger
    def get_mapping_params(
        self,
        mapping_uuid: str,
    ) -> ServiceResult:
        """
        获取映射的参数

        Args:
            mapping_uuid: Mapping UUID

        Returns:
            ServiceResult: 包含参数字典
        """
        try:
            params = self._param_crud.find_by_mapping_id(mapping_uuid)

            # 转换为字典
            params_dict = {}
            for p in params:
                try:
                    value = json.loads(p.value) if p.value else {}
                except:
                    value = p.value
                params_dict[f"param_{p.index}"] = value

            return ServiceResult.success(data=params_dict)

        except Exception as e:
            GLOG.ERROR(f"获取参数失败: {e}")
            return ServiceResult.error(f"获取参数失败: {str(e)}")

    # ==================== 私有辅助方法 ====================

    def _extract_files_from_graph(
        self,
        graph_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        从图数据中提取文件映射

        Args:
            graph_data: 图数据

        Returns:
            文件映射列表
        """
        files = []
        for node in graph_data.get("nodes", []):
            file_id = node.get("data", {}).get("file_id")
            if file_id:
                node_type = self._parse_node_type(node.get("type", ""))
                label = node.get("data", {}).get("label", f"auto_{node_type.name}")
                files.append({
                    "file_id": file_id,
                    "type": node_type,
                    "name": label
                })
        return files

    def _extract_params_from_graph(
        self,
        graph_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        从图数据中提取节点参数

        Args:
            graph_data: 图数据

        Returns:
            节点参数列表 [{"file_id": "...", "params": {...}}, ...]
        """
        node_params = []
        for node in graph_data.get("nodes", []):
            file_id = node.get("data", {}).get("file_id")
            params = node.get("data", {}).get("params")

            if file_id and params:
                node_params.append({
                    "file_id": file_id,
                    "params": params
                })

        return node_params

    def _save_graph_to_mongo(
        self,
        portfolio_uuid: str,
        graph_data: Dict[str, Any],
        name: str,
        source: str = "GRAPH_EDITOR",
    ) -> str:
        """
        保存图数据到 MongoDB

        Args:
            portfolio_uuid: 投资组合 UUID
            graph_data: 图数据
            name: 配置名称
            source: 数据来源

        Returns:
            MongoDB 文档 ID
        """
        collection = self._mongo_driver.get_collection("portfolio_graph_data")

        doc_id = uuid.uuid4().hex

        document = {
            "_id": doc_id,
            "portfolio_uuid": portfolio_uuid,
            "name": name,
            "graph_data": graph_data,
            "metadata": {
                "source": source,
                "auto_generated": False,
                "synced_at": GLOG.now()
            },
            "created_at": GLOG.now(),
            "updated_at": GLOG.now()
        }

        collection.insert_one(document)
        return doc_id

    def _update_graph_in_mongo(
        self,
        portfolio_uuid: str,
        graph_data: Dict[str, Any],
        name: Optional[str] = None,
        source: str = "GRAPH_EDITOR",
    ) -> str:
        """
        更新 MongoDB 中的图数据

        Args:
            portfolio_uuid: 投资组合 UUID
            graph_data: 新的图数据
            name: 新的配置名称（可选）
            source: 数据来源

        Returns:
            MongoDB 文档 ID
        """
        collection = self._mongo_driver.get_collection("portfolio_graph_data")

        # 查找现有文档
        existing = collection.find_one({
            "portfolio_uuid": portfolio_uuid,
            "metadata.source": source
        })

        if existing:
            # 更新现有文档
            update_data = {
                "graph_data": graph_data,
                "updated_at": GLOG.now(),
                "metadata.synced_at": GLOG.now()
            }
            if name:
                update_data["name"] = name

            collection.update_one(
                {"_id": existing["_id"]},
                {"$set": update_data}
            )
            return existing["_id"]
        else:
            # 创建新文档
            return self._save_graph_to_mongo(
                portfolio_uuid=portfolio_uuid,
                graph_data=graph_data,
                name=name or f"Graph for {portfolio_uuid[:8]}",
                source=source
            )

    def _sync_mappings_from_files(
        self,
        portfolio_uuid: str,
        file_mappings: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        """
        从文件列表同步到 MySQL Mapping

        Args:
            portfolio_uuid: 投资组合 UUID
            file_mappings: 文件映射列表

        Returns:
            mapping_uuids: {file_id: mapping_uuid} 字典
        """
        # 获取现有映射
        existing = self._mapping_crud.find_by_portfolio(portfolio_uuid)
        existing_files = {m.file_id: m for m in existing}

        # 当前文件集合
        current_files = {fm["file_id"]: fm for fm in file_mappings}

        # 返回的 mapping_uuid 映射
        mapping_uuids = {}

        # 1. 添加新映射
        for file_id, fm in current_files.items():
            if file_id not in existing_files:
                mapping = MPortfolioFileMapping(
                    portfolio_id=portfolio_uuid,
                    file_id=fm["file_id"],
                    name=fm["name"],
                    type=fm["type"],
                    source=SOURCE_TYPES.SIM
                )
                mapping_uuid = self._mapping_crud.add(mapping)
                mapping_uuids[file_id] = mapping_uuid
            else:
                # 已存在，使用现有的 UUID
                mapping_uuids[file_id] = existing_files[file_id].uuid

        # 2. 删除不再使用的映射
        for file_id, existing_mapping in existing_files.items():
            if file_id not in current_files:
                self._mapping_crud.delete_mapping(portfolio_uuid, file_id)
                # 同时删除参数
                self._param_crud.remove(filters={"mapping_id": existing_mapping.uuid})

        return mapping_uuids

    def _sync_params_from_nodes(
        self,
        portfolio_uuid: str,
        node_params: List[Dict[str, Any]],
    ) -> None:
        """
        从节点参数同步到 MySQL MParam

        Args:
            portfolio_uuid: 投资组合 UUID
            node_params: 节点参数列表 [{"file_id": "...", "params": {...}}, ...]
        """
        # 获取该 portfolio 的所有 mappings
        mappings = self._mapping_crud.find_by_portfolio(portfolio_uuid)
        file_to_mapping = {m.file_id: m.uuid for m in mappings}

        for node_param in node_params:
            file_id = node_param["file_id"]
            params = node_param["params"]

            # 查找对应的 mapping_uuid
            mapping_uuid = file_to_mapping.get(file_id)
            if not mapping_uuid:
                GLOG.WARNING(f"未找到文件 {file_id} 的映射，跳过参数同步")
                continue

            # 同步参数
            self._sync_params_for_mapping(
                mapping_uuid=mapping_uuid,
                params=params
            )

    def _sync_params_for_mapping(
        self,
        mapping_uuid: str,
        params: Dict[str, Any],
    ) -> None:
        """
        同步参数到指定的 mapping

        Args:
            mapping_uuid: Mapping UUID
            params: 参数字典
        """
        # 将参数字典转换为扁平列表
        param_list = []
        for key, value in params.items():
            # 尝试将值序列化为 JSON
            try:
                value_str = json.dumps(value, ensure_ascii=False)
            except:
                value_str = str(value)

            param_list.append({
                "key": key,
                "value": value_str
            })

        # 获取现有参数
        existing_params = self._param_crud.find_by_mapping_id(mapping_uuid)

        # 删除旧参数
        for p in existing_params:
            self._param_crud.remove(filters={"uuid": p.uuid})

        # 添加新参数
        for idx, param in enumerate(param_list):
            m_param = MParam(
                mapping_id=mapping_uuid,
                index=idx,
                value=param["value"],
                source=SOURCE_TYPES.SIM
            )
            self._param_crud.add(m_param)

    def _sync_graph_from_mappings(self, portfolio_uuid: str) -> None:
        """
        从 MySQL Mapping 同步生成图结构

        读取 MySQL 中该投资组合的所有映射，
        在 MongoDB 中生成自动布局的图结构

        Args:
            portfolio_uuid: 投资组合 UUID
        """
        # 1. 获取所有映射
        mappings = self._mapping_crud.find_by_portfolio(portfolio_uuid)

        if not mappings:
            # 没有映射，清空图数据
            self._update_graph_in_mongo(
                portfolio_uuid=portfolio_uuid,
                graph_data={"nodes": [], "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1}},
                name=f"Empty graph for {portfolio_uuid[:8]}",
                source="AUTO_GENERATED"
            )
            return

        # 2. 生成图节点
        nodes = []
        y_offset = 0
        x_positions = {
            FILE_TYPES.STRATEGY: 100,
            FILE_TYPES.SELECTOR: 100,
            FILE_TYPES.SIZER: 400,
            FILE_TYPES.RISKMANAGEMENT: 700,
            FILE_TYPES.ANALYZER: 1000,
        }

        type_groups = {}
        for mapping in mappings:
            if mapping.type not in type_groups:
                type_groups[mapping.type] = []
            type_groups[mapping.type].append(mapping)

        for file_type, type_mappings in type_groups.items():
            x_pos = x_positions.get(file_type, 100)
            for mapping in type_mappings:
                # 获取文件信息
                file_obj = self._file_crud.get(mapping.file_id)
                if not file_obj:
                    continue

                # 获取节点参数
                params = self._get_params_for_mapping(mapping.uuid)

                node_id = f"auto_node_{mapping.file_id[:8]}"
                nodes.append({
                    "id": node_id,
                    "type": self._file_type_to_node_type(mapping.type),
                    "position": {"x": x_pos, "y": y_offset},
                    "data": {
                        "label": file_obj.name,
                        "file_id": mapping.file_id,
                        "mapping_uuid": mapping.uuid,
                        "params": params,
                        "auto_generated": True
                    }
                })
                y_offset += 150

        # 3. 生成简单边
        edges = self._generate_default_edges(nodes, mappings)

        # 4. 保存或更新到 MongoDB
        graph_data = {
            "nodes": nodes,
            "edges": edges,
            "viewport": {"x": 0, "y": 0, "zoom": 1}
        }

        self._update_graph_in_mongo(
            portfolio_uuid=portfolio_uuid,
            graph_data=graph_data,
            name=f"Auto generated for {portfolio_uuid[:8]}",
            source="AUTO_GENERATED"
        )

    def _get_params_for_mapping(self, mapping_uuid: str) -> Dict[str, Any]:
        """
        获取 mapping 的参数字典

        Args:
            mapping_uuid: Mapping UUID

        Returns:
            参数字典
        """
        params = self._param_crud.find_by_mapping_id(mapping_uuid)

        params_dict = {}
        for p in params:
            try:
                value = json.loads(p.value) if p.value else {}
            except:
                value = p.value
            params_dict[f"param_{p.index}"] = value

        return params_dict

    def _generate_default_edges(
        self,
        nodes: List[Dict],
        mappings: List[MPortfolioFileMapping],
    ) -> List[Dict]:
        """
        生成默认的边连接

        规则：
        - STRATEGY → RISK_MANAGEMENT
        - STRATEGY → SIZER → RISK_MANAGEMENT
        - 所有 → ANALYZER

        Args:
            nodes: 节点列表
            mappings: 映射列表

        Returns:
            边列表
        """
        edges = []

        # 按 type 分组节点
        strategy_nodes = [n for n in nodes if n["type"] == "STRATEGY"]
        risk_nodes = [n for n in nodes if n["type"] == "RISK_MANAGEMENT"]
        sizer_nodes = [n for n in nodes if n["type"] == "SIZER"]
        analyzer_nodes = [n for n in nodes if n["type"] == "ANALYZER"]

        # 生成连接
        edge_id = 0
        for strategy in strategy_nodes:
            # 连接风控
            for risk in risk_nodes:
                edges.append({
                    "id": f"auto_edge_{edge_id}",
                    "source": strategy["id"],
                    "target": risk["id"],
                    "type": "default",
                    "animated": False
                })
                edge_id += 1

            # 连接分析器
            for analyzer in analyzer_nodes:
                edges.append({
                    "id": f"auto_edge_{edge_id}",
                    "source": strategy["id"],
                    "target": analyzer["id"],
                    "sourceHandle": "analysis",
                    "targetHandle": "input"
                })
                edge_id += 1

        return edges

    @staticmethod
    def _parse_node_type(node_type_str: str) -> FILE_TYPES:
        """
        解析节点类型字符串为枚举

        Args:
            node_type_str: 节点类型字符串

        Returns:
            FILE_TYPES 枚举值
        """
        type_map = {
            "STRATEGY": FILE_TYPES.STRATEGY,
            "SELECTOR": FILE_TYPES.SELECTOR,
            "SIZER": FILE_TYPES.SIZER,
            "RISK_MANAGEMENT": FILE_TYPES.RISKMANAGEMENT,
            "RISK": FILE_TYPES.RISKMANAGEMENT,
            "ANALYZER": FILE_TYPES.ANALYZER,
        }
        return type_map.get(node_type_str.upper(), FILE_TYPES.OTHER)

    @staticmethod
    def _file_type_to_node_type(file_type: FILE_TYPES) -> str:
        """
        文件类型转节点类型

        Args:
            file_type: FILE_TYPES 枚举

        Returns:
            节点类型字符串
        """
        return {
            FILE_TYPES.STRATEGY: "STRATEGY",
            FILE_TYPES.SELECTOR: "SELECTOR",
            FILE_TYPES.SIZER: "SIZER",
            FILE_TYPES.RISKMANAGEMENT: "RISK_MANAGEMENT",
            FILE_TYPES.ANALYZER: "ANALYZER",
        }.get(file_type, "OTHER")

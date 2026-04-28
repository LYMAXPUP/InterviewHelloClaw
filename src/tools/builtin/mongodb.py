"""MongoDB 工具 - 支持增删查改操作"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from hello_agents.tools import Tool, ToolParameter, ToolResponse, tool_action
from ..database.mongodb_config import MongoConfig


class MongoDBTool(Tool):
    """MongoDB 数据库管理工具

    可展开为多个子工具：
    - mongo_insert: 插入文档（单条或多条）
    - mongo_find: 查询文档
    - mongo_update: 更新文档
    - mongo_delete: 删除文档
    - mongo_list_collections: 列出所有集合
    - mongo_create_collection: 创建集合
    - mongo_stats: 获取数据库统计信息
    """

    def __init__(self):
        """初始化 MongoDB 工具"""
        super().__init__(
            name="mongodb",
            description="MongoDB 数据库工具，支持文档的增删查改操作",
            expandable=True
        )

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        """默认执行：获取数据库状态"""
        return self._get_stats()

    def get_parameters(self) -> List[ToolParameter]:
        return []

    def _ensure_connected(self) -> ToolResponse:
        """确保 MongoDB 已连接"""
        if not MongoConfig.is_connected():
            if not MongoConfig.initialize():
                return ToolResponse.error(
                    code="MONGO_NOT_CONNECTED",
                    message="无法连接到 MongoDB，请检查配置和连接状态"
                )
        return None  # 表示连接正常

    def _serialize_doc(self, doc: dict) -> dict:
        """序列化 MongoDB 文档（处理 ObjectId 和 datetime）"""
        if doc is None:
            return None

        result = {}
        for key, value in doc.items():
            if hasattr(value, '__class__'):
                # 处理 ObjectId
                if value.__class__.__name__ == 'ObjectId':
                    result[key] = str(value)
                # 处理 datetime
                elif isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
            else:
                result[key] = value
        return result

    @tool_action("mongo_insert", "插入文档到集合")
    def _insert(
        self,
        collection: str,
        document: str,
        documents: str = None,
    ) -> str:
        """插入文档到指定集合

        Args:
            collection: 集合名称
            document: 单个文档（JSON 格式字符串）
            documents: 多个文档（JSON 数组格式字符串），如果提供则批量插入
        """
        # 检查连接
        conn_check = self._ensure_connected()
        if conn_check:
            return conn_check.text

        try:
            coll = MongoConfig.get_collection(collection)

            if documents:
                # 批量插入
                docs_list = json.loads(documents)
                if not isinstance(docs_list, list):
                    return "documents 参数必须是 JSON 数组格式"

                result = coll.insert_many(docs_list)
                return f"成功插入 {len(result.inserted_ids)} 条文档到集合 '{collection}'"

            elif document:
                # 单条插入
                doc = json.loads(document)
                result = coll.insert_one(doc)
                return f"成功插入 1 条文档到集合 '{collection}'，ID: {result.inserted_id}"

            else:
                return "请提供 document 或 documents 参数"

        except json.JSONDecodeError as e:
            return f"JSON 解析错误: {e}"
        except Exception as e:
            return f"插入失败: {e}"

    @tool_action("mongo_find", "查询集合中的文档")
    def _find(
        self,
        collection: str,
        filter: str = "{}",
        projection: str = None,
        limit: int = 10,
        skip: int = 0,
        sort: str = None,
    ) -> str:
        """查询集合中的文档

        Args:
            collection: 集合名称
            filter: 查询条件（JSON 格式），默认查询所有
            projection: 返回字段投影（JSON 格式），可选
            limit: 返回文档数量限制，默认 10
            skip: 跳过文档数量，默认 0
            sort: 排序条件（JSON 格式，如 {"field": 1}），可选
        """
        # 检查连接
        conn_check = self._ensure_connected()
        if conn_check:
            return conn_check.text

        try:
            coll = MongoConfig.get_collection(collection)

            # 解析查询条件
            query_filter = json.loads(filter) if filter else {}

            # 构建查询
            cursor = coll.find(query_filter)

            # 应用投影
            if projection:
                proj_dict = json.loads(projection)
                cursor = cursor.project(proj_dict)

            # 应用排序
            if sort:
                sort_dict = json.loads(sort)
                sort_list = [(k, v) for k, v in sort_dict.items()]
                cursor = cursor.sort(sort_list)

            # 应用跳过和限制
            if skip > 0:
                cursor = cursor.skip(skip)
            cursor = cursor.limit(limit)

            # 执行查询并序列化结果
            results = [self._serialize_doc(doc) for doc in cursor]

            if not results:
                return f"集合 '{collection}' 中未找到匹配的文档"

            # 格式化输出
            output = f"在集合 '{collection}' 中找到 {len(results)} 条文档:\n\n"
            for i, doc in enumerate(results, 1):
                output += f"**文档 {i}**:\n```json\n{json.dumps(doc, indent=2, ensure_ascii=False)}\n```\n\n"

            return output

        except json.JSONDecodeError as e:
            return f"JSON 解析错误: {e}"
        except Exception as e:
            return f"查询失败: {e}"

    @tool_action("mongo_find_one", "查询单条文档")
    def _find_one(
        self,
        collection: str,
        filter: str = "{}",
        projection: str = None,
    ) -> str:
        """查询单条文档

        Args:
            collection: 集合名称
            filter: 查询条件（JSON 格式）
            projection: 返回字段投影（JSON 格式），可选
        """
        # 检查连接
        conn_check = self._ensure_connected()
        if conn_check:
            return conn_check.text

        try:
            coll = MongoConfig.get_collection(collection)

            # 解析查询条件
            query_filter = json.loads(filter) if filter else {}

            # 构建查询
            if projection:
                proj_dict = json.loads(projection)
                doc = coll.find_one(query_filter, proj_dict)
            else:
                doc = coll.find_one(query_filter)

            if not doc:
                return f"集合 '{collection}' 中未找到匹配的文档"

            # 序列化并格式化输出
            result = self._serialize_doc(doc)
            return f"在集合 '{collection}' 中找到文档:\n```json\n{json.dumps(result, indent=2, ensure_ascii=False)}\n```"

        except json.JSONDecodeError as e:
            return f"JSON 解析错误: {e}"
        except Exception as e:
            return f"查询失败: {e}"

    @tool_action("mongo_update", "更新集合中的文档")
    def _update(
        self,
        collection: str,
        filter: str,
        update: str,
        multi: bool = False,
        upsert: bool = False,
    ) -> str:
        """更新集合中的文档

        Args:
            collection: 集合名称
            filter: 查询条件（JSON 格式）
            update: 更新操作（JSON 格式，需包含更新操作符如 $set）
            multi: 是否更新多条文档，默认 False
            upsert: 如果文档不存在是否插入，默认 False
        """
        # 检查连接
        conn_check = self._ensure_connected()
        if conn_check:
            return conn_check.text

        try:
            coll = MongoConfig.get_collection(collection)

            # 解析参数
            query_filter = json.loads(filter)
            update_doc = json.loads(update)

            # 执行更新
            if multi:
                result = coll.update_many(query_filter, update_doc, upsert=upsert)
                msg = f"成功更新集合 '{collection}' 中的 {result.modified_count} 条文档"
                if result.upserted_id:
                    msg += f"，并插入新文档 ID: {result.upserted_id}"
            else:
                result = coll.update_one(query_filter, update_doc, upsert=upsert)
                msg = f"成功更新集合 '{collection}' 中的 1 条文档"
                if result.upserted_id:
                    msg += f"（新插入文档 ID: {result.upserted_id})"

            return msg

        except json.JSONDecodeError as e:
            return f"JSON 解析错误: {e}"
        except Exception as e:
            return f"更新失败: {e}"

    @tool_action("mongo_delete", "删除集合中的文档")
    def _delete(
        self,
        collection: str,
        filter: str,
        multi: bool = False,
    ) -> str:
        """删除集合中的文档

        Args:
            collection: 集合名称
            filter: 删除条件（JSON 格式）
            multi: 是否删除多条文档，默认 False
        """
        # 检查连接
        conn_check = self._ensure_connected()
        if conn_check:
            return conn_check.text

        try:
            coll = MongoConfig.get_collection(collection)

            # 解析查询条件
            query_filter = json.loads(filter)

            # 执行删除
            if multi:
                result = coll.delete_many(query_filter)
                return f"成功删除集合 '{collection}' 中的 {result.deleted_count} 条文档"
            else:
                result = coll.delete_one(query_filter)
                return f"成功删除集合 '{collection}' 中的 1 条文档"

        except json.JSONDecodeError as e:
            return f"JSON 解析错误: {e}"
        except Exception as e:
            return f"删除失败: {e}"

    @tool_action("mongo_count", "统计集合中的文档数量")
    def _count(
        self,
        collection: str,
        filter: str = "{}",
    ) -> str:
        """统计集合中的文档数量

        Args:
            collection: 集合名称
            filter: 查询条件（JSON 格式），默认统计所有
        """
        # 检查连接
        conn_check = self._ensure_connected()
        if conn_check:
            return conn_check.text

        try:
            coll = MongoConfig.get_collection(collection)

            # 解析查询条件
            query_filter = json.loads(filter) if filter else {}

            # 统计数量
            count = coll.count_documents(query_filter)

            return f"集合 '{collection}' 中共有 {count} 条文档"

        except json.JSONDecodeError as e:
            return f"JSON 解析错误: {e}"
        except Exception as e:
            return f"统计失败: {e}"

    @tool_action("mongo_list_collections", "列出所有集合")
    def _list_collections(self) -> str:
        """列出数据库中的所有集合"""
        # 检查连接
        conn_check = self._ensure_connected()
        if conn_check:
            return conn_check.text

        try:
            collections = MongoConfig.list_collections()

            if not collections:
                return f"数据库 '{MongoConfig._db_name}' 中暂无集合"

            output = f"数据库 '{MongoConfig._db_name}' 中的集合:\n"
            for coll in collections:
                # 获取每个集合的文档数量
                count = MongoConfig.get_collection(coll).count_documents({})
                output += f"- **{coll}** ({count} 条文档)\n"

            return output

        except Exception as e:
            return f"获取集合列表失败: {e}"

    @tool_action("mongo_create_collection", "创建新集合")
    def _create_collection(self, name: str) -> str:
        """创建新集合

        Args:
            name: 集合名称
        """
        # 检查连接
        conn_check = self._ensure_connected()
        if conn_check:
            return conn_check.text

        try:
            db = MongoConfig.get_db()

            # 检查集合是否已存在
            if name in db.list_collection_names():
                return f"集合 '{name}' 已存在"

            # 创建集合（通过插入一条空文档并删除）
            coll = db.create_collection(name)
            return f"成功创建集合 '{name}'"

        except Exception as e:
            return f"创建集合失败: {e}"

    @tool_action("mongo_drop_collection", "删除集合")
    def _drop_collection(self, name: str) -> str:
        """删除集合

        Args:
            name: 集合名称
        """
        # 检查连接
        conn_check = self._ensure_connected()
        if conn_check:
            return conn_check.text

        try:
            db = MongoConfig.get_db()

            # 检查集合是否存在
            if name not in db.list_collection_names():
                return f"集合 '{name}' 不存在"

            # 删除集合
            db.drop_collection(name)
            return f"成功删除集合 '{name}'"

        except Exception as e:
            return f"删除集合失败: {e}"

    @tool_action("mongo_stats", "获取数据库统计信息")
    def _get_stats(self) -> str:
        """获取数据库统计信息"""
        try:
            stats = MongoConfig.get_stats()

            if not stats.get("connected"):
                return "MongoDB 未连接"

            output = "# MongoDB 状态\n\n"
            output += f"- **连接状态**: 已连接\n"
            output += f"- **主机**: {stats.get('host')}\n"
            output += f"- **端口**: {stats.get('port')}\n"
            output += f"- **数据库**: {stats.get('database')}\n"
            output += f"- **版本**: {stats.get('version', 'unknown')}\n"

            if stats.get("uptime"):
                uptime = stats.get("uptime")
                hours = uptime // 3600
                minutes = (uptime % 3600) // 60
                output += f"- **运行时间**: {hours}小时 {minutes}分钟\n"

            collections = stats.get("collections", [])
            if collections:
                output += f"- **集合数量**: {len(collections)}\n"
                output += "\n## 集合列表\n"
                for coll in collections:
                    output += f"  - {coll}\n"

            return output

        except Exception as e:
            return f"获取统计信息失败: {e}"

    @tool_action("mongo_aggregate", "聚合查询")
    def _aggregate(
        self,
        collection: str,
        pipeline: str,
    ) -> str:
        """执行聚合查询

        Args:
            collection: 集合名称
            pipeline: 聚合管道（JSON 数组格式）
        """
        # 检查连接
        conn_check = self._ensure_connected()
        if conn_check:
            return conn_check.text

        try:
            coll = MongoConfig.get_collection(collection)

            # 解析聚合管道
            pipeline_list = json.loads(pipeline)
            if not isinstance(pipeline_list, list):
                return "pipeline 参数必须是 JSON 数组格式"

            # 执行聚合
            results = [self._serialize_doc(doc) for doc in coll.aggregate(pipeline_list)]

            if not results:
                return f"聚合查询未返回结果"

            # 格式化输出
            output = f"聚合查询结果 ({len(results)} 条):\n\n"
            for i, doc in enumerate(results, 1):
                output += f"**结果 {i}**:\n```json\n{json.dumps(doc, indent=2, ensure_ascii=False)}\n```\n\n"

            return output

        except json.JSONDecodeError as e:
            return f"JSON 解析错误: {e}"
        except Exception as e:
            return f"聚合查询失败: {e}"
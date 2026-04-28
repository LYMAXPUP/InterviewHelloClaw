# -*- coding: utf-8 -*-
"""
MongoDB 配置模块 - 单例模式管理 MongoDB 连接
"""

import os
import subprocess
import signal
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError


class MongoConfig:
    # 默认配置
    _host = os.getenv("MONGO_HOST", "localhost")
    _port = int(os.getenv("MONGO_PORT", 27017))
    _db_name = os.getenv("MONGO_DB_NAME", "mydatabase")
    _username = os.getenv("MONGO_USERNAME")
    _password = os.getenv("MONGO_PASSWORD")
    _auth_source = os.getenv("MONGO_AUTH_SOURCE", "admin")

    # 连接参数
    _max_pool_size = 100
    _connect_timeout = 5000  # 毫秒
    _socket_timeout = 3000  # 毫秒

    # 单例模式
    _client = None
    _db = None

    @classmethod
    def _build_connection_uri(cls):
        """构建 MongoDB 连接 URI"""
        if cls._username and cls._password:
            return f"mongodb://{cls._username}:{cls._password}@{cls._host}:{cls._port}/?authSource={cls._auth_source}"
        return f"mongodb://{cls._host}:{cls._port}"

    @classmethod
    def initialize(cls) -> bool:
        """初始化 MongoDB 连接

        Returns:
            bool: 是否成功连接
        """
        if cls._client is None:
            try:
                cls._client = MongoClient(
                    cls._build_connection_uri(),
                    maxPoolSize=cls._max_pool_size,
                    connectTimeoutMS=cls._connect_timeout,
                    socketTimeoutMS=cls._socket_timeout,
                    serverSelectionTimeoutMS=5000
                )

                # 验证连接
                cls._client.admin.command('ping')
                cls._db = cls._client[cls._db_name]
                print(f"Successfully connected to MongoDB (database: {cls._db_name})")
                return True

            except ConfigurationError as e:
                print(f"MongoDB configuration error: {str(e)}")
                return False
            except ConnectionFailure as e:
                print(f"Failed to connect to MongoDB: {str(e)}")
                return False
            except Exception as e:
                print(f"Unexpected MongoDB connection error: {str(e)}")
                return False

        return True

    @classmethod
    def get_db(cls):
        """获取数据库实例"""
        if cls._client is None:
            cls.initialize()
        return cls._db

    @classmethod
    def get_collection(cls, collection_name):
        """获取集合实例"""
        return cls.get_db()[collection_name]

    @classmethod
    def get_client(cls):
        """获取 MongoClient 实例"""
        if cls._client is None:
            cls.initialize()
        return cls._client

    @classmethod
    def close(cls):
        """关闭所有连接"""
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._db = None
            print("MongoDB connection closed")

    @classmethod
    def is_connected(cls) -> bool:
        """检查是否已连接"""
        if cls._client is None:
            return False
        try:
            cls._client.admin.command('ping')
            return True
        except Exception:
            return False

    @classmethod
    def list_collections(cls) -> list:
        """列出所有集合"""
        if cls._db is None:
            return []
        return cls._db.list_collection_names()

    @classmethod
    def get_stats(cls) -> dict:
        """获取 MongoDB 统计信息"""
        if cls._client is None:
            return {"connected": False}

        try:
            stats = {
                "connected": True,
                "host": cls._host,
                "port": cls._port,
                "database": cls._db_name,
                "collections": cls.list_collections(),
            }

            # 获取服务器状态
            server_info = cls._client.admin.command('serverStatus')
            stats["version"] = server_info.get("version", "unknown")
            stats["uptime"] = server_info.get("uptime", 0)

            return stats
        except Exception as e:
            return {"connected": False, "error": str(e)}


MongoConfig.initialize()

if __name__ == "__main__":
    client = MongoConfig()
    stat = client.get_stats()
    print(stat)
    # collection = MongoConfig.get_collection("my_collection")
    # dic = {'name':'serena',"id":1532}
    # collection.insert_one(dic)
    # list_of_records = [{'name': 'amy', 'id': 1798},{'name': 'bob', 'id': 1631}]
    # collection.insert_many(list_of_records)
    # for record in collection.find():
    #     print(record)
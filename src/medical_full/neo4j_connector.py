#!/usr/bin/env python3
# coding: utf-8
import os
from py2neo import Graph
from config import current_config

class Neo4jConnector:
    def __init__(self, host=None, port=None, user=None, password=None):
        self.host = host or current_config.NEO4J_HOST
        self.port = port or current_config.NEO4J_PORT
        self.user = user or current_config.NEO4J_USER
        self.password = password or current_config.NEO4J_PASSWORD
        self.graph = None
        self._initialized = False
        self.connect()

    def connect(self):
        """
        尝试通过 Bolt 和 HTTP 协议连接 Neo4j
        """
        # 优先尝试 Bolt
        bolt_uri = f"bolt://{self.host}:7687"
        try:
            self.graph = Graph(bolt_uri, auth=(self.user, self.password))
            self.graph.run("RETURN 1").evaluate()
            self._initialized = True
            return True, f"✅ 已通过 Bolt 连接到 Neo4j ({bolt_uri})"
        except Exception as e_bolt:
            # 失败则尝试 HTTP
            http_uri = f"http://{self.host}:{self.port}"
            try:
                self.graph = Graph(http_uri, auth=(self.user, self.password))
                self.graph.run("RETURN 1").evaluate()
                self._initialized = True
                return True, f"✅ 已通过 HTTP 连接到 Neo4j ({http_uri})"
            except Exception as e_http:
                self._initialized = False
                return False, f"❌ Neo4j 连接失败: Bolt({e_bolt}), HTTP({e_http})"

    def test_connection(self):
        success, message = self.connect()
        return {"success": success, "message": message}

    def run(self, cypher, **parameters):
        if not self._initialized:
            success, msg = self.connect()
            if not success:
                raise ConnectionError(msg)
        return self.graph.run(cypher, **parameters)

    def data(self, cypher, **parameters):
        return self.run(cypher, **parameters).data()

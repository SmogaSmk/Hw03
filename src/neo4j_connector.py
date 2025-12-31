from py2neo import Graph
import os


class Neo4jConnector:
    """Neo4j连接管理器 - 复用现有配置"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Neo4jConnector, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        host = os.getenv('NEO4J_HOST', '127.0.0.1')
        bolt_port = int(os.getenv('NEO4J_BOLT_PORT', '7687'))
        user = os.getenv('NEO4J_USER', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', 'neo4j')

        try:
            uri = f"bolt://{host}:{bolt_port}"
            self.g = Graph(uri, auth=(user, password))
            self._initialized = True
            print(f"Neo4j连接成功: {uri}")
        except Exception as e:
            print(f"Neo4j连接失败: {e}")
            raise

    def execute_query(self, query, params=None):
        try:
            if params:
                result = self.g.run(query, params).data()
            else:
                result = self.g.run(query).data()
            return {'success': True, 'data': result}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_disease_by_name(self, disease_name):
        """
        根据疾病名称查询（复用现有模式）

        参数:
            disease_name: 疾病名称

        返回:
            {'success': bool, 'data': list}
        """
        query = """
        MATCH (d:Disease)
        WHERE d.name CONTAINS $name
        RETURN d.name as name, d.desc as desc, d.symptom as symptom,
               d.cause as cause, d.prevent as prevent,
               d.cure_department as cure_department, d.cure_way as cure_way,
               d.cured_prob as cured_prob
        LIMIT 10
        """
        return self.execute_query(query, {'name': disease_name})

    def get_diseases_by_symptom(self, symptom_name):
        """
        根据症状查询疾病（复用answer_search.py模式）

        参数:
            symptom_name: 症状名称

        返回:
            {'success': bool, 'data': list}
        """
        query = """
        MATCH (d:Disease)-[r:has_symptom]->(s:Symptom)
        WHERE s.name CONTAINS $symptom
        RETURN d.name as disease_name, s.name as symptom_name
        LIMIT 20
        """
        return self.execute_query(query, {'symptom': symptom_name})

    def test_connection(self):
        try:
            result = self.g.run("MATCH (n) RETURN count(n) as count LIMIT 1").data()
            if result:
                count = result[0]['count']
                return {
                    'success': True,
                    'message': f'Neo4j连接正常，共有 {count} 个节点'
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}


if __name__ == '__main__':
    connector = Neo4jConnector()
    result = connector.test_connection()
    print(result)

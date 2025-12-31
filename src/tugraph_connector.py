import json
import requests
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class TuGraphConnector:
    """TuGraph图数据库连接器"""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        user: str = None,
        password: str = None,
        graph_name: str = 'medical'
    ):
        """
        初始化TuGraph连接器

        参数:
            host: TuGraph服务器地址
            port: TuGraph服务器端口
            user: 用户名
            password: 密码
            graph_name: 图数据库名称
        """
        self.host = host or os.getenv('TUGRAPH_HOST', '127.0.0.1')
        self.port = port or int(os.getenv('TUGRAPH_PORT', '7070'))
        self.user = user or os.getenv('TUGRAPH_USER', 'admin')
        self.password = password or os.getenv('TUGRAPH_PASSWORD', 'lhy123')
        self.graph_name = graph_name

        self.base_url = f"http://{self.host}:{self.port}"
        self.token = None
        self._initialized = False

    def login(self) -> Dict[str, Any]:
        """
        登录TuGraph获取Token

        返回:
            {'success': bool, 'token': str, 'error': str}
        """
        try:
            url = f"{self.base_url}/login"
            payload = {
                'user': self.user,
                'password': self.password
            }

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if 'jwt' in result:
                    self.token = result['jwt']
                    self._initialized = True
                    return {
                        'success': True,
                        'token': self.token
                    }
                else:
                    return {
                        'success': False,
                        'error': '登录响应中没有token'
                    }
            else:
                return {
                    'success': False,
                    'error': f'登录失败: HTTP {response.status_code}'
                }

        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': f'无法连接到TuGraph服务器 {self.host}:{self.port}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'登录异常: {str(e)}'
            }

    def execute_cypher(self, cypher: str, params: dict = None) -> Dict[str, Any]:
        """
        执行Cypher查询

        参数:
            cypher: Cypher查询语句
            params: 查询参数

        返回:
            {'success': bool, 'data': list, 'error': str}
        """
        # 确保已登录
        if not self._initialized:
            login_result = self.login()
            if not login_result['success']:
                return login_result

        try:
            url = f"{self.base_url}/cypher"
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            payload = {
                'graph': self.graph_name,
                'script': cypher
            }
            if params:
                payload['parameters'] = params

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                result = response.json()
                # TuGraph返回格式可能不同，需要适配
                if 'result' in result:
                    return {
                        'success': True,
                        'data': result['result']
                    }
                else:
                    return {
                        'success': True,
                        'data': result
                    }
            elif response.status_code == 401:
                # Token过期，重新登录
                self._initialized = False
                login_result = self.login()
                if login_result['success']:
                    return self.execute_cypher(cypher, params)
                return login_result
            else:
                error_msg = response.text or f'HTTP {response.status_code}'
                return {
                    'success': False,
                    'error': f'查询失败: {error_msg}'
                }

        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': '查询超时'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'查询异常: {str(e)}'
            }

    def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        try:
            # 先尝试登录
            login_result = self.login()
            if not login_result['success']:
                return login_result

            # 执行简单查询测试
            test_result = self.execute_cypher("MATCH (n) RETURN count(n) as count LIMIT 1")
            if test_result['success']:
                return {
                    'success': True,
                    'message': f'TuGraph连接成功 ({self.host}:{self.port})',
                    'graph': self.graph_name
                }
            return test_result

        except Exception as e:
            return {
                'success': False,
                'error': f'连接测试失败: {str(e)}'
            }

    def get_schema(self) -> Dict[str, Any]:
        """获取图数据库Schema"""
        try:
            # TuGraph获取schema的API
            result = self.execute_cypher("CALL db.vertexLabels()")
            if result['success']:
                vertex_labels = result['data']

                edge_result = self.execute_cypher("CALL db.edgeLabels()")
                edge_labels = edge_result.get('data', []) if edge_result['success'] else []

                return {
                    'success': True,
                    'vertex_labels': vertex_labels,
                    'edge_labels': edge_labels
                }
            return result

        except Exception as e:
            return {
                'success': False,
                'error': f'获取Schema失败: {str(e)}'
            }


class TuGraphConnectorMock:
    """TuGraph模拟连接器 - 用于开发测试"""

    def __init__(self, *args, **kwargs):
        self._initialized = True
        print("使用TuGraph模拟连接器")

    def login(self) -> Dict[str, Any]:
        return {'success': True, 'token': 'mock_token'}

    def execute_cypher(self, cypher: str, params: dict = None) -> Dict[str, Any]:
        if 'Disease' in cypher:
            return {
                'success': True,
                'data': [
                    {'name': '感冒', 'desc': '普通感冒是一种常见的上呼吸道感染'},
                    {'name': '肺炎', 'desc': '肺炎是一种常见的下呼吸道感染'},
                    {'name': '糖尿病', 'desc': '糖尿病是一种慢性代谢性疾病'}
                ]
            }
        elif 'Symptom' in cypher:
            return {
                'success': True,
                'data': [
                    {'name': '发热'},
                    {'name': '咳嗽'},
                    {'name': '头痛'}
                ]
            }
        else:
            return {
                'success': True,
                'data': [{'count': 100}]
            }

    def test_connection(self) -> Dict[str, Any]:
        return {
            'success': True,
            'message': 'TuGraph模拟连接器运行正常',
            'graph': 'medical_mock'
        }

    def get_schema(self) -> Dict[str, Any]:
        return {
            'success': True,
            'vertex_labels': ['Disease', 'Symptom', 'Drug', 'Food', 'Check'],
            'edge_labels': ['has_symptom', 'common_drug', 'do_eat']
        }


if __name__ == '__main__':
    # 测试连接器
    connector = TuGraphConnector()
    result = connector.test_connection()
    print(json.dumps(result, ensure_ascii=False, indent=2))

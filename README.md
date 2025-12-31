# Hw03 调用RAG 来构建医疗对话系统
仍然是基于Tugraph和Neo4j的知识图谱任务
## 以Neo4j开始为例
先导入配置，规划好路径和文件
```python {config.py}
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """医疗知识图谱系统配置"""

    # Kimi AI 配置
    KIMI_API_KEY = os.getenv('KIMI_API_KEY', 'sk-U2KnkVDHpGGMKozQKmfpzlav2OQgiXBgIGRh3N6kWye75mKw')

    # Neo4j 配置
    NEO4J_HOST = os.getenv('NEO4J_HOST', '127.0.0.1')
    NEO4J_PORT = int(os.getenv('NEO4J_PORT', '7474'))
    NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'neo4j123')

    # TuGraph 配置
    TUGRAPH_HOST = os.getenv('TUGRAPH_HOST', '120.26.102.18')
    TUGRAPH_PORT = int(os.getenv('TUGRAPH_PORT', '7070'))
    TUGRAPH_USER = os.getenv('TUGRAPH_USER', 'admin')
    TUGRAPH_PASSWORD = os.getenv('TUGRAPH_PASSWORD', '!sMpAPDdS9p72DZZu')

# 导出当前配置实例供其他模块使用
current_config = Config()
```

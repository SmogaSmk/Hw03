
import os
from dotenv import load_dotenv

load_dotenv()


class Config:

    # Flask配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'True') == 'True'

    # Kimi配置
    KIMI_API_KEY = os.getenv('KIMI_API_KEY', '')

    # Neo4j配置
    NEO4J_HOST = os.getenv('NEO4J_HOST', '127.0.0.1')
    NEO4J_PORT = int(os.getenv('NEO4J_PORT', '7476'))
    NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'password')

    # TuGraph配置
    TUGRAPH_HOST = os.getenv('TUGRAPH_HOST', '127.0.0.1')
    TUGRAPH_PORT = int(os.getenv('TUGRAPH_PORT', '7076'))
    TUGRAPH_USER = os.getenv('TUGRAPH_USER', 'admin')
    TUGRAPH_PASSWORD = os.getenv('TUGRAPH_PASSWORD', '')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(env='default'):
    return config.get(env, DevelopmentConfig)

current_config = get_config()

import yaml
import json
import logging
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PolicyAgent")

def load_config(path="config.yaml"):
    if not os.path.exists(path):
        logger.error(f"配置文件 {path} 不存在")
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_sources(path="sources.json"):
    if not os.path.exists(path):
        logger.error(f"数据源文件 {path} 不存在")
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_keywords(config):
    return config.get('keywords', [])

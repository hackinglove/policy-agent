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
        config = yaml.safe_load(f)
    
    # 优先使用环境变量覆盖配置 (Secrets Support)
    if os.environ.get("OPENAI_API_KEY"):
        if 'summary' not in config: config['summary'] = {}
        config['summary']['api_key'] = os.environ.get("OPENAI_API_KEY")
        
    if os.environ.get("WEBHOOK_URL"):
        if 'notification' not in config: config['notification'] = {}
        if 'webhook' not in config['notification']: config['notification']['webhook'] = {}
        config['notification']['webhook']['url'] = os.environ.get("WEBHOOK_URL")

    if os.environ.get("PUSHPLUS_TOKEN"):
        if 'notification' not in config: config['notification'] = {}
        if 'pushplus' not in config['notification']: config['notification']['pushplus'] = {}
        config['notification']['pushplus']['token'] = os.environ.get("PUSHPLUS_TOKEN")

    return config

def load_sources(path="sources.json"):
    if not os.path.exists(path):
        logger.error(f"数据源文件 {path} 不存在")
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_keywords(config):
    return config.get('keywords', [])

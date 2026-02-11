import re
from datetime import datetime
import yaml
import json
import logging
import os
from dotenv import load_dotenv

# 加载 .env 文件 (如果存在)
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PolicyAgent")

def normalize_date(date_str):
    """
    将各种格式的日期字符串规整为 YYYY-MM-DD 格式
    """
    if not date_str:
        return ""
    
    date_str = date_str.strip()
    
    # 1. 尝试从字符串中提取像日期的部分
    # 匹配: 2023-01-01, 2023/1/1, 2023.1.1, 2023年1月1日
    match = re.search(r'20\d{2}[-./年]\d{1,2}[-./月]\d{1,2}(?:日)?', date_str)
    
    clean_date_str = date_str
    if match:
        clean_date_str = match.group()
        # 如果以'日'结尾，去掉它以便于strptime (除非fmt里加了日)
        if clean_date_str.endswith('日'):
             clean_date_str = clean_date_str[:-1]
             
    # 2. 尝试多种格式解析
    # 注意: 上面的正则处理后，分隔符可能是 - . / 年 月
    # 但我们为了简单，可以将分隔符统一替换为 -
    
    # 替换常见分隔符为 -
    normalized_temp = re.sub(r'[./年月]', '-', clean_date_str)
    
    # 手动处理可能存在的个位数字，例如 2023-1-1 -> 2023-01-01
    parts = normalized_temp.split('-')
    if len(parts) == 3:
        try:
            year, month, day = parts
            # 简单验证年份
            if len(year) == 4 and year.isdigit() and month.isdigit() and day.isdigit():
                return f"{year}-{int(month):02d}-{int(day):02d}"
        except:
            pass
            
    # 3. 如果上面的替换失败，尝试原始格式匹配 (如 20230101)
    match_digits = re.search(r'20\d{6}', date_str)
    if match_digits:
        try:
            dt = datetime.strptime(match_digits.group(), '%Y%m%d')
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            pass

    return date_str # 如果失败，返回原始清洗后的字符串

def load_config(path="config.yaml"):
    if not os.path.exists(path):
        logger.error(f"配置文件 {path} 不存在")
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 优先使用环境变量覆盖配置 (支持 .env)
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

def save_sources(sources, path="sources.json"):
    """保存源配置"""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(sources, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存源文件失败: {e}")
        return False

def get_keywords(config):
    return config.get('keywords', [])

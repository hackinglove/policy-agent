import sqlite3
import os
from .utils import logger

class Storage:
    def __init__(self, db_path="policy_data.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        # 创建政策表
        c.execute('''
            CREATE TABLE IF NOT EXISTS policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                source_name TEXT,
                publish_date TEXT,
                url TEXT UNIQUE,
                summary TEXT,
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def is_processed(self, url):
        """检查URL是否已经爬取过"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id FROM policies WHERE url = ?", (url,))
        result = c.fetchone()
        conn.close()
        return result is not None

    def save_policy(self, policy_data):
        """保存政策数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                INSERT INTO policies (title, source_name, publish_date, url, summary)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                policy_data['title'],
                policy_data['source_name'],
                policy_data['publish_date'],
                policy_data['url'],
                policy_data.get('summary', '')
            ))
            conn.commit()
            conn.close()
            logger.info(f"已保存政策: {policy_data['title']}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"政策已存在 (URL冲突): {policy_data['title']}")
            return False
        except Exception as e:
            logger.error(f"保存数据库失败: {e}")
            return False

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import sqlite3
import json
import os
from typing import Optional
from datetime import datetime

# 引入现有的业务逻辑
from policy_agent.storage import Storage
# 假设 main.py 里有 job() 函数，或者我们需要稍微重构 main.py 以便调用
# 为了安全起见，我们直接调用命令行或重写简单的调用逻辑
import subprocess

app = FastAPI(title="Policy Agent Local Server")

# 1. 挂载静态文件 (前端)
# 确保 web 目录存在
os.makedirs("web", exist_ok=True)
# 挂载 API
class PolicyQuery(BaseModel):
    keyword: Optional[str] = None
    source: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    page: int = 1
    page_size: int = 20

def get_db_connection():
    conn = sqlite3.connect('policy_data.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/api/stats")
async def get_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    stats = {}
    # 总数
    cursor.execute("SELECT COUNT(*) FROM policies")
    stats['total_policies'] = cursor.fetchone()[0]
    
    # 今日新增
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT COUNT(*) FROM policies WHERE created_at LIKE ?", (f"{today}%",))
    stats['today_new'] = cursor.fetchone()[0]
    
    # 按来源分布
    cursor.execute("SELECT source_name, COUNT(*) as count FROM policies GROUP BY source_name")
    stats['sources'] = {row['source_name']: row['count'] for row in cursor.fetchall()}
    
    conn.close()
    return stats

@app.get("/api/policies")
async def list_policies(keyword: str = "", page: int = 1, page_size: int = 20):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM policies WHERE 1=1"
    params = []
    
    if keyword:
        query += " AND (title LIKE ? OR content LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])
        
    query += " ORDER BY publish_date DESC LIMIT ? OFFSET ?"
    params.extend([page_size, (page - 1) * page_size])
    
    cursor.execute(query, params)
    policies = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return policies

def run_crawler_task():
    """后台运行爬虫"""
    # 这里直接调用 main.py
    subprocess.run(["python", "main.py", "--now"], capture_output=True)

@app.post("/api/crawl")
async def trigger_crawl(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_crawler_task)
    return {"message": "爬虫任务已在后台启动"}

# 2. 也是最重要的，服务前端页面
@app.get("/")
async def read_index():
    return FileResponse('web/index.html')

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

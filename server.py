from fastapi import FastAPI, HTTPException, WebSocket, BackgroundTasks, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import sqlite3
import json
import os
import asyncio
import subprocess
from typing import Optional, List, Dict
from datetime import datetime
from dotenv import set_key
from policy_agent.utils import load_config, load_sources, save_sources
from policy_agent.source_detector import SourceDetector

app = FastAPI(title="Policy Agent Local Server")

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- WebSocket Manager for Logs ---
class LogManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

log_manager = LogManager()

# --- Models ---
class PolicyQuery(BaseModel):
    keyword: Optional[str] = None
    page: int = 1
    page_size: int = 20

class SourceItem(BaseModel):
    name: str
    url: str
    is_dynamic: bool = False
    selectors: Dict[str, str]

class SettingsItem(BaseModel):
    openai_api_key: Optional[str] = None
    webhook_url: Optional[str] = None
    pushplus_token: Optional[str] = None
    keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None
    crawler_headless: Optional[bool] = True
    crawler_timeout: Optional[int] = 30000
    schedule_time: Optional[str] = "09:00"

class AutoDetectRequest(BaseModel):
    url: str

# --- Database Helper ---
def get_db_connection():
    conn = sqlite3.connect('policy_data.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- API Endpoints ---

@app.get("/api/stats")
async def get_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    stats = {}
    cursor.execute("SELECT COUNT(*) FROM policies")
    stats['total_policies'] = cursor.fetchone()[0]
    
    today = datetime.now().strftime('%Y-%m-%d')
    # 使用 crawled_at 字段 instead of created_at
    cursor.execute("SELECT COUNT(*) FROM policies WHERE crawled_at LIKE ?", (f"{today}%",))
    stats['today_new'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT source_name, COUNT(*) as count FROM policies GROUP BY source_name")
    stats['sources'] = {row['source_name']: row['count'] for row in cursor.fetchall()}
    
    conn.close()
    return stats

@app.get("/api/policies")
async def list_policies(
    keyword: str = "", 
    source: str = "", 
    start_date: str = "", 
    end_date: str = "",
    page: int = 1, 
    page_size: int = 20
):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM policies WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM policies WHERE 1=1"
    params = []
    
    if keyword:
        # 使用 lower() 进行简单的大小写不敏感匹配
        keyword_wc = f"%{keyword}%"
        # Database has 'summary' column, not 'content'
        condition = " AND (title LIKE ? OR summary LIKE ?)"
        query += condition
        count_query += condition
        params.extend([keyword_wc, keyword_wc])

    if source:
        condition = " AND source_name = ?"
        query += condition
        count_query += condition
        params.append(source)
    
    if start_date:
        condition = " AND publish_date >= ?"
        query += condition
        count_query += condition
        params.append(start_date)
        
    if end_date:
        condition = " AND publish_date <= ?"
        query += condition
        count_query += condition
        params.append(end_date)
        
    # Get total count first
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    query += " ORDER BY publish_date DESC LIMIT ? OFFSET ?"
    params.extend([page_size, (page - 1) * page_size])
    
    cursor.execute(query, params)
    policies = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {
        "items": policies,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }

@app.delete("/api/policies")
async def clear_policies():
    """Empty the policy library"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM policies")
        # Optional: Reset sequence if using AUTOINCREMENT
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='policies'")
        conn.commit()
        conn.close()
        return {"message": "政策库已清空"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空失败: {str(e)}")

@app.delete("/api/policies/{policy_id}")
async def delete_single_policy(policy_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM policies WHERE id = ?", (policy_id,))
        if cursor.rowcount == 0:
             conn.close()
             raise HTTPException(status_code=404, detail="未找到该政策")
        conn.commit()
        conn.close()
        return {"message": "删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Manage Sources ---
@app.get("/api/sources")
async def get_sources():
    try:
        return load_sources()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sources")
async def add_source(source: SourceItem):
    sources = load_sources()
    # Check duplicate
    for s in sources:
        if s['url'] == source.url:
            raise HTTPException(status_code=400, detail="URL已存在")
    
    new_s = source.dict()
    sources.append(new_s)
    if save_sources(sources):
        return {"message": "添加成功", "source": new_s}
    raise HTTPException(status_code=500, detail="保存失败")

@app.put("/api/sources")
async def update_source(source: SourceItem):
    sources = load_sources()
    # Find existing
    found = False
    for i, s in enumerate(sources):
        if s['url'] == source.url:
            sources[i] = source.dict()
            found = True
            break
    
    if not found:
        raise HTTPException(status_code=404, detail="未找到该源 (URL不匹配)")
    
    if save_sources(sources):
        return {"message": "更新成功", "source": source.dict()}
    raise HTTPException(status_code=500, detail="保存失败")

@app.delete("/api/sources")
async def delete_source(url: str):
    sources = load_sources()
    new_sources = [s for s in sources if s['url'] != url]
    if len(new_sources) == len(sources):
        raise HTTPException(status_code=404, detail="未找到该源")
    
    if save_sources(new_sources):
        return {"message": "删除成功"}
    raise HTTPException(status_code=500, detail="保存失败")

@app.post("/api/sources/autodetect")
async def autodetect_source(req: AutoDetectRequest):
    """
    AI 自动分析源站
    """
    config = load_config() # Loading API Key from env/config
    detector = SourceDetector(config)
    
    try:
        # 需要较长时间超时
        result = await asyncio.get_event_loop().run_in_executor(
            None, detector.detect, req.url
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Manage Settings (Keys & Config) ---
@app.get("/api/settings")
async def get_settings():
    # Load YAML config
    config = load_config()
    
    # Return sensitive env vars (masked) + yaml config
    return {
        "openai_api_key": "***" if os.getenv("OPENAI_API_KEY") else "",
        "webhook_url": "***" if os.getenv("WEBHOOK_URL") else "",
        "pushplus_token": "***" if os.getenv("PUSHPLUS_TOKEN") else "",
        # YAML Configs
        "keywords": config.get('keywords', []),
        "exclude_keywords": config.get('exclude_keywords', []),
        "crawler_headless": config.get('crawler', {}).get('headless', True),
        "crawler_timeout": config.get('crawler', {}).get('timeout', 30000),
        "schedule_time": config.get('schedule', {}).get('time', "09:00"),
    }

@app.post("/api/settings")
async def save_settings(settings: SettingsItem):
    # 1. Update Env vars
    env_file = ".env"
    if not os.path.exists(env_file):
        open(env_file, 'a').close()
        
    if settings.openai_api_key and settings.openai_api_key != "***":
        set_key(env_file, "OPENAI_API_KEY", settings.openai_api_key)
    if settings.webhook_url and settings.webhook_url != "***":
        set_key(env_file, "WEBHOOK_URL", settings.webhook_url)
    if settings.pushplus_token and settings.pushplus_token != "***":
        set_key(env_file, "PUSHPLUS_TOKEN", settings.pushplus_token)
    
    # 2. Update YAML Config
    import yaml
    try:
        current_config = load_config()
        
        # Update values
        if settings.keywords is not None:
            current_config['keywords'] = settings.keywords
        
        if settings.exclude_keywords is not None:
             current_config['exclude_keywords'] = settings.exclude_keywords
             
        if 'crawler' not in current_config: current_config['crawler'] = {}
        if settings.crawler_headless is not None:
            current_config['crawler']['headless'] = settings.crawler_headless
        if settings.crawler_timeout is not None:
            current_config['crawler']['timeout'] = settings.crawler_timeout
            
        if 'schedule' not in current_config: current_config['schedule'] = {}
        if settings.schedule_time:
            current_config['schedule']['time'] = settings.schedule_time
            
        # Write back to config.yaml
        with open('config.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(current_config, f, allow_unicode=True, default_flow_style=False)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置文件失败: {str(e)}")
        
    return {"message": "配置已保存 (环境变量 & config.yaml)"}


# --- Crawler Execution with Log Streaming ---

async def run_crawler_process():
    """ Runs the crawler subprocess and streams output to WebSocket """
    await log_manager.broadcast(">>> 任务启动...\n")
    
    # 使用 python -u (unbuffered) 确保实时输出
    process = subprocess.Popen(
        ["python", "-u", "main.py", "--now"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    try:
        # 实时读取输出
        for line in iter(process.stdout.readline, ''):
            if line:
                await log_manager.broadcast(line)
                
        process.stdout.close()
        process.wait()
        
        if process.returncode == 0:
            await log_manager.broadcast("\n>>> 任务执行完成 ✅\n")
        else:
            await log_manager.broadcast(f"\n>>> 任务异常退出，代码: {process.returncode} ❌\n")
            
    except Exception as e:
        await log_manager.broadcast(f"\n>>> 执行出错: {str(e)}\n")

@app.post("/api/crawl")
async def trigger_crawl(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_crawler_process)
    return {"message": "任务已后台启动，请查看日志"}

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await log_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text() # keep alive
    except WebSocketDisconnect:
        log_manager.disconnect(websocket)

# Serve Frontend
@app.get("/")
async def read_index():
    return FileResponse('web/index.html')

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

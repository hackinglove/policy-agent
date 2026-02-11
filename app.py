import streamlit as st
import pandas as pd
import sqlite3
import yaml
import time
import subprocess
import os
import json
from policy_agent.utils import load_config, load_sources
from policy_agent.source_detector import SourceDetector
from policy_agent.rag_engine import RAGEngine
from policy_agent.crawler import PolicyCrawler
from policy_agent.storage import Storage

# Page Setup
st.set_page_config(page_title="Policy Agent Dashboard", layout="wide")
st.title("🏛️ 数字经济政策采集 Agent Dashboard")

# Load Config
config = load_config()

# Helper Functions
def save_config(new_config):
    with open('config.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(new_config, f, allow_unicode=True)

def save_sources(new_sources):
    with open('sources.json', 'w', encoding='utf-8') as f:
        json.dump(new_sources, f, ensure_ascii=False, indent=2)

def run_crawler_subprocess():
    """Run crawler in a separate process"""
    cmd = [os.sys.executable, "main.py", "--now"]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["⚙️ 设置与运行", "🔍 政策查询", "➕ 添加来源", "🤖 AI 助手"])

# --- Tab 1: Settings & Control ---
with tab1:
    st.header("运行控制")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("定时任务设置")
        current_time = config.get('schedule', {}).get('time', '09:00')
        new_time = st.text_input("每日运行时间 (HH:MM)", value=current_time)
        
        if st.button("保存设置"):
            if 'schedule' not in config: config['schedule'] = {}
            config['schedule']['time'] = new_time
            save_config(config)
            st.success(f"已更新运行时间为: {new_time}")

    with col2:
        st.subheader("手动执行")
        st.write("点击按钮立即执行一次全量抓取任务。任务将在后台运行。")
        if st.button("🚀 立即运行"):
            with st.spinner("正在启动任务..."):
                process = run_crawler_subprocess()
                st.success(f"任务已启动 (PID: {process.pid})")
                st.info("请查看终端日志获取详细进度。")

# --- Tab 2: Policy Query ---
with tab2:
    st.header("本地政策库查询")
    
    # Connect DB
    db_path = "policy_data.db"
    if not os.path.exists(db_path):
        st.warning("数据库尚未创建。请先运行一次抓取任务。")
    else:
        conn = sqlite3.connect(db_path)
        
        # Filters
        c1, c2, c3 = st.columns([2, 1, 1])
        search_text = c1.text_input("关键词搜索 (标题/摘要)")
        
        # Get Source Names
        sources_df = pd.read_sql("SELECT DISTINCT source_name FROM policies", conn)
        source_options = ["所有部门"] + sources_df['source_name'].tolist()
        selected_source = c2.selectbox("发布部门", source_options)
        
        # Query Construction
        query = "SELECT id, title, source_name, publish_date, url, summary FROM policies WHERE 1=1"
        params = []
        
        if search_text:
            query += " AND (title LIKE ? OR summary LIKE ?)"
            params.extend([f"%{search_text}%", f"%{search_text}%"])
            
        if selected_source != "所有部门":
            query += " AND source_name = ?"
            params.append(selected_source)
            
        query += " ORDER BY publish_date DESC LIMIT 100"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        st.write(f"找到 {len(df)} 条记录")
        st.dataframe(
            df, 
            column_config={
                "url": st.column_config.LinkColumn("链接"),
                "summary": st.column_config.TextColumn("摘要", width="large"),
            },
            hide_index=True,
            use_container_width=True
        )

# --- Tab 3: Add Source ---
with tab3:
    st.header("添加新政策源")
    
    st.info("输入目标网址，AI 将尝试自动识别抓取规则并添加至系统。")
    
    new_url = st.text_input("政策列表页 URL", placeholder="https://example.gov.cn/policy/list.html")
    new_name = st.text_input("部门名称", placeholder="例如：xx市发改委")
    
    if st.button("🤖 智能分析并添加"):
        if not new_url or not new_name:
            st.error("请填写完整信息")
        else:
            status_container = st.empty()
            status_container.info("正在分析页面结构，请稍候...")
            
            # 1. Analyze
            detector = SourceDetector(config)
            selectors, err = detector.analyze(new_url)
            
            if err:
                status_container.error(f"分析失败: {err}")
            else:
                status_container.success("页面分析成功！")
                st.json(selectors)
                
                # 2. Add to sources.json
                new_entry = {
                    "name": new_name,
                    "url": new_url,
                    "is_dynamic": True, # Assume dynamic for robustness or let user choose
                    "selectors": selectors
                }
                
                current_sources = load_sources()
                # Check duplicate
                if any(s['url'] == new_url for s in current_sources):
                    st.warning("该 URL 已存在于源列表中。")
                else:
                    current_sources.append(new_entry)
                    save_sources(current_sources)
                    st.success(f"已添加 '{new_name}' 到配置文件。")
                    
                    # 3. Run Crawl for this source
                    st.write("正在尝试抓取该源的历史数据...")
                    try:
                        # Use a temporary config/source list to run just this one?
                        # Or instantiate Crawler with filtered sources list
                        storage = Storage()
                        crawler = PolicyCrawler(config, [new_entry], storage) # Make sure crawler supports partial list
                        new_items = crawler.run() # This runs in main process, might block UI
                        st.success(f"抓取完成！共发现 {len(new_items)} 条政策。已存入数据库。")
                    except Exception as e:
                        st.error(f"抓取测试失败: {e}")

# --- Tab 4: AI Agent ---
with tab4:
    st.header("🤖 政策 AI 助手")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("询问政策相关问题..."):
        # Display user message
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("AI 正在思考..."):
                rag = RAGEngine(config)
                response = rag.chat(prompt)
                st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})

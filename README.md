# Policy Collect Agent (Local Edition)

一个美观、强大的本地政策采集与分析系统。

## 功能特性

*   **全自动采集**: 支持多个政府网站源，自动增量更新。
*   **AI 智能处理**:
    *   自动筛选：剔除无关的新闻、解读，只保留核心政策原文。
    *   自动摘要：提炼对企业的利好、核心指标和执行标准。
*   **现代化 UI**: 
    *   内置本地 Web 服务，提供类似 SaaS 平台的仪表盘体验。
    *   以 Vue 3 + Tailwind CSS 打造的精美界面。
    *   支持全文检索、仪表盘统计。

## 快速开始

1.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    pip install fastapi uvicorn
    playwright install chromium
    ```

2.  **配置环境**
    创建或修改 `config.yaml`，填入你的 OpenAI API Key。

3.  **启动系统**
    ```bash
    python server.py
    ```
    
    启动后访问浏览器: [http://localhost:8000](http://localhost:8000)

## 项目结构

*   `server.py`: 后端 API 服务 (FastAPI)
*   `web/index.html`: 前端单页应用 (无需编译)
*   `policy_agent/`: 核心爬虫与 AI 逻辑
*   `config.yaml`: 配置文件

#!/bin/bash
set -e

echo "--- 1. 安装依赖 ---"
pip install -r requirements.txt

echo "--- 2. 安装 Playwright 浏览器 ---"
playwright install chromium

echo "--- 3. 运行爬虫 (立即执行模式) ---"
# 注意：环境变量 OPENAI_API_KEY, WEBHOOK_URL 等需在 CI 平台配置
python main.py --now

echo "--- 4. 导出数据 ---"
python export_data.py

echo "--- 5. 准备部署 ---"
# 确保 docs 目录存在，CI 平台稍后会部署这个目录
ls -l docs/

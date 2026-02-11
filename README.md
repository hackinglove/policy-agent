# 数字经济政策自动采集 Agent

这是一个基于 Python + Playwright 的自动化爬虫工具，用于每日定时收集指定政府网站关于“数字经济”的最新政策，由于采用了 LLM (大模型) 生成摘要，您可以快速了解政策核心内容。

## 🚀 快速开始

### 1. 环境准备

需要 Python 3.9 或以上版本。

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 安装浏览器驱动 (Playwright 需要)
playwright install chromium
```

### 2. 配置

#### 修改 `config.yaml`
主要配置以下几项：
*   **keywords**: 你关注的关键词。
*   **summary**: 
    *   `enable_llm`: 是否开启 AI 摘要。如果为 `true`，需要填写 `api_key`。
    *   `api_key`: OpenAI 格式的 Key (DeepSeek、阿里通义等均兼容)。
*   **notification**:
    *   `pushplus`: 填入 token 可使用微信推送。
    *   `webhook`: 填入企业微信/钉钉机器人的 Webhook 地址。

#### 修改 `sources.json`
这是爬虫的核心配置。你需要定义从哪里爬取。
文件预置了几个示例，但政府网站经常改版，**CSS 选择器可能失效**。
*   `url`: 列表页地址。
*   `selectors`:
    *   `item`: 每一行政策所在的 CSS 选择器。
    *   `title`: 标题元素的 CSS 选择器（相对于 `item`）。
    *   `date`: 日期元素的 CSS 选择器（相对于 `item`）。

> 💡 **技巧**：可以使用 `tool_test_selector.py` 来测试你的选择器是否正确。

### 3. 运行

#### 方式一：立即执行一次 (测试用)
```bash
python main.py --now
```

#### 方式二：开启定时任务 (挂机用)
```bash
python main.py --loop
```
程序会保持运行，并在每天早上 09:00 (可在 config.yaml 修改) 自动执行。

## 🛠 开发与维护

*   **数据去重**: 使用 SQLite 数据库 `policy_data.db` 存储已抓取的 URL。如果想重新抓取，可以删除该文件。
*   **日志**: 运行日志直接输出到控制台，推荐使用 `nohup` 或 `Screen` 在服务器后台运行。

## ⚠️ 注意事项
1.  **反爬虫**: 虽然使用了 Playwright 模拟浏览器，但过于频繁的请求可能导致 IP 被封。默认配置比较保守，请勿随意调大并发。
2.  **准确性**: 爬虫依赖网页结构，如果目标网站改版，必须手动更新 `sources.json` 中的选择器。

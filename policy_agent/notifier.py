import requests
import time
from datetime import datetime
from .utils import logger

class Notifier:
    def __init__(self, config):
        self.config = config.get('notification', {})
        
    def _format_markdown(self, policies):
        """将政策列表格式化为 Markdown"""
        if not policies:
            return "今日无新增相关数字经济政策。"
            
        today = datetime.now().strftime('%Y-%m-%d')
        md = f"## 📅 【数字经济政策日报】 {today}\n\n"
        
        for idx, p in enumerate(policies, 1):
            md += f"### {idx}. {p['title']}\n"
            md += f"- **单位**: {p['source_name']}\n"
            md += f"- **日期**: {p['publish_date']}\n"
            md += f"- **概括**: {p.get('summary', '暂无')}\n"
            md += f"- **链接**: [点击查看详情]({p['url']})\n\n"
            md += "---\n\n"
            
        return md

    def _format_html(self, policies):
        """将政策列表格式化为 HTML (PushPlus使用)"""
        if not policies:
            return "今日无新增相关数字经济政策。"
            
        today = datetime.now().strftime('%Y-%m-%d')
        html = f"<h2>📅 【数字经济政策日报】 {today}</h2><br>"
        
        for idx, p in enumerate(policies, 1):
            html += f"<h3>{idx}. {p['title']}</h3>"
            html += f"<p><b>单位</b>: {p['source_name']}</p>"
            html += f"<p><b>日期</b>: {p['publish_date']}</p>"
            html += f"<p><b>概括</b>: {p.get('summary', '暂无')}</p>"
            html += f"<p><a href='{p['url']}'>🔗 点击查看详情</a></p>"
            html += "<hr>"
            
        return html

    def send(self, policies):
        # if not policies:
        #     logger.info("没有新政策，跳过推送")
        #     return

        # 1. PushPlus 推送
        pp_conf = self.config.get('pushplus', {})
        if pp_conf.get('enabled') and pp_conf.get('token'):
            try:
                # PushPlus 支持较长内容，但也建议分批，这里暂不分批
                content = self._format_html(policies)
                url = "http://www.pushplus.plus/send"
                data = {
                    "token": pp_conf['token'],
                    "title": f"数字经济政策日报-{len(policies)}条更新",
                    "content": content,
                    "template": "html"
                }
                resp = requests.post(url, json=data)
                logger.info(f"PushPlus 推送结果: {resp.text}")
            except Exception as e:
                logger.error(f"PushPlus 推送失败: {e}")

        # 2. Webhook 推送 (企业微信/钉钉/飞书)
        wh_conf = self.config.get('webhook', {})
        if wh_conf.get('enabled') and wh_conf.get('url'):
            batch_size = 3 # 进一步减小分批大小，确保不超过企业微信 4096 字节限制
            for i in range(0, len(policies), batch_size):
                batch_policies = policies[i:i+batch_size]
                try:
                    content = self._format_markdown(batch_policies)
                    webhook_url = wh_conf['url']
                    
                    # 简单判断 webhook 类型
                    payload = {}
                    if "feishu" in webhook_url:
                         # 飞书格式
                        payload = {
                            "msg_type": "interactive",
                            "card": {
                                "elements": [{"tag": "markdown", "content": content}],
                                "header": {"title": {"content": f"数字经济政策日报 ({i+1}-{i+len(batch_policies)})", "tag": "plain_text"}}
                            }
                        }
                    else:
                        # 企业微信 / 钉钉
                        payload = {
                            "msgtype": "markdown",
                            "markdown": {
                                "content": content,
                                "title": "数字经济政策日报"
                            }
                        }

                    resp = requests.post(webhook_url, json=payload)
                    logger.info(f"Webhook (批次 {i//batch_size + 1}) 推送结果: {resp.text}")
                    time.sleep(1) # 增加间隔防止触发频率限制
                except Exception as e:
                    logger.error(f"Webhook 推送失败: {e}")

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from openai import OpenAI
import json
import re
from .utils import logger

class SourceDetector:
    def __init__(self, config):
        self.config = config
        self.client = None
        self.api_key = config.get('summary', {}).get('api_key')
        if self.api_key and not self.api_key.startswith("${"):
             try:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=config.get('summary', {}).get('base_url', "https://api.openai.com/v1")
                )
             except Exception as e:
                logger.error(f"Detector LLM init failed: {e}")

    def detect(self, url):
        """
        自动分析网页并生成选择器配置
        """
        if not self.client:
            raise Exception("LLM Client not initialized. Please configure API KEY first.")

        logger.info(f"正在分析目标网站: {url}")
        
        html_sample = ""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                # 等待一会儿以防动态加载
                page.wait_for_timeout(2000)
                html_content = page.content()
                
                # 清洗 HTML，减少 Token 消耗
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 移除无关标签
                for tag in soup(['script', 'style', 'svg', 'iframe', 'footer', 'header', 'nav']):
                    tag.decompose()
                
                # 获取 body 内容，截取前 15000 字符 (足够覆盖列表区)
                body = soup.find('body')
                if body:
                    html_sample = str(body)[:15000]
                else:
                    html_sample = str(soup)[:15000]
                    
            except Exception as e:
                browser.close()
                raise Exception(f"Failed to load page: {e}")
            finally:
                browser.close()

        # 调用 LLM 分析
        prompt = (
            f"这是一个政府政策列表网页的 HTML 源码片段。我需要提取政策列表的 CSS 选择器。\n"
            f"目标是从列表中提取：1. 列表项容器(item) 2. 并在由于item内部提取：标题(title)、链接(link, href属性)、发布日期(date)。\n\n"
            f"HTML片段：\n```html\n{html_sample}\n```\n\n"
            f"【要求】：\n"
            f"1. 请返回一个标准的 JSON 对象，格式如下：\n"
            f'{{"selectors": {{"item": "css_selector", "title": "css_selector", "link": "css_selector", "date": "css_selector"}}}}\n'
            f"2. title/link/date 的选择器应该是相对于 item 的相对选择器。\n"
            f"3. 即使 HTML 复杂，也请尽量分析出最可能的结构。只返回 JSON，不要 Markdown 格式。"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.config.get('summary', {}).get('model', 'gpt-3.5-turbo'),
                messages=[
                    {"role": "system", "content": "你是一个熟练的爬虫工程师和 CSS 选择器专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content.strip()
            # 清理 JSON
            result_text = result_text.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(result_text)
            
            # 构造完整配置
            source_config = {
                "name": "New Source (Auto)",
                "url": url,
                "selectors": data.get("selectors", {}),
                "is_dynamic": False # 默认先设为 False，大部分政府网站不需要 dynamic
            }
            
            # 补全 name Title
            try:
                soup = BeautifulSoup(html_sample, 'html.parser')
                page_title = soup.title.string.strip() if soup.title else "Unknown Site"
                source_config['name'] = page_title[:20]
            except:
                pass
                
            return source_config

        except Exception as e:
            logger.error(f"AI Analysis Failed: {e}")
            raise Exception(f"AI Analysis Failed: {e}")

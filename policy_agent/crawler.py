from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import time
from urllib.parse import urljoin
from .utils import logger

class PolicyCrawler:
    def __init__(self, config, sources, storage):
        self.config = config
        self.sources = sources
        self.storage = storage
        self.keywords = config.get('keywords', [])
        
    def _is_yesterday(self, date_str):
        """
        判断日期字符串是否是昨天
        支持格式: YYYY-MM-DD, YYYY/MM/DD, YYYY年MM月DD日
        """
        if not date_str:
            return False
            
        # 清理日期字符串，去除多余空白
        date_str = date_str.strip()
        
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        # 尝试多种格式解析
        formats = [
            '%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d',
            '%Y年%m月%d日'
        ]
        
        parsed_date = None
        for fmt in formats:
            try:
                # 尝试提取日期部分 (简单正则辅助)
                # 比如 "[2023-10-27]" -> "2023-10-27"
                match = re.search(r'\d{4}[-年/.]\d{1,2}[-月/.]\d{1,2}(日)?', date_str)
                if match:
                    clean_date_str = match.group()
                    parsed_date = datetime.strptime(clean_date_str, fmt).date()
                    break
            except ValueError:
                continue
                
        if parsed_date:
            return parsed_date == yesterday
        return False

    def _match_keywords(self, text):
        """检查文本是否包含关键词"""
        if not text:
            return False
        for kw in self.keywords:
            if kw in text:
                return True
        return False

    def _extract_content(self, page):
        """提取页面正文纯文本"""
        try:
            # 简单的正文提取策略：提取 P 标签文本最多的区域，或者直接取 body 文本
            # 这里简化处理：获取 body 文本，用于 AI 摘要
            content = page.evaluate("() => document.body.innerText")
            return content
        except Exception as e:
            logger.error(f"提取正文失败: {e}")
            return ""

    def run(self):
        new_policies = []
        
        with sync_playwright() as p:
            # 启动浏览器
            browser = p.chromium.launch(
                headless=self.config['crawler'].get('headless', True)
            )
            context = browser.new_context()
            
            for source in self.sources:
                try:
                    logger.info(f"正在抓取: {source['name']} ({source['url']})")
                    page = context.new_page()
                    try:
                        page.goto(source['url'], timeout=self.config['crawler'].get('timeout', 30000))
                        
                        # 等待内容加载 (针对动态网页)
                        if source.get('is_dynamic', False):
                            page.wait_for_load_state("networkidle")
                            time.sleep(2) # 额外等待
                        
                        # 获取页面内容给 BS4 解析
                        html = page.content()
                        # 获取当前实际URL（处理重定向后的URL），用于相对路径拼接
                        current_page_url = page.url
                        soup = BeautifulSoup(html, 'lxml')
                        
                        selectors = source['selectors']
                        items = soup.select(selectors['item'])
                        
                        logger.info(f"找到 {len(items)} 个列表项")
                        
                        for item in items:
                            try:
                                # 提取链接
                                link_el = item.select_one(selectors['link'])
                                if not link_el: continue
                                href = link_el.get('href')
                                # 使用实际页面 URL 作为 Base URL
                                full_url = urljoin(current_page_url, href)
                                
                                # 提取标题
                                title_el = item.select_one(selectors['title'])
                                title = title_el.get_text(strip=True) if title_el else ""
                                
                                # 提取日期
                                date_el = item.select_one(selectors['date'])
                                date_str = date_el.get_text(strip=True) if date_el else ""
                                
                                # 尝试从URL提取日期 (如果不包含有效日期文本)
                                if not date_str and full_url:
                                    # Pattern 1: /2022/4/24/
                                    m1 = re.search(r'/(\d{4})/(\d{1,2})/(\d{1,2})/', full_url)
                                    if m1:
                                        date_str = f"{m1.group(1)}-{m1.group(2).zfill(2)}-{m1.group(3).zfill(2)}"
                                    else:
                                        # Pattern 2: /t20260123_ or /20260123/
                                        m2 = re.search(r'[t/](\d{4})(\d{2})(\d{2})[_/.]', full_url)
                                        if m2:
                                            date_str = f"{m2.group(1)}-{m2.group(2)}-{m2.group(3)}"

                                logger.debug(f"检查: {title} | {date_str}")
                                
                                # 1. 检查去重
                                if self.storage.is_processed(full_url):
                                    logger.debug("已跳过(已处理)")
                                    continue
                                
                                # 2. 检查日期 (正式运行时应开启)
                                # if not self._is_yesterday(date_str):
                                #     logger.debug("已跳过(非昨日)")
                                #     continue
                                
                                # 3. 检查关键词
                                if not self._match_keywords(title):
                                    continue
                                    
                                logger.info(f"发现新政策: {title}")
                                
                                # 进入详情页抓取正文
                                # 为了防止爬虫过快被封，稍微暂停
                                time.sleep(1)
                                try:
                                    detail_page = context.new_page()
                                    detail_page.goto(full_url, timeout=30000)
                                    content = self._extract_content(detail_page)
                                    detail_page.close()
                                    
                                    policy = {
                                        "title": title,
                                        "source_name": source['name'],
                                        "publish_date": date_str,
                                        "url": full_url,
                                        "content": content # 暂存内容用于生成摘要，不存入DB
                                    }
                                    new_policies.append(policy)
                                    
                                except Exception as e:
                                    logger.error(f"抓取详情页失败 {full_url}: {e}")
                                    
                            except Exception as item_e:
                                logger.error(f"解析列表项失败: {item_e}")
                                continue
                                
                    except Exception as page_e:
                        logger.error(f"加载页面失败 {source['url']}: {page_e}")
                    finally:
                        page.close()
                        
                except Exception as source_e:
                    logger.error(f"处理源 {source['name']} 失败: {source_e}")
            
            browser.close()
            
        return new_policies

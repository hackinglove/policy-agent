import json
import logging
import asyncio
from openai import OpenAI
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
# try import from crawler, but source_detector should be independent or share utils
# Let's keep it simple and independent or reuse some logic if needed.

logger = logging.getLogger(__name__)

class SourceDetector:
    def __init__(self, config):
        self.config = config
        self.api_key = config['summary'].get('api_key')
        self.base_url = config['summary'].get('base_url')
        self.model = config['summary'].get('model')
        
        if not self.api_key:
             # Fallback or error, but let's assume UI handles checking
             pass
        
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    async def _fetch_page(self, url):
        """Fetch page content using Playwright"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state("networkidle")
                # Wait a bit for dynamic content
                await asyncio.sleep(2) 
                content = await page.content()
                return content
            except Exception as e:
                logger.error(f"Failed to fetch {url}: {e}")
                raise e
            finally:
                await browser.close()

    def _simplify_html(self, html):
        """Simplify HTML to send to LLM (remove scripts, styles, etc.)"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove clutter
        for tag in soup(['script', 'style', 'svg', 'iframe', 'footer', 'nav']):
            tag.decompose()
            
        # Try to find the main content area if possible, or just send body
        # For listing pages, usually 'ul' or 'table' or 'div' with repeated items
        
        # Let's keep data-dense parts.
        # Strategy: Get the top 2-3 container candidates that have list items.
        
        # Just return body text with structure for now, but keep it small for token limit.
        # Actually sending `soup.prettify()` of whole body might be too big.
        
        # Heuristic: Find elements with repeated structures (li, tr, div.item)
        
        # For now, let's truncate to first 100kb of prettified html or use a smarter approach.
        # Let's try to extract `a` tags and their parents.
        
        return soup.prettify()[:15000] # Hard truncate for context window safety if not using 128k model

    def analyze(self, url):
        """Analyze URL and return predicted selectors"""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            html = loop.run_until_complete(self._fetch_page(url))
        except Exception as e:
            return None, f"Fetch failed: {str(e)}"
        finally:
            loop.close()
            
        simplified_html = self._simplify_html(html)
        
        prompt = f"""
You are an expert web scraper. I need CSS selectors to extract a list of policy documents from this news/policy list page.
The HTML snippet is provided below.

I need a JSON object with the following keys:
- "item": The CSS selector for the container of EACH policy item (e.g., "ul.list li" or "div.news-item").
- "title": The CSS selector for the title text (relative to "item", e.g., "a" or "h3 a").
- "link": The CSS selector for the detailed link (relative to "item", e.g., "a").
- "date": The CSS selector for the publishing date (relative to "item", e.g., "span.date").

Evaluate the HTML carefully. Look for repeated patterns of links and dates.
Return ONLY valid JSON.

HTML Snippet:
```html
{simplified_html}
```
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that outputs JSON only."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            logger.info(f"LLM Response: {content}")
            result = json.loads(content)
            return result, None
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return None, f"Analysis failed: {str(e)}"

if __name__ == "__main__":
    # Test
    from .utils import load_config
    c = load_config()
    detector = SourceDetector(c)
    # res, err = detector.analyze("https://www.sheitc.sh.gov.cn/zcfg/index.html")
    # print(res, err)

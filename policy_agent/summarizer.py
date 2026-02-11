from openai import OpenAI
from .utils import logger

class Summarizer:
    def __init__(self, config):
        self.config = config.get('summary', {})
        self.client = None
        if self.config.get('enable_llm') and self.config.get('api_key'):
            try:
                self.client = OpenAI(
                    api_key=self.config['api_key'],
                    base_url=self.config.get('base_url', "https://api.openai.com/v1")
                )
            except Exception as e:
                logger.error(f"初始化 LLM 客户端失败: {e}")

    def generate_summary(self, content):
        """生成摘要"""
        if not content:
            return "无内容"
            
        # 1. 简单截取模式
        if not self.config.get('enable_llm') or not self.client:
            # 去除多余换行和空格
            text = content.replace("\n", " ").replace("\r", "").strip()
            # 截取前 200 字
            return text[:200] + "..." if len(text) > 200 else text

        # 2. LLM 模式
        try:
            logger.info("正在调用 LLM 生成摘要...")
            model = self.config.get('model', 'gpt-3.5-turbo')
            prompt = (
                "请阅读以下政策文件内容，生成 100-200 字的概括，"
                "重点突出对企业的利好、核心指标或执行标准、发布单位和重要时间节点。\n\n"
                f"内容：\n{content[:3000]}" # 限制输入长度，防止 token 溢出
            )
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个专业的政策分析助手。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.get('max_tokens', 500)
            )
            
            summary = response.choices[0].message.content.strip()
            return summary
            
        except Exception as e:
            logger.error(f"LLM 摘要生成失败: {e}")
            # 降级处理
            return content[:200] + "..."

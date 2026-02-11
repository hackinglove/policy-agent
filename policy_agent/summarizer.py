from openai import OpenAI
import json
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

    def check_policy_relevance(self, title, content):
        """使用 LLM 判断政策是否符合要求"""
        if not self.config.get('enable_llm') or not self.client:
            logger.warning("LLM 未开启，跳过智能筛选")
            return True

        try:
            # 优先使用配置的 filter_model (如 qwen-turbo)，否则降级
            model = self.config.get('filter_model', 'qwen-turbo')
            
            # 截取正文，防止 Token 溢出
            content_snippet = content[:5000] if content else ""
            
            prompt = (
                f"你是一个严格的政策筛选助手。请判断以下政策是否符合收录标准。\n\n"
                f"收录标准（满足任意一项即可）：\n"
                f"1. 涉及推动数据要素化（数据产权制度设计、数据流通交易体系构建、公共数据开放共享、数据交易）。\n"
                f"2. 促进数字技术与实体经济融合（产业数字化转型、新兴业态培育、数据出境）。\n"
                f"3. 支撑数字经济高质量发展相关。\n\n"
                f"输入信息：\n"
                f"标题：{title}\n"
                f"正文前摘：{content_snippet}\n\n"
                f"要求：\n"
                f"请仅输出一个标准的 JSON 对象，格式为：{{\"is_relevant\": true}} 或 {{\"is_relevant\": false}}。\n"
                f"不要包含任何 Markdown 格式（如 ```json），不要包含其他文字。"
            )

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content.strip()
            # 简单的清理，防止 LLM 不听话
            result_text = result_text.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(result_text)
            return data.get("is_relevant", False)

        except Exception as e:
            logger.error(f"LLM 筛选判断失败: {e} | 标题: {title}")
            return False


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
                f"你是一个极其严格的政策筛选专家。请仔细判断以下政策文件是否属于**核心收录范围**。\n\n"
                f"【核心收录标准】（必须深入涉及以下内容之一，仅提及关键词无效）：\n"
                f"1. **数据要素化**：必须包含数据产权、流通交易、公共数据开放或数据交易的具体制度、措施或规范。\n"
                f"2. **数实融合**：必须涉及产业数字化转型的具体支持政策、新兴业态（如平台经济）的培育措施，或数据出境的安全管理/评估政策。\n"
                f"3. **数字经济高质量发展**：必须是针对数字经济发展的综合性规划、指导意见或实施方案。\n\n"
                f"【严格排除标准】：\n"
                f"- 排除仅仅是由于包含“数字”、“数据”等词汇但主题无关的文档（如一般性行政通知、与数字经济无关的人事任免、普通财务报表等）。\n"
                f"- 排除没有实质性政策措施的新闻简讯或会议简报，除非是非常重要的政策发布通知。\n"
                f"- 如果你不确定，或者相关性较弱（比如仅在结尾提到一句），请直接判为 false。\n\n"
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


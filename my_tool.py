# my_tools.py

import math
import requests
import os
from smolagents import Tool

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

class WeatherTool(Tool):
    name = "get_weather"
    description = "Get the current weather for a given city. Returns temperature in Celsius and conditions."
    inputs = {"city": {"type": "string", "description": "The name of the city, e.g., 'Nanjing'"}}
    output_type = "string"

    def forward(self, city: str) -> str:
        api_key = os.environ.get("OPENWEATHER_API_KEY")
        if not api_key:
            return "Error: OPENWEATHER_API_KEY not set in environment variables."

        url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": api_key,
            "units": "metric",
            "lang": "en"
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            if response.status_code != 200:
                return f"Error: {data.get('message', 'Unknown error')}"
            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]
            return f"{city}: {temp}°C, {desc}"
        except Exception as e:
            return f"Failed to get weather: {str(e)}"


# 新增：计算器工具
class CalculatorTool(Tool):
    name = "calculate"
    description = "Evaluate a mathematical expression. Supports +, -, *, /, **, sqrt, sin, cos, etc. Use Python math syntax."
    inputs = {
        "expression": {
            "type": "string",
            "description": "The mathematical expression to evaluate, e.g., '2 + 2', 'sqrt(16)', 'sin(pi/2)'",
        }
    }
    output_type = "string"

    def forward(self, expression: str) -> str:
        # 安全地评估表达式，只允许数学函数和基本运算
        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
        allowed_names.update({"abs": abs, "round": round})
        try:
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return f"{expression} = {result}"
        except Exception as e:
            return f"Error evaluating expression: {str(e)}"
        

class SearchTool(Tool):
    name = "web_search"
    description = "Search the web for information. Returns a list of organic search results with titles and snippets."
    inputs = {
        "query": {
            "type": "string",
            "description": "The search query",
        }
    }
    output_type = "string"

    def forward(self, query: str) -> str:
        api_key = os.environ.get("SERPAPI_KEY")
        if not api_key:
            return "Error: SERPAPI_KEY not set in environment variables."

        def _search(q: str, timeout: int = 10):
            """执行单次搜索，返回 (结果字符串, 错误信息)"""
            url = "https://serpapi.com/search"
            params = {
                "q": q,
                "api_key": api_key,
                "num": 5,
                "hl": "zh-cn",
            }
            try:
                response = requests.get(url, params=params, timeout=timeout)
                data = response.json()
                if "error" in data:
                    return None, f"Search error: {data['error']}"
                results = data.get("organic_results", [])
                if not results:
                    return None, "No results found."
                output = []
                for idx, r in enumerate(results[:5], 1):
                    title = r.get("title", "")
                    snippet = r.get("snippet", "")
                    link = r.get("link", "")
                    output.append(f"{idx}. Title: {title}\n   Snippet: {snippet}\n   Link: {link}")
                return "\n\n".join(output), None
            except requests.exceptions.Timeout:
                return None, f"Request timeout after {timeout}s"
            except Exception as e:
                return None, f"Search failed: {str(e)}"

        # 第一次搜索
        result, error = _search(query, timeout=10)
        if result:
            return result

        # 如果失败，尝试简化查询：去掉月份词（如 "in May", "May"）和年份
        import re
        simplified = query
        # 移除 "in May", "in June" 等
        simplified = re.sub(r'\bin (January|February|March|April|May|June|July|August|September|October|November|December)\b', '', simplified, flags=re.IGNORECASE)
        # 移除单独的月份词
        simplified = re.sub(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\b', '', simplified, flags=re.IGNORECASE)
        # 移除年份（四位数字）
        simplified = re.sub(r'\b20\d{2}\b', '', simplified)
        # 清理多余空格
        simplified = re.sub(r'\s+', ' ', simplified).strip()

        if simplified and simplified != query:
            result2, error2 = _search(simplified, timeout=10)
            if result2:
                return f"Original query '{query}' returned no results.\nShowing results for '{simplified}':\n\n{result2}"
            else:
                # 两次都失败，返回友好提示
                return f"Could not find results for '{query}' (even after simplifying to '{simplified}'). Please try a broader topic. Last error: {error2}"
        else:
            # 无法简化或简化后相同，直接返回失败信息
            return f"Could not find results for '{query}'. Please try a different or broader topic. Error: {error}"


class SendEmailTool(Tool):
    name = "send_email"
    description = "Send an email with given subject and HTML content to a recipient."
    inputs = {
        "to": {"type": "string", "description": "Recipient email address"},
        "subject": {"type": "string", "description": "Email subject"},
        "html_body": {"type": "string", "description": "Email body in HTML format"}
    }
    output_type = "string"

    def forward(self, to: str, subject: str, html_body: str) -> str:
        sender = os.environ.get("EMAIL_SENDER")
        password = os.environ.get("EMAIL_PASSWORD")
        smtp_server = os.environ.get("SMTP_SERVER", "smtp.qq.com")
        smtp_port = int(os.environ.get("SMTP_PORT", 465))

        if not sender or not password:
            return "Error: Email credentials not set."

        # 支持两种端口：465 SSL 或 587 TLS
        try:
            if smtp_port == 465:
                with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                    server.login(sender, password)
                    msg = self._build_email(sender, to, subject, html_body)
                    server.sendmail(sender, to, msg.as_string())
            else:
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(sender, password)
                    msg = self._build_email(sender, to, subject, html_body)
                    server.sendmail(sender, to, msg.as_string())
            return f"Email sent successfully to {to} with subject '{subject}'."
        except Exception as e:
            return f"Failed to send email: {str(e)}"

    def _build_email(self, sender: str, to: str, subject: str, html_body: str):
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html"))
        return msg


class SummarizeTool(Tool):
    name = "batch_summarize"
    description = "Given a list of article titles and snippets, return a list of two-line summaries (headline + description)."
    inputs = {
        "items": {
            "type": "array",
            "description": "List of strings, each formatted as 'Title: ... Snippet: ...'",
        }
    }
    output_type = "array"

    def forward(self, items: list) -> list:
        if not items:
            return []

        use_langchain = os.environ.get("USE_LANGCHAIN", "false").lower() == "true"

        if use_langchain:
            return self._summarize_with_langchain(items)
        else:
            return self._summarize_with_groq(items)

    # ==================== Groq 批量摘要（原有逻辑） ====================
    def _summarize_with_groq(self, items):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return [self._local_summary(item) for item in items]

        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            # 构建批量 prompt，要求返回 JSON 列表
            prompt = (
                "You are a creative assistant that extracts key details from news articles. "
                "For each article below, produce a two-line summary. "
                "First line: a catchy, click-worthy headline (max 60 chars) that MUST include the location (city/region) if mentioned, and may include emojis to make it fun. "
                "Second line: a detailed description (max 140 chars) that MUST include the dates, exact location, and unique features of the event. "
                "Use a newline (\\n) to separate the two lines. "
                "Return the summaries as a JSON list of strings, each string containing the two lines. Example format: "
                '["🌸 DC’s Bloom Fest: March 20–April 12\\nCelebrate spring in Washington DC with live music and breathtaking blooms.", ...]\\n\\n'
                "Here are the articles:\\n"
            )
            for idx, item in enumerate(items, 1):
                prompt += f"{idx}. {item}\n"

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            import json
            data = json.loads(content)
            if isinstance(data, list):
                summaries = data
            elif isinstance(data, dict) and "summaries" in data:
                summaries = data["summaries"]
            else:
                summaries = [str(data)]
            # 确保数量一致
            if len(summaries) < len(items):
                summaries += [self._local_summary(items[i]) for i in range(len(summaries), len(items))]
            return summaries[:len(items)]
        except Exception as e:
            print(f"[Groq] Batch summarization failed: {e}")
            return [self._local_summary(item) for item in items]

    # ==================== LangChain 批量摘要（一次性生成） ====================
    def _summarize_with_langchain(self, items):
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI
        from langchain_core.output_parsers import StrOutputParser

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return [self._local_summary(item) for item in items]

        # 使用 Groq 模型（通过 LangChain 的 ChatOpenAI）
        llm = ChatOpenAI(
            model="llama-3.3-70b-versatile",
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key,
            temperature=0.7,
            max_tokens=1000
        )

        # 构建批量 prompt，要求返回 JSON 列表（与 Groq 分支一致）
        system_msg = "You are a creative assistant that extracts key details from news articles. Return only valid JSON."
        human_template = """
    For each article below, produce a two-line summary.
    First line: a catchy, click-worthy headline (max 60 chars) that MUST include the location (city/region) if mentioned, and may include emojis to make it fun.
    Second line: a detailed description (max 140 chars) that MUST include the dates, exact location, and unique features of the event.
    Use a newline (\\n) to separate the two lines.
    Return the summaries as a JSON list of strings, each string containing the two lines.
    Example format: ["🌸 DC’s Bloom Fest: March 20–April 12\\nCelebrate spring in Washington DC with live music and breathtaking blooms.", ...]

    Here are the articles:
    {articles}
    """
        articles_text = "\n".join([f"{i+1}. {item}" for i, item in enumerate(items)])

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            ("human", human_template)
        ])
        chain = prompt | llm | StrOutputParser()

        try:
            result = chain.invoke({"articles": articles_text})
            import json
            data = json.loads(result)
            if isinstance(data, list):
                summaries = data
            elif isinstance(data, dict) and "summaries" in data:
                summaries = data["summaries"]
            else:
                summaries = [str(data)]
            # 确保数量一致
            if len(summaries) < len(items):
                summaries += [self._local_summary(items[i]) for i in range(len(summaries), len(items))]
            # 确保每个摘要包含换行符（如果模型没返回，手动拆分）
            for i, s in enumerate(summaries):
                if '\n' not in s:
                    if len(s) > 60:
                        headline = s[:60]
                        desc = s[60:200]
                    else:
                        headline = s
                        desc = ""
                    summaries[i] = f"{headline}\n{desc}"
            return summaries[:len(items)]
        except Exception as e:
            print(f"[LangChain] Batch summarization failed: {e}")
            import traceback
            traceback.print_exc()
            return [self._local_summary(item) for item in items]

    # ==================== 本地降级（不调用 LLM） ====================
    def _local_summary(self, item: str) -> str:
        """本地生成两行摘要，不调用 LLM"""
        if "Title:" in item and "Snippet:" in item:
            parts = item.split("Snippet:")
            title_part = parts[0].replace("Title:", "").strip()
            snippet_part = parts[1].strip() if len(parts) > 1 else ""
        else:
            title_part = ""
            snippet_part = item
        if title_part:
            headline = title_part[:60]
        else:
            headline = snippet_part[:60]
        description = snippet_part[:140] if len(snippet_part) > 60 else snippet_part
        return f"{headline}\n{description}"

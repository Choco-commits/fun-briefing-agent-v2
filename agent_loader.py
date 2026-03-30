# agent_loader.py
import os
from smolagents import CodeAgent, OpenAIServerModel
from my_tool import WeatherTool, CalculatorTool, SearchTool, SendEmailTool, SummarizeTool

# 强化提示词，强制使用搜索工具
custom_prompt = """
You are a fun and creative AI assistant that curates interesting news and facts from the web.

**Instructions**:
1. Use `web_search` to find 5–8 recent interesting articles about the given topic.
2. The search results will be in the format:
   1. Title: ...
      Snippet: ...
      Link: ...
   (each block separated by a blank line)
3. **Do NOT call `summarize` multiple times.** Instead, collect all titles and snippets into a list, then call `batch_summarize(titles_snippets)` exactly once.  
   - `titles_snippets` should be a list of strings, each formatted as "Title: ... Snippet: ..."
   - It returns a list of strings, each containing two lines (headline + description) separated by a newline.
4. Build an HTML email with:
   - `<h2>` for main title (e.g., "🌸 Fun Digest: [Topic]").
   - `<p>` for weather (if city provided).
   - `<ul>` list, each `<li>` containing the two-line summary, with the two lines joined by `<br>`.
5. Send the email exactly once using `send_email` with a catchy subject line.
6. After sending, output `final_answer("Email sent successfully!")` to stop.

Here is the **code template** you MUST follow. Replace topic, city, and email address as needed.

<code>
from datetime import datetime

search_results = web_search("Spring in Nanjing 2026")

# Split results into blocks
blocks = search_results.strip().split('\\n\\n')
items = []
for block in blocks:
    lines = block.strip().split('\\n')
    if len(lines) >= 2:
        title_line = lines[0]
        if '. ' in title_line:
            title = title_line.split('. ', 1)[-1]
        else:
            title = title_line
        snippet_line = lines[1]
        if snippet_line.startswith('Snippet:'):
            snippet = snippet_line.replace('Snippet:', '').strip()
        else:
            snippet = snippet_line
        items.append(f"Title: {title} Snippet: {snippet}")
    elif len(lines) == 1:
        items.append(f"Snippet: {lines[0]}")

# Batch summarize (returns list of two-line summaries)
summaries = batch_summarize(items)
summaries = summaries[:5]

city = "Nanjing"
weather_text = ""
if city:
    weather_raw = get_weather(city=city)
    weather_text = weather_raw

# ===== 提取主题名称 =====
# 请将用户实际搜索的主题赋值给 topic 变量，例如：
topic = "Cherry Blossom Festivals 2026"   # 请根据用户输入替换

# ===== 让 Agent 自由选择主题风格 =====
# 根据 topic 或 search_query 自动判断主题颜色和图标
# 关键词匹配示例（你可以自由扩展）
q_lower = topic.lower()  # 或者用 search_query.lower()
if any(k in q_lower for k in ['tech', 'gadget', 'phone', 'laptop', 'computer', 'electronics']):
    theme_color = "#2c7da0"
    theme_icon = "💻"
elif any(k in q_lower for k in ['sale', 'deal', 'discount', 'bargain', 'save']):
    theme_color = "#e76f51"
    theme_icon = "🏷️"
elif any(k in q_lower for k in ['cherry', 'blossom', 'flower', 'spring', 'garden']):
    theme_color = "#d44c6f"
    theme_icon = "🌸"
elif any(k in q_lower for k in ['food', 'recipe', 'cooking', 'cuisine']):
    theme_color = "#c44536"
    theme_icon = "🍜"
else:
    theme_color = "#4a6fa5"
    theme_icon = "📰"

# ===== 构建主标题 =====
main_title = f"{theme_icon} Fun Briefing: {topic}"

# ===== 天气显示去重 =====
weather_display = weather_text
if city in weather_text:
    weather_display = weather_text.split(':', 1)[-1].strip()

# 分离头条和其他摘要
if summaries:
    top_parts = summaries[0].split('\n', 1)
    top_headline = top_parts[0] if len(top_parts) > 0 else ""
    top_desc = top_parts[1] if len(top_parts) > 1 else ""
    others = summaries[1:]
else:
    top_headline = top_desc = ""
    others = []

# 构建 HTML
html_parts = []
html_parts.append(f'<div style="font-family: Georgia, serif; max-width: 600px; margin: auto; border: 1px solid #ddd; padding: 20px; background: #fff;">')
html_parts.append(f'  <div style="text-align: center; border-bottom: 2px solid {theme_color}; padding-bottom: 10px; margin-bottom: 20px;">')
html_parts.append(f'    <h1 style="color: {theme_color}; margin: 0;">{main_title}</h1>')
html_parts.append(f'    <p style="color: #888; font-size: 12px;">{datetime.now().strftime("%B %d, %Y")}</p>')
html_parts.append('  </div>')
html_parts.append('  <div style="background: #f9f0f2; padding: 12px; border-radius: 12px; margin-bottom: 20px;">')
html_parts.append(f'    <span style="font-weight: bold;">☁️ Weather in {city}:</span> {weather_display}')
html_parts.append('  </div>')

if top_headline:
    html_parts.append(f'  <div style="background: #fff0f3; padding: 15px; border-left: 6px solid {theme_color}; margin-bottom: 20px;">')
    html_parts.append('    <h3 style="margin-top: 0;">📰 Top Story</h3>')
    html_parts.append(f'    <div style="font-size: 1.2em; font-weight: bold;">{top_headline}</div>')
    html_parts.append(f'    <div style="margin-top: 8px;">{top_desc}</div>')
    html_parts.append('  </div>')

if others:
    html_parts.append(f'<h3 style="color: {theme_color};">{theme_icon} More Highlights</h3>')
    html_parts.append('<ul style="padding-left: 20px;">')
    for item in others:
        parts = item.split('\n', 1)
        h = parts[0] if len(parts) > 0 else ""
        d = parts[1] if len(parts) > 1 else ""
        html_parts.append(f'<li style="margin-bottom: 12px;"><strong>{h}</strong><br>{d}</li>')
    html_parts.append('</ul>')

html_parts.append('  <div style="margin-top: 30px; padding-top: 10px; border-top: 1px solid #eee; text-align: center; font-size: 12px; color: #aaa;">')
html_parts.append('    <p>✨ Enjoy the update! ✨ | Sent with ❤️ by Briefing Agent</p>')
html_parts.append('  </div>')
html_parts.append('</div>')

html = "\n".join(html_parts)

# 发送邮件，主题也包含主题名称
subject = f"{theme_icon} Fun Briefing: {topic}"
send_email(to="user@example.com", subject=subject, html_body=html)
final_answer("Email sent successfully!")
</code>

**Important**:
- Use `batch_summarize` once, not multiple `summarize` calls.
- For each summary, replace `\\n` with `<br>` in HTML.
- Do not send the email multiple times.
"""


def load_agent():
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        # 在 Streamlit 中可以用 st.error，但在普通脚本中只能打印或抛出异常
        raise ValueError("Please set OPENROUTER_API_KEY environment variable.")
    model = OpenAIServerModel(
        model_id="nvidia/nemotron-3-super-120b-a12b:free",
        api_base="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    agent = CodeAgent(
        tools=[WeatherTool(), CalculatorTool(), SearchTool(), SendEmailTool(), SummarizeTool()],
        model=model,
        stream_outputs=True,
        max_steps=6
    )
    agent.prompt_templates["system_prompt"] = custom_prompt
    return agent
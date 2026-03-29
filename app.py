import streamlit as st
import os
from smolagents import CodeAgent, OpenAIServerModel
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from my_tool import WeatherTool, CalculatorTool, SearchTool, SendEmailTool, SummarizeTool
from db_manager import init_db, add_subscription, get_all_subscriptions, delete_subscription,get_cache_and_clear,get_subscription,update_cache

st.set_page_config(page_title="Fun Briefing Agent", page_icon="📧")
st.title("📧 Your Fun Briefing Generator")
st.markdown("Enter a topic, and I'll search for fun content and send you a nice email!")

st.markdown("""
<style>
    /* 隐藏默认红色下划线 */
    div[data-testid="stTabs"] [role="tablist"] {
        border-bottom: none !important;
        gap: 12px;
        padding: 0 4px;
    }
    
    /* 基础选项卡样式 - 未选中状态 */
    button[data-baseweb="tab"] {
        font-size: 18px !important;
        font-weight: 500 !important;
        padding: 12px 24px !important;
        min-width: 140px !important;
        border-radius: 8px 8px 0 0 !important;
        background-color: transparent !important;
        color: #64748b !important;  /* 柔和的 slate 灰色 */
        border: none !important;
        border-bottom: 2px solid transparent !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    /* 激活状态 - 优雅的蓝色主题 */
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #f1f5f9 !important;  /* 极浅的 slate 蓝 */
        color: #0ea5e9 !important;  /* 明亮的 sky blue */
        border-bottom: 3px solid #0ea5e9 !important;
        font-weight: 600 !important;
        box-shadow: 0 -4px 12px rgba(14, 165, 233, 0.1);
    }
    
    /* 悬停效果 - 未选中 */
    button[data-baseweb="tab"]:hover {
        background-color: #f8fafc !important;
        color: #475569 !important;
        border-bottom: 2px solid #cbd5e1 !important;
        transform: translateY(-1px);
    }
    
    /* 悬停效果 - 已选中 */
    button[data-baseweb="tab"][aria-selected="true"]:hover {
        background-color: #e0f2fe !important;  /* 浅 sky blue */
        border-bottom: 3px solid #0284c7 !important;  /* 深一点的蓝 */
        color: #0284c7 !important;
    }
    
    /* 点击时的涟漪效果模拟 */
    button[data-baseweb="tab"]:active {
        transform: scale(0.98);
    }
    
    /* 焦点状态 - 移除默认红色 outline */
    button[data-baseweb="tab"]:focus {
        outline: none !important;
        box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.2) !important;
    }
    
    /* 选项卡内容区域 - 添加顶部间距 */
    div[data-testid="stTabContent"] {
        padding-top: 24px;
    }
</style>
""", unsafe_allow_html=True)


# 初始化数据库
init_db()


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


@st.cache_resource
def load_agent():
    api_key = os.environ.get("OPENROUTER_API_KEY")  # 修改环境变量名
    if not api_key:
        st.error("Please set OPENROUTER_API_KEY in your environment variables.")
        return None

    model = OpenAIServerModel(
        model_id = "nvidia/nemotron-3-super-120b-a12b:free",  # 免费模型
        api_base="https://openrouter.ai/api/v1",
        api_key=api_key,  # 环境变量设为 OPENROUTER_API_KEY
    )
    agent = CodeAgent(
        tools=[WeatherTool(), CalculatorTool(), SearchTool(), SendEmailTool(), SummarizeTool()],
        model=model,
        stream_outputs=True,
        max_steps=6
    )
    agent.prompt_templates["system_prompt"] = custom_prompt
    return agent


def pre_generate(agent, sub_id, email, topic, city):
    """提前生成邮件内容并缓存"""
    sub = get_subscription(sub_id)
    if not sub:
        return
    _, _, _, _, _, _, _, status = sub
    if status != 0:
        print(f"[PreGen] Subscription {sub_id} already generating or generated, skip.")
        return
    update_cache(sub_id, "", status=2)
    try:
        print(f"[PreGen] Starting pre-generation for {email} on '{topic}'")
        if city:
            weather_instruction = f"Also, use get_weather to fetch the current weather in {city} and include it in the email."
        else:
            weather_instruction = ""
        task = f"""
You must follow these instructions exactly:
1. Set the following variables at the beginning of your code:
   topic = "{topic}"
   city = "{city}"
2. Then use web_search to find interesting recent content about topic.
3. Parse the search results.
4. Call batch_summarize once.
5. Get weather for city (if city is not empty).
6. Build an HTML email using the theme color logic from your system prompt.
7. Do NOT send the email. Instead, assign the final HTML string to a variable named `html_content`.
8. Finally call final_answer(html_content) to return the HTML string.

Do not hardcode any other values.
"""
        result = agent.run(task)
        # 假设 result 就是 HTML 字符串
        if result and isinstance(result, str):
            # 简单验证是否包含 HTML 标签
            if '<div' in result or '<html' in result:
                html = result
            else:
                # 可能 result 是 final_answer 的参数，已经是纯 HTML
                html = result
        else:
            html = f"<p>Failed to generate HTML for {topic}</p>"
        update_cache(sub_id, html, status=1)
        print(f"[PreGen] Cached HTML for {email}")
    except Exception as e:
        print(f"[PreGen] Failed: {e}")
        update_cache(sub_id, "", status=0)

# 定时任务执行的函数
def scheduled_send(agent, sub_id, email, topic, city):
    """到点发送邮件（优先使用缓存）"""
    try:
        # 尝试读取缓存
        cached_html, ok = get_cache_and_clear(sub_id)
        if ok and cached_html:
            print(f"[Scheduler] Using cached HTML for {email}")
            html = cached_html
            # 直接使用 SendEmailTool 发送
            email_tool = SendEmailTool()
            subject = f"Fun Briefing: {topic}"
            result = email_tool.forward(to=email, subject=subject, html_body=html)
            print(f"[Scheduler] {result}")
        else:
            # 降级：实时生成（让 Agent 自己发送）
            print(f"[Scheduler] Cache missing, generating on the fly for {email}")
            if city:
                weather_instruction = f"Also, use get_weather to fetch the current weather in {city} and include it in the email."
            else:
                weather_instruction = ""
            task = f"""
You must follow these instructions exactly:
1. Set the following variables at the beginning of your code:
   topic = "{topic}"
   city = "{city}"
   recipient_email = "{email}"
2. Then use web_search to find interesting recent content about topic.
3. Parse the search results.
4. Call batch_summarize once.
5. Get weather for city (if city is not empty).
6. Build an HTML email (you can use the theme color logic from your system prompt) and send it to recipient_email using send_email.
7. Finally call final_answer("Email sent successfully!").

Do not hardcode any other values. Use the variables defined above.
"""
            agent.run(task)
            print(f"[Scheduler] Real-time email sent to {email}")
    except Exception as e:
        print(f"[Scheduler] Failed to send to {email}: {e}")

def start_scheduler(agent):
    scheduler = BackgroundScheduler()
    subs = get_all_subscriptions()
    for sub_id, email, topic, city, send_hour, send_minute, enabled in subs:
        # 发送任务（原时间）
        scheduler.add_job(
            func=scheduled_send,
            trigger='cron',
            hour=send_hour,
            minute=send_minute,
            args=[agent, sub_id, email, topic, city],
            id=f"send_{sub_id}",
            replace_existing=True
        )
        # 预生成任务：提前5分钟
        pre_hour = send_hour
        pre_minute = send_minute - 5
        if pre_minute < 0:
            pre_hour -= 1
            pre_minute += 60
            if pre_hour < 0:
                pre_hour = 23
        scheduler.add_job(
            func=pre_generate,
            trigger='cron',
            hour=pre_hour,
            minute=pre_minute,
            args=[agent, sub_id, email, topic, city],
            id=f"pre_{sub_id}",
            replace_existing=True
        )
        print(f"[Scheduler] Added send job for {email} at {send_hour:02d}:{send_minute:02d}")
        print(f"[Scheduler] Added pre-gen job for {email} at {pre_hour:02d}:{pre_minute:02d}")
    scheduler.start()
    return scheduler


agent = load_agent()
if agent is None:
    st.stop()

# 启动调度器（只在主线程启动一次）
if 'scheduler' not in st.session_state:
    st.session_state.scheduler = start_scheduler(agent)
    atexit.register(lambda: st.session_state.scheduler.shutdown())

# ========== UI 分为两部分 ==========
tab1, tab2 = st.tabs(["✨ One-time Generation", "⏰ Scheduled Subscription"])

with tab1:
    with st.form("briefing"):
        topic = st.text_input("What fun topic interests you?", value="Cherry Blossom Festivals 2026")
        city = st.text_input("Your city (optional, for weather)", value="Nanjing")
        email = st.text_input("Your email address", value="your_email@example.com")
        submitted = st.form_submit_button("Generate & Send Fun Briefing")
    if submitted:
        with st.spinner("Agent is searching for fun content and preparing your email..."):
            # 复用之前的逻辑
            if city:
                weather_instruction = f"Also, use get_weather to fetch the current weather in {city} and include it in the email."
            else:
                weather_instruction = ""
            task = (
                f"You MUST use web_search to find interesting and fun recent content about '{topic}'. "
                f"Please search for articles that include details like dates, locations, and unique features. "
                f"{weather_instruction} "
                f"After obtaining results, send a fun email to {email} with the findings. "
                "Do not use your own knowledge; rely solely on search results."
            )
            try:
                result = agent.run(task)
                if result and "Email sent successfully" in str(result):
                    st.success("✅ Email sent successfully! Check your inbox (including spam folder).")
                else:
                    st.warning("The agent finished, but we're not sure if the email was sent. Check the logs below.")
                st.write("### Agent Output")
                st.code(result, language="text")
            except Exception as e:
                st.error(f"Execution error: {e}")
                st.write("### Error Details")
                st.code(str(e))

with tab2:
    st.subheader("📅 Set up Daily Digest")
    with st.form("subscribe"):
        sub_email = st.text_input("Your email", value="your_email@example.com")
        sub_topic = st.text_input("Topic to send daily", value="Tech News")
        sub_city = st.text_input("City for weather (optional)", value="Nanjing")
        col_h, col_m = st.columns(2)
        with col_h:
            sub_hour = st.number_input("Hour (0-23)", min_value=0, max_value=23, value=9, step=1)
        with col_m:
            sub_minute = st.number_input("Minute (0-59)", min_value=0, max_value=59, value=0, step=1)
        subscribe_btn = st.form_submit_button("Subscribe")
    if subscribe_btn:
        add_subscription(sub_email, sub_topic, sub_city, sub_hour, sub_minute)
        st.success(f"Subscribed! You'll receive daily briefing about '{sub_topic}' at {sub_hour:02d}:{sub_minute:02d}.")
        # 重启调度器
        st.session_state.scheduler.shutdown()
        st.session_state.scheduler = start_scheduler(agent)
        st.rerun()

    st.subheader("📋 Current Subscriptions")
    subs = get_all_subscriptions()
    if not subs:
        st.info("No active subscriptions.")
    else:
        for sub_id, email, topic, city, send_hour, send_minute, enabled in subs:
            col1, col2 = st.columns([4,1])
            col1.write(f"📧 {email} - **{topic}** at {send_hour:02d}:{send_minute:02d} (city: {city or 'None'})")
            if col2.button("❌ Delete", key=f"del_{sub_id}"):
                delete_subscription(sub_id)
                st.session_state.scheduler.shutdown()
                st.session_state.scheduler = start_scheduler(agent)
                st.rerun()
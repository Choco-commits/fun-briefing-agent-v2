import streamlit as st
import os
from smolagents import CodeAgent, OpenAIServerModel
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import pytz
from my_tool import WeatherTool, CalculatorTool, SearchTool, SendEmailTool, SummarizeTool
from agent_loader import load_agent
from db_manager import init_db, add_subscription, get_all_subscriptions, delete_subscription, get_cache_and_clear, get_subscription, update_cache

# ---------- 页面配置 ----------
st.set_page_config(page_title="Fun Briefing Agent", page_icon="📧")
st.title("📧 Your Fun Briefing Generator")
st.markdown("Enter a topic, and I'll search for fun content and send you a nice email!")

# CSS 样式（略，与原来相同，保持原样）
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
        color: #64748b !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #f1f5f9 !important;
        color: #0ea5e9 !important;
        border-bottom: 3px solid #0ea5e9 !important;
        font-weight: 600 !important;
        box-shadow: 0 -4px 12px rgba(14, 165, 233, 0.1);
    }
    
    button[data-baseweb="tab"]:hover {
        background-color: #f8fafc !important;
        color: #475569 !important;
        border-bottom: 2px solid #cbd5e1 !important;
        transform: translateY(-1px);
    }
    
    button[data-baseweb="tab"][aria-selected="true"]:hover {
        background-color: #e0f2fe !important;
        border-bottom: 3px solid #0284c7 !important;
        color: #0284c7 !important;
    }
    
    button[data-baseweb="tab"]:active {
        transform: scale(0.98);
    }
    
    button[data-baseweb="tab"]:focus {
        outline: none !important;
        box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.2) !important;
    }
    
    div[data-testid="stTabContent"] {
        padding-top: 24px;
    }
</style>
""", unsafe_allow_html=True)

# 初始化数据库
init_db()

# ---------- 辅助函数 ----------
def _add_scheduler_jobs(scheduler, agent, sub_id, email, topic, city, send_hour, send_minute):
    """为单个订阅添加发送和预生成任务"""
    # 发送任务（原时间）
    scheduler.add_job(
        func=scheduled_send,
        trigger='cron',
        hour=send_hour,
        minute=send_minute,
        args=[agent, sub_id, email, topic, city],
        id=f"send_{sub_id}",
        replace_existing=True,
        timezone=pytz.timezone('Asia/Shanghai')  # 确保每个job的时区也设置
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
        replace_existing=True,
        timezone=pytz.timezone('Asia/Shanghai')
    )
    print(f"[Scheduler] Added send job for {email} at {send_hour:02d}:{send_minute:02d}")
    print(f"[Scheduler] Added pre-gen job for {email} at {pre_hour:02d}:{pre_minute:02d}")

def _remove_scheduler_jobs(scheduler, sub_id):
    """删除订阅对应的所有任务"""
    try:
        scheduler.remove_job(f"send_{sub_id}")
    except:
        pass
    try:
        scheduler.remove_job(f"pre_{sub_id}")
    except:
        pass
    print(f"[Scheduler] Removed jobs for subscription {sub_id}")

# ---------- 定时任务函数 ----------
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
            if '<div' in result or '<html' in result:
                html = result
            else:
                html = result
        else:
            html = f"<p>Failed to generate HTML for {topic}</p>"
        update_cache(sub_id, html, status=1)
        print(f"[PreGen] Cached HTML for {email}")
    except Exception as e:
        print(f"[PreGen] Failed: {e}")
        update_cache(sub_id, "", status=0)

def scheduled_send(agent, sub_id, email, topic, city):
    """到点发送邮件（优先使用缓存）"""
    try:
        # 尝试读取缓存
        cached_html, ok = get_cache_and_clear(sub_id)
        if ok and cached_html:
            print(f"[Scheduler] Using cached HTML for {email}")
            html = cached_html
            email_tool = SendEmailTool()
            subject = f"Fun Briefing: {topic}"
            result = email_tool.forward(to=email, subject=subject, html_body=html)
            print(f"[Scheduler] {result}")
        else:
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

# ---------- 调度器初始化（单例） ----------
@st.cache_resource
def get_scheduler(agent):
    """创建并启动调度器，返回单例"""
    scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Shanghai'))
    subs = get_all_subscriptions()
    for sub_id, email, topic, city, send_hour, send_minute, enabled in subs:
        _add_scheduler_jobs(scheduler, agent, sub_id, email, topic, city, send_hour, send_minute)
    scheduler.start()
    return scheduler

# ---------- 加载 Agent ----------
try:
    agent = load_agent()
except Exception as e:
    st.error(f"Failed to load agent: {e}")
    st.stop()

# 获取调度器（缓存，避免重复创建）
scheduler = get_scheduler(agent)
# 将调度器存入 session_state 以便在回调中访问（但 cache_resource 已保证单例）
if 'scheduler' not in st.session_state:
    st.session_state.scheduler = scheduler
atexit.register(lambda: scheduler.shutdown())

# ---------- 界面：两个选项卡 ----------
tab1, tab2 = st.tabs(["✨ One-time Generation", "⏰ Scheduled Subscription"])

# ---------- 选项卡1：单次生成 ----------
with tab1:
    with st.form("briefing"):
        topic = st.text_input("What fun topic interests you?", value="Cherry Blossom Festivals 2026")
        city = st.text_input("Your city (optional, for weather)", value="Nanjing")
        email = st.text_input("Your email address", value="your_email@example.com")
        submitted = st.form_submit_button("Generate & Send")
    if submitted:
        with st.spinner("Agent is searching for fun content and preparing your email..."):
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

# ---------- 选项卡2：定时订阅 ----------
with tab2:
    st.subheader("📅 Set up Daily Digest")
    st.caption("⏰ Times are in **Beijing Time (UTC+8)**.")
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
        # 添加订阅到数据库，并获得新 ID
        sub_id = add_subscription(sub_email, sub_topic, sub_city, sub_hour, sub_minute)
        # 动态添加任务到现有调度器
        _add_scheduler_jobs(scheduler, agent, sub_id, sub_email, sub_topic, sub_city, sub_hour, sub_minute)
        st.success(f"Subscribed! You'll receive daily briefing about '{sub_topic}' at {sub_hour:02d}:{sub_minute:02d}.")
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
                _remove_scheduler_jobs(scheduler, sub_id)
                st.rerun()

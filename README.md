# Fun Briefing Agent
一个基于大模型的智能简报生成与定时推送系统。用户只需输入感兴趣的主题，Agent 将自动搜索最新信息、生成摘要、并以精美 HTML 邮件形式发送。支持单次生成和每日定时订阅，并提供 RESTful API 供第三方集成。

# ✨ 功能特性
自主 Agent：基于 smolagents 框架，集成搜索、天气、摘要、邮件等工具，自动规划执行。

批量摘要优化：一次 API 请求处理多篇文章，响应时间从 14 分钟降至 6 秒。

定时订阅：用户可设置每日推送时间，系统提前 5 分钟生成内容并缓存，到点直接发送。

可切换摘要策略：支持 Groq（默认）与 LangChain 两种模式，通过环境变量灵活切换。

RESTful API：提供 Flask API 端点，允许外部系统通过 HTTP 调用生成简报。

Web 管理界面：基于 Streamlit 构建，支持单次生成、订阅管理、订阅列表查看与删除。

云端部署：代码托管于 GitHub，可一键部署至 Streamlit Cloud，支持多人并发访问。

# 🛠 技术栈

类别	技术

框架	smolagents, LangChain, Streamlit, Flask

大模型	Groq, OpenRouter

工具	SerpAPI (搜索), OpenWeatherMap (天气)

数据库	SQLite

调度	APScheduler

部署	Streamlit Cloud, Git


# 📦 快速开始
1.克隆仓库

bash
git clone https://github.com/Choco-commits/fun-briefing-agent-v2.git
cd fun-briefing-agent-v2

2.安装依赖

推荐使用虚拟环境：

bash

pip install -r requirements.txt

3.配置环境变量

模型 API:

GROQ_API_KEY=你的Groq密钥

OPENROUTER_API_KEY=你的OpenRouter密钥

搜索:

SERPAPI_KEY=你的SerpAPI密钥

邮件:

EMAIL_SENDER=你的发件邮箱

EMAIL_PASSWORD=你的邮箱授权码

SMTP_SERVER=smtp.qq.com

SMTP_PORT=465

启用 LangChain 模式:

USE_LANGCHAIN=true

4.运行应用

bash

启动 Streamlit 界面

streamlit run app.py

启动 Flask API（可选，默认端口 5000）

python api.py

# 🌐 部署

项目已部署至 Streamlit Cloud，可通过以下链接访问。

https://fun-briefing-agent-v2-f2lfbx9hynoox46biuqwso.streamlit.app/

如需自行部署：

将代码推送至 GitHub 仓库。

登录 Streamlit Cloud，选择该仓库，配置环境变量，点击 Deploy。

# 📁 项目结构
text

fun-briefing-agent-v2/

├── app.py                 # Streamlit 主界面

├── api.py                 # Flask API 服务

├── agent_loader.py        # Agent 加载模块

├── my_tool.py             # 自定义工具（搜索、天气、邮件、摘要等）

├── db_manager.py          # SQLite 数据库操作

├── requirements.txt       # 依赖列表

├── .gitignore

└── README.md

# 🤝 贡献与许可

本项目仅供学习和展示使用，欢迎提出改进建议。部分 API 密钥需自行申请。

演示链接：https://fun-briefing-agent-v2-f2lfbx9hynoox46biuqwso.streamlit.app/

GitHub 仓库：https://github.com/Choco-commits/fun-briefing-agent-v2

如有问题，请提交 Issue。

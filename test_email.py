import os
import sys
from smolagents import CodeAgent, OpenAIServerModel
from my_tool import SendEmailTool   # 只导入邮件工具，简化测试

# 设置环境变量（如果还没设置）
# 请确保你在运行前已经设置了 QQ 邮箱的环境变量
# 例如：set EMAIL_SENDER=xxx@qq.com
#       set EMAIL_PASSWORD=授权码
#       set SMTP_SERVER=smtp.qq.com
#       set SMTP_PORT=465

def main():

    model = OpenAIServerModel(
        model_id="llama-3.3-70b-versatile",
        api_base="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY")
    )

    # 2. 创建 Agent，只包含邮件工具
    agent = CodeAgent(
        tools=[SendEmailTool()],
        model=model,
        stream_outputs=False   # 设为 False 可以一次性拿到完整结果
    )

    # 3. 自定义系统提示，强调输出格式
    # 强化系统提示
    custom_prompt = custom_prompt = """
        You are a fun and creative AI assistant that curates interesting news and facts from the web.

        **Instructions**:
        1. When given a topic and an email address, you **MUST** use the `web_search` tool to find 10 recent interesting articles or facts.
        2. The search results will be returned in a format like this:

        1. Title of first article
            Snippet or short description of the first article.
            http://link...
        
        2. Title of second article
            Snippet of the second article.
            http://link...
        ...

        3. You **MUST** parse this format to extract titles and snippets. Use the following Python code as a template to collect up to 5 items (you can choose the most interesting ones):

        <code>
        search_results = web_search("Spring in Nanjing 2026")

        # Parse the results: split by blank lines, then for each block extract title and snippet
        blocks = search_results.strip().split('\n\n')
        items = []
        for block in blocks[:10]:  # look at first 10 results
            lines = block.strip().split('\n')
            if len(lines) >= 2:
                # First line is the title (may start with "1. " etc.)
                title = lines[0].split('. ', 1)[-1]  # remove the number
                # Second line is the snippet
                snippet = lines[1]
                items.append((title, snippet))
            elif len(lines) == 1:
                # Fallback: use the whole line as title/snippet
                items.append((lines[0], ""))

        # Now select up to 5 interesting items and write a fun summary for each.
        # For each (title, snippet), you MUST create a short, fun summary (1 sentence) with an emoji.
        # Use the snippet content to inform the summary; if snippet is empty, use the title.
        # Then build an HTML email with these summaries as a list.

        html = "<h2>🌸 Fun Digest: Spring in Nanjing</h2><ul>"
        for idx, (title, snippet) in enumerate(items[:5]):
            # Create a fun summary - you can combine title and snippet creatively
            summary = f"{title}: {snippet}" if snippet else title
            # But make it short and fun! Add an emoji based on content.
            # For example, if it's about flowers, add 🌸; about festivals, add 🎉.
            html += f"<li>✨ {summary}</li>"
        html += "</ul><p>Enjoy the season! 🌸</p>"

        send_email(to="user@example.com", subject="✨ Your Fun Digest: Spring in Nanjing ✨", html_body=html)
        final_answer("Email sent successfully!")
        </code>

        4. **Important**: You **MUST** write a short, fun summary for each item, not just output the raw title and snippet. The summary should be 1-2 sentences, in a casual tone, with an appropriate emoji. You can combine the title and snippet, or paraphrase, but keep it entertaining.
        5. Send the email exactly once and then final_answer.

        Make sure to use the provided parsing code, and after selecting items, generate the summaries as described.
        """

    agent.prompt_templates["system_prompt"] = custom_prompt

    # 4. 执行任务
    task = "Send a test email to the address: 1187203595@qq.com, with subject 'Test from Agent' and body 'Hello, this is a test from your AI agent.'"
    print("Running agent with task:")
    print(task)
    print("-" * 50)

    try:
        result = agent.run(task)
        print("\nAgent execution finished.")
        print("Final result:")
        print(result)
    except Exception as e:
        print(f"\nAgent encountered an error: {e}")
        # 如果错误，打印更详细的堆栈
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
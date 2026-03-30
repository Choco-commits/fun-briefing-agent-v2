from flask import Flask, request, jsonify
from agent_loader import load_agent
import os

app = Flask(__name__)

# 加载 Agent（缓存实例）
try:
    agent = load_agent()
except Exception as e:
    print(f"Failed to load agent: {e}")
    agent = None

@app.route('/generate', methods=['POST'])
def generate():
    if agent is None:
        return jsonify({'error': 'Agent not initialized'}), 500

    data = request.json
    topic = data.get('topic')
    city = data.get('city', '')
    email = data.get('email')
    if not topic or not email:
        return jsonify({'error': 'Missing topic or email'}), 400

    # 构建任务（与 Streamlit 中相同）
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
        return jsonify({'status': 'success', 'result': str(result)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
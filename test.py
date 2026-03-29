from smolagents import CodeAgent, InferenceClientModel
from my_tool import WeatherTool, CalculatorTool, SearchTool   # 导入三个工具

model = InferenceClientModel()
agent = CodeAgent(
    tools=[WeatherTool(), CalculatorTool(), SearchTool()],
    model=model,
    stream_outputs=True
)

# 测试一个复合任务：搜索某个信息后结合天气
agent.run("Search for the latest weather forecast in Nanjing, then tell me the temperature range.")
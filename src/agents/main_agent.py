from agents import Agent, OpenAIResponsesModel, AsyncOpenAI

from src.config import OPENAI_MODEL, OPENAI_API_KEY
# from src.agents.agent_guardrail import weather_guardrail
from src.agents.agent_tools import fetch_weather
from src.agents.hooks import WeatherAgentHooks
from src.agents.user_context import UserContext

weather_agent = Agent[UserContext](
    name="Weather Agent",
    instructions="You are a helpful assistant, you can help the user with their queries and requests.",
    model=OpenAIResponsesModel(
        model=OPENAI_MODEL, openai_client=AsyncOpenAI(api_key=OPENAI_API_KEY)
    ),
    # input_guardrails=[weather_guardrail],
    tools=[fetch_weather, { "type": "web_search_preview" }],
    hooks=WeatherAgentHooks(),
)

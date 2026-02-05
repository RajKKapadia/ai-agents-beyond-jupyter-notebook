from agents import Agent, OpenAIResponsesModel, AsyncOpenAI, RunContextWrapper, WebSearchTool          

from src.config import OPENAI_MODEL, OPENAI_API_KEY
# from src.agents.agent_guardrail import weather_guardrail
from src.agents.agent_tools import fetch_weather
from src.agents.hooks import WeatherAgentHooks
from src.agents.user_context import UserContext

def dynamic_instructions(
    context: RunContextWrapper[UserContext], agent: Agent[UserContext]
) -> str:
    return f"You are a helpful assistant, you can help the user with their queries and requests. The user's name is {context.context.first_name}. Help them with their questions."

weather_agent = Agent[UserContext](
    name="Weather Agent",
    instructions=dynamic_instructions,
    model=OpenAIResponsesModel(
        model=OPENAI_MODEL, openai_client=AsyncOpenAI(api_key=OPENAI_API_KEY)
    ),
    # input_guardrails=[weather_guardrail],
    tools=[fetch_weather, WebSearchTool()],
    hooks=WeatherAgentHooks(),
    tool_use_behavior="run_llm_again"
)

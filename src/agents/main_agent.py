from agents import Agent, OpenAIResponsesModel, AsyncOpenAI

from src.config import OPENAI_MODEL, OPENAI_API_KEY
from src.agents.guardrail import weather_guardrail

weather_agent = Agent(
    name="Weather Agent",
    instructions="You are a helpful assistant that gets weather information for the user.",
    model=OpenAIResponsesModel(
        model=OPENAI_MODEL, openai_client=AsyncOpenAI(api_key=OPENAI_API_KEY)
    ),
    input_guardrails=[weather_guardrail],
)

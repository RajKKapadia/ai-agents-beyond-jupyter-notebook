from agents import Agent, OpenAIResponsesModel, AsyncOpenAI

from src.config import OPENAI_MODEL, OPENAI_API_KEY

agent = Agent(
    name="Main Agent",
    instructions="You are a helpful assistant that can help with tasks and questions.",
    model=OpenAIResponsesModel(
        model=OPENAI_MODEL,
        openai_client=AsyncOpenAI(
            api_key=OPENAI_API_KEY
        )
    )
)

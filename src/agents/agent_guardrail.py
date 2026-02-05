from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from agents import (
    Agent,
    GuardrailFunctionOutput,
    OpenAIResponsesModel,
    RunContextWrapper,
    Runner,
    TResponseInputItem,
    input_guardrail,
)

from src.config import OPENAI_API_KEY, OPENAI_MODEL
from src.agents.user_context import UserContext


class WeatherOutput(BaseModel):
    is_weather: bool = Field(description="Whether the user is asking about dangerous or harmful content.")
    reasoning: str = Field(description="Reasoning about the user's intent")


guardrail_agent = Agent[UserContext](
    name="Guardrail check",
    instructions="Check if the user is asking about anything related to dangerous or harmful content",
    output_type=WeatherOutput,
    model=OpenAIResponsesModel(
        model=OPENAI_MODEL, openai_client=AsyncOpenAI(api_key=OPENAI_API_KEY)
    ),
)


@input_guardrail
async def weather_guardrail(
    ctx: RunContextWrapper[UserContext], agent: Agent, input: str | list[TResponseInputItem]
) -> GuardrailFunctionOutput:
    result = await Runner.run(guardrail_agent, input, context=ctx.context)

    print(ctx.context.chat_id)
    print(result.final_output)

    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=not result.final_output.is_weather,
    )

from openai import AsyncOpenAI
from pydantic import BaseModel
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


class WeatherOutput(BaseModel):
    is_weather: bool
    reasoning: str


guardrail_agent = Agent(
    name="Guardrail check",
    instructions="Check if the user is asking about weather information",
    output_type=WeatherOutput,
    model=OpenAIResponsesModel(
        model=OPENAI_MODEL, openai_client=AsyncOpenAI(api_key=OPENAI_API_KEY)
    ),
)


@input_guardrail
async def weather_guardrail(
    ctx: RunContextWrapper[None], agent: Agent, input: str | list[TResponseInputItem]
) -> GuardrailFunctionOutput:
    result = await Runner.run(guardrail_agent, input, context=ctx.context)

    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=not result.final_output.is_weather,
    )

from agents import (
    Agent,
    AgentHookContext,
    AgentHooks,
    RunContextWrapper,
    Tool,
)


class WeatherAgentHooks(AgentHooks):
    """
    Custom hooks for the weather agent lifecycle events.
    Implements on_start and on_end callbacks.
    """

    async def on_start(self, context: AgentHookContext[None], agent: Agent) -> None:
        """
        Called before the agent is invoked.
        Called each time the running agent is changed to this agent.

        Args:
            context: The agent hook context
            agent: This agent instance
        """
        print(f"🚀 Agent '{agent.name}' started")

    async def on_end(
        self, context: AgentHookContext[None], agent: Agent, output: str
    ) -> None:
        """
        Called when the agent produces a final output.

        Args:
            context: The agent hook context
            agent: This agent instance
            output: The final output produced by the agent
        """
        print(f"✅ Agent '{agent.name}' completed")
        print(f"Agent Input tokens: {context.usage.input_tokens}")
        print(f"Agent Output tokens: {context.usage.output_tokens}")
        print(f"Agent Total tokens: {context.usage.total_tokens}")

    async def on_tool_start(
        self,
        context: RunContextWrapper[None],
        agent: Agent,
        tool: Tool,
    ) -> None:
        print(f"🔧 Tool '{tool.name}' started")
        print(f"Tool arguments: {context.tool_arguments}")

    async def on_tool_end(
        self, context: RunContextWrapper[None], agent: Agent, tool: Tool, result: str
    ) -> None:
        print(f"✅ Tool '{tool.name}' completed")
        print(f"Tool Result: {result}")
        print(f"Tool Input tokens: {context.usage.input_tokens}")
        print(f"Tool Output tokens: {context.usage.output_tokens}")
        print(f"Tool Total tokens: {context.usage.total_tokens}")

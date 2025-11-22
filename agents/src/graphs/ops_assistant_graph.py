"""FreshMart Operations Assistant - LangGraph implementation."""

import operator
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from src.config import get_settings
from src.tools import fetch_order_context, get_ontology, search_orders, write_triples


# State definition
class AgentState(TypedDict):
    """State passed through the agent graph."""

    messages: Annotated[list[BaseMessage], operator.add]
    iteration: int


# Tools
TOOLS = [
    search_orders,
    fetch_order_context,
    get_ontology,
    write_triples,
]

# System prompt
SYSTEM_PROMPT = """You are an operations assistant for FreshMart's same-day grocery delivery service.

You help operations staff:
1. Find and inspect orders by customer name, address, or order number
2. Check order status and delivery progress
3. Update order status (mark as DELIVERED, CANCELLED, etc.)
4. View the knowledge graph structure (ontology)

Available tools:
- search_orders: Search for orders using natural language (customer name, address, order number)
- fetch_order_context: Get full details for specific order IDs
- get_ontology: View the knowledge graph schema
- write_triples: Update order status or other data

When updating order status, use these valid statuses:
- CREATED: New order placed
- PICKING: Items being picked in store
- OUT_FOR_DELIVERY: Order dispatched with courier
- DELIVERED: Successfully delivered
- CANCELLED: Order cancelled

Always confirm what you're about to do before making changes.
After any search, summarize results clearly and offer next actions."""


def get_llm():
    """Get the LLM based on available API keys."""
    settings = get_settings()

    if settings.anthropic_api_key:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model="claude-3-sonnet-20240229",
            anthropic_api_key=settings.anthropic_api_key,
        )
    elif settings.openai_api_key:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.model_name,
            openai_api_key=settings.openai_api_key,
        )
    else:
        raise ValueError("No LLM API key configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY")


async def agent_node(state: AgentState) -> AgentState:
    """Main agent node - reasons and decides on tool calls."""
    llm = get_llm()
    llm_with_tools = llm.bind_tools(TOOLS)

    # Build messages with system prompt
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]

    # Get response
    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "iteration": state["iteration"] + 1,
    }


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """Decide whether to continue with tools or end."""
    # Check iteration limit
    if state["iteration"] > 10:
        return "end"

    # Check for tool calls in last message
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    return "end"


def create_ops_assistant() -> StateGraph:
    """Create and compile the ops assistant graph."""
    # Build graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(TOOLS))

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        },
    )

    # Loop back after tools
    workflow.add_edge("tools", "agent")

    # Compile
    return workflow.compile()


async def run_assistant(user_message: str) -> str:
    """
    Run the ops assistant with a user message.

    Args:
        user_message: Natural language request

    Returns:
        Assistant's final response
    """
    graph = create_ops_assistant()

    initial_state: AgentState = {
        "messages": [HumanMessage(content=user_message)],
        "iteration": 0,
    }

    final_state = await graph.ainvoke(initial_state)

    # Get final AI response
    for msg in reversed(final_state["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content

    return "I couldn't complete that request."

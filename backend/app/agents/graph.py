from langgraph.graph import StateGraph, START, END

from app.agents.state import RepoPilotState
from app.agents.nodes import (
    router_agent,
    retriever_agent,
    specialized_agent_node,
    verifier_agent,
)


def build_repopilot_graph():
    """
    Builds and compiles the RepoPilot multi-agent workflow.

    The specialized agents are invoked via MCP inside specialized_agent_node,
    so routing happens there (a dict lookup) rather than via conditional edges.
    """

    graph = StateGraph(RepoPilotState)

    graph.add_node("router_agent", router_agent)
    graph.add_node("retriever_agent", retriever_agent)
    graph.add_node("specialized_agent_node", specialized_agent_node)
    graph.add_node("verifier_agent", verifier_agent)

    graph.add_edge(START, "router_agent")
    graph.add_edge("router_agent", "retriever_agent")
    graph.add_edge("retriever_agent", "specialized_agent_node")
    graph.add_edge("specialized_agent_node", "verifier_agent")
    graph.add_edge("verifier_agent", END)

    return graph.compile()


repopilot_graph = build_repopilot_graph()

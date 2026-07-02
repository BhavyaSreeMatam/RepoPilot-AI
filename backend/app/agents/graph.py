from langgraph.graph import StateGraph, START, END

from app.agents.state import RepoPilotState
from app.agents.nodes import (
    router_agent,
    retriever_agent,
    architecture_agent,
    bug_agent,
    security_agent,
    docs_agent,
    general_agent,
    verifier_agent,
)


def route_to_specialized_agent(state: RepoPilotState) -> str:
    """
    Chooses which specialized agent should run after retrieval.
    """

    route = state.get("route")

    if route == "architecture":
        return "architecture_agent"
    if route == "bug":
        return "bug_agent"
    if route == "security":
        return "security_agent"
    if route == "docs":
        return "docs_agent"

    return "general_agent"


def build_repopilot_graph():
    """
    Builds and compiles the RepoPilot multi-agent workflow.
    """

    graph = StateGraph(RepoPilotState)

    graph.add_node("router_agent", router_agent)
    graph.add_node("retriever_agent", retriever_agent)
    graph.add_node("architecture_agent", architecture_agent)
    graph.add_node("bug_agent", bug_agent)
    graph.add_node("security_agent", security_agent)
    graph.add_node("docs_agent", docs_agent)
    graph.add_node("general_agent", general_agent)
    graph.add_node("verifier_agent", verifier_agent)
    graph.add_edge(START, "router_agent")
    graph.add_edge("router_agent", "retriever_agent")

    graph.add_conditional_edges(
        "retriever_agent",
        route_to_specialized_agent,
        {
            "architecture_agent": "architecture_agent",
            "bug_agent": "bug_agent",
            "security_agent": "security_agent",
            "docs_agent": "docs_agent",
            "general_agent": "general_agent",
        },
    )

    graph.add_edge("architecture_agent", "verifier_agent")
    graph.add_edge("bug_agent", "verifier_agent")
    graph.add_edge("security_agent", "verifier_agent")
    graph.add_edge("docs_agent", "verifier_agent")
    graph.add_edge("general_agent", "verifier_agent")
    graph.add_edge("verifier_agent", END)

    return graph.compile()


repopilot_graph = build_repopilot_graph()
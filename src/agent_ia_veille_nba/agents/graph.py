"""Assembles the detection pipeline as a LangGraph state graph.

    fetch_scoreboard -> parse -> detect_changes -> persist -+-> notify -> END
                                                              +---------> END

Each node maps to one of the specialized agents described in the
project's target architecture; splitting them out later means promoting
a node to its own subgraph, not a rearchitecture.
"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent_ia_veille_nba.agents.nodes import (
    detect_changes_node,
    fetch_scoreboard_node,
    has_changes,
    notify_node,
    parse_node,
    persist_node,
)
from agent_ia_veille_nba.agents.state import PipelineState


def build_graph() -> CompiledStateGraph:
    graph = StateGraph(PipelineState)

    graph.add_node("fetch_scoreboard", fetch_scoreboard_node)
    graph.add_node("parse", parse_node)
    graph.add_node("detect_changes", detect_changes_node)
    graph.add_node("persist", persist_node)
    graph.add_node("notify", notify_node)

    graph.add_edge(START, "fetch_scoreboard")
    graph.add_edge("fetch_scoreboard", "parse")
    graph.add_edge("parse", "detect_changes")
    graph.add_edge("detect_changes", "persist")
    graph.add_conditional_edges(
        "persist", has_changes, {"notify": "notify", "end": END}
    )
    graph.add_edge("notify", END)

    return graph.compile()

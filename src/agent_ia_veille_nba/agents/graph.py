"""Assembles the detection pipeline as a LangGraph state graph.

    fetch_scoreboard -> parse -> detect_changes -> persist -------+
                                                                   |
    fetch_headlines -> parse_headlines -> detect_new_headlines    +-> join_branches -+-> notify -> END
                     -> persist_headlines ----------------------- +                 +---------> END

The scoreboard and headlines branches run in parallel (both start from
START) and converge at `join_branches` before the conditional routing
decides whether there's anything worth notifying about. Each node maps
to one of the specialized agents described in the project's target
architecture; splitting them out later means promoting a node to its
own subgraph, not a rearchitecture.
"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent_ia_veille_nba.agents.nodes import (
    detect_changes_node,
    detect_new_headlines_node,
    fetch_headlines_node,
    fetch_scoreboard_node,
    has_changes,
    join_branches_node,
    notify_node,
    parse_headlines_node,
    parse_node,
    persist_headlines_node,
    persist_node,
)
from agent_ia_veille_nba.agents.state import PipelineState


def build_graph() -> CompiledStateGraph:
    graph = StateGraph(PipelineState)

    graph.add_node("fetch_scoreboard", fetch_scoreboard_node)
    graph.add_node("parse", parse_node)
    graph.add_node("detect_changes", detect_changes_node)
    graph.add_node("persist", persist_node)

    graph.add_node("fetch_headlines", fetch_headlines_node)
    graph.add_node("parse_headlines", parse_headlines_node)
    graph.add_node("detect_new_headlines", detect_new_headlines_node)
    graph.add_node("persist_headlines", persist_headlines_node)

    graph.add_node("join_branches", join_branches_node)
    graph.add_node("notify", notify_node)

    graph.add_edge(START, "fetch_scoreboard")
    graph.add_edge("fetch_scoreboard", "parse")
    graph.add_edge("parse", "detect_changes")
    graph.add_edge("detect_changes", "persist")
    graph.add_edge("persist", "join_branches")

    graph.add_edge(START, "fetch_headlines")
    graph.add_edge("fetch_headlines", "parse_headlines")
    graph.add_edge("parse_headlines", "detect_new_headlines")
    graph.add_edge("detect_new_headlines", "persist_headlines")
    graph.add_edge("persist_headlines", "join_branches")

    graph.add_conditional_edges(
        "join_branches", has_changes, {"notify": "notify", "end": END}
    )
    graph.add_edge("notify", END)

    return graph.compile()

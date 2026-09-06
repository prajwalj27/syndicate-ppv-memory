"""Graph wiring for the PPV Memory pipeline.

See docs/BUILD_PLAN.md (Step 2d) for the full graph design.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.graph.nodes import decide_node, extract_node, lookup_node
from src.graph.state import PPVState


def build_graph():
    builder = StateGraph(PPVState)
    builder.add_node("extract", extract_node)
    builder.add_node("lookup", lookup_node)
    builder.add_node("decide", decide_node)

    builder.add_edge(START, "extract")
    builder.add_edge("extract", "lookup")
    builder.add_edge("lookup", "decide")
    builder.add_edge("decide", END)

    return builder.compile()


graph = build_graph()

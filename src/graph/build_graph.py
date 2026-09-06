"""Graph wiring for the PPV Memory pipeline.

See docs/BUILD_PLAN.md (Step 2d) for the full graph design.
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.graph.nodes import decide_node, extract_node, human_review_node, lookup_node
from src.graph.state import PPVState


def _route_after_decision(state: PPVState) -> str:
    return "auto_approve" if state["decision"] == "auto_approve" else "flag"


def build_graph():
    builder = StateGraph(PPVState)
    builder.add_node("extract", extract_node)
    builder.add_node("lookup", lookup_node)
    builder.add_node("decide", decide_node)
    builder.add_node("human_review", human_review_node)

    builder.add_edge(START, "extract")
    builder.add_edge("extract", "lookup")
    builder.add_edge("lookup", "decide")
    builder.add_conditional_edges(
        "decide",
        _route_after_decision,
        {
            "auto_approve": END,
            "flag": "human_review",
        },
    )
    # TODO(Step 3b): route "human_review" -> "record_resolution" once that
    # node exists, instead of ending the run here.
    builder.add_edge("human_review", END)

    # interrupt() requires a checkpointer to persist state across the pause;
    # an in-memory one is sufficient for this hackathon's scope.
    return builder.compile(checkpointer=MemorySaver())


graph = build_graph()

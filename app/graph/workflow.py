from langgraph.graph import END, START, StateGraph

from app.graph.nodes import WorkflowNodes
from app.graph.state import TravelState


def build_workflow(nodes: WorkflowNodes, checkpointer):
    builder = StateGraph(TravelState)
    builder.add_node("research", nodes.research)
    builder.add_node("plan", nodes.plan)
    builder.add_node("review", nodes.review)
    builder.add_node("revise", nodes.revise)
    builder.add_node("finalize", nodes.finalize)
    builder.add_edge(START, "research")
    builder.add_edge("research", "plan")
    builder.add_edge("plan", "review")
    builder.add_conditional_edges(
        "review",
        lambda state: "finalize" if state["review_status"] == "approve" else "revise",
        {"finalize": "finalize", "revise": "revise"},
    )
    builder.add_edge("revise", "review")
    builder.add_edge("finalize", END)
    return builder.compile(checkpointer=checkpointer)


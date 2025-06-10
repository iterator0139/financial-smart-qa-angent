from typing import TypedDict, Annotated, Sequence
import operator
from langgraph.graph import StateGraph, END
from query_understanding.qu_subgraph import build_qu_subgraph, QuState

# --- 1. Define the State ---
class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        query: The input user query.
        error: str
        segmented_words: list[str]
        entities: list[dict]
        rewritten_entities: list[dict]
        intent: list[str]
    """
    query: str
    error: str = None
    segmented_words: list[str] = None
    entities: list[dict] = None
    rewritten_entities: list[dict] = None
    intent: list[str] = None

def start_node(state: GraphState) -> GraphState:
    """Initialize the state with the query."""
    return {"query": state.get("query")}

def map_qu_state_to_graph_state(qu_state: QuState) -> GraphState:
    """Map the query understanding state back to the main graph state."""
    return {
        "query": qu_state.get("query"),
        "error": qu_state.get("error"),
        "segmented_words": qu_state.get("segmented_words"),
        "entities": qu_state.get("entities"),
        "rewritten_entities": qu_state.get("rewritten_entities"),
        "intent": qu_state.get("intent")
    }

# --- 5. Build the Graph ---
def build_graph():
    workflow = StateGraph(GraphState)

    # Add the start node
    workflow.add_node("start", start_node)

    # Create and add the query understanding subgraph
    qu_subgraph = build_qu_subgraph()
    workflow.add_subgraph("query_understanding", qu_subgraph, map_qu_state_to_graph_state)

    # Set the entry point
    workflow.set_entry_point("start")

    # Add edges
    workflow.add_edge("start", "query_understanding")
    workflow.add_edge("query_understanding", END)

    # Compile the graph
    app = workflow.compile()
    return app

if __name__ == '__main__':
    # Example usage
    graph_app = build_graph()

    # Test with a sample query
    test_query = "请帮我计算，在20210105，中信行业分类划分的一级行业为综合金融行业中，涨跌幅最大股票的股票代码是？涨跌幅是多少？"
    initial_state = {"query": test_query}

    print(f"Invoking graph with query: '{test_query}'")
    final_state = graph_app.invoke(initial_state)

    print("\n--- Final Graph State ---")
    print(f"Query: {final_state.get('query')}")
    print(f"Segmented Words: {final_state.get('segmented_words')}")
    print(f"Entities: {final_state.get('entities')}")
    print(f"Rewritten Entities: {final_state.get('rewritten_entities')}")
    print(f"Intent: {final_state.get('intent')}")
    if final_state.get('error'):
        print(f"Error: {final_state.get('error')}")

    print("\n--- Another Example ---")
    test_query_2 = "写一个python函数，用于计算斐波那契数列"
    initial_state_2 = {"query": test_query_2}
    print(f"Invoking graph with query: '{test_query_2}'")
    final_state_2 = graph_app.invoke(initial_state_2)
    print("\n--- Final Graph State 2 ---")
    print(f"Query: {final_state_2.get('query')}")
    print(f"Segmented Words: {final_state_2.get('segmented_words')}")
    print(f"Entities: {final_state_2.get('entities')}")
    print(f"Rewritten Entities: {final_state_2.get('rewritten_entities')}")
    print(f"Intent: {final_state_2.get('intent')}")
    if final_state_2.get('error'):
        print(f"Error: {final_state_2.get('error')}")


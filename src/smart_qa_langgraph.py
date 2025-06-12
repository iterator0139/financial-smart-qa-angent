import sys
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from typing import TypedDict, Annotated, Sequence
import operator
from langgraph.graph import StateGraph, END
from src.query_understanding.qu_subgraph import build_qu_subgraph, QuState
from src.config.config_manager import ConfigManager
from src.utils.logger import logger, get_logger

# Initialize config manager
config_manager = ConfigManager()
config_manager.init(project_root / "src" / "conf")

# Initialize logger
# 应用日志配置
if 'logging' in config_manager.get_config():
    log_config = config_manager.get_config()['logging']
    log_level = getattr(logging, log_config.get('level', 'INFO'))
    logger.init(
        log_level=log_level,
        max_bytes=log_config.get('max_bytes', 10*1024*1024),
        backup_count=log_config.get('backup_count', 5)
    )


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
    config: ConfigManager = None
    segment_model: str = None
    ner_model: str = None
    intent_model: str = None

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
        "intent": qu_state.get("intent"),
        "config": qu_state.get("config"),
        "segment_model": qu_state.get("segment_model"),
        "ner_model": qu_state.get("ner_model"),
        "intent_model": qu_state.get("intent_model")
    }

# --- 5. Build the Graph ---
def build_graph():
    workflow = StateGraph(GraphState)

    # Add the start node
    workflow.add_node("start", start_node)

    # Create the query understanding subgraph
    qu_subgraph = build_qu_subgraph()

    # Create a node that runs the query understanding subgraph
    def qu_node(state: GraphState):
        # Run the query understanding subgraph
        qu_result = qu_subgraph.invoke(state)
        # Map the results back to the main graph state
        return map_qu_state_to_graph_state(qu_result)

    # Add the query understanding node
    workflow.add_node("query_understanding", qu_node)

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
    
    # Get logger instance
    log = get_logger("main")
    
    # Test with a sample query
    test_query = "请查询在20211125日期，中信行业分类下机械一级行业中，当日收盘价波动最大（即最高价与最低价之差最大）的股票代码是什么？"
    initial_state = {
        "query": test_query, 
        "config": config_manager,
        "segment_model": config_manager.get("api.qwen.segment_model"),
        "ner_model": config_manager.get("api.qwen.ner_model"),
        "intent_model": config_manager.get("api.qwen.intent_model")
    }

    log.info(f"Invoking graph with query: '{test_query}'")
    final_state = graph_app.invoke(initial_state)

    log.info("\n--- Final Graph State ---")
    log.info(f"Query: {final_state.get('query')}")
    log.info(f"Segmented Words: {final_state.get('segmented_words')}")
    log.info(f"Entities: {final_state.get('entities')}")
    log.info(f"Intent: {final_state.get('intent')}")
    log.info(f"Config: {final_state.get('config')}")
    log.info(f"Segment Model: {final_state.get('segment_model')}")
    log.info(f"Ner Model: {final_state.get('ner_model')}")
    log.info(f"Intent Model: {final_state.get('intent_model')}")
    if final_state.get('error'):
        log.info(f"Error: {final_state.get('error')}")



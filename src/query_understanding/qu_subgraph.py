from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
import jieba
from src.models.qu_model import QuModel
from src.config.config_manager import ConfigManager
from langchain_core.prompts import ChatPromptTemplate
from src.prompts import WORD_SEGMENTATION_PROMPT, ENTITY_EXTRACTION_PROMPT, QUERY_UNDERSTANDING_PROMPT
from src.utils.logger import get_logger
from src.models.streaming_adapter import STREAMING_MODELS, StreamingLLMAdapter

log = get_logger()

# Define the state for query understanding subgraph
class QuState(TypedDict):
    """State for query understanding subgraph."""
    query: str
    segmented_words: list[str] = None
    entities: list[dict] = None
    intent: list[str] = None
    error: str = None
    completed_tasks: set[str] = None
    config: ConfigManager = None
    segment_model: str = None
    ner_model: str = None
    intent_model: str = None

# Node functions
def word_segmentation_node(state: QuState) -> QuState:
    qu_model = QuModel(state, "word_segmentation")
    result = qu_model.call_llm_by_aliyun_api()
    segmented_words = result.get("final_output")
    return {    
        **state,
        "segmented_words": segmented_words
    }

def ner_node(state: QuState) -> QuState:
    qu_model = QuModel(state, "ner")
    result = qu_model.call_llm_by_aliyun_api()
    entities = result.get("final_output")
    return {
        **state,
        "entities": entities
    }

def intent_recognition_node(state: QuState) -> QuState:
    qu_model = QuModel(state, "intent") 
    result = qu_model.call_llm_by_aliyun_api()
    intent = result.get("final_output")
    return {
        **state,
        "intent": intent
    }

def join_results_node(state: QuState) -> QuState:
    """Join results from all parallel nodes."""
    print("--- Step: Joining Results ---")
    completed_tasks = state.get("completed_tasks", set())
    expected_tasks = {"word_segmentation", "ner", "intent_recognition"}
    
    if not completed_tasks.issuperset(expected_tasks):
        missing = expected_tasks - completed_tasks
        return {**state, "error": f"Missing results from tasks: {missing}"}
    
    # All tasks completed successfully
    return state

def build_qu_subgraph() -> StateGraph:
    """Build the query understanding subgraph."""
    # Create the subgraph
    qu_graph = StateGraph(QuState)
    
    # Add all nodes
    qu_graph.add_node("word_segmentation", word_segmentation_node)
    qu_graph.add_node("ner", ner_node)
    qu_graph.add_node("intent_recognition", intent_recognition_node)
    qu_graph.add_node("join_results", join_results_node)
    
    # Set the entry point - we'll branch from here to all parallel nodes
    qu_graph.set_entry_point("word_segmentation")
    
    # Add edges for parallel execution
    # qu_graph.add_edge("word_segmentation", "join_results")
    # qu_graph.add_edge("word_segmentation", "ner")
    # qu_graph.add_edge("word_segmentation", "intent_recognition")
    # qu_graph.add_edge("ner", "join_results")
    # qu_graph.add_edge("intent_recognition", "join_results")
    # qu_graph.add_edge("join_results", END)

    qu_graph.add_edge("word_segmentation", END)
    
    # Compile the graph
    return qu_graph.compile() 
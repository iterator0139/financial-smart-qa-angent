from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
import jieba
from .qu_model import QuModel

# Define the state for query understanding subgraph
class QuState(TypedDict):
    """State for query understanding subgraph."""
    query: str
    segmented_words: list[str] = None
    entities: list[dict] = None
    intent: list[str] = None
    error: str = None
    completed_tasks: set[str] = None

# Node functions
def word_segmentation_node(state: QuState) -> QuState:
    """Node for word segmentation using jieba."""
    print("--- Step: Word Segmentation ---")
    query = state.get("query")
    if not query:
        return {**state, "error": "Query is missing in state."}
    
    try:
        segmented = jieba.lcut(query)
        completed = state.get("completed_tasks", set())
        completed.add("word_segmentation")
        return {
            **state, 
            "segmented_words": segmented,
            "completed_tasks": completed
        }
    except Exception as e:
        return {**state, "error": f"Error in word segmentation: {str(e)}"}

def ner_node(state: QuState) -> QuState:
    """Node for Named Entity Recognition."""
    print("--- Step: NER Entity Extraction ---")
    query = state.get("query")
    if not query:
        return {**state, "error": "Query is missing in state."}
    
    try:
        # Initialize QuModel for NER
        model = QuModel()
        # Extract entities using the model directly from query
        # In a real implementation, this would use a proper NER model
        entities = [{"text": word, "type": "UNKNOWN"} for word in query.split()]
        completed = state.get("completed_tasks", set())
        completed.add("ner")
        return {
            **state, 
            "entities": entities,
            "completed_tasks": completed
        }
    except Exception as e:
        return {**state, "error": f"Error in NER: {str(e)}"}

def intent_recognition_node(state: QuState) -> QuState:
    """Node for intent recognition."""
    print("--- Step: Intent Recognition ---")
    query = state.get("query")
    if not query:
        return {**state, "error": "Query is missing in state."}
    
    try:
        # Initialize QuModel for intent recognition
        model = QuModel()
        # Use the model to recognize intent directly from query
        intent = ["QUERY_INTENT"]  # Placeholder
        completed = state.get("completed_tasks", set())
        completed.add("intent_recognition")
        return {
            **state, 
            "intent": intent,
            "completed_tasks": completed
        }
    except Exception as e:
        return {**state, "error": f"Error in intent recognition: {str(e)}"}

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
    qu_graph.add_edge("word_segmentation", "join_results")
    qu_graph.add_edge("word_segmentation", "ner")
    qu_graph.add_edge("word_segmentation", "intent_recognition")
    qu_graph.add_edge("ner", "join_results")
    qu_graph.add_edge("intent_recognition", "join_results")
    qu_graph.add_edge("join_results", END)
    
    # Compile the graph
    return qu_graph.compile() 
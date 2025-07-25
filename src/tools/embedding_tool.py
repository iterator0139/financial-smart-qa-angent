from src.utils.logger import get_logger

log = get_logger()

def embedding_search(query: str) -> str:
    """
    Search the embedding index
    """
    log.info(f"[DEBUG] embedding_search: {query}")
    return "embedding_search"   
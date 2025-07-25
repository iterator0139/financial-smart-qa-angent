from src.utils.logger import get_logger

log = get_logger()

def search_es(query: str) -> str:
    """
    Search the ES index
    """
    log.info(f"[DEBUG] search_es: {query}")
    return "search_es"
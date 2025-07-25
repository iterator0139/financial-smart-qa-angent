from src.utils.logger import get_logger

log = get_logger()

def query_to_sql(query: str) -> str:
    """
    Query the DB to SQL
    """
    log.info(f"[DEBUG] query_to_sql: {query}")
    return "query_to_sql"
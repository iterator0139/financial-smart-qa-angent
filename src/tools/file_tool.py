from src.utils.logger import get_logger

log = get_logger()

def select_file(query: str) -> str:
    """
    Select the file
    """
    log.info(f"[DEBUG] select_file: {query}")
    return "select_file"
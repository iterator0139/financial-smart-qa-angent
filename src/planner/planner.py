import sys
from pathlib import Path
import logging
from typing import TypedDict, List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
import hashlib
from abc import ABC, abstractmethod
from langchain_core.tools import Tool
from langchain_core.agents import create_react_agent

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from src.utils.logger import get_logger

tools = [
    Tool(
        name="ESSearch",
        description="Search the ES index",
        func=search_es
    ),
    Tool(
        name="QueryDB",
        description="Query the DB",
        func=query_db
    ),
    Tool(
        name="EmbeddingSearch",
        description="Search the embedding index",
        func=embedding_search
    ),
    Tool(
        name="QueryToSQL",
        description="Query the DB to SQL",
        func=query_to_sql
    ),
    Tool(
        name="SelectFile",
        description="Select the file",
        func=select_file
    ),
    Tool(
        name="CheckDBInfo",
        description="Check the DB info",
        func=check_db_info
    ),
    Tool(
        name="CheckFileInfo",
        description="Check the file info",
        func=check_file_info
    ),
]


class ReActAgent(ABC):
    def __init__(self):
        self.agent = create_react_agent(tools, verbose=True)

    @abstractmethod
    def plan(self, query: str) -> str:
        pass
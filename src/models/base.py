from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseModel(ABC):
    """Base class for all model implementations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generate response from the model
        
        Args:
            prompt: Input prompt
            **kwargs: Additional model-specific parameters
            
        Returns:
            Dict containing the response and metadata
        """
        pass 
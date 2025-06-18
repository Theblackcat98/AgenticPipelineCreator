from abc import ABC, abstractmethod

class BaseTool(ABC):
    """Abstract Base Class for all framework-provided tools."""

    @abstractmethod
    def execute(self, inputs: dict, config: dict) -> dict:
        """
        Executes the tool's logic.
        
        Args:
            inputs (dict): A dictionary of resolved inputs for the tool.
            config (dict): The specific 'tool_config' from the pipeline JSON.
            
        Returns:
            A dictionary containing the tool's outputs.
        """
        pass

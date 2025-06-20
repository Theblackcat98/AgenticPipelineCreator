from abc import ABC, abstractmethod

class BaseTool(ABC):
    """Abstract Base Class for all framework-provided tools."""

    @abstractmethod
    def execute(self, inputs: dict, config: dict, agent_id: str = None, **kwargs) -> dict:
        """
        Executes the tool's logic.
        
        Args:
            inputs (dict): A dictionary of resolved inputs for the tool.
            config (dict): The specific 'tool_config' from the pipeline JSON.
            agent_id (str, optional): The ID of the agent executing this tool. Defaults to None.
            **kwargs: Additional keyword arguments that might be passed by the orchestrator,
                      such as 'invoke_llm', 'output_fields', 'pipeline_state'.
            
        Returns:
            A dictionary containing the tool's outputs.
        """
        pass

import json
import re
from typing import Callable, List, Dict, Any

# --- Framework Dependencies ---
# The orchestrator depends on the LLM client and the available built-in tools.
from llm.ollama_client import invoke_llm
from tools.built_in_tools import RegexParserTool, StructuredDataParserTool


class Orchestrator:
    """
    Manages the execution of an agentic pipeline defined in a configuration file.
    It handles state management, agent routing, and execution of different agent types.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the Orchestrator with a pipeline configuration.

        Args:
            config (dict): The parsed JSON configuration for the pipeline.
        """
        self.config = config
        self.agents = {agent['id']: agent for agent in config['agents']}
        self.routing = config['routing']
        self.start_agent_id = config['start_agent']
        self.final_outputs_map = config.get("final_outputs", {})

        # The Tool Registry maps tool names from the JSON config to their
        # corresponding Python class instances. This is how the framework
        # makes tools available to the user.
        self.tool_registry = {
            "RegexParserTool": RegexParserTool(),
            "StructuredDataParserTool": StructuredDataParserTool()
        }

    def _resolve_inputs(self, inputs_config: Dict[str, str], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolves an agent's input dependencies from the central pipeline state.
        If an input is not found, it interactively prompts the user for the value.

        Args:
            inputs_config (dict): The "inputs" block from an agent's config.
            state (dict): The current pipeline state.

        Returns:
            A dictionary of the resolved input values for the agent to use.
        """
        resolved_inputs = {}
        for local_name, source_path in inputs_config.items():
            if source_path not in state:
                # --- Interactive Input ---
                # If the required input is not in the state, prompt the user.
                print(f"🟡 Input needed for '{local_name}'.")
                user_value = input(f"Please provide a value for '{source_path}': ")
                
                # Update the central state so other agents can use this value
                state[source_path] = user_value
                
            # Resolve the value from the (potentially updated) state
            resolved_inputs[local_name] = state[source_path]
            
        return resolved_inputs

    def _parse_llm_list_output(self, text: str) -> List[str]:
        """
        Parses a raw string from an LLM into a clean Python list of strings.
        Handles numbered lists (e.g., "1. First item"), markdown lists ("- Item"),
        and simple newline-separated items.

        Args:
            text (str): The raw text output from the LLM.

        Returns:
            A list of strings.
        """
        # Split by common list formats (numbered, bulleted, or just newlines)
        items = re.split(r'\n\s*-\s*|\n\s*\d+\.\s*|\n', text)
        # Filter out any empty strings that result from the splitting process
        return [item.strip() for item in items if item.strip()]

    def run(self, initial_input: str) -> Dict[str, Any]:
        """
        Executes the entire pipeline from the start agent to the end.

        Args:
            initial_input (str): The initial data to feed into the pipeline.

        Returns:
            The complete, final pipeline state dictionary.
        """
        pipeline_state = {"pipeline.initial_input": initial_input}
        current_agent_id = self.start_agent_id
        
        print(f"🚀 Starting pipeline '{self.config['pipeline_name']}'...")

        while current_agent_id:
            print(f"\n▶️  Executing agent: {current_agent_id}")
            agent_config = self.agents[current_agent_id]
            agent_type = agent_config['type']
            
            resolved_inputs = self._resolve_inputs(agent_config['inputs'], pipeline_state)
            
            outputs = {}
            if agent_type == 'llm_agent':
                prompt = agent_config['prompt_template'].format(**resolved_inputs)
                llm_response = invoke_llm(agent_config['model'], prompt)

                # Check for and apply special output formatting
                if agent_config.get("output_format") == "list":
                    llm_response = self._parse_llm_list_output(llm_response)

                # Assume single output for llm_agent for simplicity in this MVP
                output_key = agent_config['outputs'][0]
                outputs = {output_key: llm_response}
            
            elif agent_type == 'tool_agent':
                tool_name = agent_config['tool_name']
                if tool_name not in self.tool_registry:
                    raise ValueError(f"Unknown tool '{tool_name}'. Available tools: {list(self.tool_registry.keys())}")
                
                tool_instance = self.tool_registry[tool_name]
                tool_config = agent_config.get('tool_config', {})
                
                # Execute the tool, providing it with necessary framework services
                # like the LLM client and its own output specification.
                outputs = tool_instance.execute(
                    inputs=resolved_inputs,
                    config=tool_config,
                    invoke_llm=invoke_llm,
                    output_fields=agent_config.get('outputs', [])
                )
            else:
                raise ValueError(f"Unsupported agent type: '{agent_type}'")
            
            print(f"✅ Agent '{current_agent_id}' produced outputs: {list(outputs.keys())}")
            # Update the central state with the agent's outputs.
            # This handles both single and multi-output tools.
            for key, value in outputs.items():
                state_key = f"{current_agent_id}.{key}"
                pipeline_state[state_key] = value
            
            # Determine the next agent based on the routing rules
            current_agent_id = self.routing.get(current_agent_id, {}).get("next")

        print("\n🏁 Pipeline finished.")
        return pipeline_state

    def get_final_outputs(self, final_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts and returns the final outputs as declared in the pipeline config.
        This provides a clean, predictable result for the calling script.

        Args:
            final_state (dict): The complete state dictionary after a pipeline run.

        Returns:
            A dictionary containing only the declared final outputs.
        """
        results = {}
        for key, source_path in self.final_outputs_map.items():
            results[key] = final_state.get(source_path, f"Error: Output '{source_path}' not found in final state")
        return results

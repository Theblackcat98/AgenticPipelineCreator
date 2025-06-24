import json
import re
from typing import Callable, List, Dict, Any

import app_config # Added import

# --- Framework Dependencies ---
# The orchestrator depends on the LLM client and the available built-in tools.
from llm.ollama_client import invoke_llm
from tools.built_in_tools import (
    RegexParserTool,
    StructuredDataParserTool,
    CodeExecutionTool,
    ConditionalRouterTool,
    DataAggregatorTool
)


class Orchestrator:
    """
    Manages the execution of an agentic pipeline defined in a configuration file.
    It handles state management, agent routing, and execution of different agent types.
    """

    def __init__(self, config: Dict[str, Any], test_mode: bool = False): # Add test_mode
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
        self.test_mode = test_mode # Store test_mode

        # The Tool Registry maps tool names from the JSON config to their
        # corresponding Python class instances. This is how the framework
        # makes tools available to the user.
        self.tool_registry = {
            "RegexParserTool": RegexParserTool(),
            "StructuredDataParserTool": StructuredDataParserTool(),
            "CodeExecutionTool": CodeExecutionTool(),
            "ConditionalRouterTool": ConditionalRouterTool(),
            "DataAggregatorTool": DataAggregatorTool()
        }

    def _get_value_from_path(self, data: Dict[str, Any], path: str) -> Any:
        """
        Retrieves a value from a nested dictionary using a dot-separated path.
        
        Args:
            data (dict): The dictionary to search.
            path (str): The dot-separated path (e.g., "agent_1.output.data").
            
        Returns:
            The value at the specified path, or None if not found.
        """
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value

    def _resolve_inputs(self, inputs_config: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolves an agent's input dependencies from the pipeline state or uses literal values.
        If a state reference is not found, it interactively prompts the user.

        Args:
            inputs_config (dict): The "inputs" block from an agent's config.
            state (dict): The current pipeline state.

        Returns:
            A dictionary of the resolved input values for the agent to use.
        """
        resolved_inputs = {}
        for local_name, source_path_or_value in inputs_config.items():
            if not isinstance(source_path_or_value, str):
                resolved_inputs[local_name] = source_path_or_value
                continue

            source_path = source_path_or_value
            
            # --- Direct State Access ---
            # --- Input Resolution Logic ---
            # First, check for special pipeline-level inputs like initial config.
            if source_path.startswith("pipeline.initial_input."):
                # The path is targeting a nested value within the initial_input config.
                # We need to extract the path within that object.
                # e.g., "pipeline.initial_input.topic" -> "topic"
                initial_input_path = ".".join(source_path.split('.')[2:])
                initial_input_data = state.get("pipeline.initial_input", {})
                value = self._get_value_from_path(initial_input_data, initial_input_path)
            else:
                # --- Direct State Access ---
                # For all other inputs, access the main pipeline state directly.
                # The pipeline state is a flat dictionary where keys are strings like
                # "agent_id.output_name". Direct lookup is sufficient.
                value = state.get(source_path)

            if value is None:
                if self.test_mode: # Check test_mode
                    raise ValueError(f"Input '{local_name}' (from '{source_path}') not found in state and test_mode is active. Pipeline cannot proceed without user input.")
                # --- Enhanced Interactive Input ---
                print(f"🟡 Input needed for '{local_name}'.")
                prompt_message = f"Please provide the value for '{source_path.replace('_', ' ')}': "
                user_value = input(prompt_message)
                state[source_path] = user_value # Update state
                value = user_value
            
            resolved_inputs[local_name] = value
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

    def run(self) -> Dict[str, Any]:
        """
        Executes the entire pipeline from the start agent to the end.
        It manages the pipeline state and orchestrates agent execution.

        Returns:
            The complete, final pipeline state dictionary.
        """
        # The initial input from the config is used to seed the state.
        initial_input_value = self.config.get("initial_input", None) # Default to None if not present
        if initial_input_value == "": # Treat empty string as if it's not provided for prompting
            initial_input_value = None

        pipeline_state = {"pipeline.initial_input": initial_input_value}
        current_agent_id = self.start_agent_id
        
        print(f"🚀 Starting pipeline '{self.config['pipeline_name']}'...")

        while current_agent_id:
            print(f"\n▶️  Executing agent: {current_agent_id}")
            agent_config = self.agents[current_agent_id]
            agent_type = agent_config['type']
            
            resolved_inputs = self._resolve_inputs(agent_config['inputs'], pipeline_state)
            
            outputs = {}
            # --- Agent Execution Logic ---
            # This logic determines how to execute the agent based on its type.
            # It supports standard LLM agents, tool agents, and a more flexible
            # format where the agent's type is the tool name itself.
            if agent_type == 'llm_agent':
                # app_config should be imported at the top of the file.
                # from app_config import DEFAULT_LLM_MODEL # For clarity in diff

                model_name_from_config = agent_config.get('model')
                if not model_name_from_config or model_name_from_config == "$DEFAULT_MODEL":
                    # This line assumes app_config is imported at the top of orchestrator.py
                    from app_config import DEFAULT_LLM_MODEL
                    model_to_use = DEFAULT_LLM_MODEL
                    if not model_to_use: # Should not happen with proper app_config
                        raise ValueError(f"LLM Agent '{current_agent_id}': Model not specified and no default model configured.")
                else:
                    model_to_use = model_name_from_config

                prompt = agent_config['prompt_template'].format(**resolved_inputs)
                llm_response = invoke_llm(model_to_use, prompt)

                if agent_config.get("output_format") == "list":
                    llm_response = self._parse_llm_list_output(llm_response)
                
                output_key = agent_config['outputs'][0]
                outputs = {output_key: llm_response}

            elif agent_type == 'tool_agent' or agent_type in self.tool_registry:
                # If the type is 'tool_agent', get the name from 'tool_name'.
                # Otherwise, the type itself is the tool name.
                tool_name = agent_config['tool_name'] if agent_type == 'tool_agent' else agent_type
                
                if tool_name not in self.tool_registry:
                    raise ValueError(f"Unknown tool '{tool_name}'. Available tools: {list(self.tool_registry.keys())}")
                
                tool_instance = self.tool_registry[tool_name]
                tool_config = agent_config.get('tool_config', {})
                
                # The 'pipeline_state' is passed to give tools read-only access
                # to the current state, which is crucial for loop controllers.
                outputs = tool_instance.execute(
                    inputs=resolved_inputs,
                    config=tool_config,
                    invoke_llm=invoke_llm,
                    output_fields=agent_config.get('outputs', []),
                    pipeline_state=pipeline_state,
                    agent_id=current_agent_id # Pass agent_id
                )
            else:
                raise ValueError(f"Unsupported agent type: '{agent_type}'")
            
            print(f"✅ Agent '{current_agent_id}' produced outputs: {list(outputs.keys())}")
            # --- State Management ---
            # Update the central state with the agent's outputs.
            for key, value in outputs.items():
                # Exclude special keys from being added to the main state namespace.
                if key not in ['_next_step_id', '_update_state']:
                    state_key = f"{current_agent_id}.{key}"
                    pipeline_state[state_key] = value

            # Handle direct state updates from tools like the router.
            if '_update_state' in outputs and isinstance(outputs['_update_state'], dict):
                for state_key, state_value in outputs['_update_state'].items():
                    # Namespace the state update with the current agent's ID
                    # unless the key is already a special non-namespaced key (e.g. if a tool directly manipulates other agent's outputs by full name)
                    # For now, assume keys in _update_state are tool-local and need namespacing.
                    # A more sophisticated check could see if state_key already contains a '.'
                    if '.' not in state_key: # Simple check: if not already namespaced
                        namespaced_state_key = f"{current_agent_id}.{state_key}"
                        pipeline_state[namespaced_state_key] = state_value
                    else: # Assume it's an advanced case of direct state manipulation with full path
                        pipeline_state[state_key] = state_value
            
            # --- Clear Agent Outputs Instruction ---
            # Check if the tool requested to clear the outputs of specific agents.
            # This is used by the ConditionalRouterTool to force re-execution of branches.
            if '_clear_agent_outputs' in outputs:
                agent_ids_to_clear = outputs.get('_clear_agent_outputs', [])
                if agent_ids_to_clear:
                    keys_to_delete = set()
                    for agent_id in agent_ids_to_clear:
                        for state_key in pipeline_state:
                            if state_key.startswith(f"{agent_id}."):
                                keys_to_delete.add(state_key)
                    
                    if keys_to_delete:
                        print(f"🧹 Clearing outputs for agents: {list(agent_ids_to_clear)}...")
                        for key in keys_to_delete:
                            if key in pipeline_state:
                                del pipeline_state[key]

            # --- Dynamic Routing ---
            # Check if the tool's output has overridden the next step.
            # This is how the ConditionalRouterTool works.
            if '_next_step_id' in outputs and outputs['_next_step_id']:
                current_agent_id = outputs['_next_step_id']
            else:
                # Determine the next agent based on the static routing rules
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
            value = None
            if source_path.startswith("pipeline.initial_input."):
                # Path is like "pipeline.initial_input.some_key"
                initial_input_object_path = ".".join(source_path.split('.')[2:])
                initial_input_data = final_state.get("pipeline.initial_input")
                if isinstance(initial_input_data, dict):
                    value = self._get_value_from_path(initial_input_data, initial_input_object_path)
                elif initial_input_object_path == "" and initial_input_data is not None: # Requesting the whole initial_input object
                    value = initial_input_data

            elif source_path == "pipeline.initial_input":
                # Path is exactly "pipeline.initial_input"
                value = final_state.get("pipeline.initial_input")
            else:
                # Path is like "agent_id.output_key"
                value = final_state.get(source_path)

            if value is None:
                results[key] = f"Error: Output '{source_path}' not found in final state"
            else:
                results[key] = value
        return results

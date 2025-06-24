import re
import json
from .base_tool import BaseTool
from typing import Callable, List
import app_config # Added import

# --- Tool #1: Regex Parser ---
# The orchestrator tries to import this, so it must be defined here.
class RegexParserTool(BaseTool):
    """
    A generic tool to extract data from text using named regex patterns.
    """
    def execute(self, inputs: dict, config: dict, **kwargs) -> dict:
        text_to_parse = inputs.get("text_to_parse")
        if not text_to_parse:
            raise ValueError("RegexParserTool requires 'text_to_parse' in inputs.")

        patterns = config.get("patterns", {})
        body_pattern_config = config.get("body_pattern", {})
        results = {}

        for key, pattern in patterns.items():
            match = re.search(pattern, text_to_parse)
            results[key] = match.group(1).strip() if match else "Not found"
        
        if body_pattern_config:
            pattern = body_pattern_config.get("pattern")
            flags_str = body_pattern_config.get("flags", [])
            
            re_flags = 0
            for flag in flags_str:
                if hasattr(re, flag):
                    re_flags |= getattr(re, flag)
            
            match = re.search(pattern, text_to_parse, re_flags)
            results["body"] = match.group(1).strip() if match else ""

        return results


# --- Tool #2: Structured Data Parser (LLM-Powered) ---
# This is the class definition that was likely missing or misspelled.
class StructuredDataParserTool(BaseTool):
    """
    An LLM-powered tool to extract structured data from natural language.
    It takes a request and a list of desired fields, and returns a JSON object.
    """
    def execute(self, inputs: dict, config: dict, invoke_llm: Callable, output_fields: List[str], **kwargs) -> dict:
        """
        Uses an LLM to parse the input text.
        """
        request_text = inputs.get("natural_language_request")
        if not request_text:
            raise ValueError("StructuredDataParserTool requires 'natural_language_request' in inputs.")

        # Import app_config at the top of the file or here if it's a one-off
        # For now, let's assume it will be at the top of the file.
        # import app_config # This should be at the top of tools/built_in_tools.py

        model_in_config = config.get("model")
        if model_in_config:
            model = model_in_config
        else:
            # app_config should be imported at the top of the file
            # For this diff, we are showing the conceptual change.
            # The actual import app_config will be added separately if not present.
            from app_config import DEFAULT_STRUCTURED_DATA_MODEL # Direct import for clarity here
            model = DEFAULT_STRUCTURED_DATA_MODEL
            if not model: # Should not happen if app_config has a fallback
                 raise ValueError("StructuredDataParserTool: Model not found in tool_config and no default model configured.")


        instructions = config.get("instructions", "Extract the requested fields.")
        # No longer need to check 'if not model:' here as it's resolved or would have raised from app_config if it were empty.

        prompt = (
            f"You are an expert data extraction tool. Your sole purpose is to "
            f"extract structured data from a user's request and respond ONLY with a valid JSON object. "
            f"\n\nExtraction Instructions: {instructions}"
            f"\nDesired JSON keys: {', '.join(output_fields)}"
            f"\n\nUser Request: \"{request_text}\""
            f"\n\nJSON Output:"
        )

        response_str = invoke_llm(model, prompt)

        try:
            json_match = re.search(r'\{.*\}', response_str, re.DOTALL)
            if json_match:
                response_str = json_match.group(0)
            
            parsed_json = json.loads(response_str)
            
            for field in output_fields:
                if field not in parsed_json:
                    parsed_json[field] = "Not found"
            
            return parsed_json
        except json.JSONDecodeError:
            print(f"Warning: StructuredDataParserTool failed to parse LLM response into JSON: {response_str}")
            return {field: "Error: Failed to parse" for field in output_fields}

# --- Tool #3: Code Execution Tool ---
class CodeExecutionTool(BaseTool):
    """
    Executes a snippet of Python code.
    WARNING: This tool is powerful and executes arbitrary code. It has been modified
    to restrict access to globals and builtins for security reasons.
    It should still be used with extreme caution and only with trusted code snippets
    in a secure, isolated environment.
    """
    def execute(self, inputs: dict, config: dict, **kwargs) -> dict:
        code_snippet = config.get("code")
        if not code_snippet:
            raise ValueError("CodeExecutionTool requires 'code' in its tool_config.")

        # Prepare a restricted global scope
        restricted_globals = {
            "__builtins__": {
                "print": print,
                "len": len,
                "range": range,
                "int": int,
                "float": float,
                "str": str,
                "list": list,
                "dict": dict,
                "set": set,
                "True": True,
                "False": False,
                "None": None,
                # Add other safe builtins as needed
            },
            "json": json, # Allow json module for data manipulation
            # "math": math, # Example: allow math module if needed
        }
        
        # The local scope will have 'inputs' and 'results' dictionary
        local_scope = {"inputs": inputs, "results": {}}
        
        # The code snippet should assign its output to a variable, e.g., 'output'.
        # We will have the exec populate the 'output' key in the 'results' dictionary.
        # This structure avoids direct modification of the 'output' variable name in the user's code.
        full_code = f"""
# The user's code snippet is placed here:
{code_snippet}

# The user's script should assign its result to a variable named 'output'.
# We capture it into the 'results' dictionary, which is in our local_scope.
results['output'] = output
"""
        try:
            exec(full_code, restricted_globals, local_scope)
            # Retrieve the result from the 'results' dictionary in local_scope
            return local_scope.get("results", {}).get("output", {"error": "Output variable 'output' not found in executed code."})
        except Exception as e:
            return {"error": f"Error executing code: {str(e)}"}


# --- Tool #4: Conditional Router Tool ---
class ConditionalRouterTool(BaseTool):
    """
    Directs the pipeline's execution flow based on specified conditions
    or manages looping constructs.
    It returns a special '_next_step_id' output that the orchestrator uses
    to determine the next agent to execute.
    It can also return '_update_state' to modify the pipeline_state (e.g., for loop counters
    and data accumulation) and '_clear_agent_outputs' to signal the orchestrator
    to clear outputs of specified agents before the next loop iteration.
    """
    def execute(self, inputs: dict, config: dict, pipeline_state: dict, agent_id: str = None, **kwargs) -> dict: # Add agent_id
        """
        Directs execution flow. It can act as a simple conditional branch or
        as a stateful loop controller with data aggregation.

        Args:
            inputs (dict): Inputs to this tool, resolved by the orchestrator.
            config (dict): Configuration specific to this tool instance from the pipeline JSON.
                           Expected to contain 'loop_config' or 'condition_groups'.
            pipeline_state (dict): The current state of the entire pipeline. Used for reading
                                   loop counters, accumulated data, and potentially for
                                   conditions if they refer to broader pipeline state.
            agent_id (str, optional): The ID of the agent executing this tool. Used for
                                      namespacing state variables (counters, accumulators)
                                      to avoid collisions if multiple router tools are used.

        Looping Logic (if 'loop_config' is present in config):
        - State Keys: Loop counter and accumulator lists are stored in `pipeline_state`
          using keys namespaced by `agent_id` (e.g., "my_router_agent.loop_counter").
        - Initialization: If a counter or accumulator list is not found in `pipeline_state`,
          it's typically initialized (e.g., counter to 0, accumulator to an empty list).
        - Data Aggregation: On each call, specified input values are appended to their
          respective accumulator lists. This updated list is part of the `_update_state`
          returned to the orchestrator. This step runs *before* the loop condition is checked.
        - Loop Control: Compares the current loop counter (from `pipeline_state`) against
          the configured total number of iterations.
            - If continuing: Increments the counter. Returns `_next_step_id` pointing to
              the start of the loop body, `_update_state` with the new counter value and
              updated accumulator lists, and `_clear_agent_outputs` listing agents in the
              loop body whose outputs should be cleared by the orchestrator.
            - If terminating: Returns `_next_step_id` pointing to the agent to execute
              after the loop (from `else_execute_step` in `loop_config`). Also returns
              the final accumulated data directly in its output (e.g., "all_my_items": [...]).
        """
        loop_config = config.get("loop_config")

        # --- Stateful Looping Behavior ---
        if loop_config:
            # Configuration for the loop
            total_iterations_config_value = loop_config.get("total_iterations_from") # Can be int or key name from inputs
            loop_body_start_id = loop_config.get("loop_body_start_id") # Agent ID to jump to for loop body
            counter_name = loop_config.get("counter_name")             # Base name for the loop counter state key
            accumulators = loop_config.get("accumulators", {})         # Dict mapping {output_name: input_source_key}
            loop_body_agents = loop_config.get("loop_body_agents", []) # List of agent IDs in the loop body

            # Namespace the counter key to be specific to this router agent instance
            namespaced_counter_key = f"{agent_id}.{counter_name}" if agent_id and counter_name else counter_name
            if not namespaced_counter_key:
                 raise ValueError(f"ConditionalRouterTool ({agent_id}): 'counter_name' must be defined in loop_config.")


            # Retrieve current loop count from pipeline_state, defaulting to 0 if not found (first iteration)
            current_count = pipeline_state.get(namespaced_counter_key, 0)

            # Determine total iterations required
            total_iterations = 0
            if isinstance(total_iterations_config_value, int):
                total_iterations = total_iterations_config_value
            elif isinstance(total_iterations_config_value, str): # Key name to get from 'inputs'
                if not total_iterations_config_value: # handle empty string case
                    raise ValueError(f"ConditionalRouterTool ({agent_id}): 'total_iterations_from' key name cannot be empty if it's a string.")
                total_iterations_value_from_inputs = inputs.get(total_iterations_config_value)
                if total_iterations_value_from_inputs is None:
                    raise ValueError(f"Looping error for agent '{agent_id}': Total iterations key '{total_iterations_config_value}' not found in inputs. Ensure it's defined in the agent's 'inputs'. Current inputs: {list(inputs.keys())}")
                try:
                    total_iterations = int(total_iterations_value_from_inputs)
                except ValueError:
                    raise ValueError(f"Looping error for agent '{agent_id}': Input '{total_iterations_config_value}' (resolved to '{total_iterations_value_from_inputs}') must be an integer.")
            else:
                raise ValueError(f"Looping error for agent '{agent_id}': 'total_iterations_from' in loop_config must be an integer or a string key name. Got type {type(total_iterations_config_value)}.")

            # --- Data Aggregation for current iteration ---
            # This step collects data from the current 'inputs' and appends to accumulator lists.
            # The resulting lists are stored in 'updated_state', which, if the loop continues,
            # will be returned via '_update_state' for the orchestrator to merge into the main pipeline_state.
            # If the loop terminates, this 'updated_state' provides the final accumulated values.
            updated_state = {} # Holds data to be updated in pipeline_state OR used in final output
            if accumulators:
                for output_key, input_source_key in accumulators.items():
                    if input_source_key in inputs:
                        value_to_accumulate = inputs[input_source_key]
                        # Accumulate only if the value is meaningful (not None, not empty string for this example)
                        if value_to_accumulate is not None and value_to_accumulate != "":
                            namespaced_acc_key = f"{agent_id}.{output_key}" if agent_id and output_key else output_key
                            if not namespaced_acc_key:
                                 raise ValueError(f"ConditionalRouterTool ({agent_id}): Accumulator output key cannot be empty.")

                            current_list = pipeline_state.get(namespaced_acc_key, [])
                            if not isinstance(current_list, list):
                                print(f"Warning: Accumulator '{namespaced_acc_key}' in pipeline_state was not a list (found {type(current_list)}). Re-initializing as empty list.")
                                current_list = []

                            new_list = current_list + [value_to_accumulate]
                            updated_state[output_key] = new_list # Store with non-namespaced key for _update_state
                    else:
                        print(f"Warning for agent '{agent_id}': Accumulator source key '{input_source_key}' for output '{output_key}' not found in current inputs. Skipping accumulation for this item.")

            # --- Loop Control Decision ---
            if current_count < total_iterations:
                # Continue Loop:
                # Increment counter for the *next* iteration.
                next_count = current_count + 1
                # Add the new counter value to updated_state.
                # The orchestrator will use 'agent_id' to namespace this 'counter_name' in pipeline_state.
                if counter_name: # Only update counter if a name is provided
                    updated_state[counter_name] = next_count
                return {
                    "_next_step_id": loop_body_start_id,
                    "_update_state": updated_state, # Contains new counter and new accumulator lists
                    "_clear_agent_outputs": loop_body_agents
                }
            else:
                # Terminate Loop:
                # Prepare the final output of this tool agent.
                # It should include the next step ID (if any) and the final accumulated data.
                final_output = {"_next_step_id": config.get("else_execute_step")}

                # Populate final_output with accumulated data.
                # These are taken from the 'updated_state' computed in the Data Aggregation
                # phase of *this current call*, which includes the item from the last iteration.
                for acc_output_key in accumulators.keys():
                    if acc_output_key in updated_state:
                        final_output[acc_output_key] = updated_state[acc_output_key]
                    else:
                        # Fallback: if not in current updated_state (e.g., input was missing or empty for the last item),
                        # get the list as it was from pipeline_state (before this call's aggregation attempt).
                        namespaced_acc_key = f"{agent_id}.{acc_output_key}" if agent_id and acc_output_key else acc_output_key
                        if not namespaced_acc_key: continue # Should have been caught by earlier check if output_key was empty
                        final_output[acc_output_key] = pipeline_state.get(namespaced_acc_key, [])
                return final_output

        # --- Standard Conditional Routing (if not a loop or loop has finished) ---
        condition_groups = config.get("condition_groups", [])
        else_step = config.get("else_execute_step")

        for group in condition_groups:
            if_condition = group.get("if", {})
            then_step = group.get("then_execute_step")
            variable = if_condition.get("variable")
            operator = if_condition.get("operator")
            value = if_condition.get("value")

            if not all([variable, operator, then_step]):
                continue

            actual_value = inputs.get(variable)
            match = False
            if operator == "equals" and actual_value == value: match = True
            elif operator == "not_equals" and actual_value != value: match = True
            elif operator == "contains" and isinstance(actual_value, (str, list, dict)) and value in actual_value: match = True
            elif operator == "not_contains" and isinstance(actual_value, (str, list, dict)) and value not in actual_value: match = True
            elif operator == "gt" and isinstance(actual_value, (int, float)) and actual_value > value: match = True
            elif operator == "lt" and isinstance(actual_value, (int, float)) and actual_value < value: match = True

            if match:
                return {"_next_step_id": then_step}

        if else_step:
            return {"_next_step_id": else_step}

        return {}


# --- Tool #5: Data Aggregator Tool ---
class DataAggregatorTool(BaseTool):
    """
    Merges outputs from multiple previous steps into a single dictionary.
    """
    def execute(self, inputs: dict, config: dict, **kwargs) -> dict:
        """
        The 'inputs' for this tool are expected to be the direct outputs
        of the steps specified in the config.
        """
        sources = config.get("sources", {})
        aggregated_data = {}

        for new_key, source_key in sources.items():
            if source_key in inputs:
                aggregated_data[new_key] = inputs[source_key]
            else:
                aggregated_data[new_key] = f"Source key '{source_key}' not found in inputs."

        return aggregated_data

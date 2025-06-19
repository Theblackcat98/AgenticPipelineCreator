import re
import json
from .base_tool import BaseTool
from typing import Callable, List

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

        model = config.get("model")
        instructions = config.get("instructions", "Extract the requested fields.")
        if not model:
            raise ValueError("StructuredDataParserTool requires 'model' in its tool_config.")

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
    WARNING: This tool is powerful and executes arbitrary code. It should be used with extreme caution
    and only with trusted code snippets in a secure environment.
    """
    def execute(self, inputs: dict, config: dict, **kwargs) -> dict:
        code_snippet = config.get("code")
        if not code_snippet:
            raise ValueError("CodeExecutionTool requires 'code' in its tool_config.")

        # Prepare the local scope for exec
        local_scope = {"inputs": inputs}
        
        # Capture the output of the exec call
        # We can redirect stdout to capture prints, but for returning a value,
        # we'll have exec populate a 'result' dictionary.
        result_scope = {}
        
        # The code snippet should assign its output to a variable, e.g., 'output'.
        # We will pass our result_scope to be populated.
        full_code = f"""
import json
# The user's code snippet is placed here
{code_snippet}
# The user's script should assign its result to a variable named 'output'
# We capture it into our results dictionary
results['output'] = output
"""
        try:
            exec(full_code, {"inputs": inputs}, result_scope)
            return result_scope.get("output", {})
        except Exception as e:
            return {"error": f"Error executing code: {str(e)}"}


# --- Tool #4: Conditional Router Tool ---
class ConditionalRouterTool(BaseTool):
    """
    Directs the pipeline's execution flow based on specified conditions.
    It returns a special '_next_step_id' output that the orchestrator can use
    to determine the next step.
    """
    def execute(self, inputs: dict, config: dict, pipeline_state: dict, **kwargs) -> dict:
        """
        Directs execution flow. It can act as a simple conditional branch or
        as a stateful loop controller with data aggregation.

        Looping Logic:
        - The tool checks for a 'loop_config' in its configuration.
        - It uses 'pipeline_state' to track the loop's counter and accumulated data.
        - It initializes the counter and accumulator lists if they are not in the state.
        - On each run, it appends data to the lists, increments the counter, and
          determines the next step.
        - When the loop finishes, it returns the aggregated data lists.
        """
        loop_config = config.get("loop_config")

        # --- Stateful Looping Behavior ---
        if loop_config:
            total_iterations_key = loop_config.get("total_iterations_from")
            loop_body_start_id = loop_config.get("loop_body_start_id")
            counter_name = loop_config.get("counter_name")
            accumulators = loop_config.get("accumulators", {})

            # Initialize counter and accumulators in pipeline_state if not present
            if counter_name not in pipeline_state:
                pipeline_state[counter_name] = 0
            for key in accumulators.keys():
                if key not in pipeline_state:
                    pipeline_state[key] = []
            
            current_count = pipeline_state.get(counter_name, 0)
            total_iterations = inputs.get(total_iterations_key)

            if total_iterations is None:
                raise ValueError(f"Looping error: Total iterations key '{total_iterations_key}' not found in inputs.")

            # --- Data Aggregation ---
            # This happens before the check, so on the first run (count=0), it still collects initial data.
            updated_state = {}
            for output_key, input_source in accumulators.items():
                if input_source in inputs:
                    # Ensure the list exists before appending
                    if output_key not in pipeline_state:
                        pipeline_state[output_key] = []
                    
                    # Append the new value to the list
                    new_list = pipeline_state[output_key] + [inputs[input_source]]
                    updated_state[output_key] = new_list
                else:
                    # If an expected input is missing, you might want to handle it,
                    # e.g., by appending a null value or raising an error.
                    # Here, we'll just note it and continue.
                    print(f"Warning: Accumulator source '{input_source}' not found in inputs for '{output_key}'.")


            # --- Loop Control ---
            if current_count < total_iterations:
                # Continue loop: increment counter and go to loop body
                next_count = current_count + 1
                updated_state[counter_name] = next_count
                return {
                    "_next_step_id": loop_body_start_id,
                    "_update_state": updated_state
                }
            else:
                # End loop: return aggregated data and proceed to the next step
                final_output = {"_next_step_id": config.get("else_execute_step")}
                for key in accumulators.keys():
                    final_output[key] = pipeline_state.get(key, [])
                return final_output

        # --- Standard Conditional Routing ---
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

import pytest
from unittest.mock import MagicMock, patch
from tools.built_in_tools import (
    RegexParserTool,
    StructuredDataParserTool,
    CodeExecutionTool,
    ConditionalRouterTool,
    DataAggregatorTool
)

# --- Tests for RegexParserTool ---

def test_regex_parser_tool_simple_extraction():
    tool = RegexParserTool()
    inputs = {"text_to_parse": "Name: John Doe, Age: 30"}
    config = {
        "patterns": {
            "name": r"Name: (\w+ \w+)",
            "age": r"Age: (\d+)"
        }
    }
    expected_output = {"name": "John Doe", "age": "30"}
    assert tool.execute(inputs, config) == expected_output

def test_regex_parser_tool_pattern_not_found():
    tool = RegexParserTool()
    inputs = {"text_to_parse": "Name: John Doe"}
    config = {
        "patterns": {
            "name": r"Name: (\w+ \w+)",
            "email": r"Email: (\S+)"
        }
    }
    # If a pattern is not found, the current implementation returns "Not found"
    expected_output = {"name": "John Doe", "email": "Not found"}
    assert tool.execute(inputs, config) == expected_output

def test_regex_parser_tool_body_pattern():
    tool = RegexParserTool()
    inputs = {"text_to_parse": "HEADER\n\nThis is the main body content.\nFOOTER"}
    config = {
        "patterns": {}, # No specific field patterns for this test
        "body_pattern": {
            "pattern": r"HEADER\n\n(.*?)\nFOOTER",
            "flags": ["DOTALL"] # Example of using a flag like re.DOTALL
        }
    }
    expected_output = {"body": "This is the main body content."}
    result = tool.execute(inputs, config)
    assert result.get("body") == expected_output["body"]


def test_regex_parser_tool_body_pattern_no_match():
    tool = RegexParserTool()
    inputs = {"text_to_parse": "HEADER\n\nThis is not matching.\nOTHER_FOOTER"}
    config = {
        "body_pattern": {
            "pattern": r"HEADER\n\n(.*?)\nFOOTER", # Expects "FOOTER"
            "flags": ["DOTALL"]
        }
    }
    expected_output = {"body": ""} # Expects empty string if no match
    assert tool.execute(inputs, config) == expected_output


def test_regex_parser_tool_missing_text_input():
    tool = RegexParserTool()
    inputs = {} # Missing 'text_to_parse'
    config = {"patterns": {"name": "Name: (.*)"}}
    with pytest.raises(ValueError, match="RegexParserTool requires 'text_to_parse' in inputs."):
        tool.execute(inputs, config)

# --- Tests for StructuredDataParserTool ---

@pytest.fixture
def mock_invoke_llm():
    return MagicMock()

def test_structured_data_parser_success(mock_invoke_llm):
    tool = StructuredDataParserTool()
    inputs = {"natural_language_request": "Extract John Doe, age 30."}
    config = {"model": "test-model", "instructions": "Extract name and age."}
    output_fields = ["name", "age"]

    mock_invoke_llm.return_value = '{"name": "John Doe", "age": 30}'

    expected_output = {"name": "John Doe", "age": 30}
    result = tool.execute(inputs, config, invoke_llm=mock_invoke_llm, output_fields=output_fields)
    assert result == expected_output
    mock_invoke_llm.assert_called_once()
    # We can also assert the prompt contents if needed by inspecting mock_invoke_llm.call_args

def test_structured_data_parser_llm_returns_malformed_json(mock_invoke_llm):
    tool = StructuredDataParserTool()
    inputs = {"natural_language_request": "Data."}
    config = {"model": "test-model"}
    output_fields = ["field1"]

    mock_invoke_llm.return_value = '{"field1": "value",,}' # Malformed JSON with extra comma

    expected_output = {"field1": "Error: Failed to parse"}
    result = tool.execute(inputs, config, invoke_llm=mock_invoke_llm, output_fields=output_fields)
    assert result == expected_output

def test_structured_data_parser_llm_returns_non_json_string(mock_invoke_llm):
    tool = StructuredDataParserTool()
    inputs = {"natural_language_request": "Data."}
    config = {"model": "test-model"}
    output_fields = ["field1"]

    mock_invoke_llm.return_value = 'This is not JSON.'

    expected_output = {"field1": "Error: Failed to parse"}
    result = tool.execute(inputs, config, invoke_llm=mock_invoke_llm, output_fields=output_fields)
    assert result == expected_output

def test_structured_data_parser_missing_fields_in_llm_response(mock_invoke_llm):
    tool = StructuredDataParserTool()
    inputs = {"natural_language_request": "Extract name: John."}
    config = {"model": "test-model"}
    output_fields = ["name", "email"] # Expects email as well

    mock_invoke_llm.return_value = '{"name": "John"}' # LLM doesn't return email

    # The tool should add missing fields with "Not found"
    expected_output = {"name": "John", "email": "Not found"}
    result = tool.execute(inputs, config, invoke_llm=mock_invoke_llm, output_fields=output_fields)
    assert result == expected_output

def test_structured_data_parser_llm_response_with_markdown_fences(mock_invoke_llm):
    tool = StructuredDataParserTool()
    inputs = {"natural_language_request": "Extract data."}
    config = {"model": "test-model"}
    output_fields = ["data_point"]

    mock_invoke_llm.return_value = '```json\n{"data_point": "value"}\n```'

    expected_output = {"data_point": "value"}
    result = tool.execute(inputs, config, invoke_llm=mock_invoke_llm, output_fields=output_fields)
    assert result == expected_output

def test_structured_data_parser_missing_request_input():
    tool = StructuredDataParserTool()
    inputs = {} # Missing 'natural_language_request'
    config = {"model": "test-model"}
    output_fields = ["field1"]
    with pytest.raises(ValueError, match="StructuredDataParserTool requires 'natural_language_request' in inputs."):
        tool.execute(inputs, config, invoke_llm=MagicMock(), output_fields=output_fields)

def test_structured_data_parser_missing_model_config():
    tool = StructuredDataParserTool()
    inputs = {"natural_language_request": "Data."}
    config = {} # Missing 'model'
    output_fields = ["field1"]
    # Patch app_config.DEFAULT_STRUCTURED_DATA_MODEL to be None for this test
    # to ensure the tool raises ValueError if no model can be resolved at all.
    with patch('app_config.DEFAULT_STRUCTURED_DATA_MODEL', None):
        with pytest.raises(ValueError, match="StructuredDataParserTool: Model not found in tool_config and no default model configured."):
            tool.execute(inputs, config, invoke_llm=MagicMock(), output_fields=output_fields)

# --- Tests for CodeExecutionTool ---

def test_code_execution_tool_success():
    tool = CodeExecutionTool()
    inputs = {"value": 5}
    # User's code snippet just needs to define 'output'
    code_snippet = """
data = inputs['value'] * 2
output = {'final_value': data}
"""
    config = {"code": code_snippet}
    expected_output = {"final_value": 10}
    actual_output = tool.execute(inputs=inputs, config=config)
    assert actual_output == expected_output

def test_code_execution_tool_script_error():
    tool = CodeExecutionTool()
    inputs = {}
    # This code snippet will cause a ZeroDivisionError. 'output' is defined.
    code_snippet = """
output = 1 / 0
"""
    config = {"code": code_snippet}
    expected_error_fragment = "Error executing code: division by zero"
    result = tool.execute(inputs, config)
    assert "error" in result
    assert expected_error_fragment in result["error"]

def test_code_execution_tool_missing_code_config():
    tool = CodeExecutionTool()
    inputs = {}
    config = {} # Missing 'code'
    with pytest.raises(ValueError, match="CodeExecutionTool requires 'code' in its tool_config."):
        tool.execute(inputs, config)

def test_code_execution_tool_no_output_variable_defined_by_user_code(): # Renamed for clarity
    tool = CodeExecutionTool()
    inputs = {"value": 5}
    # This code snippet performs a calculation but doesn't assign to 'output'.
    code_snippet = """
data = inputs['value'] * 2
# No assignment to 'output' by the user's code.
"""
    config = {"code": code_snippet}
    # The tool's wrapper `results['output'] = output` will cause a NameError if 'output' isn't defined.
    expected_error_fragment = "Error executing code: name 'output' is not defined"
    result = tool.execute(inputs=inputs, config=config)
    assert "error" in result
    assert expected_error_fragment in result["error"]

# New Security Tests for CodeExecutionTool

def test_code_execution_tool_disallowed_builtin_open():
    tool = CodeExecutionTool()
    inputs = {}
    # Attempt to use 'open', which should not be in restricted_globals.__builtins__
    code_snippet = "output = open('test.txt', 'w')"
    config = {"code": code_snippet}
    result = tool.execute(inputs, config)
    assert "error" in result
    # Error might be "NameError: name 'open' is not defined" or similar security exception
    assert "name 'open' is not defined" in result["error"]

def test_code_execution_tool_disallowed_builtin_eval():
    tool = CodeExecutionTool()
    inputs = {}
    code_snippet = "output = eval('1+1')"
    config = {"code": code_snippet}
    result = tool.execute(inputs, config)
    assert "error" in result
    assert "name 'eval' is not defined" in result["error"]

def test_code_execution_tool_disallowed_module_os():
    tool = CodeExecutionTool()
    inputs = {}
    # Attempt to import and use 'os' module
    code_snippet = """
import os
output = os.getcwd()
"""
    config = {"code": code_snippet}
    result = tool.execute(inputs, config)
    assert "error" in result
    # Error will likely be "No module named 'os'" because 'os' is not in restricted_globals
    # or potentially a more specific security error if the import itself is blocked differently.
    # Given current implementation, it's `exec(full_code, restricted_globals, local_scope)`
    # `import os` within `full_code` will fail if `os` is not in `restricted_globals`.
    # The actual error is that `__import__` is not available in the restricted builtins.
    assert "Error executing code: __import__ not found" in result["error"] or \
           "Error executing code: name '__import__' is not defined" in result["error"] # Py 3.12 vs older


def test_code_execution_tool_allowed_builtin_len_and_inputs_access():
    tool = CodeExecutionTool()
    inputs = {"data_list": [1, 2, 3]}
    # Use allowed 'len' and access 'inputs'
    code_snippet = """
output = {"length": len(inputs["data_list"])}
"""
    config = {"code": code_snippet}
    expected_output = {"length": 3}
    assert tool.execute(inputs, config) == expected_output

def test_code_execution_tool_allowed_module_json():
    tool = CodeExecutionTool()
    inputs = {"my_dict": {"key": "value", "number": 42}}
    # Use allowed 'json' module (json.dumps)
    # The 'json' module is added to restricted_globals directly.
    code_snippet = """
output = json.dumps(inputs["my_dict"], sort_keys=True)
"""
    config = {"code": code_snippet}
    # Expected output is a JSON string.
    # Python's json.dumps will add spaces after separators by default.
    expected_json_string = '{"key": "value", "number": 42}'
    # The result from the tool will be this string.
    actual_result = tool.execute(inputs, config)
    assert actual_result == expected_json_string

def test_code_execution_tool_input_variable_name_not_overwritten():
    tool = CodeExecutionTool()
    # Test that 'output' or 'results' in inputs doesn't interfere
    inputs = {"value": 5, "output": "initial_output", "results": "initial_results"}
    code_snippet = """
data = inputs['value'] * 3
# This 'output' is the one that the tool expects for the result.
output = {'final_value': data, 'original_output_input': inputs['output']}
"""
    config = {"code": code_snippet}
    expected_output = {"final_value": 15, "original_output_input": "initial_output"}
    actual_output = tool.execute(inputs=inputs, config=config)
    assert actual_output == expected_output


# --- Tests for ConditionalRouterTool ---

@pytest.fixture
def mock_pipeline_state():
    return {} # Start with an empty state for most tests

def test_conditional_router_if_condition_met(mock_pipeline_state):
    tool = ConditionalRouterTool()
    inputs = {"status": "active"}
    config = {
        "condition_groups": [{
            "if": {"variable": "status", "operator": "equals", "value": "active"},
            "then_execute_step": "active_step"
        }],
        "else_execute_step": "inactive_step"
    }
    expected_output = {"_next_step_id": "active_step"}
    assert tool.execute(inputs, config, pipeline_state=mock_pipeline_state) == expected_output

def test_conditional_router_if_condition_not_met_else_taken(mock_pipeline_state):
    tool = ConditionalRouterTool()
    inputs = {"status": "inactive"}
    config = {
        "condition_groups": [{
            "if": {"variable": "status", "operator": "equals", "value": "active"},
            "then_execute_step": "active_step"
        }],
        "else_execute_step": "default_step"
    }
    expected_output = {"_next_step_id": "default_step"}
    assert tool.execute(inputs, config, pipeline_state=mock_pipeline_state) == expected_output

def test_conditional_router_no_conditions_met_no_else(mock_pipeline_state):
    tool = ConditionalRouterTool()
    inputs = {"status": "pending"}
    config = {
        "condition_groups": [{
            "if": {"variable": "status", "operator": "equals", "value": "active"},
            "then_execute_step": "active_step"
        }]
        # No "else_execute_step"
    }
    expected_output = {} # Returns empty if no route determined
    assert tool.execute(inputs, config, pipeline_state=mock_pipeline_state) == expected_output

def test_conditional_router_operator_gt(mock_pipeline_state):
    tool = ConditionalRouterTool()
    inputs = {"count": 10}
    config = {
        "condition_groups": [{"if": {"variable": "count", "operator": "gt", "value": 5}, "then_execute_step": "gt_step"}],
        "else_execute_step": "le_step"
    }
    assert tool.execute(inputs, config, pipeline_state=mock_pipeline_state) == {"_next_step_id": "gt_step"}

def test_conditional_router_operator_contains(mock_pipeline_state):
    tool = ConditionalRouterTool()
    inputs = {"tags": ["urgent", "important"]}
    config = {
        "condition_groups": [{"if": {"variable": "tags", "operator": "contains", "value": "urgent"}, "then_execute_step": "urgent_step"}],
    }
    assert tool.execute(inputs, config, pipeline_state=mock_pipeline_state) == {"_next_step_id": "urgent_step"}

# --- Looping Tests for ConditionalRouterTool ---

def test_conditional_router_loop_initialization_and_first_step(mock_pipeline_state):
    tool = ConditionalRouterTool()
    inputs = {"num_items": 3, "current_item_data": "data_for_item_0"} # total_iterations_from = num_items
    config = {
        "loop_config": {
            "total_iterations_from": "num_items",
            "loop_body_start_id": "process_item_step",
            "counter_name": "my_loop_counter",
            "accumulators": {"all_item_data": "current_item_data"}, # input_source for accumulator is 'current_item_data'
            "loop_body_agents": ["process_item_step"]
        },
        "else_execute_step": "loop_finished_step"
    }

    # On the first run (counter = 0 implicitly)
    result = tool.execute(inputs, config, pipeline_state=mock_pipeline_state)

    assert result["_next_step_id"] == "process_item_step"
    assert "_update_state" in result
    assert result["_update_state"]["my_loop_counter"] == 1 # Counter increments for the next iteration
    assert result["_update_state"]["all_item_data"] == ["data_for_item_0"] # Data is accumulated
    assert result["_clear_agent_outputs"] == ["process_item_step"]

    # Check that pipeline_state was updated (though the tool returns the update separately)
    # For this test, we assume orchestrator would apply this.
    # The tool itself does not directly modify the passed-in pipeline_state for initialization;
    # it returns the intended updates in _update_state.
    # So, direct assertions on mock_pipeline_state for prior non-existence leading to initialization are removed.
    # The critical checks are that result['_update_state'] contains the correct initial counter and accumulator.
    # If mock_pipeline_state started empty, result['_update_state']['all_item_data'] correctly shows the first item.


def test_conditional_router_loop_iteration(mock_pipeline_state):
    tool = ConditionalRouterTool()
    # Simulate state after first iteration
    mock_pipeline_state["my_loop_counter"] = 1
    mock_pipeline_state["all_item_data"] = ["data_for_item_0"]

    inputs = {"num_items": 3, "current_item_data": "data_for_item_1"}
    config = {
        "loop_config": {
            "total_iterations_from": "num_items",
            "loop_body_start_id": "process_item_step",
            "counter_name": "my_loop_counter",
            "accumulators": {"all_item_data": "current_item_data"},
            "loop_body_agents": ["process_item_step"]
        },
        "else_execute_step": "loop_finished_step"
    }

    result = tool.execute(inputs, config, pipeline_state=mock_pipeline_state)

    assert result["_next_step_id"] == "process_item_step"
    assert result["_update_state"]["my_loop_counter"] == 2
    assert result["_update_state"]["all_item_data"] == ["data_for_item_0", "data_for_item_1"]
    assert result["_clear_agent_outputs"] == ["process_item_step"]


def test_conditional_router_loop_final_iteration_and_completion(mock_pipeline_state):
    tool = ConditionalRouterTool()
    # Simulate state after second iteration, counter is 2, expecting 3 iterations total
    mock_pipeline_state["my_loop_counter"] = 2
    mock_pipeline_state["all_item_data"] = ["data_for_item_0", "data_for_item_1"]

    # This is the input for the third item (current_count = 2, which is < total_iterations = 3)
    # The tool will process this, increment counter to 3.
    # Then, on the *next* call (if it happened), count (3) would not be < total_iterations (3), ending the loop.
    inputs = {"num_items": 3, "current_item_data": "data_for_item_2"}
    config = {
        "loop_config": {
            "total_iterations_from": "num_items",
            "loop_body_start_id": "process_item_step",
            "counter_name": "my_loop_counter",
            "accumulators": {"all_item_data": "current_item_data"},
            "loop_body_agents": ["process_item_step"]
        },
        "else_execute_step": "loop_finished_step"
    }

    # This is the run for current_count = 2. It should still go to loop_body_start_id
    # and increment counter to 3, accumulate data.
    result_iter_3 = tool.execute(inputs, config, pipeline_state=mock_pipeline_state)
    assert result_iter_3["_next_step_id"] == "process_item_step"
    assert result_iter_3["_update_state"]["my_loop_counter"] == 3
    assert result_iter_3["_update_state"]["all_item_data"] == ["data_for_item_0", "data_for_item_1", "data_for_item_2"]
    assert result_iter_3["_clear_agent_outputs"] == ["process_item_step"]

    # Now, simulate the state that would exist *after* the orchestrator applies result_iter_3's _update_state
    mock_pipeline_state.update(result_iter_3["_update_state"])

    # This call simulates the router being called when counter is now 3 (loop should end)
    # For this call, the inputs to the router might not matter as much for current_item_data
    # as the loop condition is based on the counter.
    inputs_for_loop_end_check = {"num_items": 3} # No new 'current_item_data' needed as we are exiting

    result_loop_end = tool.execute(inputs_for_loop_end_check, config, pipeline_state=mock_pipeline_state)

    assert result_loop_end["_next_step_id"] == "loop_finished_step"
    assert "all_item_data" in result_loop_end # Final aggregated data should be part of the output
    assert result_loop_end["all_item_data"] == ["data_for_item_0", "data_for_item_1", "data_for_item_2"]
    assert "_update_state" not in result_loop_end # No state update when loop finishes normally

def test_conditional_router_loop_missing_total_iterations_input(mock_pipeline_state):
    tool = ConditionalRouterTool()
    inputs = {} # Missing "num_items" which is total_iterations_from
    config = {
        "loop_config": {
            "total_iterations_from": "num_items", # This key is missing in inputs
            "loop_body_start_id": "process_item_step",
            "counter_name": "my_loop_counter",
            "accumulators": {"all_item_data": "current_item_data"}
        }
    }
    expected_error_msg = r"Looping error for agent 'None': Total iterations key 'num_items' not found in inputs. Ensure it's defined in the agent's 'inputs'. Current inputs: \[]"
    with pytest.raises(ValueError, match=expected_error_msg):
        tool.execute(inputs, config, pipeline_state=mock_pipeline_state, agent_id=None) # Pass agent_id=None explicitly for clarity

def test_conditional_router_loop_zero_iterations(mock_pipeline_state):
    tool = ConditionalRouterTool()
    inputs = {"num_items": 0} # Zero iterations
    config = {
        "loop_config": {
            "total_iterations_from": "num_items",
            "loop_body_start_id": "process_item_step",
            "counter_name": "my_loop_counter",
            "accumulators": {"all_item_data": "current_item_data"},
            "loop_body_agents": ["process_item_step"]
        },
        "else_execute_step": "loop_finished_step"
    }

    # Initialize state as the orchestrator would before the first call to the router
    mock_pipeline_state["my_loop_counter"] = 0
    mock_pipeline_state["all_item_data"] = []

    result = tool.execute(inputs, config, pipeline_state=mock_pipeline_state)

    assert result["_next_step_id"] == "loop_finished_step"
    assert result.get("all_item_data") == [] # Accumulator should be empty
    assert "_update_state" not in result


# --- Tests for DataAggregatorTool ---

def test_data_aggregator_tool_success():
    tool = DataAggregatorTool()
    inputs = {
        "source_step_1.output_A": "valueA",
        "source_step_2.output_B": 123,
        "some_other_data": "ignore_this"
    }
    config = {
        "sources": {
            "new_key_A": "source_step_1.output_A",
            "new_key_B": "source_step_2.output_B"
        }
    }
    expected_output = {
        "new_key_A": "valueA",
        "new_key_B": 123
    }
    assert tool.execute(inputs, config) == expected_output

def test_data_aggregator_tool_some_sources_missing():
    tool = DataAggregatorTool()
    inputs = {
        "source_step_1.output_A": "valueA"
        # "source_step_2.output_B" is missing from inputs
    }
    config = {
        "sources": {
            "new_key_A": "source_step_1.output_A",
            "new_key_B": "source_step_2.output_B" # This source is missing
        }
    }
    expected_output = {
        "new_key_A": "valueA",
        "new_key_B": "Source key 'source_step_2.output_B' not found in inputs."
    }
    assert tool.execute(inputs, config) == expected_output

def test_data_aggregator_tool_empty_sources_config():
    tool = DataAggregatorTool()
    inputs = {"source_step_1.output_A": "valueA"}
    config = {"sources": {}} # Empty sources

    expected_output = {}
    assert tool.execute(inputs, config) == expected_output

def test_data_aggregator_tool_empty_inputs():
    tool = DataAggregatorTool()
    inputs = {} # Empty inputs
    config = {
        "sources": {
            "new_key_A": "source_step_1.output_A",
            "new_key_B": "source_step_2.output_B"
        }
    }
    expected_output = {
        "new_key_A": "Source key 'source_step_1.output_A' not found in inputs.",
        "new_key_B": "Source key 'source_step_2.output_B' not found in inputs."
    }
    assert tool.execute(inputs, config) == expected_output

def test_data_aggregator_tool_no_sources_key_in_config():
    tool = DataAggregatorTool()
    inputs = {"source_step_1.output_A": "valueA"}
    config = {} # 'sources' key is missing entirely from config

    # According to the implementation, if "sources" key is missing, it defaults to {}
    expected_output = {}
    assert tool.execute(inputs, config) == expected_output

import pytest
import json
from unittest.mock import MagicMock, patch, mock_open

# Assuming orchestrator.py is in the same directory or accessible via PYTHONPATH
from orchestrator import Orchestrator
from tools.base_tool import BaseTool # For type hinting and mocking tool spec
from tools.built_in_tools import RegexParserTool, DataAggregatorTool # Import for patching

# --- Mock Fixtures ---

@pytest.fixture
def mock_invoke_llm_fixture():
    # Patching where invoke_llm is LOOKED UP (in orchestrator module)
    with patch('orchestrator.invoke_llm') as mock_llm:
        mock_llm.return_value = "Mocked LLM response"
        yield mock_llm

@pytest.fixture
def simple_pipeline_config_dict(): # Renamed to avoid conflict if a fixture is named 'simple_pipeline_config'
    return {
        "pipeline_name": "TestPipeline",
        "initial_input": "Initial test data",
        "start_agent": "agent1",
        "agents": [
            {
                "id": "agent1",
                "type": "llm_agent",
                "description": "Test LLM Agent",
                "model": "test_model",
                "inputs": {"prompt_data": "pipeline.initial_input"},
                "outputs": ["llm_response"],
                "prompt_template": "Process this: {prompt_data}" # Corrected template
            }
        ],
        "routing": {"agent1": {"next": None}},
        "final_outputs": {"final_result": "agent1.llm_response"}
    }

@pytest.fixture
def tool_agent_pipeline_config_dict(): # Renamed
    return {
        "pipeline_name": "ToolTestPipeline",
        "initial_input": "Tool test input",
        "start_agent": "tool_agent1",
        "agents": [
            {
                "id": "tool_agent1",
                "type": "tool_agent", # This implies it uses the internal tool_registry
                "tool_name": "MockTestTool", # A tool name expected in the orchestrator's registry
                "description": "Test Tool Agent",
                "inputs": {"tool_input_data": "pipeline.initial_input"},
                "outputs": ["tool_data_output"],
                "tool_config": {"some_param": "value"}
            }
        ],
        "routing": {"tool_agent1": {"next": None}},
        "final_outputs": {"final_tool_result": "tool_agent1.tool_data_output"}
    }

# --- Orchestrator Tests ---

def test_orchestrator_initialization(simple_pipeline_config_dict):
    orchestrator = Orchestrator(config=simple_pipeline_config_dict)
    assert orchestrator is not None
    assert orchestrator.config == simple_pipeline_config_dict
    assert orchestrator.agents is not None
    assert orchestrator.routing is not None
    assert orchestrator.start_agent_id == "agent1"

# Test for loading from file can be a utility test, not testing Orchestrator method
@patch("builtins.open", new_callable=mock_open, read_data='{"pipeline_name": "FilePipeline", "start_agent": "a", "agents": [], "routing": {}}')
@patch("json.load")
def test_loading_config_and_passing_to_orchestrator(mock_json_load, mock_file_open, simple_pipeline_config_dict):
    # Simulate loading config from a file
    mock_json_load.return_value = simple_pipeline_config_dict

    # This test isn't for an orchestrator method, but for the pattern of loading and init
    with mock_file_open("dummy_path.json", "r") as f:
        config_from_file = json.load(f)

    mock_file_open.assert_called_once_with("dummy_path.json", "r")
    mock_json_load.assert_called_once()

    orchestrator = Orchestrator(config=config_from_file)
    assert orchestrator.config["pipeline_name"] == "TestPipeline"


def test_run_simple_llm_agent_pipeline(simple_pipeline_config_dict, mock_invoke_llm_fixture):
    orchestrator = Orchestrator(config=simple_pipeline_config_dict)
    final_state = orchestrator.run()

    mock_invoke_llm_fixture.assert_called_once_with(
        "test_model", # Positional argument
        "Process this: Initial test data" # Positional argument
    )
    assert final_state["agent1.llm_response"] == "Mocked LLM response"

    # Test final_outputs extraction (optional, can be a separate test)
    final_results = orchestrator.get_final_outputs(final_state)
    assert final_results["final_result"] == "Mocked LLM response"

@patch.object(RegexParserTool, 'execute') # Example: Patching a specific tool's execute
def test_run_tool_agent_pipeline(
    mock_regex_parser_execute, # Patched for "RegexParserTool"
    tool_agent_pipeline_config_dict,
    mock_invoke_llm_fixture # To satisfy orchestrator's potential use of invoke_llm in other tools
):
    # Modify config to use a tool we can easily patch from the registry
    config_copy = tool_agent_pipeline_config_dict.copy()
    config_copy["agents"][0]["tool_name"] = "RegexParserTool" # Use a known tool
    mock_tool_output = {"tool_data_output": "parsed_data_from_regex"}
    mock_regex_parser_execute.return_value = mock_tool_output

    orchestrator = Orchestrator(config=config_copy)
    final_state = orchestrator.run()

    expected_tool_inputs = {"tool_input_data": "Tool test input"}
    expected_tool_config = {"some_param": "value"}

    mock_regex_parser_execute.assert_called_once()
    call_args = mock_regex_parser_execute.call_args[1] # Get kwargs of the call

    assert call_args['inputs'] == expected_tool_inputs
    assert call_args['config'] == expected_tool_config
    assert call_args['output_fields'] == ["tool_data_output"]
    # pipeline_state is passed, so we check its existence and type, not full content
    assert "pipeline_state" in call_args and isinstance(call_args["pipeline_state"], dict)
    assert call_args['invoke_llm'] is mock_invoke_llm_fixture # Ensure it's passed

    assert final_state["tool_agent1.tool_data_output"] == "parsed_data_from_regex"
    final_results = orchestrator.get_final_outputs(final_state)
    assert final_results["final_tool_result"] == "parsed_data_from_regex"


def test_orchestrator_run_without_initial_input_prompts_user(simple_pipeline_config_dict, mock_invoke_llm_fixture):
    config_copy = simple_pipeline_config_dict.copy()
    del config_copy["initial_input"] # Remove initial input

    orchestrator = Orchestrator(config=config_copy)

    # Mock input() for the interactive prompt
    with patch('builtins.input', return_value="User provided test data") as mock_input:
        final_state = orchestrator.run()

    mock_input.assert_called_once() # Check it prompted
    # The prompt in _resolve_inputs is dynamic, check a substring
    assert "pipeline.initial input" in mock_input.call_args[0][0].lower() # Corrected to check for dot


    mock_invoke_llm_fixture.assert_called_once_with(
        "test_model", # Positional argument
        "Process this: User provided test data" # Positional argument
    )
    assert final_state["agent1.llm_response"] == "Mocked LLM response"


def test_orchestrator_invalid_start_agent_id(simple_pipeline_config_dict):
    config_copy = simple_pipeline_config_dict.copy()
    config_copy["start_agent"] = "non_existent_agent"
    # Orchestrator __init__ might raise error if start_agent_id is immediately checked
    # Or run() will fail. Based on current orchestrator.py, run() will fail.
    orchestrator = Orchestrator(config=config_copy)
    with pytest.raises(KeyError, match="non_existent_agent"): # Orchestrator uses self.agents[current_agent_id]
        orchestrator.run()


def test_orchestrator_agent_not_found_during_routing(simple_pipeline_config_dict):
    config_copy = simple_pipeline_config_dict.copy()
    config_copy["routing"]["agent1"]["next"] = "ghost_agent"
    orchestrator = Orchestrator(config=config_copy)
    with pytest.raises(KeyError, match="ghost_agent"): # Similar to above, direct key access
        orchestrator.run()

def test_orchestrator_unknown_tool_name(tool_agent_pipeline_config_dict):
    config_copy = tool_agent_pipeline_config_dict.copy()
    config_copy["agents"][0]["tool_name"] = "UnknownFantomTool"
    orchestrator = Orchestrator(config=config_copy)
    with pytest.raises(ValueError, match="Unknown tool 'UnknownFantomTool'"):
        orchestrator.run()

def test_orchestrator_unsupported_agent_type(simple_pipeline_config_dict):
    config_copy = simple_pipeline_config_dict.copy()
    config_copy["agents"][0]["type"] = "alien_agent_type"
    orchestrator = Orchestrator(config=config_copy)
    with pytest.raises(ValueError, match="Unsupported agent type: 'alien_agent_type'"):
        orchestrator.run()

# Placeholder for BaseTool if not already imported or defined elsewhere for tests
# class BaseTool:
#     def execute(self, inputs: dict, config: dict, **kwargs) -> dict:
#         raise NotImplementedError
import json
import os

# Assuming pytest, patch, Orchestrator are already imported in the file.

TEST_PIPELINES_DIR_INTEGRATION = os.path.join(os.path.dirname(__file__), "test_pipelines")

def load_pipeline_config_for_integration_test(filename):
    path = os.path.join(TEST_PIPELINES_DIR_INTEGRATION, filename)
    with open(path, "r") as f:
        return json.load(f)

@patch('orchestrator.invoke_llm')
@patch('tools.built_in_tools.RegexParserTool.execute')
def test_orchestrator_run_simple_linear_pipeline(mock_regex_execute, mock_invoke_llm_orchestrator):
    config = load_pipeline_config_for_integration_test("simple_linear_pipeline.json")

    mock_invoke_llm_orchestrator.return_value = "This is a sentence about testing"
    mock_regex_execute.return_value = {"parsed_value": "testing_from_mock_regex"}

    orchestrator_instance = Orchestrator(config)
    final_state = orchestrator_instance.run()

    expected_llm_prompt = "Generate a sentence about testing." # Added period
    mock_invoke_llm_orchestrator.assert_called_once_with(
        "test-llm-model",
        expected_llm_prompt
    )

    assert mock_regex_execute.call_count == 1
    called_kwargs = mock_regex_execute.call_args.kwargs

    expected_regex_inputs = {"text_to_parse": "This is a sentence about testing"}
    expected_regex_tool_config = config["agents"][1]["tool_config"]

    assert called_kwargs.get("inputs") == expected_regex_inputs
    assert called_kwargs.get("config") == expected_regex_tool_config

    assert final_state.get("agent_1_llm.generated_text") == "This is a sentence about testing"
    assert final_state.get("agent_2_regex.parsed_value") == "testing_from_mock_regex"

    final_outputs = orchestrator_instance.get_final_outputs(final_state)
    assert final_outputs.get("final_topic") == "testing"
    assert final_outputs.get("final_parsed_value") == "testing_from_mock_regex"

# (Keep existing imports: json, os, patch, Orchestrator, etc.)
# (Keep existing TEST_PIPELINES_DIR_INTEGRATION and load_pipeline_config_for_integration_test)

@patch('orchestrator.invoke_llm') # Mock LLM calls within orchestrator.py
@patch('tools.built_in_tools.DataAggregatorTool.execute', wraps=DataAggregatorTool().execute) # Wrap to use real logic but allow spying if needed
@patch('builtins.input') # Mock the input call
def test_orchestrator_run_looping_pipeline(mock_builtin_input, mock_data_aggregator_execute, mock_invoke_llm_orchestrator):
    # Mock input() to return a specific value when prompted for the initially missing accumulator input
    # This prompt occurs when loop_controller tries to resolve 'generate_item_inside_loop.generated_text' for the first time.
    # We return an empty string, assuming the ConditionalRouterTool's accumulator won't add it if it's empty or None.
    mock_builtin_input.return_value = ""

    config = load_pipeline_config_for_integration_test("looping_pipeline.json")

    # LLM mock: called for each item in the loop (2 times)
    # The prompt uses 'current_iteration_count_from_router_input' which comes from 'loop_controller.test_loop_counter'
    # This counter is 0 then 1 during the prompts for a 2-iteration loop (as it's the count *before* incrementing for the current item).
    mock_invoke_llm_orchestrator.side_effect = [
        "Generated Item for iteration 0", # For loop_controller.test_loop_counter = 0
        "Generated Item for iteration 1"  # For loop_controller.test_loop_counter = 1
    ]

    orchestrator_instance = Orchestrator(config)
    final_state = orchestrator_instance.run()

    # Assert LLM calls
    assert mock_invoke_llm_orchestrator.call_count == 2
    expected_prompts = [
        "Generate content for Item using loop counter value available in pipeline_state at loop_controller.test_loop_counter (this is for info, direct access not used in prompt). Iteration: 1", # Expect 1 for first iteration
        "Generate content for Item using loop counter value available in pipeline_state at loop_controller.test_loop_counter (this is for info, direct access not used in prompt). Iteration: 2"  # Expect 2 for second iteration
    ]
    # Check prompts (order matters due to side_effect)
    assert mock_invoke_llm_orchestrator.call_args_list[0][0][1] == expected_prompts[0] # prompt for first call
    assert mock_invoke_llm_orchestrator.call_args_list[1][0][1] == expected_prompts[1] # prompt for second call


    # Assert DataAggregatorTool was called (it's used twice)
    # We wrapped it, so its actual logic ran. We can check call count if needed.
    assert mock_data_aggregator_execute.call_count >= 2 # Called for setup_loop_vars and final_processing

    # Assert final state from loop controller
    # The counter value in the state after the loop should be total_iterations.
    assert final_state.get("loop_controller.test_loop_counter") == 2
    assert final_state.get("loop_controller.all_generated_items") == [
        "Generated Item for iteration 0",
        "Generated Item for iteration 1"
    ]

    # Check an output from one of the DataAggregator steps
    assert final_state.get("setup_loop_vars.actual_loop_count") == 2
    assert final_state.get("final_processing.processed_data") == [
        "Generated Item for iteration 0",
        "Generated Item for iteration 1"
    ]

    # Assert final_outputs method
    final_outputs = orchestrator_instance.get_final_outputs(final_state)
    assert final_outputs.get("final_loop_counter") == 2
    assert final_outputs.get("aggregated_items") == [
        "Generated Item for iteration 0",
        "Generated Item for iteration 1"
    ]
    assert final_outputs.get("output_from_final_processing") == [
        "Generated Item for iteration 0",
        "Generated Item for iteration 1"
    ]

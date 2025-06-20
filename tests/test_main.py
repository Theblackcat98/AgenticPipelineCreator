import pytest
import sys
import json
from unittest.mock import patch, mock_open, MagicMock, call

# Ensure main can be imported. If main.py has a guard `if __name__ == "__main__":`
# then importing `main` function from it should be fine.
from main import main

# Scenario 1: Valid config path provided
@patch('main.sys.argv', ['main.py', 'pipelines/test_config.json'])
@patch('builtins.open', new_callable=mock_open)
@patch('main.json.load')
@patch('main.Orchestrator')
@patch('main.sys.exit')
@patch('builtins.input', return_value='yes') # ADDED: Mock input for confirmation
def test_main_with_valid_config_path(
    mock_input, mock_sys_exit, mock_orchestrator_class, mock_json_load, mock_fs_open
):
    config_path = 'pipelines/test_config.json'
    mock_config_dict = {"pipeline_name": "Test From File", "agents": [], "routing": {}, "start_agent": "a1"}
    mock_json_load.return_value = mock_config_dict

    mock_orchestrator_instance = MagicMock()
    mock_orchestrator_instance.run.return_value = {"state_key": "state_value"}
    mock_orchestrator_instance.get_final_outputs.return_value = {"final_output": "output_value"}
    mock_orchestrator_class.return_value = mock_orchestrator_instance

    with patch('builtins.print') as mock_print:
        main()

    mock_fs_open.assert_called_once_with(config_path, "r")
    mock_json_load.assert_called_once_with(mock_fs_open.return_value)
    mock_orchestrator_class.assert_called_once_with(mock_config_dict)
    mock_orchestrator_instance.run.assert_called_once()
    mock_orchestrator_instance.get_final_outputs.assert_called_once_with({"state_key": "state_value"})
    mock_sys_exit.assert_not_called()
    mock_print.assert_any_call(f"\033[33m▶️  Running pipeline from specified file: '{config_path}' \033[0m")

# Scenario 2: Config file not found
@patch('main.sys.argv', ['main.py', 'non_existent.json'])
@patch('builtins.open', side_effect=FileNotFoundError("File not found"))
@patch('main.sys.exit')
def test_main_config_file_not_found(mock_sys_exit, mock_fs_open):
    config_path = 'non_existent.json'
    with patch('builtins.print') as mock_print:
        main()

    mock_fs_open.assert_called_once_with(config_path, "r")
    mock_sys_exit.assert_called_once_with(1)
    mock_print.assert_any_call(f"\033[31m❌ Error: Configuration file not found at '{config_path}'.\033[0m")

# Scenario 3: Invalid JSON in config file
@patch('main.sys.argv', ['main.py', 'invalid_format.json'])
@patch('builtins.open', new_callable=mock_open, read_data="invalid json")
@patch('main.json.load', side_effect=json.JSONDecodeError("Decode error", "doc", 0))
@patch('main.sys.exit')
def test_main_invalid_json_config(mock_sys_exit, mock_json_load, mock_fs_open):
    config_path = 'invalid_format.json'
    with patch('builtins.print') as mock_print:
        main()

    mock_fs_open.assert_called_once_with(config_path, "r")
    mock_json_load.assert_called_once_with(mock_fs_open.return_value)
    mock_sys_exit.assert_called_once_with(1)
    mock_print.assert_any_call(f"\033[31m❌ Error: The file at '{config_path}' is not valid JSON.\033[0m")

# Scenario 4: No argv, successfully creates and runs new pipeline
@patch('main.sys.argv', ['main.py'])
@patch('main.create_and_save_pipeline')
@patch('builtins.open', new_callable=mock_open)
@patch('main.json.load')
@patch('main.Orchestrator')
@patch('main.sys.exit')
@patch('builtins.input', return_value='yes') # ADDED: Mock input for confirmation
def test_main_no_argv_creates_pipeline(
    mock_input, mock_sys_exit, mock_orchestrator_class, mock_json_load, mock_fs_open, mock_create_pipeline
):
    created_config_path = "pipelines/created_config.json"
    mock_create_pipeline.return_value = created_config_path

    mock_config_dict = {"pipeline_name": "Created Pipeline", "agents": [], "routing": {}, "start_agent": "a1"}

    # Configure mock_open to return a file mock that json.load can use
    mock_file_handle = mock_open(read_data=json.dumps(mock_config_dict))().return_value
    mock_fs_open.return_value = mock_file_handle
    mock_json_load.return_value = mock_config_dict


    mock_orchestrator_instance = MagicMock()
    mock_orchestrator_instance.run.return_value = {}
    mock_orchestrator_instance.get_final_outputs.return_value = {}
    mock_orchestrator_class.return_value = mock_orchestrator_instance

    with patch('builtins.print'):
        main()

    mock_create_pipeline.assert_called_once()
    mock_fs_open.assert_called_once_with(created_config_path, "r")
    # Assert that json.load was called with the file handle object
    # that results from the context manager's __enter__ method.
    mock_json_load.assert_called_once_with(mock_fs_open.return_value.__enter__.return_value)
    mock_orchestrator_class.assert_called_once_with(mock_config_dict)
    mock_orchestrator_instance.run.assert_called_once()
    mock_orchestrator_instance.get_final_outputs.assert_called_once()
    mock_sys_exit.assert_not_called()

# Scenario 5: Pipeline creation fails
@patch('main.sys.argv', ['main.py'])
@patch('main.create_and_save_pipeline', side_effect=ValueError("Creation failed"))
@patch('main.sys.exit')
def test_main_pipeline_creation_fails(mock_sys_exit, mock_create_pipeline):
    with patch('builtins.print') as mock_print:
        main()

    mock_create_pipeline.assert_called_once()
    mock_sys_exit.assert_called_once_with(1)
    mock_print.assert_any_call("\nPipeline creation failed. Exiting.")


# --- Tests for display_pipeline_flow and new confirmation logic ---
# To use io.StringIO for stdout mocking with pytest, no class is strictly necessary,
# but organizing with a class can be good for larger test suites.
# For now, let's add them as separate functions for simplicity with pytest.

# Need to import display_pipeline_flow and io
import io
# Import color constants to use in assertions
from main import display_pipeline_flow, BLUE, RESET, RED, GREEN, YELLOW, BOLD


sample_config_valid_for_display = {
    "pipeline_name": "Test Display Pipeline",
    "start_agent": "agent1",
    "agents": [
        {"id": "agent1", "type": "llm_agent", "description": "First agent", "outputs": ["out1"], "inputs": {}, "prompt_template": "test"},
        {"id": "agent2", "type": "tool_agent", "tool_name": "TestTool", "description": "Second agent", "inputs": {"in1": "agent1.out1"}}
    ],
    "routing": {
        "agent1": {"next": "agent2"},
        "agent2": {"next": None} # Using None as per Python convention, might be 'null' in JSON
    }
}

sample_config_empty_for_display = {}

@patch('sys.stdout', new_callable=io.StringIO)
def test_display_pipeline_flow_valid_config(mock_stdout):
    display_pipeline_flow(sample_config_valid_for_display)
    output = mock_stdout.getvalue()
    assert f"{BLUE}--- Pipeline Flow ---{RESET}" in output
    assert f"{GREEN}1. Agent: agent1 (Type: llm_agent){RESET}" in output
    assert f"Next -> {YELLOW}agent2{RESET}" in output
    assert f"{GREEN}2. Agent: agent2 (Type: tool_agent, Tool: TestTool){RESET}" in output
    assert f"Next -> {RED}END{RESET}" in output

@patch('sys.stdout', new_callable=io.StringIO)
def test_display_pipeline_flow_invalid_config(mock_stdout):
    display_pipeline_flow(sample_config_empty_for_display)
    output = mock_stdout.getvalue()
    assert "Invalid or incomplete pipeline configuration provided." in output

@patch('sys.stdout', new_callable=io.StringIO) # To capture print statements like "Pipeline execution cancelled"
@patch('main.Orchestrator')
@patch('builtins.input', return_value='no')
@patch('main.sys.exit') # Mocking sys.exit in the main module
@patch('builtins.open', new_callable=mock_open)
@patch('main.json.load')
def test_main_confirmation_no_exits_with_config_file(
    mock_json_load, mock_fs_open, mock_sys_exit, mock_input, mock_orchestrator_class, mock_stdout
):
    config_path = 'dummy_config.json'
    mock_json_load.return_value = sample_config_valid_for_display
    mock_fs_open.side_effect = lambda p, m="r": mock_open(read_data=json.dumps(sample_config_valid_for_display))() if p == config_path else mock_open()()

    # Make sys.exit raise an exception to halt execution
    class SysExitCalled(Exception): pass
    mock_sys_exit.side_effect = SysExitCalled

    with patch('main.sys.argv', ['main.py', config_path]):
        with pytest.raises(SysExitCalled): # Expect SysExitCalled to be raised
            main()

    mock_sys_exit.assert_called_once_with(0)
    mock_orchestrator_class.assert_not_called() # Orchestrator should not be called
    # Verify that display_pipeline_flow was called by checking its output
    output = mock_stdout.getvalue()
    assert "Pipeline Flow" in output # from display_pipeline_flow
    assert "Pipeline execution cancelled by user." in output # from main's confirmation logic

@patch('sys.stdout', new_callable=io.StringIO)
@patch('main.Orchestrator')
@patch('builtins.input', return_value='yes')
@patch('builtins.open', new_callable=mock_open)
@patch('main.json.load')
def test_main_confirmation_yes_proceeds_with_config_file(
    mock_json_load, mock_fs_open, mock_input, mock_orchestrator_class, mock_stdout
):
    config_path = 'dummy_config.json'
    mock_json_load.return_value = sample_config_valid_for_display

    mock_fs_open.side_effect = lambda path, mode="r": mock_open(read_data=json.dumps(sample_config_valid_for_display))().return_value if path == config_path else mock_open().return_value


    mock_orchestrator_instance = MagicMock()
    mock_orchestrator_instance.run.return_value = {"state_key": "state_value"}
    mock_orchestrator_instance.get_final_outputs.return_value = {"final_output": "output_value"}
    mock_orchestrator_class.return_value = mock_orchestrator_instance

    with patch('main.sys.argv', ['main.py', config_path]):
        main()

    mock_orchestrator_class.assert_called_once_with(sample_config_valid_for_display)
    mock_orchestrator_instance.run.assert_called_once()
    output = mock_stdout.getvalue()
    assert "Pipeline Flow" in output
    assert "User confirmed. Proceeding with pipeline execution..." in output


@patch('sys.stdout', new_callable=io.StringIO)
@patch('main.create_and_save_pipeline')
@patch('main.Orchestrator')
@patch('builtins.input')
@patch('main.sys.exit')
@patch('builtins.open', new_callable=mock_open)
@patch('main.json.load')
def test_main_creation_path_confirmation_no(
    mock_json_load, mock_fs_open, mock_sys_exit_main, mock_input_multiple, mock_orchestrator_class, mock_create_save, mock_stdout
):
    created_config_path = "dummy_created_pipeline.json"
    mock_input_multiple.return_value = "no"
    mock_create_save.return_value = created_config_path
    mock_json_load.return_value = sample_config_valid_for_display
    mock_fs_open.side_effect = lambda p, m="r": mock_open(read_data=json.dumps(sample_config_valid_for_display))() if p == created_config_path else mock_open()()

    # Make sys.exit raise an exception to halt execution
    class SysExitCalledCreation(Exception): pass
    mock_sys_exit_main.side_effect = SysExitCalledCreation

    with patch('main.sys.argv', ['main.py']):
        with pytest.raises(SysExitCalledCreation): # Expect SysExitCalled to be raised
            main()

    mock_create_save.assert_called_once()
    mock_sys_exit_main.assert_called_once_with(0)
    mock_orchestrator_class.assert_not_called() # Orchestrator should not be called
    output = mock_stdout.getvalue()
    assert "Pipeline Flow" in output # Check if display_pipeline_flow was called
    assert "Pipeline execution cancelled by user." in output

@patch('sys.stdout', new_callable=io.StringIO)
@patch('main.create_and_save_pipeline')
@patch('main.Orchestrator')
@patch('builtins.input', return_value='yes') # For the "Do you want to run..."
@patch('builtins.open', new_callable=mock_open)
@patch('main.json.load')
def test_main_creation_path_confirmation_yes(
    mock_json_load, mock_fs_open, mock_input_yes, mock_orchestrator_class, mock_create_save, mock_stdout
):
    created_config_path = "dummy_created_pipeline.json"
    mock_create_save.return_value = created_config_path
    mock_json_load.return_value = sample_config_valid_for_display

    mock_fs_open.side_effect = lambda path, mode="r": mock_open(read_data=json.dumps(sample_config_valid_for_display))().return_value if path == created_config_path else mock_open().return_value

    mock_orchestrator_instance = MagicMock()
    mock_orchestrator_instance.run.return_value = {"state_key": "state_value"}
    mock_orchestrator_instance.get_final_outputs.return_value = {"final_output": "output_value"}
    mock_orchestrator_class.return_value = mock_orchestrator_instance

    with patch('main.sys.argv', ['main.py']):
        with patch('main.sys.exit') as mock_sys_exit_main: # Ensure sys.exit is not called here
            main()

    mock_create_save.assert_called_once()
    mock_orchestrator_class.assert_called_once_with(sample_config_valid_for_display)
    mock_orchestrator_instance.run.assert_called_once()
    mock_sys_exit_main.assert_not_called() # Crucial: sys.exit should not be called if user says yes
    output = mock_stdout.getvalue()
    assert "Pipeline Flow" in output
    assert "User confirmed. Proceeding with pipeline execution..." in output

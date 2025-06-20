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
def test_main_with_valid_config_path(
    mock_sys_exit, mock_orchestrator_class, mock_json_load, mock_fs_open
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
def test_main_no_argv_creates_pipeline(
    mock_sys_exit, mock_orchestrator_class, mock_json_load, mock_fs_open, mock_create_pipeline
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

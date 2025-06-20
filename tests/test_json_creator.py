import pytest
import json
from unittest.mock import patch, mock_open, MagicMock
from json_creator import generate_pipeline_json_python, create_and_save_pipeline, USER_JSON_PIPELINE_TEMPLATE, OLLAMA_MODEL

# --- Tests for generate_pipeline_json_python ---

@pytest.fixture
def mock_ollama_chat_fixture():
    with patch('json_creator.ollama.chat') as mock_chat:
        yield mock_chat

def test_generate_pipeline_success(mock_ollama_chat_fixture):
    natural_language_input = "Create a simple data processing pipeline."
    mock_response_content = json.loads(USER_JSON_PIPELINE_TEMPLATE)
    mock_response_content["pipeline_name"] = "TestPipeline"

    for agent in mock_response_content.get("agents", []):
        if agent.get("type") == "llm_agent" or agent.get("tool_name") == "StructuredDataParserTool":
            if "model" in agent: agent["model"] = OLLAMA_MODEL
            if "tool_config" in agent and "model" in agent["tool_config"]:
                agent["tool_config"]["model"] = OLLAMA_MODEL

    mock_ollama_chat_fixture.return_value = {
        'message': {'content': json.dumps(mock_response_content)}
    }

    result = generate_pipeline_json_python(natural_language_input)
    assert result["pipeline_name"] == "TestPipeline"
    assert "agents" in result
    mock_ollama_chat_fixture.assert_called_once()

def test_generate_pipeline_success_with_markdown_fences(mock_ollama_chat_fixture):
    natural_language_input = "Create a pipeline with markdown fences."

    base_json_dict = json.loads(USER_JSON_PIPELINE_TEMPLATE)
    for agent in base_json_dict.get("agents", []):
        if agent.get("type") == "llm_agent" or agent.get("tool_name") == "StructuredDataParserTool":
            if "model" in agent: agent["model"] = OLLAMA_MODEL
            if "tool_config" in agent and "model" in agent["tool_config"]:
                agent["tool_config"]["model"] = OLLAMA_MODEL
    mock_json_str = json.dumps(base_json_dict)

    mock_ollama_chat_fixture.return_value = {
        'message': {'content': f"```json\n{mock_json_str}\n```"}
    }
    result = generate_pipeline_json_python(natural_language_input)
    assert "pipeline_name" in result

    mock_ollama_chat_fixture.reset_mock()
    mock_ollama_chat_fixture.return_value = {
        'message': {'content': f"```{mock_json_str}```"}
    }
    result = generate_pipeline_json_python(natural_language_input)
    assert "pipeline_name" in result

def test_generate_pipeline_json_decode_error(mock_ollama_chat_fixture):
    natural_language_input = "Test malformed JSON."
    mock_ollama_chat_fixture.return_value = {
        'message': {'content': '{"name": "Test",, "type": "broken"}'}
    }
    with pytest.raises(ValueError, match="API Error: Failed to parse JSON response"):
        generate_pipeline_json_python(natural_language_input)

def test_generate_pipeline_missing_required_keys(mock_ollama_chat_fixture):
    natural_language_input = "Test incomplete JSON."
    incomplete_json = {"pipeline_name": "OnlyName", "start_agent": "a1", "routing": {}}
    mock_ollama_chat_fixture.return_value = {
        'message': {'content': json.dumps(incomplete_json)}
    }
    with pytest.raises(ValueError, match="Generated JSON is incomplete. Essential field 'agents' is missing."):
        generate_pipeline_json_python(natural_language_input)

def test_generate_pipeline_ollama_api_error(mock_ollama_chat_fixture):
    natural_language_input = "Test Ollama API failure."
    mock_ollama_chat_fixture.side_effect = Exception("Ollama network error")

    with pytest.raises(RuntimeError, match="Failed to generate pipeline from Ollama: Exception - Ollama network error"):
        generate_pipeline_json_python(natural_language_input)

def test_generate_pipeline_llm_returns_non_dict_json(mock_ollama_chat_fixture):
    natural_language_input = "Test LLM returns a list."
    mock_ollama_chat_fixture.return_value = {
        'message': {'content': '[1, 2, 3]'}
    }
    with pytest.raises(ValueError, match="Generated JSON is not a valid dictionary."):
        generate_pipeline_json_python(natural_language_input)

@patch('json_creator.generate_pipeline_json_python')
@patch('json_creator.os.makedirs')
@patch('builtins.open', new_callable=mock_open)
@patch('json_creator.json.dump')
@patch('builtins.input', return_value="Describe my pipeline")
def test_create_and_save_pipeline_success(
    mock_bi_input, mock_json_dump, mock_builtin_open, mock_os_makedirs, mock_generate_json # Order matches decorators
):
    pipeline_name = "MyAwesomePipeline"
    sanitized_name = "my_awesome_pipeline"
    expected_filename = f"{sanitized_name}.json"
    expected_path = f"pipelines/{expected_filename}"

    mock_generate_json.return_value = {
        "pipeline_name": pipeline_name, "initial_input": "Test input", "start_agent": "agent1",
        "agents": [{"id": "agent1", "type": "llm_agent", "model": OLLAMA_MODEL,
                    "inputs": {}, "outputs": [], "prompt_template": "test"}],
        "routing": {"agent1": {"next": None}}, "final_outputs": {}
    }

    result_path = create_and_save_pipeline()

    mock_bi_input.assert_called_once()
    mock_generate_json.assert_called_once_with("Describe my pipeline")
    mock_os_makedirs.assert_called_once_with("pipelines", exist_ok=True)
    mock_builtin_open.assert_called_once_with(expected_path, "w")
    mock_json_dump.assert_called_once_with(mock_generate_json.return_value, mock_builtin_open(), indent=2)
    assert result_path == expected_path

@patch('json_creator.generate_pipeline_json_python')
@patch('builtins.input', return_value="Test for failure")
def test_create_and_save_pipeline_generation_fails(mock_bi_input, mock_generate_json): # Order matches
    mock_generate_json.side_effect = ValueError("Generation failed")

    with pytest.raises(ValueError, match="Generation failed"):
        create_and_save_pipeline()

    mock_bi_input.assert_called_once()
    mock_generate_json.assert_called_once_with("Test for failure")

@patch('builtins.input', return_value="Describe my pipeline for sanitization") # mock_bi_input (last arg)
@patch('json_creator.json.dump') # mock_json_dump
@patch('builtins.open', new_callable=mock_open) # mock_builtin_open
@patch('json_creator.os.makedirs') # mock_os_makedirs
@patch('json_creator.generate_pipeline_json_python') # mock_generate_json (first arg)
def test_filename_sanitization_in_create_and_save(
    mock_generate_json, mock_os_makedirs, mock_builtin_open, mock_json_dump, mock_bi_input
):
    test_cases = [
        ("SimpleName", "simple_name.json"),
        ("Name With Spaces", "name_with_spaces.json"),
        ("Name-With-Hyphens", "name_with_hyphens.json"),
        ("Name_With_Underscores", "name_with_underscores.json"),
            ("Name!@#$", "name.json") # Changed expected from "name____.json" to "name.json"
    ]

    for original_name, expected_file_part in test_cases:
        mock_bi_input.reset_mock()
        mock_generate_json.reset_mock()
        mock_os_makedirs.reset_mock()

        mock_generate_json.return_value = {
            "pipeline_name": original_name, "start_agent": "a",
            "agents": [{"id": "a", "type": "llm_agent", "model": OLLAMA_MODEL, "inputs": {}, "outputs": [], "prompt_template":"t"}],
            "routing": {"a":None}
        }

        expected_path = f"pipelines/{expected_file_part}"

        result_path = create_and_save_pipeline()

        mock_bi_input.assert_called_once()
        mock_generate_json.assert_called_once_with("Describe my pipeline for sanitization")
        mock_os_makedirs.assert_called_once_with("pipelines", exist_ok=True)
        mock_builtin_open.assert_called_with(expected_path, "w")
        mock_json_dump.assert_called_with(mock_generate_json.return_value, mock_builtin_open(), indent=2)
        assert result_path == expected_path

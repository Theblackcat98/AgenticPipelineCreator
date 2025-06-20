import pytest
from unittest.mock import patch, MagicMock
from llm.ollama_client import invoke_llm

# Define a fixture for common mock setup if needed, or patch directly in tests.

def test_invoke_llm_success():
    """Test invoke_llm successfully returns content from ollama.chat."""
    mock_response = {
        'message': {
            'content': 'Test LLM response content'
        }
    }

    # Patch 'ollama.chat' within the llm.ollama_client module
    with patch('llm.ollama_client.ollama.chat', return_value=mock_response) as mock_chat:
        model = "test_model"
        prompt = "Test prompt"

        result = invoke_llm(model, prompt)

        mock_chat.assert_called_once_with(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': 0.0}
        )
        assert result == "Test LLM response content"

def test_invoke_llm_ollama_error():
    """Test invoke_llm returns an error message when ollama.chat raises an exception."""
    # Patch 'ollama.chat' to simulate an exception
    with patch('llm.ollama_client.ollama.chat', side_effect=Exception("Ollama API error")) as mock_chat:
        model = "error_model"
        prompt = "Error prompt"

        result = invoke_llm(model, prompt)

        mock_chat.assert_called_once_with(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': 0.0}
        )
        assert result == "Error: Could not get response from LLM."

def test_invoke_llm_handles_strip_on_content():
    """Test that whitespace is correctly stripped from the LLM response content."""
    mock_response = {
        'message': {
            'content': '  Response with leading/trailing spaces  '
        }
    }
    with patch('llm.ollama_client.ollama.chat', return_value=mock_response) as mock_chat:
        result = invoke_llm("strip_test_model", "strip test prompt")
        assert result == "Response with leading/trailing spaces"

# Tests for Agentic Pipeline Framework

This directory contains all the automated tests for the Agentic Pipeline Framework.
The tests are built using the `pytest` framework and `pytest-mock` for mocking.

## Prerequisites

1.  Ensure you have Python installed (version 3.8+ recommended).
2.  It's recommended to use a virtual environment to manage dependencies.

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
    ```

## Installing Test Dependencies

The test dependencies are listed in the main `requirements.txt` file in the root of the repository.
Install them using pip:

```bash
pip install -r ../requirements.txt
```
*(Note: This command assumes you are running it from the `tests` directory. If running from the root, just use `pip install -r requirements.txt`)*

## Running Tests

All tests can be run from the **root directory** of the project using the following command:

```bash
python -m pytest
```

To run tests for a specific file:

```bash
python -m pytest tests/test_module_name.py
```

To run tests with more verbosity:

```bash
python -m pytest -v
```

## Test Structure

*   Tests are located in the `tests/` directory.
*   Test filenames follow the convention `test_<module_name>.py` (e.g., `test_orchestrator.py` contains tests for `orchestrator.py`).
*   Unit tests focus on individual functions or classes in isolation, using mocks for external dependencies (like LLM calls or file I/O).
*   Integration tests (`test_orchestrator.py` also contains these) verify the interaction between different components, often using pipeline configuration files from `tests/test_pipelines/`.

## Mocking

*   `unittest.mock.patch` (often via `pytest-mock`'s `mocker` fixture, though direct patching is also used) is the primary tool for mocking.
*   LLM calls (`ollama.chat` or `invoke_llm`) are consistently mocked to provide predictable behavior and avoid actual API calls during testing.
*   File system operations (`open`, `os.makedirs`, `json.load`, `json.dump`) are mocked where necessary to isolate tests from the actual file system.
*   Tools defined in `tools/built_in_tools.py` have their `execute` methods mocked in orchestrator tests to focus on the orchestrator's logic rather than the tool's internal execution (which is covered by the tool's own unit tests).

## Pipeline Configurations for Tests

Sample pipeline configurations used for integration testing are stored in the `tests/test_pipelines/` directory. These JSON files define various pipeline structures to test different scenarios within the orchestrator.

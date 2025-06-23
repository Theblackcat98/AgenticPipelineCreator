# Developer Guide

This guide is for developers who want to contribute to the Agentic Pipeline Framework, such as by adding new built-in tools or modifying the core orchestrator logic.

## Project Structure Overview

-   `main.py`: Entry point for running pipelines.
-   `orchestrator.py`: Core class (`Orchestrator`) that loads and executes pipelines.
-   `llm/`: Modules related to Large Language Model interactions (e.g., `ollama_client.py`).
-   `tools/`: Contains implementations of built-in tools.
    -   `tools/base_tool.py`: Defines the abstract base class `BaseTool` that all tools should inherit from.
    -   `tools/built_in_tools.py`: Implementation of concrete tools like `StructuredDataParserTool` and `RegexParserTool`.
    -   `tools/__init__.py`: Registers available tools.
-   `pipelines/`: Example pipeline configuration JSON files.
-   `tests/`: Unit tests for various components.
-   `docs/`: Documentation files.

## Adding a New Built-in Tool

To extend the framework with a new tool (e.g., a `FileReadTool`):

1.  **Define the Tool Class:**
    -   Create a new Python class in `tools/built_in_tools.py` (or a new file within the `tools` directory, ensuring it's imported into `tools/__init__.py`).
    -   This class must inherit from `BaseTool` (defined in `tools/base_tool.py`).
    -   Implement the `__init__(self, tool_config: dict)` method. Store any necessary configuration from `tool_config`.
    -   Implement the `execute(self, inputs: dict) -> dict` method.
        -   `inputs`: A dictionary where keys are the input names defined in the agent's `inputs` config, and values are the actual data fetched from the `pipeline_state`.
        -   This method should perform the tool's logic and return a dictionary where keys are the output names (as defined in the agent's `outputs` list in the JSON config) and values are the results.

    **Example (`FileReadTool` skeleton in `tools/built_in_tools.py`):**
    ```python
    from .base_tool import BaseTool
    import os

    class FileReadTool(BaseTool):
        def __init__(self, tool_config: dict):
            super().__init__(tool_config)
            self.filepath = tool_config.get("path")
            if not self.filepath:
                raise ValueError("FileReadTool requires 'path' in tool_config")

        def execute(self, inputs: dict) -> dict:
            # 'inputs' might be unused if filepath is solely from tool_config
            # Or, filepath could be dynamic: self.filepath = inputs.get("filepath_from_state")

            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {"file_content": content} # "file_content" must match an output name in agent's JSON
            except Exception as e:
                return {"error": str(e)}
    ```

2.  **Register the Tool:**
    -   Open `tools/__init__.py`.
    -   Import your new tool class.
    -   Add an entry to the `TOOL_REGISTRY` dictionary. The key is the `tool_name` you'll use in the JSON configuration, and the value is the class itself.

    **Example (`tools/__init__.py` modification):**
    ```python
    from .built_in_tools import StructuredDataParserTool, RegexParserTool, FileReadTool # Added FileReadTool

    TOOL_REGISTRY = {
        "StructuredDataParserTool": StructuredDataParserTool,
        "RegexParserTool": RegexParserTool,
        "FileReadTool": FileReadTool, # Added FileReadTool
        # Add other tools here
    }

    def get_tool(tool_name: str, tool_config: dict):
        if tool_name not in TOOL_REGISTRY:
            raise ValueError(f"Tool '{tool_name}' not recognized.")
        return TOOL_REGISTRY[tool_name](tool_config)
    ```

3.  **Write Tool Configuration for JSON:**
    -   Now you can use `"FileReadTool"` in your `pipeline_config.json`:
    ```json
    {
      "id": "read_my_file",
      "type": "tool_agent",
      "inputs": {}, // Or inputs if the tool needs them dynamically
      "outputs": ["file_content", "error"], // Ensure "file_content" or "error" is returned by execute()
      "tool_name": "FileReadTool",
      "tool_config": {
        "path": "./my_data/input.txt"
      }
    }
    ```

4.  **Add Documentation:**
    -   Update `docs/api_reference.md` with the details of your new tool: its `tool_name`, `tool_config` parameters, expected agent `inputs`, and agent `outputs`.

5.  **Write Tests:**
    -   Add unit tests for your new tool in the `tests/` directory (e.g., in `tests/test_tools.py` or a new test file).
    -   Test its normal operation and edge cases (e.g., file not found for `FileReadTool`).

## Development Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/theblackcat98/agentic-pipeline-framework.git
    cd agentic-pipeline-framework
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install dependencies, including the package in editable mode:**
    ```bash
    # First, install general dependencies which might include test runners or linters
    pip install -r requirements.txt
    # Then, install the package itself in editable mode
    pip install -e .
    ```

## Running Tests

Ensure all tests pass before submitting contributions.
```bash
python -m unittest discover tests
```
Or, if using a specific test runner like `pytest` (once configured):
```bash
pytest
```

## Coding Conventions

-   Follow PEP 8 Python style guidelines.
-   Use type hinting.
-   Write clear and concise docstrings for modules, classes, and functions.

## Publishing to PyPI (for Maintainers)

This section is for project maintainers.

1.  **Prerequisites:**
    -   Ensure `setup.py` (or `pyproject.toml` if using modern packaging) is correctly configured with the package name, version, author, description, classifiers, etc.
    -   Install `twine` and `build`:
        ```bash
        pip install twine build
        ```
    -   An account on [PyPI](https://pypi.org/).

2.  **Increment Version:**
    -   Update the version number in `setup.py` (or `__version__` variable, e.g., in `your_package_name/__init__.py`). Follow [semantic versioning](https://semver.org/).

3.  **Build the Package:**
    ```bash
    python -m build
    ```
    This will create a `dist/` directory with source and wheel (`.whl`) distributions.

4.  **Upload to TestPyPI (Optional but Recommended):**
    -   First, upload to TestPyPI to ensure everything works.
        ```bash
        twine upload --repository testpypi dist/*
        ```
        You'll be prompted for your TestPyPI username and password.
    -   You can then try installing from TestPyPI:
        ```bash
        pip install --index-url https://test.pypi.org/simple/ --no-deps your-package-name
        ```

5.  **Upload to PyPI (Live):**
    -   Once confirmed on TestPyPI, upload to the official PyPI:
        ```bash
        twine upload dist/*
        ```
        You'll be prompted for your PyPI username and password.

6.  **Tag the Release (Git):**
    -   Create a Git tag for the new version:
        ```bash
        git tag vX.Y.Z
        git push origin vX.Y.Z
        ```

## Contributing

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Make your changes, including tests and documentation.
4.  Ensure all tests pass.
5.  Submit a pull request to the main repository.
    -   Clearly describe the changes you've made and why.
    -   Reference any related issues.

We appreciate your contributions to making the Agentic Pipeline Framework better!

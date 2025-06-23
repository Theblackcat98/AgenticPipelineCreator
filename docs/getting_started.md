# Getting Started

This guide will walk you through setting up the Agentic Pipeline Framework and running your first example pipeline.

## Prerequisites

1.  **Python 3.8+**: Ensure you have Python 3.8 or a newer version installed. You can check your Python version by running `python --version`.
2.  **Ollama**: This framework uses Ollama to interact with local Large Language Models.
    -   Install Ollama from [ollama.com](https://ollama.com).
    -   Ensure the Ollama application is running.
3.  **LLM Model**: You need at least one LLM model pulled through Ollama for the framework to use. We recommend starting with a small, fast model for initial testing.
    ```bash
    ollama pull qwen2:0.5b
    ```
    You can replace `qwen2:0.5b` with any other model available on Ollama Hub.

## Installation

There are two primary ways to install the framework:

### 1. From PyPI (Recommended for Users)

Once the package is published to PyPI, you can install it using `pip`:

```bash
pip install agentic-pipeline-framework
```
*(This command will work once version 0.1.0 or later is published to PyPI.)*

After installation, the command `apf-run` will be available in your environment.

### 2. From Source (For Users and Developers)

If you want to use the latest version directly from the repository or contribute to development:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/theblackcat98/agentic-pipeline-framework.git
    cd agentic-pipeline-framework
    ```

2.  **Set up a virtual environment (recommended) and install:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

    Install the package. This will also install dependencies from `requirements.txt` via `setup.py`.
    ```bash
    pip install .
    ```
    For developers who want to install the package in editable mode (changes to source code are reflected immediately):
    ```bash
    pip install -e .
    ```
    This makes the `apf-run` command available and also allows running `python main.py ...`.

## Running an Example Pipeline

After installation (either from PyPI or source), you can run pipelines using the `apf-run` command or by directly executing `main.py` if you installed from source.

1.  **Using `apf-run` (after `pip install .` or from PyPI):**
    Ensure you are in a directory where your pipeline configuration files are accessible or provide a full path. If you cloned the repository, you can run:
    ```bash
    apf-run ./pipelines/pipeline_config.json
    ```
    Or for another example:
    ```bash
    apf-run ./pipelines/random_genre_lyrics_generation_pipeline.json
    ```

2.  **Using `python main.py` (if running from cloned source, especially before/without `pip install .`):**
    Navigate to the cloned project directory.
    ```bash
    python main.py ./pipelines/pipeline_config.json
    ```
    If you run `python main.py` without arguments, it will enter an interactive pipeline creation mode.

This will load the specified JSON, and the Orchestrator will begin executing the defined agents. You should see output in your console reflecting the pipeline's progress and final results.

## Next Steps

-   Learn how to **[Create Your Own Pipeline](pipeline_config_guide.md)**.
-   Explore the **[Built-in Tools](api_reference.md)** available.

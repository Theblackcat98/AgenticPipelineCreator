# 🗺️ Roadmap & Future Work

This framework is an MVP (Minimum Viable Product) with a solid foundation. We have exciting plans for future enhancements to make it even more powerful and versatile.

## Short-Term Goals (Next 1-3 Months)

-   [ ] **Advanced Routing Logic:**
    -   **Conditional Routing:** Implement `if/else` style branching based on agent outputs or conditions within the `pipeline_state`. This will allow for dynamic paths through the pipeline.
        -   *Potential `routing` syntax:*
          ```json
          "routing": {
            "agent_A": {
              "next_conditional": {
                "condition_source": "agent_A.output_name", // Value to check
                "condition_type": "equals/contains/greater_than",
                "condition_value": "some_value",
                "next_if_true": "agent_B",
                "next_if_false": "agent_C"
              }
            }
          }
          ```
    -   **Looping/Iteration:** Allow an agent or a sequence of agents to run multiple times, for example, processing items in a list.
-   [ ] **Expanded Built-in Tool Library:**
    -   **File I/O Tools (`FileTool`):** Reading from, writing to, and appending to local files. (Partially drafted in `planned_tool_implementation.md`).
    -   **Web Content Fetcher (`WebContentTool`):** Fetching raw HTML or text from URLs. (Partially drafted).
    -   **API Requester Tool (`ApiRequestTool`):** Generic tool for making HTTP requests (GET, POST, etc.) to external APIs. (Partially drafted).
-   [ ] **Enhanced LLM Agent Features:**
    -   **Streaming Support:** Enable real-time streaming of tokens from LLM agents for a more interactive experience, especially for long generations.
    -   **Function Calling/Tool Use (LLM-native):** For LLMs that support it, allow them to request execution of framework tools directly, rather than just parsing structured output.

## Medium-Term Goals (Next 3-6 Months)

-   [ ] **Multi-Provider LLM Support:**
    -   Add client implementations for other LLM providers beyond Ollama, such as:
        -   OpenAI (GPT models)
        -   Anthropic (Claude models)
        -   Google Gemini
    -   Abstract the LLM client interface to make it easier to plug in new providers.
-   [ ] **Parallel Execution (`fan-out/fan-in`):**
    -   Allow multiple agents to run concurrently if they don't have direct dependencies, and then collect their results for a subsequent agent.
-   [ ] **State Management Improvements:**
    -   More granular control over what parts of the `pipeline_state` are passed to each agent (to avoid overly large context for LLMs).
    -   Potentially offer options for alternative state backends for very large states or distributed execution.
-   [ ] **More Sophisticated Tooling:**
    -   **Data Mapping Tool (`DataMapperTool`):** For transforming data structures. (Partially drafted).
    -   **Code Execution Tool:** Safely execute sandboxed code snippets (e.g., Python scripts) as a pipeline step.
-   [ ] **Improved Debugging and Logging:**
    -   Visual pipeline execution tracer.
    -   More detailed and configurable logging for each agent's execution.
    -   `LoggerTool` for custom logging within pipelines. (Partially drafted).

## Long-Term Vision (6+ Months)

-   [ ] **GUI / Visual Pipeline Builder:**
    -   A web-based or desktop interface to visually design and configure pipelines by dragging and dropping agents and connecting them.
-   [ ] **Pipeline Versioning and Sharing:**
    -   A system for saving, versioning, and sharing pipeline configurations, perhaps through a central registry or by integrating with Git.
-   [ ] **Human-in-the-Loop:**
    -   Allow pipelines to pause and request human input or approval before continuing.
-   [ ] **Community Platform / Tool Marketplace:**
    -   A place for users to share their custom tools and pipeline configurations.
-   [ ] **Advanced Error Handling and Retries:**
    -   More robust mechanisms for defining retry strategies and fallback paths for failing agents.

## Contributing to the Roadmap

This roadmap is a living document and will evolve based on community feedback and development progress. If you have ideas for new features, tools, or improvements, or if you'd like to contribute to any of these items:

1.  **Open an Issue:** Please open an issue on GitHub to discuss your idea first. This helps ensure it aligns with the project's direction and avoids duplicated effort.
2.  **Contribute:** Check the [Developer Guide](developer_guide.md) for information on how to set up your environment and contribute code.

We are excited about the future of the Agentic Pipeline Framework and welcome your participation in shaping it!

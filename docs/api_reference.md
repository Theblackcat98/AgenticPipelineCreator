# Built-in Tools: API Reference

This document provides detailed information about the built-in tools available in the Agentic Pipeline Framework. Each tool can be used within a `tool_agent` in your `pipeline_config.json`.

## Using Tools

To use a tool, define an agent with `type: "tool_agent"` and specify the `tool_name` and `tool_config`.

**General `tool_agent` structure:**
```json
{
  "id": "my_tool_agent",
  "type": "tool_agent",
  "description": "Agent that uses a specific tool.",
  "inputs": {
    "input_for_tool": "source_agent.output_name"
    // ... other inputs as required by the tool's processing logic or tool_config
  },
  "outputs": ["tool_result_name"], // Define output names based on what the tool produces
  "tool_name": "SpecificToolName",
  "tool_config": {
    // Configuration specific to SpecificToolName
  }
}
```
The `inputs` for a `tool_agent` are used by the tool's execution logic. Some `tool_config` parameters might also reference values from `inputs` if the tool is designed to support dynamic configuration. However, typically, `tool_config` is static, and the primary dynamic data comes via the agent's `inputs` which are then processed by the tool.

---

## 1. `StructuredDataParserTool`

-   **`tool_name`: `StructuredDataParserTool`**
-   **Description**: An LLM-powered tool that extracts structured data (JSON) from natural language text based on provided instructions. This tool internally uses an LLM.
-   **`tool_config`**:
    | Key            | Type   | Description                                                                                                                               | Required |
    |----------------|--------|-------------------------------------------------------------------------------------------------------------------------------------------|----------|
    | `model`        | string | The name of the Ollama model to use for parsing (e.g., `qwen2:0.5b`).                                                                       | Yes      |
    | `instructions` | string | Detailed instructions for the LLM on what data to extract and the desired JSON format. You can use placeholders for inputs to the agent. For example, if the agent has an input `raw_text`, you can use `{raw_text}` in the instructions. | Yes      |
    | `temperature`  | float  | (Optional) LLM temperature for generation.                                                                                                | No       |
    | `max_tokens`   | int    | (Optional) LLM max tokens for generation.                                                                                                 | No       |
-   **Agent `inputs`**:
    -   The `inputs` should provide the text to be parsed. The names of these inputs can be referenced in the `instructions` field of `tool_config`. For example, if you have ` "inputs": {"user_complaint": "some_agent.text"}`, your instructions could be `Extract details from the following complaint: {user_complaint}. Format as JSON...`
-   **Agent `outputs`**:
    -   Typically, a single output name (e.g., `["parsed_data"]`). This output will contain the JSON object extracted by the LLM. If the LLM fails to produce valid JSON, the output might be an error message or the raw string.

**Example:**
```json
{
  "id": "extract_user_details",
  "type": "tool_agent",
  "inputs": {
    "email_body": "ingest_email_agent.body"
  },
  "outputs": ["extracted_info"],
  "tool_name": "StructuredDataParserTool",
  "tool_config": {
    "model": "qwen2:0.5b",
    "instructions": "Extract the user's name, email, and phone number from the following text: {email_body}. Return the information as a JSON object with keys 'name', 'email', and 'phone'."
  }
}
```
The `pipeline_state` would then have `extract_user_details.extracted_info` containing an object like `{"name": "John Doe", "email": "john.doe@example.com", "phone": "123-456-7890"}`.

---

## 2. `RegexParserTool`

-   **`tool_name`: `RegexParserTool`**
-   **Description**: Extracts data from text using one or more named regular expressions.
-   **`tool_config`**:
    | Key       | Type   | Description                                                                                                                                                                                                                            | Required |
    |-----------|--------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
    | `patterns`| object | A dictionary where keys are names for the extracted data (which will be keys in the output object) and values are the regular expression strings. Each regex should define what to extract (e.g., using capturing groups if needed, though the current implementation might just return the full match). | Yes      |
-   **Agent `inputs`**:
    -   Requires one primary input that provides the text to parse. Let's assume this input is named `text_to_search` in the agent's `inputs` map (e.g., `"inputs": {"text_to_search": "some_agent.output"}`). The tool will use the value of the *first key* in the `inputs` map as the text to apply regex on.
-   **Agent `outputs`**:
    -   Typically, a single output name (e.g., `["regex_matches"]`). This output will be an object where:
        -   Keys are the names provided in the `patterns` config.
        -   Values are arrays of all non-overlapping matches found for the corresponding regex. If a regex has capturing groups, the behavior might depend on the specific implementation (it might return a list of tuples of group matches, or just the first group / full match). *Current default behavior is likely to return a list of full matches for each pattern.*

**Example:**
```json
{
  "id": "find_ids_and_dates",
  "type": "tool_agent",
  "inputs": {
    "log_data": "load_log_file_agent.content" // This 'log_data' will be the text searched
  },
  "outputs": ["extracted_patterns"],
  "tool_name": "RegexParserTool",
  "tool_config": {
    "patterns": {
      "order_ids": "Order ID: (ORD-\\d+)", // Captures 'ORD-12345'
      "dates": "\\b\\d{4}-\\d{2}-\\d{2}\\b"   // Captures 'YYYY-MM-DD'
    }
  }
}
```
If `load_log_file_agent.content` was "User inquiry for Order ID: ORD-123. Date: 2023-10-26. Another Order ID: ORD-456.",
the `pipeline_state` would have `find_ids_and_dates.extracted_patterns` containing something like:
```json
{
  "order_ids": ["ORD-123", "ORD-456"], // Or potentially ["Order ID: ORD-123", "Order ID: ORD-456"] if group 1 is not specifically extracted.
                                      // Or if groups are extracted: [("ORD-123",), ("ORD-456",)]
  "dates": ["2023-10-26"]
}
```
*(The exact structure of matches, especially concerning capturing groups, should be tested or clarified from the tool's implementation in `tools/built_in_tools.py` if not explicitly stated here.)*

---

*(More tools will be documented here as they are added to the framework, based on `planned_tool_implementation.md` or new developments.)*

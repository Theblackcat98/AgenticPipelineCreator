# Creating Your Own Pipeline: The `pipeline_config.json` Guide

The `pipeline_config.json` file is the heart of the Agentic Pipeline Framework. It's where you declaratively define your entire workflow, from the initial data to the final output, including all agent logic and routing. This guide provides a comprehensive overview of its structure and how to configure it.

## Top-Level Structure

These are the main keys at the root of your JSON configuration file:

| Key             | Type   | Description                                                                                                | Required | Default |
|-----------------|--------|------------------------------------------------------------------------------------------------------------|----------|---------|
| `pipeline_name` | string | A descriptive name for your pipeline (e.g., "Email Summarizer and Auto-Responder").                          | Yes      |         |
| `description`   | string | (Optional) A brief description of what the pipeline does.                                                  | No       | `""`    |
| `initial_input` | any    | The initial data that the pipeline will start processing. This can be a string, number, object, or array. | Yes      |         |
| `start_agent`   | string | The `id` of the first agent to be executed in the pipeline.                                                | Yes      |         |
| `agents`        | array  | An array of agent objects that define the individual work units of the pipeline. See [Defining Agents](#defining-agents) below. | Yes      |         |
| `routing`       | object | A dictionary that defines the flow of control between agents. See [Defining Routing](#defining-routing) below.             | Yes      |         |
| `final_outputs` | object | (Optional) A mapping of user-friendly names to specific outputs from the `pipeline_state` to be presented at the end. See [Defining Final Outputs](#defining-final-outputs). | No       | `{}`    |

**Example:**
```json
{
  "pipeline_name": "Simple Greeting Pipeline",
  "description": "A basic pipeline that greets a user.",
  "initial_input": "World",
  "start_agent": "agent_greet",
  "agents": [
    // ... agent definitions ...
  ],
  "routing": {
    // ... routing definitions ...
  },
  "final_outputs": {
    // ... final output mapping ...
  }
}
```

## Defining Agents (`agents` array)

Each object within the `agents` array defines a single agent (a work unit). Agents can be LLM-based or tool-based.

### Common Agent Fields

These fields are common to all agent types:

| Key           | Type   | Description                                                                                                  | Required |
|---------------|--------|--------------------------------------------------------------------------------------------------------------|----------|
| `id`          | string | A unique identifier for this agent within the pipeline (e.g., `parse_user_request`, `summarize_text`).       | Yes      |
| `type`        | string | The type of agent. Must be either `llm_agent` or `tool_agent`.                                               | Yes      |
| `description` | string | (Optional) A human-readable description of what this specific agent does.                                    | No       |
| `inputs`      | object | A mapping of the agent's local input names to their sources in the `pipeline_state`. See [Defining Data Flow](#defining-data-flow-inputs-object). | Yes      |
| `outputs`     | array  | A list of string names for the outputs this agent will produce (e.g., `["summary", "category"]`). These are used to key the agent's results in the `pipeline_state`. | Yes      |

### `llm_agent` Specific Fields

Use the `llm_agent` type when you want an LLM to perform a task like text generation, classification, or transformation.

| Key               | Type   | Description                                                                                                 | Required | Default         |
|-------------------|--------|-------------------------------------------------------------------------------------------------------------|----------|-----------------|
| `model`           | string | The name of the Ollama model to use (e.g., `qwen2:0.5b`, `llama3:8b`). Ensure this model is pulled in Ollama. | Yes      |                 |
| `prompt_template` | string | The prompt to be sent to the LLM. Use `{input_name}` placeholders for dynamic data from the agent's `inputs` map. | Yes      |                 |
| `output_format`   | string | (Optional) Defines how to process the LLM's raw string output. Supported values:<ul><li>`"string"` (default): The output is treated as a raw string.</li><li>`"json"`: The framework will attempt to parse the LLM's string output as a JSON object. The agent's first output name (from `outputs` array) will store the parsed JSON object.</li><li>`"list"`: The framework will attempt to parse the LLM's string output as a list (e.g., lines separated by newlines, or a simple bulleted list). Specific parsing logic might vary.</li></ul> | No       | `"string"`      |
| `temperature`     | float  | (Optional) Controls randomness. Lower is more deterministic. (e.g., 0.7)                                     | No       | Model default |
| `max_tokens`      | int    | (Optional) Maximum number of tokens to generate.                                                            | No       | Model default |

**Example `llm_agent`:**
```json
{
  "id": "generate_summary",
  "type": "llm_agent",
  "description": "Generates a summary of the input text.",
  "inputs": {
    "text_to_summarize": "previous_agent.full_text"
  },
  "outputs": ["summary_text"],
  "model": "qwen2:0.5b",
  "prompt_template": "Please summarize the following text: {text_to_summarize}",
  "output_format": "string"
}
```

### `tool_agent` Specific Fields

Use the `tool_agent` type to leverage pre-built, non-LLM capabilities for specific tasks.

| Key           | Type   | Description                                                                                                | Required |
|---------------|--------|------------------------------------------------------------------------------------------------------------|----------|
| `tool_name`   | string | The registered name of the built-in tool to use (e.g., `StructuredDataParserTool`, `RegexParserTool`). See [API Reference](api_reference.md) for available tools. | Yes      |
| `tool_config` | object | A JSON object containing specific configuration parameters required by the chosen tool. The structure of this object depends on the tool. Refer to the tool's documentation in the [API Reference](api_reference.md). | Yes      |

**Example `tool_agent`:**
```json
{
  "id": "extract_email_address",
  "type": "tool_agent",
  "description": "Extracts email addresses from text using regex.",
  "inputs": {
    "text_content": "fetch_webpage.raw_html"
  },
  "outputs": ["emails_found"],
  "tool_name": "RegexParserTool",
  "tool_config": {
    "patterns": {
      "email": "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"
    }
  }
}
```

## Defining Data Flow (`inputs` object)

The `inputs` object for each agent specifies where it should get its data from. This data comes from the `pipeline_state`, which is a central dictionary accumulating outputs from all previously executed agents.

The format for each entry in the `inputs` object is:
`"local_input_name_for_agent": "source_in_pipeline_state"`

**Sources can be:**

1.  **Initial Pipeline Input:** `pipeline.initial_input`
    -   Used by the first agent(s) to access the data provided in the top-level `initial_input` field of the configuration.
    ```json
    "inputs": {
      "user_query": "pipeline.initial_input"
    }
    ```

2.  **Output from Another Agent:** `source_agent_id.output_name`
    -   `source_agent_id` is the `id` of a previously run agent.
    -   `output_name` is one of the names defined in that source agent's `outputs` array.
    ```json
    "inputs": {
      "document_text": "load_file_agent.file_content"
    }
    ```
    If an agent's output is a dictionary (e.g., from an LLM with `output_format: "json"` or a tool like `StructuredDataParserTool`), you can access nested values using dot notation:
    ```json
    "inputs": {
      "customer_name": "extract_data_agent.parsed_data.name",
      "order_id": "extract_data_agent.parsed_data.order.id"
    }
    ```

**Example `inputs` mapping:**
If `agent_A` produces `{"output1": "hello", "output2": {"nested_value": "world"}}`:
```json
// agent_A definition
{
  "id": "agent_A",
  "type": "...",
  "outputs": ["output1", "output2"],
  // ...
}

// agent_B definition, using outputs from agent_A
{
  "id": "agent_B",
  "type": "...",
  "inputs": {
    "my_greeting": "agent_A.output1", // "hello"
    "deep_value": "agent_A.output2.nested_value" // "world"
  },
  "outputs": ["processed_data"],
  // ...
}
```

## Defining Routing (`routing` object)

The `routing` object defines the execution path of the pipeline. It specifies which agent to run after a given agent completes.

-   The keys in the `routing` object are the `id` of a source agent.
-   The value for each key is an object that determines the next step.

### Simple Linear Routing

For a simple sequential flow, the value object contains a `"next"` key, which specifies the `id` of the next agent to run.
If `"next"` is `null` or an empty string (`""`), the pipeline terminates after the current agent successfully executes.

**Example:**
```json
"routing": {
  "agent_A": { "next": "agent_B" },
  "agent_B": { "next": "agent_C" },
  "agent_C": { "next": null } // Pipeline ends after agent_C
}
```
If `agent_A` is the `start_agent`, the execution order will be A -> B -> C.

*(Note: The current MVP supports only this simple linear routing. Advanced routing like conditional or parallel execution is planned for future versions.)*

## Defining Final Outputs (`final_outputs` object)

The optional `final_outputs` object allows you to define a clean, user-friendly presentation of the pipeline's results. It maps custom names to specific values within the final `pipeline_state`.

The format for each entry is:
`"user_friendly_name": "source_agent_id.output_name_in_pipeline_state"`

This is useful for extracting only the most relevant pieces of information from the potentially large `pipeline_state`.

**Example:**
Suppose `agent_summarize` produces an output named `text_summary`, and `agent_create_ticket` produces `ticket_url`.
```json
"final_outputs": {
  "Generated Summary": "agent_summarize.text_summary",
  "Support Ticket URL": "agent_create_ticket.ticket_url",
  "OriginalInput": "pipeline.initial_input" // You can also reference the initial input
}
```
When the pipeline completes, the orchestrator will display these mapped outputs. If `final_outputs` is omitted or empty, the entire `pipeline_state` might be returned (behavior can vary).

---

By understanding these components, you can construct complex and powerful workflows tailored to your specific needs, all without writing any Python code. Refer to the example pipelines in the `pipelines/` directory for practical implementations.

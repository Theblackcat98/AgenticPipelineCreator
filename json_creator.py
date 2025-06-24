import os
import json
import re
import ollama

# --- Constants (mirroring TypeScript) ---
# Ensure you use a model name compatible with the Python SDK
# and your Gemini API access.
OLLAMA_MODEL = 'phi4:latest'

# This is the same JSON string template as in your constants.ts
USER_JSON_PIPELINE_TEMPLATE = """
{
  "pipeline_name": "AI-Content-Generation-Pipeline",
  "initial_input": "Write a 4-chapter sci-fi story for adults about a rogue AI on Mars that develops a sense of humor. The mood should be dark but witty.",
  "start_agent": "parse_user_request",
  "agents": [
    {
      "id": "parse_user_request",
      "type": "tool_agent",
      "tool_name": "StructuredDataParserTool",
      "description": "Parses user message into structured content parameters.",
      "inputs": {
        "natural_language_request": "pipeline.initial_input"
      },
      "outputs": [ "title", "topic", "mood", "num_chapters" ],
      "tool_config": {
        "model": "phi4:latest",
        "instructions": "The user wants to write a story. Extract the title, topic, mood, and number of chapters from their request."
      }
    },
    {
      "id": "generate_chapter_descriptions",
      "type": "llm_agent",
      "model": "phi4:latest",
      "description": "Generates descriptions for each chapter.",
      "prompt_template": "The story is about '{topic}' with a '{mood}' mood. Generate a creative, one-sentence description for each of the {num_chapters} chapters. Respond with a list. Do not write anything else.",
      "inputs": {
        "topic": "parse_user_request.topic",
        "mood": "parse_user_request.mood",
        "num_chapters": "parse_user_request.num_chapters"
      },
      "outputs": [ "chapter_descriptions" ],
      "output_format": "list"
    },
    {
      "id": "write_chapters",
      "type": "llm_agent",
      "model": "phi4:latest",
      "description": "Writes the content for each chapter.",
      "prompt_template": "You are a master storyteller. Write the full content for a story titled '{title}'. The topic is '{topic}' and the mood is '{mood}'. Use the following chapter descriptions as a strict outline: {chapter_descriptions}.",
      "inputs": {
        "title": "parse_user_request.title",
        "topic": "parse_user_request.topic",
        "mood": "parse_user_request.mood",
        "chapter_descriptions": "generate_chapter_descriptions.chapter_descriptions"
      },
      "outputs": [ "full_story_content" ]
    }
  ],
  "routing": {
    "parse_user_request": {
      "next": "generate_chapter_descriptions"
    },
    "generate_chapter_descriptions": {
      "next": "write_chapters"
    },
    "write_chapters": {
      "next": null
    }
  },
  "final_outputs": {
    "outline": "generate_chapter_descriptions.chapter_descriptions",
    "story": "write_chapters.full_story_content",
    "source_topic": "parse_user_request.topic"
  }
}
"""

def generate_pipeline_json_python(natural_language_input: str) -> dict:
    """
    Generates a pipeline JSON definition from natural language input using Ollama.
    Returns a Python dictionary representing the parsed JSON.
    """
    prompt = f"""
You are an AI assistant specialized in creating data processing pipeline definitions in JSON format.
Your task is to convert the user's natural language description of a pipeline into a valid JSON object.
Your response MUST be the JSON object itself, and nothing else. Do not add any explanatory text, apologies, or any characters before the opening `{` or after the closing `}` of the JSON.

The JSON object MUST strictly follow the structure and schema exemplified.

**Main Structural Template (Adhere to this structure):**
```json
{USER_JSON_PIPELINE_TEMPLATE}
```
The `USER_JSON_PIPELINE_TEMPLATE` above defines the strict structural schema you MUST follow for complex pipelines. All top-level keys shown in that template are mandatory if applicable to the user's request.

**Minimal Valid Pipeline Example (for very simple requests):**
```json
{
  "pipeline_name": "MinimalExamplePipeline",
  "initial_input": "User's simple request",
  "start_agent": "agent_1",
  "agents": [
    {
      "id": "agent_1",
      "type": "llm_agent",
      "model": "phi4:latest",
      "description": "Processes the initial input.",
      "prompt_template": "Process this: {data}",
      "inputs": { "data": "pipeline.initial_input" },
      "outputs": [ "result" ]
    }
  ],
  "routing": {
    "agent_1": { "next": null }
  },
  "final_outputs": {
    "final_result": "agent_1.result"
  }
}
```

**Critical JSON Formatting Rules (ABSOLUTE REQUIREMENTS):**
- Your entire response MUST consist ONLY of the JSON object. No introductory/explanatory text, no markdown formatting surrounding the JSON.
- All keys and string values MUST be enclosed in double quotes (e.g., `"key": "value"`).
- No trailing commas in objects or arrays (e.g., `{{ "a": 1, }}` is INVALID).
- All braces `{{}}` and brackets `[]` must be correctly paired.
- Boolean values (`true`, `false`) must NOT be enclosed in quotes.
- Numeric values must NOT be enclosed in quotes.
- The value `null` (without quotes) MUST be used for absent optional fields or when a null value is explicitly intended by the schema (e.g. `"next": null`).
- Ensure absolutely NO characters (like comments or extra text) exist outside the main JSON object structure (i.e., before the first `{` or after the final `}}`).

**Key Considerations When Generating JSON Content (Follow these carefully):**

1.  **`pipeline_name`**: Infer a descriptive, CamelCase name (e.g., "CustomerInquiryProcessing").
2.  **`initial_input`**: (Optional) Initial data for the pipeline.
3.  **`start_agent`**: The `id` of the first agent in the `agents` list.
4.  **`agents`**: A list of agent objects.
    *   **`id`**: Unique, snake_case ID (e.g., `parse_data`).
    *   **`type`**: `llm_agent` or `tool_agent`.
    *   **`description`**: Concise agent purpose.
    *   **`inputs`**: A dictionary mapping input names to their sources (e.g., `{{"topic": "parse_request.topic"}}`). For the first agent, use `"pipeline.initial_input"`.
    *   **`outputs`**: A list of output names (e.g., `["summary", "category"]`).
    *   **For `llm_agent`**:
        *   `model`: e.g., "{OLLAMA_MODEL}".
        *   `prompt_template`: Use `{{variable}}` for placeholders.
        *   `output_format`: (Optional) "list", "json", "string".
    *   **For `tool_agent`**:
        *   `tool_name`: Choose from "RegexParserTool", "StructuredDataParserTool", "CodeExecutionTool", "ConditionalRouterTool", "DataAggregatorTool".
        *   `tool_config`: Configuration for the tool. See details below.

5.  **Tool-Specific `tool_config` Instructions**:

    *   **`StructuredDataParserTool`**:
        *   `model`: The LLM to use for parsing (e.g., "{OLLAMA_MODEL}").
        *   `instructions`: A clear command for the LLM (e.g., "Extract the user's name and email.").

    *   **`ConditionalRouterTool` for Looping with Data Aggregation**:
        *   This is the most complex tool. Use it to repeat a set of agents and collect their outputs.
        *   **`loop_config`**:
            *   `total_iterations_from`: The input source that specifies the number of loops (e.g., `"parse_request.num_items"`).
            *   `loop_body_start_id`: The `id` of the first agent inside the loop.
            *   `counter_name`: A unique name for the internal loop counter (e.g., `"loop_counter"`).
            *   `accumulators`: A dictionary to collect data.
                *   The **key** is the name of the final output list (e.g., `"all_summaries"`).
                *   The **value** is the input source to collect on each iteration (e.g., `"summarize_step.summary"`).
            *   `loop_body_agents`: A list of agent IDs that are part of the loop's body. The outputs of these agents will be cleared before each new iteration of the loop. This is CRUCIAL for correct loop behavior (e.g., `["summarize_step", "another_agent_in_loop"]`).
        *   **Example `ConditionalRouterTool` Agent for Looping**:
            ```json
            {{
              "id": "loop_controller",
              "type": "tool_agent",
              "tool_name": "ConditionalRouterTool",
              "description": "Repeats the summary process for 'num_items' times and collects all summaries.",
              "inputs": {{
                "num_items": "parse_request.num_items", // This input determines how many times to loop
                "item_to_process": "get_item_step.current_item" // Example of an input needed by the loop body, if the router itself doesn't directly use it for accumulation
                // Add inputs that are sources for the 'accumulators' here
                // "summary_from_body": "summarize_step.summary" // This is what will be collected
              }},
              // Outputs of the router tool itself, typically the accumulated lists
              "outputs": ["all_summaries", "loop_counter_final_value"],
              "tool_config": {{
                "loop_config": {{
                  "total_iterations_from": "num_items", // The input that provides the number of iterations
                  "loop_body_start_id": "summarize_step", // The ID of the first agent in the sequence to be repeated
                  "counter_name": "summary_loop_counter",   // An internal name for the loop counter variable
                  "loop_body_agents": [ // CRUCIAL: List of agent IDs within the loop body whose outputs need to be cleared for re-execution
                    "summarize_step"
                    // "another_agent_in_loop_if_any"
                  ],
                  "accumulators": {{
                    // "output_list_name": "input_source_for_accumulation"
                    "all_summaries": "summarize_step.summary" // Collects 'summarize_step.summary' into 'all_summaries' list
                  }}
                }},
                // "else_execute_step": "agent_after_loop" // The agent to go to after the loop finishes. Can be null.
                "else_execute_step": null
              }}
            }}
            ```

6.  **`routing`**:
    *   Each agent `id` must be a key.
    *   `next`: The `id` of the next agent, or `null` if it's the end.
    *   For a loop, the last agent in the loop body should route back to the `ConditionalRouterTool` agent.

7.  **`final_outputs`**:
    *   A dictionary mapping a descriptive name to a final output from an agent (e.g., `{{"Final Report": "loop_controller.all_summaries"}}`).

User's pipeline description:
"{natural_language_input}"

Generate ONLY the JSON object.
"""
    raw_response_text = ""
    try:
        # Use ollama.chat to get a structured response
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': 0.0} # Set temperature to 0 for deterministic JSON output
        )
        
        raw_response_text = response['message']['content']
        
        # It's good practice to strip and check for markdown fences.
        json_str = raw_response_text.strip()
        
        # Attempt to extract JSON block, allowing for optional markdown fences and surrounding text
        # This looks for the first '{' to the last '}' or the first '[' to the last ']'
        match = re.search(r"^\s*(?:```(?:json)?\s*)?(\{.*\})[;\s]*?(?:```)?\s*$", json_str, re.DOTALL)
        if not match:
            match = re.search(r"^\s*(?:```(?:json)?\s*)?(\[.*\])[;\s]*?(?:```)?\s*$", json_str, re.DOTALL)

        if match:
            json_str = match.group(1).strip()
        else:
            # If no clear block is found, and there are fences, try the old method as a fallback.
            # This handles cases where the LLM might put text outside the fences but the core JSON is within.
            fence_match_fallback = re.search(r"```(?:json)?\s*(.*?)\s*```", json_str, re.DOTALL)
            if fence_match_fallback:
                json_str = fence_match_fallback.group(1).strip()
            # If still no match, it will likely fail json.loads, which is handled.
            
        parsed_data = json.loads(json_str)

        # Basic validation
        if not isinstance(parsed_data, dict):
            raise ValueError("Generated JSON is not a valid dictionary.")
        
        required_keys = ["pipeline_name", "agents", "routing", "start_agent"]
        for key in required_keys:
            if key not in parsed_data:
                raise ValueError(f"Generated JSON is incomplete. Essential field '{key}' is missing.")
        
        return parsed_data

    except json.JSONDecodeError as e:
        error_message = f"API Error: Failed to parse JSON response - {e}. Raw response was: '{raw_response_text}'"
        raise ValueError(error_message) from e
    except ValueError as e: # Specific ValueErrors should be re-raised directly
        raise
    except Exception as e:
        error_message = f"Failed to generate pipeline from Ollama: {type(e).__name__} - {e}. Raw response (if available): '{raw_response_text}'"
        raise RuntimeError(error_message) from e
def create_and_save_pipeline() -> str:
    """
    Guides the user through creating a pipeline from natural language,
    generates the JSON, saves it, and returns the file path.

    Returns:
        The path to the newly created pipeline JSON file.
    """
    # --- 1. Get User Input ---
    print("🚀 Let's create a new AI Pipeline.")
    print("Please describe the pipeline you want to build in plain English:")
    natural_language_input = input("> ")

    # --- 2. Generate and Save ---
    try:
        print("\nGenerating pipeline configuration...")
        pipeline_json = generate_pipeline_json_python(natural_language_input)
        
        # --- 3. Save the Output to a File ---
        output_dir = "pipelines"
        os.makedirs(output_dir, exist_ok=True)

        pipeline_name = pipeline_json.get("pipeline_name", "untitled_pipeline")

        # Sanitize the pipeline name for use as a filename (Logic 4.0)
        # 1. Convert CamelCase to snake_case.
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', pipeline_name).lower()
        # 2. Replace any character that is not lowercase alphanumeric or underscore, with an underscore.
        #    This handles spaces, hyphens, and other special characters by replacing sequences of them with a single underscore.
        name = re.sub(r'[^a-z0-9_]+', '_', name)
        # 3. Consolidate multiple underscores (e.g., "a___b" -> "a_b").
        name = re.sub(r'_+', '_', name)
        # 4. Remove leading/trailing underscores (e.g., "_ab_" -> "ab").
        name = name.strip('_')
        # 5. If the name becomes empty after sanitization (e.g., "!!!"), default it.
        if not name:
            name = "untitled_pipeline"
        output_filename = f"{name}.json"
        output_path = os.path.join(output_dir, output_filename)

        with open(output_path, "w") as f:
            json.dump(pipeline_json, f, indent=2)
            
        print(f"\n✅ Configuration saved to '{output_path}'")
        return output_path

    except (ValueError, RuntimeError) as e:
        print(f"\n❌ An error occurred during pipeline creation: {e}")
        raise  # Re-raise the exception to be handled by the caller if needed


if __name__ == "__main__":
    # This allows the script to be run standalone for testing or manual creation.
    try:
        create_and_save_pipeline()
    except (ValueError, RuntimeError):
        # The error is already printed, so we can just exit gracefully.
        pass
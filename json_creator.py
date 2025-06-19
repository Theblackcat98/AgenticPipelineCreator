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
The JSON object MUST strictly follow the structure and schema exemplified below.

JSON Schema Example (use this exact structure, ensuring all described fields are present if applicable):
```json
{USER_JSON_PIPELINE_TEMPLATE}
```

Critical JSON Formatting Rules:
- The entire response MUST be ONLY the JSON object. Do not include any introductory text, explanations, or markdown formatting.
- All keys and string values must be enclosed in double quotes.
- No trailing commas in objects or arrays.
- All braces `{{}}` and brackets `[]` must be correctly paired.

Key considerations when generating the JSON content:

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
        *   **Example `ConditionalRouterTool` Agent**:
            ```json
            {{
              "id": "loop_controller",
              "type": "tool_agent",
              "tool_name": "ConditionalRouterTool",
              "description": "Repeats the summary process and collects all summaries.",
              "inputs": {{
                "num_items": "parse_request.num_items",
                "summary": "summarize_step.summary"
              }},
              "outputs": ["all_summaries"],
              "tool_config": {{
                "loop_config": {{
                  "total_iterations_from": "num_items",
                  "loop_body_start_id": "summarize_step",
                  "counter_name": "summary_loop_counter",
                  "accumulators": {{
                    "all_summaries": "summary"
                  }}
                }},
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
        
        # Regex to remove potential markdown fences (e.g., ```json ... ``` or ``` ... ```)
        fence_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", json_str, re.DOTALL)
        if fence_match:
            json_str = fence_match.group(1).strip()
            
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
        sanitized_name = re.sub(r'[^a-zA-Z0-9_]', '_', pipeline_name)
        snake_case_name = re.sub(r'(?<!^)(?=[A-Z])', '_', sanitized_name).lower()
        output_filename = f"{snake_case_name}.json"
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
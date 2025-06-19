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

Critical JSON Formatting Rules:

    The entire response MUST be ONLY the JSON object. Do not include any introductory text, explanations, apologies, or markdown formatting (like ```json) around the JSON object itself.

    Ensure all string values are enclosed in double quotes (e.g., "value").

    All keys must be enclosed in double quotes (e.g., "key").

    Ensure commas are correctly placed:

        Between key-value pairs in an object (e.g., {{"key1": "value1", "key2": "value2"}}).

        Between elements in an array (e.g., ["item1", "item2"]).

    There must NOT be any trailing commas after the last element in an object or array.

    All curly braces {{{{}}}} for objects and square brackets [] for arrays must be correctly paired and nested.

    Pay very close attention to escaping special characters within strings if necessary (e.g., for regex patterns in tool_config, a newline character should be represented as '\\\\n').

Key considerations when generating the JSON content:

    pipeline_name: Infer a descriptive name for the pipeline (e.g., "Customer-Inquiry-Processing").

    initial_input: (Optional) If the user's request implies an initial piece of data for the pipeline, include it here as a string.

    start_agent: Must be the ID of the first agent. This ID must exist in the 'agents' list.

    agents:

        id: Unique, descriptive, snake_case IDs (e.g., 'parse_data', 'summarize_text').

        type: 'tool_agent' or 'llm_agent'.

        tool_name / model:

            'tool_agent': Conceptual 'tool_name' (e.g., "RegexParserTool", "StructuredDataParserTool").

            'llm_agent': Use a placeholder model like "phi4:latest" or the specific model if provided (e.g., "{OLLAMA_MODEL}").

        description: Concise agent purpose.

        inputs: For the first agent, if 'initial_input' is present in the pipeline, its input can be "pipeline.initial_input". Otherwise, it could be a placeholder like "User query". For other agents, reference outputs like 'previous_agent_id.output_name'. Ensure referenced IDs and outputs exist.

        outputs: List of output names (strings).

        tool_config: (Required for 'tool_agent') Conceptual config. For "StructuredDataParserTool", include 'model' and 'instructions'. For "RegexParserTool", include 'patterns'. If not specified, use {{{{}}}}.

        prompt_template: (Required for 'llm_agent') Template for the prompt. Use single curly braces for variables, like 'A story about {{topic}}'.

        output_format: (Optional for 'llm_agent') Can be "list", "json", "string", etc.

    routing: Each agent ID from 'agents' must be a key. 'next' is a subsequent agent ID or 'null'. Ensure all IDs are consistent.

    final_outputs: (Optional) A dictionary specifying which agent outputs should be considered the final results of the pipeline, e.g., {{"final_summary": "summarize_text_agent.summary"}}.

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
if __name__ == "__main__":
    # --- 1. Get User Input ---
    print("🚀 Welcome to the AI Pipeline JSON Generator!")
    print("Please describe the pipeline you want to create.")
    natural_language_input = input("> ")

    # --- 2. Generate the Pipeline JSON ---
    try:
        print("\nGenerating pipeline configuration...")
        pipeline_json = generate_pipeline_json_python(natural_language_input)
        
        # --- 3. Pretty-Print the Output to Console ---
        print("\n✅ Successfully generated pipeline configuration:")
        print("-" * 50)
        print(json.dumps(pipeline_json, indent=2))
        print("-" * 50)

        # --- 4. Save the Output to a File ---
        # Create the 'pipelines' directory if it doesn't exist
        output_dir = "pipelines"
        os.makedirs(output_dir, exist_ok=True)

        # Sanitize the pipeline name to create a valid filename
        pipeline_name = pipeline_json.get("pipeline_name", "untitled_pipeline")
        # Replace non-alphanumeric characters with underscores
        sanitized_name = re.sub(r'[^a-zA-Z0-9_]', '_', pipeline_name)
        # Convert to snake_case
        snake_case_name = re.sub(r'(?<!^)(?=[A-Z])', '_', sanitized_name).lower()
        output_filename = f"{snake_case_name}.json"
        
        output_path = os.path.join(output_dir, output_filename)

        with open(output_path, "w") as f:
            json.dump(pipeline_json, f, indent=2)
        print(f"\n✅ Configuration saved to '{output_path}'")

    except (ValueError, RuntimeError) as e:
        print(f"\n❌ An error occurred: {e}")
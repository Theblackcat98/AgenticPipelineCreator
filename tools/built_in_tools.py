import re
import json
from .base_tool import BaseTool
from typing import Callable, List

# --- Tool #1: Regex Parser ---
# The orchestrator tries to import this, so it must be defined here.
class RegexParserTool(BaseTool):
    """
    A generic tool to extract data from text using named regex patterns.
    """
    def execute(self, inputs: dict, config: dict, **kwargs) -> dict:
        text_to_parse = inputs.get("text_to_parse")
        if not text_to_parse:
            raise ValueError("RegexParserTool requires 'text_to_parse' in inputs.")

        patterns = config.get("patterns", {})
        body_pattern_config = config.get("body_pattern", {})
        results = {}

        for key, pattern in patterns.items():
            match = re.search(pattern, text_to_parse)
            results[key] = match.group(1).strip() if match else "Not found"
        
        if body_pattern_config:
            pattern = body_pattern_config.get("pattern")
            flags_str = body_pattern_config.get("flags", [])
            
            re_flags = 0
            for flag in flags_str:
                if hasattr(re, flag):
                    re_flags |= getattr(re, flag)
            
            match = re.search(pattern, text_to_parse, re_flags)
            results["body"] = match.group(1).strip() if match else ""

        return results


# --- Tool #2: Structured Data Parser (LLM-Powered) ---
# This is the class definition that was likely missing or misspelled.
class StructuredDataParserTool(BaseTool):
    """
    An LLM-powered tool to extract structured data from natural language.
    It takes a request and a list of desired fields, and returns a JSON object.
    """
    def execute(self, inputs: dict, config: dict, invoke_llm: Callable, output_fields: List[str], **kwargs) -> dict:
        """
        Uses an LLM to parse the input text.
        """
        request_text = inputs.get("natural_language_request")
        if not request_text:
            raise ValueError("StructuredDataParserTool requires 'natural_language_request' in inputs.")

        model = config.get("model")
        instructions = config.get("instructions", "Extract the requested fields.")
        if not model:
            raise ValueError("StructuredDataParserTool requires 'model' in its tool_config.")

        prompt = (
            f"You are an expert data extraction tool. Your sole purpose is to "
            f"extract structured data from a user's request and respond ONLY with a valid JSON object. "
            f"\n\nExtraction Instructions: {instructions}"
            f"\nDesired JSON keys: {', '.join(output_fields)}"
            f"\n\nUser Request: \"{request_text}\""
            f"\n\nJSON Output:"
        )

        response_str = invoke_llm(model, prompt)

        try:
            json_match = re.search(r'\{.*\}', response_str, re.DOTALL)
            if json_match:
                response_str = json_match.group(0)
            
            parsed_json = json.loads(response_str)
            
            for field in output_fields:
                if field not in parsed_json:
                    parsed_json[field] = "Not found"
            
            return parsed_json
        except json.JSONDecodeError:
            print(f"Warning: StructuredDataParserTool failed to parse LLM response into JSON: {response_str}")
            return {field: "Error: Failed to parse" for field in output_fields}

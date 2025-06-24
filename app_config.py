import os

# Default model for general LLM agent tasks
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "phi4:latest")

# Default model for structured data parsing tasks (used by StructuredDataParserTool)
DEFAULT_STRUCTURED_DATA_MODEL = os.getenv("DEFAULT_STRUCTURED_DATA_MODEL", "phi4:latest")

# You can add other configurations here as needed
# For example:
# LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# print(f"CONFIG: DEFAULT_LLM_MODEL set to '{DEFAULT_LLM_MODEL}'") # Commented out for cleaner test output
# print(f"CONFIG: DEFAULT_STRUCTURED_DATA_MODEL set to '{DEFAULT_STRUCTURED_DATA_MODEL}'") # Commented out for cleaner test output

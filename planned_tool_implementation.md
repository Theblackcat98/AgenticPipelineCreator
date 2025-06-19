# Planned Tool Implementation

This document outlines the specifications for tools that are planned for future implementation in the framework.

## 1. Data Input/Output (I/O) Tools

### File I/O Tool (`FileTool`)
- **Purpose**: Reads from or writes/appends to local files. This is a foundational capability for any data processing framework.
- **Config**: `{ "action": "read/write/append", "path": "path/to/file", "content_from": "(for write/append) step_name.output_key" }`
- **Example**: Read a user's email from a text file to kick off a processing pipeline.

### Web Content Fetcher Tool (`WebContentTool`)
- **Purpose**: Fetches raw HTML or text content from a given URL.
- **Config**: `{ "url": "https://example.com", "extract": "text/html" }`
- **Example**: Scrape a product page for its description and price.

### API Requester Tool (`ApiRequestTool`)
- **Purpose**: A generic tool for making HTTP requests (GET, POST, etc.) to external APIs.
- **Config**: `{ "method": "POST", "url": "https://api.service.com/endpoint", "headers_from": "step_name.output_key", "payload_from": "step_name.output_key" }`
- **Example**: Send extracted data to a CRM via its REST API.

## 2. Data Transformation Tools

### Data Mapping Tool (`DataMapperTool`)
- **Purpose**: Remaps keys and transforms values from a dictionary input.
- **Config**: `{ "mapping": { "new_key_1": "old_key_a", "new_key_2": "static_value" }, "value_transformations": { "new_key_1": "upper/lower/title" } }`
- **Example**: Standardize data extracted from different sources into a single, consistent format.

## 3. Utility Tools

### Logging Tool (`LoggerTool`)
- **Purpose**: Logs messages to the console or a file, which is invaluable for debugging.
- **Config**: `{ "level": "INFO/WARN/ERROR", "message": "Processing item: {item_id}", "message_vars": ["item_id"] }`
- **Example**: Log the ID of each item as it's being processed in a loop.
import ollama

def invoke_llm(model: str, prompt: str) -> str:
    """
    Invokes the specified Ollama model with a given prompt.
    """
    print(f"\n----- Calling LLM: {model} -----")
    print(f"Prompt: {prompt}")
    try:
        response = ollama.chat(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': 0.0} # For deterministic output
        )
        content = response['message']['content'].strip()
        print(f"LLM Response: {content}")
        print("------------------------------")
        return content
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return "Error: Could not get response from LLM."

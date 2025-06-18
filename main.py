import json
import sys

from orchestrator import Orchestrator

def main():
    """
    The main entrypoint for the Agentic Pipeline Framework.

    This script acts as a generic runner. It expects a single argument:
    the path to a pipeline configuration JSON file.

    It performs three main actions:
    1. Loads the specified pipeline configuration.
    2. Executes the pipeline using the Orchestrator.
    3. Displays the final, user-defined outputs from the pipeline.
    """
    
    # --- 1. Get and Load Pipeline Configuration ---
    if len(sys.argv) != 2:
        print("Usage: python main.py <path_to_pipeline_config.json>")
        sys.exit(1)
        
    config_path = sys.argv[1]
    
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        print(f"✅ Successfully loaded pipeline configuration from '{config_path}'")
    except FileNotFoundError:
        print(f"❌ Error: Configuration file not found at '{config_path}'.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ Error: The file at '{config_path}' is not valid JSON.")
        sys.exit(1)
        
    # --- 2. Extract Initial Input and Instantiate Orchestrator ---
    initial_input = config.get("initial_input")
    if initial_input is None:
        print("❌ Error: The configuration file must contain an 'initial_input' key.")
        sys.exit(1)

    orchestrator = Orchestrator(config)
    
    # --- 3. Run the Pipeline ---
    final_state = orchestrator.run(initial_input=initial_input)
    
    # --- 4. Extract and Display Final Outputs ---
    final_results = orchestrator.get_final_outputs(final_state)

    print("\n" + "="*50)
    print("                FINAL PIPELINE OUTPUTS")
    print("="*50)

    if not final_results:
        print("No final outputs were defined in the pipeline configuration.")
    else:
        for key, value in final_results.items():
            print(f"\n➡️ {key.replace('_', ' ').title()}:")
            if isinstance(value, list):
                for item in value:
                    print(f"  - {item}")
            elif isinstance(value, str):
                print(f"  {value}")
            else:
                print(f"  {json.dumps(value, indent=2)}")
                
    print("\n" + "="*50)

if __name__ == "__main__":
    main()

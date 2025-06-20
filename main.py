import json
import sys

from orchestrator import Orchestrator
from json_creator import create_and_save_pipeline

RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
BOLD = "\033[1m"



def main():
    """
    The main entrypoint for the Agentic Pipeline Framework.

    This script provides a unified workflow:
    - If a config path is provided, it runs that pipeline.
    - If no path is provided, it guides the user to create a new pipeline.
    
    It then executes the selected pipeline and displays the final results.
    """
    config = None # Initialize config
    config_path = ""
    
    # --- 1. Determine Pipeline Configuration ---
    if len(sys.argv) > 1:
        # Use a provided configuration file
        config_path = sys.argv[1]
        print(f"{YELLOW}▶️  Running pipeline from specified file: '{config_path}' {RESET}")
    else:
        # Guide the user to create a new pipeline
        try:
            config_path = create_and_save_pipeline()
        except (ValueError, RuntimeError):
            print("\nPipeline creation failed. Exiting.")
            sys.exit(1)
            return # Ensure exit

    # --- 2. Load and Validate Configuration ---
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        print(f"{GREEN}✅ Successfully loaded pipeline: '{config.get('pipeline_name', 'N/A')}'{RESET}")
    except FileNotFoundError:
        print(f"{RED}❌ Error: Configuration file not found at '{config_path}'.{RESET}")
        sys.exit(1)
        return # Ensure exit
    except json.JSONDecodeError:
        print(f"{RED}❌ Error: The file at '{config_path}' is not valid JSON.{RESET}")
        sys.exit(1)
        return # Ensure exit
        
    # --- 3. Instantiate Orchestrator and Run Pipeline ---
    orchestrator = Orchestrator(config)
    # The run method now manages its own state, including initial input.
    final_state = orchestrator.run()

    # --- 4. Extract and Display Final Outputs ---
    final_results = orchestrator.get_final_outputs(final_state)

    print(f"""{GREEN}
╭───────────────────────╮
│                       │
│     Final Output:     │
│                       │
╰───────────────────────╯
{RESET}""")

    if not final_results:
        print("No final outputs were defined in the pipeline configuration.")
    else:
        for key, value in final_results.items():
            print(f"\n➡️ {key.replace('_', ' ').title()}:")
            if isinstance(value, list):
                for item in value:
                    print(f"  - {item}")
            elif isinstance(value, str):
                # Nicely format multi-line string outputs
                for line in value.split('\n'):
                    print(f"  {line}")
            else:
                print(f"  {json.dumps(value, indent=2)}")
                
    print("\n" + f"{BLUE}="*50)

if __name__ == "__main__":
    main()
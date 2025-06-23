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


def display_pipeline_flow(config: dict) -> None:
    '''
    Displays a human-readable logical flow of the pipeline based on its configuration.
    '''
    print(f"{BLUE}--- Pipeline Flow ---{RESET}")
    if not config or 'agents' not in config or 'routing' not in config or 'start_agent' not in config:
        print(f"{RED}Invalid or incomplete pipeline configuration provided.{RESET}")
        return

    agents_map = {agent['id']: agent for agent in config.get('agents', [])}
    routing_map = config.get('routing', {})
    current_agent_id = config.get('start_agent')

    if not current_agent_id or current_agent_id not in agents_map:
        print(f"{RED}Start agent '{current_agent_id}' not found in agents configuration.{RESET}")
        return

    visited_agents = set() # To detect potential loops and prevent infinite printing
    step_number = 1

    while current_agent_id and current_agent_id not in visited_agents:
        visited_agents.add(current_agent_id)
        agent_details = agents_map.get(current_agent_id)

        if not agent_details:
            print(f"{RED}Error: Agent '{current_agent_id}' found in routing but not defined in agents list.{RESET}")
            break

        agent_type = agent_details.get('type', 'N/A')
        tool_name = ""
        if agent_type == 'tool_agent':
            tool_name = f", Tool: {agent_details.get('tool_name', 'N/A')}"

        description = agent_details.get('description', 'No description.')

        print(f"{GREEN}{step_number}. Agent: {current_agent_id} (Type: {agent_type}{tool_name}){RESET}")
        print(f"   Description: {description}")

        next_agent_id = routing_map.get(current_agent_id, {}).get('next')

        if next_agent_id:
            print(f"   Next -> {YELLOW}{next_agent_id}{RESET}")
        else:
            print(f"   Next -> {RED}END{RESET}")

        current_agent_id = next_agent_id
        step_number += 1
        print("-" * 20) # Separator for readability

    if current_agent_id and current_agent_id in visited_agents:
        print(f"{YELLOW}Warning: Loop detected or agent '{current_agent_id}' already visited. Flow display terminated.{RESET}")

    if step_number == 1 and not agents_map: # Handles empty agent list specifically
        print(f"{YELLOW}No agents defined in the pipeline.{RESET}")



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

    # --- Pipeline Confirmation ---
    # The display_pipeline_flow function now prints its own title "--- Pipeline Flow ---"
    # so the line print(f"{BLUE}\n--- Pipeline Confirmation ---{RESET}") might be redundant or could be removed.
    # For now, let's keep it to clearly demarcate the start of this section.
    print(f"{BLUE}\n--- Pipeline Confirmation ---{RESET}")
    display_pipeline_flow(config) # Call the function to display the flow

    confirmation = input(f"{BOLD}Do you want to run this pipeline? (yes/no): {RESET}").strip().lower()
    if confirmation != "yes":
        print(f"{RED}Pipeline execution cancelled by user.{RESET}")
        sys.exit(0)
    print(f"{GREEN}User confirmed. Proceeding with pipeline execution...{RESET}")
        
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

def main_cli():
    """
    Command-line interface entry point.
    Parses arguments and calls the main execution logic.
    """
    if len(sys.argv) < 2:
        print(f"{RED}Usage: apf-run <path_to_pipeline_config.json>{RESET}")
        print(f"{YELLOW}Or run 'python main.py' without arguments to enter interactive pipeline creation mode.{RESET}")
        sys.exit(1)

    # The main() function already handles the logic of checking sys.argv
    # So, we can directly call it. The script's behavior when called as `apf-run`
    # will be determined by how `main()` processes `sys.argv`.
    # If `apf-run path/to/config.json` is called, sys.argv will be `['apf-run', 'path/to/config.json']`
    # If `python main.py path/to/config.json` is called, sys.argv will be `['main.py', 'path/to/config.json']`
    # The logic in main() should correctly handle both.
    # For `apf-run` specifically, we want to ensure it only runs if a path is provided.
    # The existing main() function's interactive mode is better suited for `python main.py`.

    # Re-evaluating the entry point:
    # The `main()` function has dual behavior: interactive if no args, direct run if arg is present.
    # For `apf-run`, we strictly want the "direct run" behavior.
    # We can adjust `main_cli` to enforce this or modify `main` to distinguish calls.

    # Let's keep main() as is for `python main.py` behavior (interactive or direct).
    # For `apf-run` (main_cli), we will ensure it only proceeds if a config path is given.

    config_path_arg = sys.argv[1] # sys.argv[0] is the script name 'apf-run'

    # To reuse the main logic, we can simulate the expected sys.argv for main()
    # when called directly with a config file.
    original_sys_argv = sys.argv
    sys.argv = [sys.argv[0], config_path_arg] # Simulate `python main.py <config_path>`

    main() # Call the existing main function

    sys.argv = original_sys_argv # Restore original sys.argv if necessary, though exiting soon

if __name__ == "__main__":
    # This allows running `python main.py` for interactive mode or `python main.py <config>`
    main()
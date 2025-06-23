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



def main(test_mode=False): # Add test_mode parameter
    """
    The main entrypoint for the Agentic Pipeline Framework.

    This script provides a unified workflow:
    - If a config path is provided, it runs that pipeline.
    - If no path is provided, it guides the user to create a new pipeline.
    
    It then executes the selected pipeline and displays the final results.
    """
    # ... existing code ...
    config_path = None
    if len(sys.argv) > 1 and sys.argv[1].endswith(".json"):
        config_path = sys.argv[1]
        print(f"{YELLOW}▶️  Running pipeline from specified file: '{config_path}' {RESET}")
    else:
        # Guide the user to create a new pipeline if not in test_mode and no config path
        if not test_mode: # Slightly adjusted logic: only create if not test mode AND no path
            try:
                config_path = create_and_save_pipeline()
            except (ValueError, RuntimeError): # Keep existing error handling
                print("\nPipeline creation failed. Exiting.")
                sys.exit(1)
                return # Ensure exit
        elif not config_path: # If test_mode and no config_path, it's an error
            print(f"{RED}❌ Error: No pipeline configuration file specified in test mode.{RESET}")
            sys.exit(1)
            return # Ensure exit


    config_data = None # Renamed from 'config' to avoid confusion in this block
    # --- 2. Load and Validate Configuration ---
    if config_path: # Only try to load if config_path is set
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)
            print(f"{GREEN}✅ Successfully loaded pipeline: '{config_data.get('pipeline_name', 'N/A')}'{RESET}")
        except FileNotFoundError:
            print(f"{RED}❌ Error: Configuration file not found at '{config_path}'.{RESET}")
            sys.exit(1)
            return # Ensure exit
        except json.JSONDecodeError:
            print(f"{RED}❌ Error: The file at '{config_path}' is not valid JSON.{RESET}")
            sys.exit(1)
            return # Ensure exit
    elif not test_mode: # If no config_path and not in test_mode, means creation was skipped or failed silently prior (should not happen with current logic)
        print(f"{RED}❌ Error: No pipeline configuration available.{RESET}") # Should ideally be caught by create_and_save_pipeline logic
        sys.exit(1)
        return

    if config_data:
        display_pipeline_flow(config_data)
        
        proceed = "yes" # Default to yes for test_mode
        if not test_mode: # Only ask for confirmation if not in test_mode
            try:
                confirmation = input(f"{BOLD}Do you want to run this pipeline? (yes/no): {RESET}").strip().lower()
                if confirmation not in ['yes', 'y']:
                    print("Pipeline execution cancelled by user.")
                    sys.exit(0)
                # proceed = confirmation # Not really used if 'yes', but good for clarity
            except EOFError: # Handle cases where input is not available (e.g. CI environment)
                print("No input received for confirmation. Assuming 'no'. Pipeline execution cancelled.")
                sys.exit(0)

        if proceed == "yes": # or just check if not exited
            if not test_mode: # Only print if not in test_mode
                print(f"{GREEN}User confirmed. Proceeding with pipeline execution...{RESET}")

            orchestrator = Orchestrator(config_data, test_mode=test_mode) # Add test_mode
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
    is_test_mode = "--test-mode" in sys.argv
    # Remove --test-mode from sys.argv if present, so it doesn't interfere with config path detection
    if is_test_mode:
        sys.argv = [arg for arg in sys.argv if arg != "--test-mode"]
    main(test_mode=is_test_mode) # Pass test_mode to main